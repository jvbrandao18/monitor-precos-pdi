"""Coleta, persistência e relatórios, sem dependência de interface gráfica."""

import csv
import html
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def price_cents(text, decimal_separator=","):
    """Converte um único preço em centavos sem arredondamento de ponto flutuante."""
    if decimal_separator not in (",", "."):
        raise ValueError("decimal_separator deve ser ',' ou '.'")
    if re.search(r"-\s*\d", text):
        raise ValueError("Preço não pode ser negativo.")
    matches = re.findall(r"\d[\d.,\s]*", text.strip())
    if len(matches) != 1:
        raise ValueError(f"Esperado um único preço, recebido: {text!r}")
    number = re.sub(r"\s", "", matches[0])
    thousands = "." if decimal_separator == "," else ","
    # Rejeita formatos ambíguos ou casas decimais excessivas.
    pattern = rf"(?:\d+|\d{{1,3}}(?:{re.escape(thousands)}\d{{3}})+)(?:{re.escape(decimal_separator)}\d{{1,2}})?"
    if not re.fullmatch(pattern, number):
        raise ValueError(f"Formato de preço inválido: {text!r}")
    try:
        value = Decimal(number.replace(thousands, "").replace(decimal_separator, "."))
        return int(value * 100)
    except InvalidOperation as exc:
        raise ValueError("Preço inválido") from exc


def load_products(path):
    products = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(products, list) or not products:
        raise ValueError("A configuração deve conter uma lista não vazia de produtos.")
    ids = set()
    for item in products:
        if not isinstance(item, dict):
            raise ValueError("Cada produto deve ser um objeto JSON.")
        for key in ("id", "name", "url", "selector", "currency", "target_price"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f"Campo obrigatório inválido: {key}")
        if item["id"] in ids:
            raise ValueError(f"ID duplicado: {item['id']}")
        ids.add(item["id"])
        if urlparse(item["url"]).scheme not in ("http", "https"):
            raise ValueError("Use URLs HTTP ou HTTPS.")
        if not re.fullmatch(r"[A-Z]{3}", item["currency"]):
            raise ValueError("currency deve ser um código como BRL ou GBP.")
        if item.get("decimal_separator", ",") not in (",", "."):
            raise ValueError("decimal_separator deve ser ',' ou '.'")
        price_cents(item["target_price"], ".")
    return products


def collect(item, browser=False):
    if browser:
        # Importação opcional: HTTP não exige instalar um navegador.
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            with playwright.chromium.launch(headless=True) as chromium:
                page = chromium.new_page()
                response = page.goto(item["url"], wait_until="domcontentloaded", timeout=30000)
                if response is None or response.status >= 400:
                    raise ValueError("Falha ao abrir a página no navegador.")
                element = page.locator(item["selector"])
                element.first.wait_for(state="attached", timeout=15000)
                if element.count() != 1:
                    raise ValueError("O seletor deve encontrar exatamente um preço.")
                value = element.inner_text()
    else:
        with requests.Session() as session:
            retry = Retry(total=2, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
            session.mount("https://", HTTPAdapter(max_retries=retry))
            session.mount("http://", HTTPAdapter(max_retries=retry))
            response = session.get(item["url"], timeout=20, headers={"User-Agent": "MonitorPrecosPDI/1.0"})
            response.raise_for_status()
            elements = BeautifulSoup(response.content, "html.parser").select(item["selector"])
            if len(elements) != 1:
                raise ValueError(f"Seletor encontrou {len(elements)} elementos; esperado: 1.")
            value = elements[0].get_text(" ", strip=True)
    return price_cents(value, item.get("decimal_separator", ","))


@contextmanager
def connect(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY, checked_at TEXT NOT NULL, product_id TEXT NOT NULL,
        name TEXT NOT NULL, url TEXT NOT NULL, currency TEXT NOT NULL,
        price_cents INTEGER, target_cents INTEGER NOT NULL,
        status TEXT NOT NULL, error TEXT NOT NULL DEFAULT '')""")
    db.commit()
    try:
        yield db
    finally:
        db.close()


def run(products, db_path, browser=False):
    results = []
    with connect(db_path) as db:
        for item in products:
            row = dict(checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       product_id=item["id"], name=item["name"], url=item["url"],
                       currency=item["currency"], price_cents=None,
                       target_cents=price_cents(item["target_price"], "."), status="OK", error="")
            try:
                row["price_cents"] = collect(item, browser=browser)
                if row["price_cents"] <= row["target_cents"]:
                    row["status"] = "ALERTA"
            except Exception as exc:
                # Uma loja indisponível não impede a coleta dos outros produtos.
                row.update(status="ERRO", error=f"{type(exc).__name__}: {exc}")
            db.execute("""INSERT INTO observations
                (checked_at, product_id, name, url, currency, price_cents, target_cents, status, error)
                VALUES (:checked_at, :product_id, :name, :url, :currency, :price_cents, :target_cents, :status, :error)""", row)
            db.commit()
            results.append(row)
    return results


def report(db_path, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as db:
        rows = [dict(row) for row in db.execute("SELECT * FROM observations ORDER BY id")]
    fields = ["id", "checked_at", "product_id", "name", "url", "currency", "price_cents", "target_cents", "status", "error"]
    with (output / "historico.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        # Evita fórmulas ao abrir textos externos em planilhas.
        for row in rows:
            writer.writerow({k: ("'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@")) else v) for k, v in row.items()})
    def money(value, currency):
        return "—" if value is None else f"{currency} {value / 100:,.2f}"
    table = "".join("<tr>" + "".join(f"<td>{html.escape(str(cell))}</td>" for cell in (
        row["checked_at"], row["name"], money(row["price_cents"], row["currency"]),
        money(row["target_cents"], row["currency"]), row["status"], row["error"])) + "</tr>" for row in reversed(rows))
    page = """<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Monitor de preços • Histórico</title>
<style>body{font:16px system-ui;background:#f3f5fa;color:#19243b;margin:32px auto;max-width:1100px;padding:0 16px}h1{color:#183c76}.table{overflow:auto;background:white;border-radius:12px}table{border-collapse:collapse;width:100%}th,td{padding:14px;text-align:left;border-bottom:1px solid #e4e8ef}th{background:#183c76;color:white}p{line-height:1.6}</style>
<h1>Monitor de preços</h1><p>Histórico da automação em Python. ALERTA indica preço menor ou igual ao alvo.
Horários em UTC. Valores e metas usam a moeda de cada produto.</p><div class="table"><table>
<thead><tr><th>Data</th><th>Produto</th><th>Preço</th><th>Alvo</th><th>Status</th><th>Detalhe</th></tr></thead><tbody>""" + table + "</tbody></table></div></html>"
    (output / "relatorio.html").write_text(page, encoding="utf-8")
    return rows
