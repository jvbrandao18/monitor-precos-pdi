import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from monitor_precos.cli import demo
from monitor_precos.core import connect, load_products, price_cents, report, run


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.db = self.root / "history.sqlite3"

    def test_prices_and_invalid_values(self):
        for text, separator, expected in [("R$ 1.299,90", ",", 129990), ("£51.77", ".", 5177), ("0,00", ",", 0), ("1,299.90", ".", 129990)]:
            with self.subTest(text=text):
                self.assertEqual(price_cents(text, separator), expected)
        for text in ["indisponível", "R$ 10,00 ou R$ 20,00", "12,345", "1.29,90", "R$ -10,00"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                price_cents(text)

    def test_demo_collects_http_history_and_alert(self):
        rows = demo(self.db, self.root / "output")
        self.assertEqual([row["status"] for row in rows], ["OK", "ALERTA"])
        self.assertEqual([row["price_cents"] for row in rows], [19990, 12990])
        with connect(self.db) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 2)
        self.assertIn("129.90", (self.root / "output/relatorio.html").read_text())
        self.assertIn("ALERTA", (self.root / "output/historico.csv").read_text(encoding="utf-8-sig"))
        demo(self.db, self.root / "output")
        self.assertEqual(len(report(self.db, self.root / "output")), 4)

    def test_failure_does_not_stop_next_product_and_target_is_inclusive(self):
        products = [dict(id=str(i), name="Produto", url="https://example.com", currency="BRL", target_price="10.00") for i in range(2)]
        with patch("monitor_precos.core.collect", side_effect=[ValueError("sem preço"), 1000]):
            rows = run(products, self.db)
        self.assertEqual([row["status"] for row in rows], ["ERRO", "ALERTA"])
        self.assertIsNone(rows[0]["price_cents"])
        self.assertIn("sem preço", rows[0]["error"])

    def test_config_rejects_duplicate_ids(self):
        product = dict(id="a", name="A", url="https://example.com", selector=".price", currency="BRL", target_price="10.00")
        path = self.root / "products.json"
        path.write_text(json.dumps([product, product]))
        with self.assertRaisesRegex(ValueError, "duplicado"):
            load_products(path)

    def test_reports_escape_html_and_spreadsheet_formulas(self):
        product = dict(id="a", name='=SUM(1)<script>alert(1)</script>', url="https://example.com", currency="BRL", target_price="10.00")
        with patch("monitor_precos.core.collect", return_value=500):
            run([product], self.db)
        report(self.db, self.root)
        self.assertNotIn("<script>", (self.root / "relatorio.html").read_text())
        self.assertIn("'=SUM", (self.root / "historico.csv").read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
