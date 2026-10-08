from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from build_dwh import DB_PATH, connect

BASE_DIR = Path(__file__).resolve().parents[1]
TABLEAU_DIR = BASE_DIR / "output" / "tableau"
EXPORT_DIR = BASE_DIR / "output" / "exports"
VIEW_EXPORTS = {
    "kpi_summary": "SELECT * FROM vw_kpi_summary",
    "monthly_kpi": "SELECT * FROM vw_monthly_kpi ORDER BY year, month",
    "category_kpi": "SELECT * FROM vw_category_kpi ORDER BY revenue_rank",
    "region_kpi": "SELECT * FROM vw_region_kpi ORDER BY revenue_rank",
    "product_rank": "SELECT * FROM vw_product_rank LIMIT 100",
    "customer_rfm": "SELECT * FROM vw_customer_rfm ORDER BY rfm_score DESC, monetary DESC",
}


def export_dashboard_data():
    TABLEAU_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {}
    with connect(DB_PATH) as connection:
        for name, query in VIEW_EXPORTS.items():
            frame = pd.read_sql_query(query, connection)
            frame.to_csv(EXPORT_DIR / f"{name}.csv", index=False, encoding="utf-8-sig")
            frame.to_csv(TABLEAU_DIR / f"{name}.csv", index=False, encoding="utf-8-sig")
            outputs[name] = len(frame)

        flat = pd.read_sql_query(
            """
            WITH rfm AS (
                SELECT customer_id, customer_segment, rfm_score
                FROM vw_customer_rfm
            )
            SELECT
                f.invoice_no,
                f.line_no,
                d.full_date AS order_date,
                d.year,
                d.quarter,
                d.month,
                d.year || '-' || printf('%02d', d.month) AS year_month,
                c.customer_id,
                c.region,
                c.segment,
                COALESCE(r.customer_segment, '一般客户') AS customer_segment,
                COALESCE(r.rfm_score, 0) AS rfm_score,
                p.stock_code,
                p.product_name,
                p.category,
                f.quantity,
                f.unit_price,
                f.gross_amount,
                f.cost_amount,
                f.gross_profit,
                f.is_return
            FROM fact_sales f
            JOIN dim_date d ON d.date_key = f.date_key
            JOIN dim_customer c ON c.customer_key = f.customer_key
            JOIN dim_product p ON p.product_key = f.product_key
            LEFT JOIN rfm r ON r.customer_id = c.customer_id
            ORDER BY f.date_key, f.invoice_no, f.line_no
            """,
            connection,
        )
        flat.to_csv(TABLEAU_DIR / "sales_flat.csv", index=False, encoding="utf-8-sig")
        flat.to_csv(EXPORT_DIR / "sales_flat.csv", index=False, encoding="utf-8-sig")
        outputs["sales_flat"] = len(flat)

    manifest = {
        "generated_files": sorted(path.name for path in TABLEAU_DIR.glob("*.csv")),
        "row_counts": outputs,
        "notes": "CSV files are Tableau-ready. sales_flat.csv is the self-contained workbook source.",
    }
    (TABLEAU_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest


if __name__ == "__main__":
    export_dashboard_data()