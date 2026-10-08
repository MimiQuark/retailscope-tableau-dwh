from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
SQL_DIR = BASE_DIR / "sql"
OUTPUT_DIR = BASE_DIR / "output"
DB_PATH = OUTPUT_DIR / "retail_dwh.sqlite"
SUMMARY_PATH = OUTPUT_DIR / "build_summary.json"


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def load_raw() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    products = pd.read_csv(RAW_DIR / "raw_products.csv", dtype={"StockCode": str})
    customers = pd.read_csv(RAW_DIR / "raw_customers.csv", dtype={"CustomerID": str})
    sales = pd.read_csv(RAW_DIR / "raw_sales.csv", dtype={"InvoiceNo": str, "StockCode": str, "CustomerID": str})
    return products, customers, sales


def prepare_customer_dim(customers: pd.DataFrame, sales: pd.DataFrame) -> pd.DataFrame:
    customers = customers.copy()
    customers["CustomerID"] = customers["CustomerID"].fillna("UNKNOWN").astype(str)
    if "UNKNOWN" not in set(customers["CustomerID"]):
        customers = pd.concat(
            [customers, pd.DataFrame([{"CustomerID": "UNKNOWN", "Region": "未知", "Segment": "未知", "JoinDate": "2023-01-01"}])],
            ignore_index=True,
        )
    customers = customers.drop_duplicates(subset=["CustomerID"], keep="first")
    first_purchase = (
        sales.groupby("CustomerID", dropna=False)["InvoiceDate"].min().rename("FirstPurchaseDate").reset_index()
    )
    dim = customers.merge(first_purchase, on="CustomerID", how="left")
    dim = dim.sort_values("CustomerID").reset_index(drop=True)
    dim.insert(0, "CustomerKey", range(1, len(dim) + 1))
    return dim.rename(
        columns={
            "CustomerID": "CustomerID",
            "Region": "Region",
            "Segment": "Segment",
            "JoinDate": "JoinDate",
            "FirstPurchaseDate": "FirstPurchaseDate",
        }
    )


def prepare_product_dim(products: pd.DataFrame) -> pd.DataFrame:
    products = products.drop_duplicates(subset=["StockCode"], keep="first").copy()
    products["StockCode"] = products["StockCode"].astype(str)
    products = products.sort_values("StockCode").reset_index(drop=True)
    products.insert(0, "ProductKey", range(1, len(products) + 1))
    return products


def build_date_dim(start_date: str, end_date: str) -> pd.DataFrame:
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    dim = pd.DataFrame({"FullDate": dates.strftime("%Y-%m-%d")})
    dim.insert(0, "DateKey", dates.strftime("%Y%m%d").astype(int))
    dim["Year"] = dates.year
    dim["Quarter"] = dates.quarter
    dim["Month"] = dates.month
    dim["MonthName"] = dates.strftime("%m月")
    dim["WeekOfYear"] = dates.isocalendar().week.astype(int).to_numpy()
    dim["DayOfWeek"] = dates.dayofweek + 1
    dim["IsWeekend"] = (dates.dayofweek >= 5).astype(int)
    return dim


def build_fact_sales(sales: pd.DataFrame, dim_customer: pd.DataFrame, dim_product: pd.DataFrame) -> pd.DataFrame:
    fact = sales.copy()
    fact["InvoiceDate"] = pd.to_datetime(fact["InvoiceDate"], errors="coerce")
    fact["CustomerID"] = fact["CustomerID"].fillna("UNKNOWN").astype(str)
    fact["StockCode"] = fact["StockCode"].astype(str)
    fact["Quantity"] = pd.to_numeric(fact["Quantity"], errors="coerce")
    fact["UnitPrice"] = pd.to_numeric(fact["UnitPrice"], errors="coerce")
    fact = fact.dropna(subset=["InvoiceNo", "LineNo", "StockCode", "InvoiceDate", "Quantity", "UnitPrice"])

    customer_map = dim_customer.set_index("CustomerID")["CustomerKey"]
    product_map = dim_product.set_index("StockCode")["ProductKey"]
    product_cost = dim_product.set_index("StockCode")["UnitCost"]

    fact["CustomerKey"] = fact["CustomerID"].map(customer_map).fillna(0).astype(int)
    fact["ProductKey"] = fact["StockCode"].map(product_map).fillna(0).astype(int)
    fact["DateKey"] = fact["InvoiceDate"].dt.strftime("%Y%m%d").astype(int)
    fact["UnitCost"] = fact["StockCode"].map(product_cost).fillna(0.0).astype(float)
    fact["GrossAmount"] = (fact["Quantity"] * fact["UnitPrice"]).round(2)
    fact["CostAmount"] = (fact["Quantity"] * fact["UnitCost"]).round(2)
    fact["GrossProfit"] = (fact["GrossAmount"] - fact["CostAmount"]).round(2)
    fact["IsReturn"] = (fact["Quantity"] < 0).astype(int)
    fact = fact.sort_values(["InvoiceNo", "LineNo"]).reset_index(drop=True)
    fact.insert(0, "SaleKey", range(1, len(fact) + 1))
    return fact[[
        "SaleKey", "InvoiceNo", "LineNo", "DateKey", "CustomerKey", "ProductKey",
        "Quantity", "UnitPrice", "GrossAmount", "CostAmount", "GrossProfit", "IsReturn",
    ]]


def write_table(connection: sqlite3.Connection, table: str, frame: pd.DataFrame):
    frame.to_sql(table, connection, if_exists="append", index=False)


def build_database(rebuild: bool = True) -> dict:
    if DB_PATH.exists() and rebuild:
        DB_PATH.unlink()
    products, customers, sales = load_raw()
    if sales.empty:
        raise ValueError("Raw sales data is empty")

    dim_customer = prepare_customer_dim(customers, sales)
    dim_product = prepare_product_dim(products)
    start_date = pd.to_datetime(sales["InvoiceDate"]).min().date().isoformat()
    end_date = pd.to_datetime(sales["InvoiceDate"]).max().date().isoformat()
    dim_date = build_date_dim(start_date, end_date)
    fact_sales = build_fact_sales(sales, dim_customer, dim_product)

    with connect() as connection:
        connection.executescript((SQL_DIR / "schema_sqlite.sql").read_text(encoding="utf-8"))

        staging_products = products.rename(
            columns={"StockCode": "stock_code", "ProductName": "product_name", "Category": "category", "ListPrice": "list_price", "UnitCost": "unit_cost"}
        )[["stock_code", "product_name", "category", "list_price", "unit_cost"]]
        staging_customers = customers.rename(
            columns={"CustomerID": "customer_id", "Region": "region", "Segment": "segment", "JoinDate": "join_date"}
        )[["customer_id", "region", "segment", "join_date"]]
        staging_sales = sales.rename(
            columns={
                "InvoiceNo": "invoice_no",
                "LineNo": "line_no",
                "StockCode": "stock_code",
                "InvoiceDate": "invoice_datetime",
                "Quantity": "quantity",
                "UnitPrice": "unit_price",
                "CustomerID": "customer_id",
                "Region": "region",
                "Segment": "segment",
            }
        )[["invoice_no", "line_no", "stock_code", "invoice_datetime", "quantity", "unit_price", "customer_id", "region", "segment"]]
        write_table(connection, "stg_products", staging_products)
        write_table(connection, "stg_customers", staging_customers)
        write_table(connection, "stg_sales", staging_sales)

        write_table(connection, "dim_date", dim_date.rename(columns={
            "DateKey": "date_key", "FullDate": "full_date", "Year": "year", "Quarter": "quarter",
            "Month": "month", "MonthName": "month_name", "WeekOfYear": "week_of_year",
            "DayOfWeek": "day_of_week", "IsWeekend": "is_weekend",
        }))
        write_table(connection, "dim_customer", dim_customer.rename(columns={
            "CustomerKey": "customer_key", "CustomerID": "customer_id", "Region": "region",
            "Segment": "segment", "JoinDate": "join_date", "FirstPurchaseDate": "first_purchase_date",
        }))
        write_table(connection, "dim_product", dim_product.rename(columns={
            "ProductKey": "product_key", "StockCode": "stock_code", "ProductName": "product_name",
            "Category": "category", "ListPrice": "list_price", "UnitCost": "unit_cost",
        }))
        write_table(connection, "fact_sales", fact_sales.rename(columns={
            "SaleKey": "sale_key", "InvoiceNo": "invoice_no", "LineNo": "line_no", "DateKey": "date_key",
            "CustomerKey": "customer_key", "ProductKey": "product_key", "Quantity": "quantity",
            "UnitPrice": "unit_price", "GrossAmount": "gross_amount", "CostAmount": "cost_amount",
            "GrossProfit": "gross_profit", "IsReturn": "is_return",
        }))
        connection.executescript((SQL_DIR / "metrics_sqlite.sql").read_text(encoding="utf-8"))
        connection.commit()
        kpi = pd.read_sql_query("SELECT * FROM vw_kpi_summary", connection).iloc[0].to_dict()
        summary = {
            "database": str(DB_PATH),
            "date_range": [start_date, end_date],
            "rows": {
                "dim_date": len(dim_date),
                "dim_customer": len(dim_customer),
                "dim_product": len(dim_product),
                "fact_sales": len(fact_sales),
            },
            "kpi": {key: float(value) if value is not None else None for key, value in kpi.items()},
        }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Build the SQL star schema and metric views.")
    parser.add_argument("--no-rebuild", action="store_true", help="Append to an existing database instead of rebuilding.")
    args = parser.parse_args()
    summary = build_database(rebuild=not args.no_rebuild)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()