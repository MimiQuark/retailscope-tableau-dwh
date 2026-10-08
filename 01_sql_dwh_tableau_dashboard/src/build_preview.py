from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd

from build_dwh import DB_PATH, connect

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_PATH = BASE_DIR / "output" / "dashboard_preview.html"


def money(value):
    return f"¥{value:,.0f}"


def pct(value):
    if value is None or pd.isna(value):
        return "-"
    return f"{value:.1%}"


def bar_rows(frame, label_col, value_col, limit=10, formatter=money):
    frame = frame.head(limit)
    max_value = max(float(frame[value_col].max()), 1.0)
    rows = []
    for _, row in frame.iterrows():
        width = max(2, int(float(row[value_col]) / max_value * 100))
        rows.append(
            "<div class='bar-row'>"
            f"<span class='bar-label'>{html.escape(str(row[label_col]))}</span>"
            f"<span class='bar-track'><span class='bar-fill' style='width:{width}%'></span></span>"
            f"<span class='bar-value'>{formatter(float(row[value_col]))}</span>"
            "</div>"
        )
    return "".join(rows)


def metric_card(label, value, note=""):
    return f"<div class='metric'><div class='metric-label'>{html.escape(label)}</div><div class='metric-value'>{value}</div><div class='metric-note'>{html.escape(note)}</div></div>"


def build_preview():
    with connect(DB_PATH) as connection:
        kpi = pd.read_sql_query("SELECT * FROM vw_kpi_summary", connection).iloc[0]
        monthly = pd.read_sql_query("SELECT * FROM vw_monthly_kpi ORDER BY year, month", connection)
        category = pd.read_sql_query("SELECT * FROM vw_category_kpi ORDER BY revenue_rank", connection)
        region = pd.read_sql_query("SELECT * FROM vw_region_kpi ORDER BY revenue_rank", connection)
        products = pd.read_sql_query("SELECT * FROM vw_product_rank ORDER BY revenue_rank LIMIT 10", connection)
        rfm = pd.read_sql_query(
            "SELECT customer_segment, COUNT(*) AS customers, ROUND(SUM(monetary), 2) AS monetary FROM vw_customer_rfm GROUP BY customer_segment ORDER BY monetary DESC",
            connection,
        )
        active_customers = int(pd.read_sql_query("SELECT COUNT(DISTINCT customer_key) AS n FROM fact_sales WHERE is_return = 0", connection).iloc[0]["n"])
        units_sold = int(pd.read_sql_query("SELECT SUM(quantity) AS n FROM fact_sales WHERE is_return = 0", connection).iloc[0]["n"])

    cards = "".join([
        metric_card("净 GMV", money(float(kpi["net_gmv"])), "含退货冲减"),
        metric_card("订单量", f"{int(kpi['order_count']):,}", "有效销售订单"),
        metric_card("客单价", money(float(kpi["avg_order_value"])), "净 GMV / 订单量"),
        metric_card("毛利", money(float(kpi["gross_profit"])), "销售收入 - 成本"),
        metric_card("毛利率", pct(float(kpi["gross_profit"]) / float(kpi["net_gmv"])), "毛利 / 净 GMV"),
        metric_card("活跃客户", f"{active_customers:,}", "有效销售客户"),
        metric_card("销量", f"{units_sold:,}", "有效销售件数"),
        metric_card("单均件数", f"{units_sold / float(kpi['order_count']):.2f}", "销量 / 订单量"),
        metric_card("月均 GMV", money(float(monthly["net_gmv"].mean())), "36 个月平均"),
        metric_card("退货金额率", pct(float(kpi["return_amount_rate"])), "退货金额 / 销售金额"),
        metric_card("复购客户率", pct(float(kpi["repeat_customer_rate"])), "下单次数大于 1"),
        metric_card("Top 品类集中度", pct(float(category["net_gmv"].max()) / float(category["net_gmv"].sum())), "最大品类销售额占比"),
        metric_card("Top 区域集中度", pct(float(region["net_gmv"].max()) / float(region["net_gmv"].sum())), "最大区域销售额占比"),
        metric_card("最新同比", pct(monthly.iloc[-1]["yoy_rate"]), "最后一个月同比"),
    ])

    monthly_rows = monthly.tail(18).copy()
    max_gmv = max(float(monthly_rows["net_gmv"].max()), 1.0)
    trend_svg = []
    width, height = 1000, 260
    points = []
    for idx, row in monthly_rows.reset_index(drop=True).iterrows():
        x = 36 + idx * ((width - 72) / max(1, len(monthly_rows) - 1))
        y = height - 32 - (float(row["net_gmv"]) / max_gmv * (height - 72))
        points.append(f"{x:.1f},{y:.1f}")
    trend_svg.append(f"<svg viewBox='0 0 {width} {height}' role='img' aria-label='月度净GMV趋势'>")
    trend_svg.append("<line x1='36' y1='228' x2='964' y2='228' stroke='#cbd5e1' />")
    trend_svg.append(f"<polyline points='{' '.join(points)}' fill='none' stroke='#1f4e79' stroke-width='4' />")
    for idx, row in monthly_rows.reset_index(drop=True).iterrows():
        x = 36 + idx * ((width - 72) / max(1, len(monthly_rows) - 1))
        y = height - 32 - (float(row["net_gmv"]) / max_gmv * (height - 72))
        trend_svg.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='4' fill='#1f4e79'><title>{row['year_month']}: {money(float(row['net_gmv']))}</title></circle>")
    trend_svg.append("</svg>")
    trend_svg = "".join(trend_svg)

    category_table = "".join(
        "<tr>"
        f"<td>{html.escape(str(row['category']))}</td>"
        f"<td>{money(float(row['net_gmv']))}</td>"
        f"<td>{money(float(row['gross_profit']))}</td>"
        f"<td>{int(row['units_sold']):,}</td>"
        f"<td>{pct(float(row['gross_margin']))}</td>"
        "</tr>"
        for _, row in category.iterrows()
    )
    region_table = "".join(
        "<tr>"
        f"<td>{html.escape(str(row['region']))}</td>"
        f"<td>{money(float(row['net_gmv']))}</td>"
        f"<td>{int(row['order_count']):,}</td>"
        f"<td>{money(float(row['avg_order_value']))}</td>"
        f"<td>{int(row['active_customers']):,}</td>"
        f"<td>{pct(float(row['revenue_contribution']))}</td>"
        "</tr>"
        for _, row in region.iterrows()
    )
    rfm_table = "".join(
        "<tr>"
        f"<td>{html.escape(str(row['customer_segment']))}</td>"
        f"<td>{int(row['customers']):,}</td>"
        f"<td>{money(float(row['monetary']))}</td>"
        "</tr>"
        for _, row in rfm.iterrows()
    )

    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SQL 数据仓库与经营看板预览</title>
<style>
:root {{ --navy:#1f4e79; --blue:#2f80ed; --ink:#17212b; --muted:#64748b; --line:#dbe4ee; --bg:#f5f8fb; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:14px/1.5 "Microsoft YaHei",Arial,sans-serif; }}
main {{ max-width:1180px; margin:0 auto; padding:32px 24px 56px; }}
header {{ display:flex; justify-content:space-between; gap:24px; align-items:flex-end; margin-bottom:24px; }}
h1 {{ margin:0; color:var(--navy); font-size:30px; }}
.subtitle {{ color:var(--muted); margin-top:6px; }}
.badge {{ padding:8px 12px; border:1px solid var(--line); background:white; border-radius:999px; color:var(--navy); }}
.grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:18px; }}
.metric,.panel {{ background:white; border:1px solid var(--line); border-radius:14px; box-shadow:0 6px 18px rgba(31,78,121,.06); }}
.metric {{ padding:15px; }}
.metric-label {{ color:var(--muted); }} .metric-value {{ font-size:22px; font-weight:700; margin:5px 0; }} .metric-note {{ color:var(--muted); font-size:12px; }}
.two {{ display:grid; grid-template-columns:1.05fr .95fr; gap:18px; }}
.panel {{ padding:20px; margin-bottom:18px; }}
.panel h2 {{ margin:0 0 16px; font-size:18px; color:var(--navy); }}
.bar-row {{ display:grid; grid-template-columns:150px 1fr 94px; align-items:center; gap:10px; margin:9px 0; }}
.bar-label {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.bar-track {{ height:10px; background:#e9f0f7; border-radius:8px; overflow:hidden; }}
.bar-fill {{ display:block; height:100%; background:linear-gradient(90deg,var(--navy),var(--blue)); border-radius:8px; }}
.bar-value {{ text-align:right; font-variant-numeric:tabular-nums; }}
table {{ width:100%; border-collapse:collapse; }}
th,td {{ padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; }}
th {{ color:var(--navy); background:#f8fbfe; }}
footer {{ color:var(--muted); text-align:center; margin-top:28px; }}
@media print {{
  @page {{ size: A4 landscape; margin: 8mm; }}
  body {{ background: #ffffff; }}
  main {{ max-width: none; padding: 0; }}
  .metric, .panel {{ box-shadow: none; }}
  .panel {{ break-inside: avoid; }}
}}
@media (max-width:850px) {{ .grid,.two {{ grid-template-columns:1fr; }} header {{ display:block; }} .badge {{ display:inline-block; margin-top:14px; }} }}
</style>
</head>
<body><main>
<header><div><h1>SQL 数据仓库与经营看板</h1><div class="subtitle">脱敏零售销售数据 · 星型模型 · 可复现分析结果</div></div><div class="badge">Tableau-ready · 4 个分析主题</div></header>
<section class="grid">{cards}</section>
<section class="panel"><h2>01 经营趋势｜月度净 GMV</h2>{trend_svg}</section>
<section class="two">
  <div class="panel"><h2>02 品类结构</h2>{bar_rows(category, 'category', 'net_gmv', 8)}</div>
  <div class="panel"><h2>03 区域贡献</h2>{bar_rows(region, 'region', 'net_gmv', 7)}</div>
</section>
<section class="two">
  <div class="panel"><h2>04 商品排名｜Top 10</h2>{bar_rows(products, 'product_name', 'net_gmv', 10)}</div>
  <div class="panel"><h2>客户分层｜RFM</h2><table><thead><tr><th>客户分层</th><th>客户数</th><th>消费金额</th></tr></thead><tbody>{rfm_table}</tbody></table></div>
</section>
<section class="two">
  <div class="panel"><h2>05 品类经营明细</h2><table><thead><tr><th>品类</th><th>净 GMV</th><th>毛利</th><th>销量</th><th>毛利率</th></tr></thead><tbody>{category_table}</tbody></table></div>
  <div class="panel"><h2>06 区域经营明细</h2><table><thead><tr><th>区域</th><th>净 GMV</th><th>订单量</th><th>客单价</th><th>客户数</th><th>贡献</th></tr></thead><tbody>{region_table}</tbody></table></div>
</section>
<footer>数据为固定随机种子生成的脱敏模拟数据，不代表真实企业。生成时间：2026-10-08。</footer>
</main></body></html>"""
    OUTPUT_PATH.write_text(html_text, encoding="utf-8")
    print(str(OUTPUT_PATH))
    return OUTPUT_PATH


if __name__ == "__main__":
    build_preview()