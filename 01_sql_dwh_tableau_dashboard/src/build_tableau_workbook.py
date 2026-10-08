from __future__ import annotations

import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
from pytableau.build import DashboardBuilder, DatasourceBuilder, WorksheetBuilder, quick_chart
from pytableau.constants import DataType, Role
from pytableau.core.workbook import Workbook

BASE_DIR = Path(__file__).resolve().parents[1]
TABLEAU_DIR = BASE_DIR / "output" / "tableau"
DATA_DIR = TABLEAU_DIR / "Data"
CSV_NAME = "sales_flat.csv"
CSV_PATH = DATA_DIR / CSV_NAME
TWB_PATH = TABLEAU_DIR / "RetailSalesDashboard.twb"
TWBX_PATH = TABLEAU_DIR / "RetailSalesDashboard.twbx"
REPORT_PATH = TABLEAU_DIR / "tableau_validation.json"
CAPTION = "Retail Sales"

DIMENSIONS = {
    "invoice_no",
    "line_no",
    "order_date",
    "year",
    "quarter",
    "month",
    "year_month",
    "customer_id",
    "region",
    "segment",
    "customer_segment",
    "stock_code",
    "product_name",
    "category",
    "is_return",
}
MEASURES = {"quantity", "unit_price", "gross_amount", "cost_amount", "gross_profit", "rfm_score"}


def prepare_csv():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(TABLEAU_DIR / CSV_NAME, encoding="utf-8-sig")
    frame["order_date"] = pd.to_datetime(frame["order_date"]).dt.strftime("%Y-%m-%d")
    frame.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    return frame


def build_datasource(frame: pd.DataFrame):
    builder = DatasourceBuilder(CAPTION).connection(
        "csv",
        directory="Data",
        filename=CSV_NAME,
    )
    for column in frame.columns:
        name_lower = column.lower()
        if name_lower in DIMENSIONS:
            datatype = DataType.DATE if name_lower == "order_date" else DataType.STRING
            role = Role.DIMENSION
        elif name_lower in {"year", "quarter", "month", "line_no", "rfm_score"}:
            datatype, role = DataType.INTEGER, Role.DIMENSION
        else:
            datatype, role = DataType.REAL, Role.MEASURE
        if name_lower == "is_return":
            datatype, role = DataType.BOOLEAN, Role.DIMENSION
        builder.column(column, datatype, role)
    return builder


def build_workbook(frame: pd.DataFrame):
    datasource = build_datasource(frame)
    workbook = quick_chart(
        caption=CAPTION,
        chart_type="line",
        dimension="year_month",
        measure="gross_amount",
        title="01 月度净GMV",
        datasource_builder=datasource,
    )

    worksheet_specs = [
        ("02 品类结构", "bar", "category", "gross_amount", "category"),
        ("03 区域贡献", "bar", "region", "gross_amount", "region"),
        ("04 客户价值", "bar", "customer_segment", "gross_amount", "customer_segment"),
    ]
    for name, chart_type, dimension, measure, color in worksheet_specs:
        builder = WorksheetBuilder(name)
        builder.datasource(datasource.name)
        builder.mark_type(chart_type)
        builder.rows(dimension)
        builder.columns(f"SUM({measure})")
        builder.color(color)
        builder.label(f"SUM({measure})")
        workbook.add_worksheet(builder)

    dashboard_specs = [
        ("01 经营趋势", "01 月度净GMV", "月度净 GMV 趋势与经营节奏"),
        ("02 品类结构", "02 品类结构", "品类销售贡献与结构分析"),
        ("03 区域贡献", "03 区域贡献", "区域销售贡献与市场对比"),
        ("04 客户价值", "04 客户价值", "RFM 客户分层与消费贡献"),
    ]
    for dashboard_name, worksheet_name, subtitle in dashboard_specs:
        dashboard = (
            DashboardBuilder(dashboard_name, width=1200, height=800)
            .text(subtitle, x=20, y=16, w=1160, h=44, name=f"{dashboard_name}_title")
            .sheet(worksheet_name, x=20, y=72, w=1160, h=704)
        )
        workbook.add_dashboard(dashboard)

    issues = workbook.validate(semantic=False)
    errors = [str(issue) for issue in issues if getattr(issue, "level", "") == "error"]
    if errors:
        raise RuntimeError("; ".join(errors))
    workbook.save_as(TWB_PATH)
    return workbook, issues


def sanitize_twb():
    tree = ET.parse(TWB_PATH)
    root = tree.getroot()
    root.set("original-version", "18.1")
    root.set("version", "18.1")
    root.set("source-platform", "win")
    root.set("xmlns:user", "http://www.tableausoftware.com/xml/user")
    datasource = root.find("./datasources/datasource")
    if datasource is None:
        raise RuntimeError("Tableau datasource is missing")
    datasource.set("inline", "true")
    datasource.set("version", "18.1")
    columns = datasource.find("columns")
    connection = datasource.find("connection")
    if columns is not None:
        insert_at = list(datasource).index(connection) + 1 if connection is not None else 0
        for offset, column in enumerate(list(columns)):
            datasource.insert(insert_at + offset, column)
        datasource.remove(columns)
    ET.indent(tree, space="  ")
    tree.write(TWB_PATH, encoding="utf-8", xml_declaration=True)
    text = TWB_PATH.read_text(encoding="utf-8").replace("[SUM(gross_amount)]", "[sum:gross_amount:qk]")
    TWB_PATH.write_text(text, encoding="utf-8")

def package_twbx():
    with zipfile.ZipFile(TWBX_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(TWB_PATH, TWB_PATH.name)
        archive.write(CSV_PATH, f"Data/{CSV_NAME}")


def inspect_package():
    with zipfile.ZipFile(TWBX_PATH) as archive:
        names = sorted(archive.namelist())
        bad = archive.testzip()
    return {"members": names, "zip_test_result": bad}


def main():
    frame = prepare_csv()
    workbook, issues = build_workbook(frame)
    sanitize_twb()
    issues = Workbook.open(TWB_PATH).validate(semantic=True)
    errors = [str(issue) for issue in issues if getattr(issue, "level", "") == "error"]
    if errors:
        raise RuntimeError("; ".join(errors))
    package_twbx()
    package_report = inspect_package()
    reopened = Workbook.open(TWB_PATH)
    report = {
        "source_rows": len(frame),
        "source_columns": list(frame.columns),
        "worksheets": reopened.worksheets.names,
        "dashboards": reopened.dashboards.names,
        "validation_issue_count": len(issues),
        "validation_issues": [str(issue) for issue in issues],
        "twb": str(TWB_PATH),
        "twbx": str(TWBX_PATH),
        "package": package_report,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()