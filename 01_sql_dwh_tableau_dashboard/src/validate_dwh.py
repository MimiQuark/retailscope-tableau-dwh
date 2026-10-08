from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from build_dwh import DB_PATH

BASE_DIR = Path(__file__).resolve().parents[1]
REPORT_PATH = BASE_DIR / "output" / "validation_report.json"


def scalar(connection, query):
    return connection.execute(query).fetchone()[0]


def validate_database(db_path: Path = DB_PATH) -> dict:
    checks = []
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        def add_check(name, actual, expected, passed=None):
            passed = actual == expected if passed is None else passed
            checks.append({"name": name, "actual": actual, "expected": expected, "passed": bool(passed)})

        add_check("fact_sales rows", scalar(connection, "SELECT COUNT(*) FROM fact_sales"), 0, scalar(connection, "SELECT COUNT(*) FROM fact_sales") > 0)
        add_check("orphan date keys", scalar(connection, "SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_date d ON d.date_key=f.date_key WHERE d.date_key IS NULL"), 0)
        add_check("orphan customer keys", scalar(connection, "SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_customer c ON c.customer_key=f.customer_key WHERE c.customer_key IS NULL"), 0)
        add_check("orphan product keys", scalar(connection, "SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_product p ON p.product_key=f.product_key WHERE p.product_key IS NULL"), 0)
        add_check("amount arithmetic errors", scalar(connection, "SELECT COUNT(*) FROM fact_sales WHERE ABS(gross_amount - ROUND(quantity * unit_price, 2)) > 0.005"), 0)
        add_check("profit arithmetic errors", scalar(connection, "SELECT COUNT(*) FROM fact_sales WHERE ABS(gross_profit - ROUND(gross_amount - cost_amount, 2)) > 0.005"), 0)
        add_check("monthly metric rows", scalar(connection, "SELECT COUNT(*) FROM vw_monthly_kpi"), 0, scalar(connection, "SELECT COUNT(*) FROM vw_monthly_kpi") >= 24)
        add_check("category metric rows", scalar(connection, "SELECT COUNT(*) FROM vw_category_kpi"), 0, scalar(connection, "SELECT COUNT(*) FROM vw_category_kpi") >= 6)

        fact_gmv = scalar(connection, "SELECT ROUND(SUM(gross_amount), 2) FROM fact_sales")
        view_gmv = scalar(connection, "SELECT ROUND(net_gmv, 2) FROM vw_kpi_summary")
        add_check("KPI GMV reconciliation", round(fact_gmv, 2), round(view_gmv, 2))

    report = {
        "database": str(db_path),
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    report = validate_database()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()