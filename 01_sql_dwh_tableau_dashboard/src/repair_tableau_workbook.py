from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
TABLEAU_DIR = BASE / "output" / "tableau"
TWB = TABLEAU_DIR / "RetailSalesDashboard.twb"
TWBX = TABLEAU_DIR / "RetailSalesDashboard.twbx"
CSV = TABLEAU_DIR / "Data" / "sales_flat.csv"
DS_NAME = "csv.retail_sales"
DS_CAPTION = "Retail Sales"

WORKSHEET = """<worksheet name="{name}"><table><view><datasources><datasource caption="{caption}" name="{ds}" /></datasources><datasource-dependencies datasource="{ds}"><column datatype="string" name="[{dimension}]" role="dimension" type="nominal" /><column-instance column="[{dimension}]" derivation="None" name="[none:{dimension}:nk]" pivot="key" type="nominal" /><column datatype="real" name="[gross_amount]" role="measure" type="quantitative" /><column-instance column="[gross_amount]" derivation="Sum" name="[sum:gross_amount:qk]" pivot="key" type="quantitative" /></datasource-dependencies><aggregation value="true" /></view><style /><panes><pane selection-relaxation-option="selection-relaxation-allow"><view><breakdown value="auto" /></view><mark class="{mark}" /><encodings><text column="[{ds}].[sum:gross_amount:qk]" />{color}</encodings></pane></panes><rows>{rows}</rows><cols>{cols}</cols></table></worksheet>"""

DASHBOARD = """<dashboard name="{name}"><style /><size maxheight="800" maxwidth="1200" minheight="800" minwidth="1200" /><datasources><datasource caption="{caption}" name="{ds}" /></datasources><zones><zone h="100000" id="{id1}" type-v2="layout-basic" w="100000" x="0" y="0"><zone h="98000" id="{id2}" name="{name}" w="98400" x="800" y="1000"><zone-style><format attr="border-color" value="#000000" /><format attr="border-style" value="none" /><format attr="border-width" value="0" /><format attr="margin" value="4" /></zone-style></zone></zone></zones></dashboard>"""


def build_worksheet(name: str, dimension: str, mark: str, rows_measure: bool) -> ET.Element:
    if rows_measure:
        rows = f"[{DS_NAME}].[sum:gross_amount:qk]"
        cols = f"[{DS_NAME}].[none:{dimension}:nk]"
    else:
        rows = f"[{DS_NAME}].[none:{dimension}:nk]"
        cols = f"[{DS_NAME}].[sum:gross_amount:qk]"
    color = f'<color column="[{DS_NAME}].[none:{dimension}:nk]" />' if mark == "Bar" else ""
    xml = WORKSHEET.format(
        name=name, caption=DS_CAPTION, ds=DS_NAME, dimension=dimension, mark=mark,
        color=color, rows=rows, cols=cols,
    )
    return ET.fromstring(xml)


def build_dashboard(name: str, number: int) -> ET.Element:
    xml = DASHBOARD.format(name=name, id1=number * 10, id2=number * 10 + 1, caption=DS_CAPTION, ds=DS_NAME)
    return ET.fromstring(xml)


def repair():
    tree = ET.parse(TWB)
    root = tree.getroot()
    root.set("original-version", "18.1")
    root.set("version", "18.1")
    root.set("source-platform", "win")
    root.set("xmlns:user", "http://www.tableausoftware.com/xml/user")
    datasource = root.find("./datasources/datasource")
    datasource.set("inline", "true")
    datasource.set("version", "18.1")
    columns = datasource.find("columns")
    old_connection = datasource.find("connection")
    connection_position = list(datasource).index(old_connection) if old_connection is not None else 0
    if old_connection is not None:
        datasource.remove(old_connection)
    connection = ET.Element("connection", {"class": "federated"})
    named_connections = ET.SubElement(connection, "named-connections")
    named_connection = ET.SubElement(
        named_connections,
        "named-connection",
        {"caption": DS_CAPTION, "name": "hyper.retail_sales"},
    )
    ET.SubElement(
        named_connection,
        "connection",
        {"class": "hyper", "dbname": "Data/retail_sales.hyper"},
    )
    ET.SubElement(
        connection,
        "relation",
        {
            "connection": "hyper.retail_sales",
            "name": DS_CAPTION,
            "table": "[public].[Retail Sales]",
            "type": "table",
        },
    )
    datasource.insert(connection_position, connection)
    if columns is not None:
        position = list(datasource).index(connection) + 1
        for offset, column in enumerate(list(columns)):
            datasource.insert(position + offset, column)
        datasource.remove(columns)
    for tag in ("worksheets", "dashboards"):
        old = root.find(tag)
        if old is not None:
            root.remove(old)

    worksheets = ET.Element("worksheets")
    specs = [
        ("01 月度净GMV", "year_month", "Line", True),
        ("02 品类结构", "category", "Bar", False),
        ("03 区域贡献", "region", "Bar", False),
        ("04 客户价值", "customer_segment", "Bar", False),
    ]
    for name, dimension, mark, rows_measure in specs:
        worksheets.append(build_worksheet(name, dimension, mark, rows_measure))
    root.append(worksheets)

    dashboards = ET.Element("dashboards")
    dashboard_names = ["01 经营趋势", "02 品类分析", "03 区域分析", "04 客户分层"]
    for number, (sheet_name, _, _, _) in enumerate(specs, start=1):
        dashboard = build_dashboard(sheet_name, number)
        dashboard.set("name", dashboard_names[number - 1])
        sheet_zone = dashboard.find("./zones/zone/zone")
        if sheet_zone is not None:
            sheet_zone.set("name", sheet_name)
        dashboards.append(dashboard)
    root.append(dashboards)

    old_windows = root.find("windows")
    if old_windows is not None:
        root.remove(old_windows)
    windows = ET.Element("windows", {"source-height": "30"})
    for dashboard_name, worksheet_name in zip(dashboard_names, [item[0] for item in specs]):
        window = ET.SubElement(windows, "window", {"class": "dashboard", "maximized": "true", "name": dashboard_name})
        viewpoints = ET.SubElement(window, "viewpoints")
        ET.SubElement(viewpoints, "viewpoint", {"name": worksheet_name})
        ET.SubElement(window, "active", {"id": "-1"})
        preview = ET.SubElement(window, "device-preview")
        ET.SubElement(preview, "device", {"is-portrait": "true", "name": "Generic Phone", "type": "Phone"})
    root.append(windows)

    ET.indent(tree, space="  ")
    tree.write(TWB, encoding="utf-8", xml_declaration=True)

    with zipfile.ZipFile(TWBX, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(TWB, TWB.name)
        archive.write(CSV, "Data/sales_flat.csv")


if __name__ == "__main__":
    repair()
    print(TWB)
    print(TWBX)