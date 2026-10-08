from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
TABLEAU_DIR = BASE_DIR / "output" / "tableau"
SOURCE_TWB = TABLEAU_DIR / "RetailSalesDashboard.twb"
OUTPUT_TWB = TABLEAU_DIR / "RetailSalesDashboard-Professional.twb"
OUTPUT_TWBX = TABLEAU_DIR / "RetailSalesDashboard-Professional.twbx"
DATA_DIR = Path(r"C:\Users\27800\Desktop\RetailSalesDashboard_Data")


def specs():
    return {
        "sales_flat": ("Retail Sales", "sales_flat.csv", [("invoice_no", "string", "dimension"), ("line_no", "integer", "dimension"), ("order_date", "date", "dimension"), ("year", "integer", "dimension"), ("quarter", "integer", "dimension"), ("month", "integer", "dimension"), ("year_month", "string", "dimension"), ("customer_id", "string", "dimension"), ("region", "string", "dimension"), ("segment", "string", "dimension"), ("customer_segment", "string", "dimension"), ("rfm_score", "integer", "dimension"), ("stock_code", "string", "dimension"), ("product_name", "string", "dimension"), ("category", "string", "dimension"), ("quantity", "real", "measure"), ("unit_price", "real", "measure"), ("gross_amount", "real", "measure"), ("cost_amount", "real", "measure"), ("gross_profit", "real", "measure"), ("is_return", "boolean", "dimension")]),
        "kpi_summary": ("KPI Summary", "kpi_summary_long.csv", [("metric_group", "string", "dimension"), ("metric_name", "string", "dimension"), ("metric_value", "real", "measure"), ("formatted_value", "string", "dimension"), ("definition", "string", "dimension")]),
        "monthly_kpi": ("Monthly KPI", "monthly_kpi.csv", [("year", "integer", "dimension"), ("month", "integer", "dimension"), ("year_month", "string", "dimension"), ("net_gmv", "real", "measure"), ("gross_profit", "real", "measure"), ("order_count", "integer", "measure"), ("avg_order_value", "real", "measure"), ("mom_rate", "real", "measure"), ("yoy_rate", "real", "measure")]),
        "category_kpi": ("Category KPI", "category_kpi.csv", [("category", "string", "dimension"), ("gross_sales", "real", "measure"), ("net_gmv", "real", "measure"), ("gross_profit", "real", "measure"), ("units_sold", "integer", "measure"), ("order_count", "integer", "measure"), ("gross_margin", "real", "measure"), ("revenue_rank", "integer", "measure")]),
        "region_kpi": ("Region KPI", "region_kpi.csv", [("region", "string", "dimension"), ("gross_sales", "real", "measure"), ("net_gmv", "real", "measure"), ("gross_profit", "real", "measure"), ("order_count", "integer", "measure"), ("active_customers", "integer", "measure"), ("avg_order_value", "real", "measure"), ("revenue_contribution", "real", "measure"), ("revenue_rank", "integer", "measure")]),
        "product_rank": ("Product Rank", "product_rank.csv", [("stock_code", "string", "dimension"), ("product_name", "string", "dimension"), ("category", "string", "dimension"), ("gross_sales", "real", "measure"), ("net_gmv", "real", "measure"), ("gross_profit", "real", "measure"), ("units_sold", "integer", "measure"), ("revenue_rank", "integer", "measure")]),
        "rfm_summary": ("RFM Summary", "rfm_summary.csv", [("customer_segment", "string", "dimension"), ("customers", "integer", "measure"), ("monetary", "real", "measure"), ("avg_recency_days", "real", "measure"), ("avg_frequency", "real", "measure")]),
    }


def internal_name(key):
    return f"textscan.{key}"


def make_datasource(key, spec):
    caption, filename, columns = spec
    ds = ET.Element("datasource", {"caption": caption, "inline": "true", "name": internal_name(key), "version": "18.1"})
    ET.SubElement(ds, "connection", {"class": "textscan", "directory": str(DATA_DIR).replace("\\", "/"), "filename": filename, "password": "", "server": ""})
    for name, datatype, role in columns:
        ET.SubElement(ds, "column", {"name": f"[{name}]", "caption": name, "datatype": datatype, "role": role, "type": "quantitative" if role == "measure" else "nominal"})
    return ds


def make_worksheet(name, ds_key, ds_caption, dimension, measure=None, mark="Bar", text_value=None):
    worksheet = ET.Element("worksheet", {"name": name})
    table = ET.SubElement(worksheet, "table")
    view = ET.SubElement(table, "view")
    ds_container = ET.SubElement(view, "datasources")
    ET.SubElement(ds_container, "datasource", {"caption": ds_caption, "name": internal_name(ds_key)})
    deps = ET.SubElement(view, "datasource-dependencies", {"datasource": internal_name(ds_key)})
    ET.SubElement(deps, "column", {"datatype": "string", "name": f"[{dimension}]", "role": "dimension", "type": "nominal"})
    ET.SubElement(deps, "column-instance", {"column": f"[{dimension}]", "derivation": "None", "name": f"[none:{dimension}:nk]", "pivot": "key", "type": "nominal"})
    if text_value:
        ET.SubElement(deps, "column", {"datatype": "string", "name": f"[{text_value}]", "role": "dimension", "type": "nominal"})
        ET.SubElement(deps, "column-instance", {"column": f"[{text_value}]", "derivation": "None", "name": f"[none:{text_value}:nk]", "pivot": "key", "type": "nominal"})
    else:
        ET.SubElement(deps, "column", {"datatype": "real", "name": f"[{measure}]", "role": "measure", "type": "quantitative"})
        ET.SubElement(deps, "column-instance", {"column": f"[{measure}]", "derivation": "Sum", "name": f"[sum:{measure}:qk]", "pivot": "key", "type": "quantitative"})
    ET.SubElement(view, "aggregation", {"value": "true"})
    ET.SubElement(table, "style")
    panes = ET.SubElement(table, "panes")
    pane = ET.SubElement(panes, "pane", {"selection-relaxation-option": "selection-relaxation-allow"})
    pane_view = ET.SubElement(pane, "view")
    ET.SubElement(pane_view, "breakdown", {"value": "auto"})
    ET.SubElement(pane, "mark", {"class": mark})
    encodings = ET.SubElement(pane, "encodings")
    if text_value:
        ET.SubElement(encodings, "text", {"column": f"[{internal_name(ds_key)}].[none:{text_value}:nk]"})
        ET.SubElement(table, "rows").text = f"[{internal_name(ds_key)}].[none:{dimension}:nk]"
    else:
        if mark == "Bar":
            ET.SubElement(encodings, "color", {"column": f"[{internal_name(ds_key)}].[none:{dimension}:nk]"})
        ET.SubElement(encodings, "text", {"column": f"[{internal_name(ds_key)}].[sum:{measure}:qk]"})
        if mark == "Line":
            ET.SubElement(table, "rows").text = f"[{internal_name(ds_key)}].[sum:{measure}:qk]"
            ET.SubElement(table, "cols").text = f"[{internal_name(ds_key)}].[none:{dimension}:nk]"
        else:
            ET.SubElement(table, "rows").text = f"[{internal_name(ds_key)}].[none:{dimension}:nk]"
            ET.SubElement(table, "cols").text = f"[{internal_name(ds_key)}].[sum:{measure}:qk]"
    return worksheet


def add_style_zone(zone):
    style = ET.SubElement(zone, "zone-style")
    for attr, value in (("border-color", "#d7e1eb"), ("border-style", "solid"), ("border-width", "1"), ("margin", "5")):
        ET.SubElement(style, "format", {"attr": attr, "value": value})


def sheet_zone(name, zone_id, x, y, w, h):
    zone = ET.Element("zone", {"h": str(h), "id": str(zone_id), "name": name, "w": str(w), "x": str(x), "y": str(y)})
    add_style_zone(zone)
    return zone


def make_dashboard(name, sheets, base_id):
    dashboard = ET.Element("dashboard", {"name": name})
    layout = ET.SubElement(dashboard, "layout-options")
    title = ET.SubElement(layout, "title")
    formatted = ET.SubElement(title, "formatted-text")
    run = ET.SubElement(formatted, "run", {"fontalignment": "0", "fontsize": "16"})
    run.text = name
    ET.SubElement(dashboard, "style")
    ET.SubElement(dashboard, "size", {"maxheight": "800", "maxwidth": "1200", "minheight": "800", "minwidth": "1200"})
    ds_container = ET.SubElement(dashboard, "datasources")
    for key in sorted(set(key for _, key in sheets)):
        ET.SubElement(ds_container, "datasource", {"caption": specs()[key][0], "name": internal_name(key)})
    zones = ET.SubElement(dashboard, "zones")
    outer = ET.SubElement(zones, "zone", {"h": "100000", "id": str(base_id), "type-v2": "layout-basic", "w": "100000", "x": "0", "y": "0"})
    if len(sheets) == 2:
        flow = ET.SubElement(outer, "zone", {"h": "98000", "id": str(base_id + 1), "param": "horz", "type-v2": "layout-flow", "w": "99200", "x": "400", "y": "1000"})
        flow.append(sheet_zone(sheets[0][0], base_id + 2, 400, 1000, 49400, 98000))
        flow.append(sheet_zone(sheets[1][0], base_id + 3, 50400, 1000, 49400, 98000))
    else:
        vertical = ET.SubElement(outer, "zone", {"h": "98000", "id": str(base_id + 1), "param": "vert", "type-v2": "layout-flow", "w": "99200", "x": "400", "y": "1000"})
        row1 = ET.SubElement(vertical, "zone", {"h": "48500", "id": str(base_id + 2), "param": "horz", "type-v2": "layout-flow", "w": "99200", "x": "400", "y": "1000"})
        row1.append(sheet_zone(sheets[0][0], base_id + 3, 400, 1000, 49400, 48500))
        row1.append(sheet_zone(sheets[1][0], base_id + 4, 50400, 1000, 49400, 48500))
        vertical.append(sheet_zone(sheets[2][0], base_id + 5, 400, 50500, 99200, 48500))
    return dashboard


def build():
    tree = ET.parse(SOURCE_TWB)
    root = tree.getroot()
    root.set("version", "18.1")
    root.set("original-version", "18.1")
    root.set("source-platform", "win")
    root.set("xmlns:user", "http://www.tableausoftware.com/xml/user")
    for tag in ("worksheets", "dashboards", "windows"):
        old = root.find(tag)
        if old is not None:
            root.remove(old)
    ds_container = root.find("datasources")
    expected_names = {internal_name(key) for key in specs()}
    for node in list(ds_container.findall("datasource")):
        if node.get("name") not in expected_names:
            ds_container.remove(node)
    existing = {node.get("name") for node in ds_container.findall("datasource")}
    for key, spec in specs().items():
        if internal_name(key) not in existing:
            ds_container.append(make_datasource(key, spec))
    worksheets = ET.Element("worksheets")
    definitions = [
        ("01 月度净GMV", "sales_flat", "Retail Sales", "year_month", "gross_amount", "Line", None),
        ("02 品类结构", "sales_flat", "Retail Sales", "category", "gross_amount", "Bar", None),
        ("03 区域贡献", "sales_flat", "Retail Sales", "region", "gross_amount", "Bar", None),
        ("04 客户价值", "sales_flat", "Retail Sales", "customer_segment", "gross_amount", "Bar", None),
        ("05 核心指标卡", "kpi_summary", "KPI Summary", "metric_name", None, "Text", "formatted_value"),
        ("06 月度同比", "monthly_kpi", "Monthly KPI", "year_month", "yoy_rate", "Line", None),
        ("07 品类毛利率", "category_kpi", "Category KPI", "category", "gross_margin", "Bar", None),
        ("08 区域客户数", "region_kpi", "Region KPI", "region", "active_customers", "Bar", None),
        ("09 RFM客户数", "rfm_summary", "RFM Summary", "customer_segment", "customers", "Bar", None),
        ("10 商品Top20", "product_rank", "Product Rank", "product_name", "net_gmv", "Bar", None),
    ]
    for definition in definitions:
        worksheets.append(make_worksheet(*definition))
    root.append(worksheets)
    dashboards = ET.Element("dashboards")
    dashboard_defs = [
        ("01 经营总览", [("05 核心指标卡", "kpi_summary"), ("01 月度净GMV", "sales_flat")], 100),
        ("02 品类与商品", [("02 品类结构", "sales_flat"), ("07 品类毛利率", "category_kpi"), ("10 商品Top20", "product_rank")], 200),
        ("03 区域与客户", [("03 区域贡献", "sales_flat"), ("08 区域客户数", "region_kpi"), ("09 RFM客户数", "rfm_summary")], 300),
        ("04 趋势与客户质量", [("06 月度同比", "monthly_kpi"), ("04 客户价值", "sales_flat"), ("05 核心指标卡", "kpi_summary")], 400),
    ]
    windows = ET.Element("windows", {"source-height": "30"})
    for dashboard_name, sheets, base_id in dashboard_defs:
        dashboards.append(make_dashboard(dashboard_name, sheets, base_id))
        window = ET.SubElement(windows, "window", {"class": "dashboard", "maximized": "true", "name": dashboard_name})
        viewpoints = ET.SubElement(window, "viewpoints")
        for sheet_name, _ in sheets:
            ET.SubElement(viewpoints, "viewpoint", {"name": sheet_name})
        ET.SubElement(window, "active", {"id": "-1"})
        preview = ET.SubElement(window, "device-preview")
        ET.SubElement(preview, "device", {"is-portrait": "true", "name": "Generic Phone", "type": "Phone"})
    root.append(dashboards)
    root.append(windows)
    ET.indent(tree, space="  ")
    tree.write(OUTPUT_TWB, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(OUTPUT_TWBX, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(OUTPUT_TWB, OUTPUT_TWB.name)
    print(OUTPUT_TWB)
    print(OUTPUT_TWBX)


if __name__ == "__main__":
    build()