from __future__ import annotations

import csv
import shutil
from pathlib import Path

import pandas as pd

from build_dwh import DB_PATH, connect

BASE_DIR = Path(__file__).resolve().parents[1]
TABLEAU_DIR = BASE_DIR / "output" / "tableau"
EXTERNAL_DIR = Path(r"C:\Users\27800\Desktop\RetailSalesDashboard_Data")


def money(value):
    return f"¥{value:,.0f}"


def pct(value):
    return f"{value:.1%}"


def main():
    TABLEAU_DIR.mkdir(parents=True, exist_ok=True)
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    with connect(DB_PATH) as connection:
        kpi = pd.read_sql_query("SELECT * FROM vw_kpi_summary", connection).iloc[0]
        monthly = pd.read_sql_query("SELECT * FROM vw_monthly_kpi ORDER BY year, month", connection)
        category = pd.read_sql_query("SELECT * FROM vw_category_kpi ORDER BY revenue_rank", connection)
        region = pd.read_sql_query("SELECT * FROM vw_region_kpi ORDER BY revenue_rank", connection)
        products = pd.read_sql_query("SELECT * FROM vw_product_rank ORDER BY revenue_rank LIMIT 20", connection)
        rfm = pd.read_sql_query(
            """SELECT customer_segment, COUNT(*) AS customers, ROUND(SUM(monetary), 2) AS monetary,
                      ROUND(AVG(recency_days), 1) AS avg_recency_days,
                      ROUND(AVG(frequency), 2) AS avg_frequency
               FROM vw_customer_rfm GROUP BY customer_segment ORDER BY monetary DESC""",
            connection,
        )
        units_sold = int(pd.read_sql_query("SELECT SUM(quantity) AS n FROM fact_sales WHERE is_return = 0", connection).iloc[0]["n"])
        active_customers = int(pd.read_sql_query("SELECT COUNT(DISTINCT customer_key) AS n FROM fact_sales WHERE is_return = 0", connection).iloc[0]["n"])
        gross_margin_rate = float(kpi["gross_profit"]) / float(kpi["net_gmv"])
        avg_units_per_order = units_sold / float(kpi["order_count"])
        avg_monthly_gmv = float(monthly["net_gmv"].mean())
        top_category_share = float(category["net_gmv"].max()) / float(category["net_gmv"].sum())
        top_region_share = float(region["net_gmv"].max()) / float(region["net_gmv"].sum())

    metrics = [
        ("规模", "净 GMV", float(kpi["net_gmv"]), money(float(kpi["net_gmv"])), "含退货冲减"),
        ("规模", "订单量", float(kpi["order_count"]), f"{int(kpi['order_count']):,}", "有效销售订单"),
        ("规模", "客单价", float(kpi["avg_order_value"]), money(float(kpi["avg_order_value"])), "净 GMV / 订单量"),
        ("规模", "销量", float(units_sold), f"{int(units_sold):,}", "有效销售件数"),
        ("盈利", "毛利", float(kpi["gross_profit"]), money(float(kpi["gross_profit"])), "销售收入 - 成本"),
        ("盈利", "毛利率", gross_margin_rate, pct(gross_margin_rate), "毛利 / 净 GMV"),
        ("客户", "活跃客户", float(active_customers), f"{int(active_customers):,}", "有效销售客户"),
        ("客户", "复购客户率", float(kpi["repeat_customer_rate"]), pct(float(kpi["repeat_customer_rate"])), "下单次数大于 1"),
        ("运营", "月均 GMV", avg_monthly_gmv, money(avg_monthly_gmv), "月份平均"),
        ("运营", "单均件数", avg_units_per_order, f"{avg_units_per_order:.2f}", "销量 / 订单量"),
        ("运营", "退货金额率", float(kpi["return_amount_rate"]), pct(float(kpi["return_amount_rate"])), "退货金额 / 销售金额"),
        ("集中度", "Top 品类集中度", top_category_share, pct(top_category_share), "最大品类占比"),
        ("集中度", "Top 区域集中度", top_region_share, pct(top_region_share), "最大区域占比"),
        ("趋势", "最新同比", float(monthly.iloc[-1]["yoy_rate"]), pct(float(monthly.iloc[-1]["yoy_rate"])), "最后一个月同比"),
    ]
    kpi_long = pd.DataFrame(metrics, columns=["metric_group", "metric_name", "metric_value", "formatted_value", "definition"])
    outputs = {
        "sales_flat.csv": TABLEAU_DIR / "sales_flat.csv",
        "kpi_summary_long.csv": kpi_long,
        "monthly_kpi.csv": monthly,
        "category_kpi.csv": category,
        "region_kpi.csv": region,
        "product_rank.csv": products,
        "rfm_summary.csv": rfm,
    }
    for name, source in outputs.items():
        target = EXTERNAL_DIR / name
        if isinstance(source, pd.DataFrame):
            source.to_csv(target, index=False, encoding="utf-8-sig")
            source.to_csv(TABLEAU_DIR / name, index=False, encoding="utf-8-sig")
        else:
            shutil.copy2(source, target)
    print({"external_dir": str(EXTERNAL_DIR), "files": list(outputs), "kpi_rows": len(kpi_long), "rfm_rows": len(rfm)})


if __name__ == "__main__":
    main()