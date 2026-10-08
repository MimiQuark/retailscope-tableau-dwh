from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

from build_dwh import DB_PATH, build_database  # noqa: E402


class DataWarehouseIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DB_PATH.exists():
            build_database(rebuild=True)

    def setUp(self):
        self.connection = sqlite3.connect(DB_PATH)
        self.connection.execute("PRAGMA foreign_keys = ON")

    def tearDown(self):
        self.connection.close()

    def scalar(self, query):
        return self.connection.execute(query).fetchone()[0]

    def test_fact_table_has_rows(self):
        self.assertGreater(self.scalar("SELECT COUNT(*) FROM fact_sales"), 100000)

    def test_referential_integrity(self):
        self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_customer c ON c.customer_key=f.customer_key WHERE c.customer_key IS NULL"),
            0,
        )
        self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_product p ON p.product_key=f.product_key WHERE p.product_key IS NULL"),
            0,
        )

    def test_amount_arithmetic(self):
        self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM fact_sales WHERE ABS(gross_amount - ROUND(quantity * unit_price, 2)) > 0.005"),
            0,
        )

    def test_metric_views(self):
        self.assertGreater(self.scalar("SELECT COUNT(*) FROM vw_monthly_kpi"), 24)
        self.assertGreater(self.scalar("SELECT COUNT(*) FROM vw_category_kpi"), 6)
        self.assertGreater(self.scalar("SELECT COUNT(*) FROM vw_customer_rfm"), 100)

    def test_kpi_reconciliation(self):
        fact_gmv = self.scalar("SELECT ROUND(SUM(gross_amount), 2) FROM fact_sales")
        view_gmv = self.scalar("SELECT ROUND(net_gmv, 2) FROM vw_kpi_summary")
        self.assertAlmostEqual(float(fact_gmv), float(view_gmv), places=2)


class TableauArtifactTest(unittest.TestCase):
    def test_tableau_xml_compatibility(self):
        import xml.etree.ElementTree as ET

        twb_path = BASE_DIR / "output" / "tableau" / "RetailSalesDashboard.twb"
        self.assertTrue(twb_path.exists())
        root = ET.parse(twb_path).getroot()
        datasource = root.find("./datasources/datasource")
        self.assertIsNotNone(datasource)
        self.assertEqual(datasource.get("inline"), "true")
        self.assertIsNone(datasource.find("columns"))
        self.assertGreaterEqual(len(datasource.findall("column")), 1)
        self.assertIn("[sum:gross_amount:qk]", twb_path.read_text(encoding="utf-8"))
    def test_twbx_package_members(self):
        import json
        import zipfile

        report_path = BASE_DIR / "output" / "tableau" / "tableau_validation.json"
        twbx_path = BASE_DIR / "output" / "tableau" / "RetailSalesDashboard.twbx"
        self.assertTrue(report_path.exists(), "Run build_tableau_workbook.py first")
        self.assertTrue(twbx_path.exists(), "Tableau package is missing")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(len(report["worksheets"]), 4)
        self.assertEqual(len(report["dashboards"]), 4)
        with zipfile.ZipFile(twbx_path) as archive:
            members = set(archive.namelist())
            self.assertIn("RetailSalesDashboard.twb", members)
            self.assertIn("Data/sales_flat.csv", members)
            self.assertIsNone(archive.testzip())


if __name__ == "__main__":
    unittest.main()