import argparse
import functools
import json
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .core import load_products, report, run


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def demo(db_path, output, browser=False):
    """Demonstra uma queda de preço numa loja local, sem depender de terceiros."""
    with tempfile.TemporaryDirectory() as folder:
        page = Path(folder) / "produto.html"
        handler = functools.partial(QuietHandler, directory=folder)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            product = {"id": "demo-teclado", "name": "Teclado — demonstração fictícia",
                       "url": f"http://127.0.0.1:{server.server_port}/produto.html",
                       "selector": ".preco", "currency": "BRL", "target_price": "150.00"}
            results = []
            for price in ("199,90", "129,90"):
                page.write_text(f'<html><meta charset="utf-8"><h1>Teclado</h1><span class="preco">R$ {price}</span></html>', encoding="utf-8")
                results.extend(run([product], db_path, browser=browser))
            report(db_path, output)
            return results
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


def main():
    parser = argparse.ArgumentParser(description="Monitor de preços — Python, RPA e automação")
    parser.add_argument("command", choices=["run", "demo", "report"])
    parser.add_argument("--config", default="products.json", help="Configuração dos produtos")
    parser.add_argument("--db", default="data/precos.sqlite3", help="Banco SQLite")
    parser.add_argument("--output", default="output", help="Pasta dos relatórios")
    parser.add_argument("--browser", action="store_true", help="Coletar com Chromium/Playwright (RPA)")
    args = parser.parse_args()
    try:
        if args.command == "demo":
            rows = demo(args.db, args.output, browser=args.browser)
        elif args.command == "run":
            rows = run(load_products(args.config), args.db, browser=args.browser)
            report(args.db, args.output)
        else:
            report(args.db, args.output)
            rows = []
        for row in rows:
            price = "indisponível" if row["price_cents"] is None else f"{row['currency']} {row['price_cents'] / 100:.2f}"
            print(f"[{row['status']}] {row['name']}: {price}")
            if row["error"]:
                print(f"  {row['error']}")
        print(f"Relatórios: {Path(args.output).resolve()}")
        raise SystemExit(1 if any(row["status"] == "ERRO" for row in rows) else 0)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Erro: {exc}\n")
