PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS vw_kpi_summary;
DROP VIEW IF EXISTS vw_monthly_kpi;
DROP VIEW IF EXISTS vw_category_kpi;
DROP VIEW IF EXISTS vw_region_kpi;
DROP VIEW IF EXISTS vw_product_rank;
DROP VIEW IF EXISTS vw_customer_rfm;

DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS stg_sales;
DROP TABLE IF EXISTS stg_customers;
DROP TABLE IF EXISTS stg_products;

CREATE TABLE stg_products (
    stock_code TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    list_price REAL NOT NULL CHECK (list_price >= 0),
    unit_cost REAL NOT NULL CHECK (unit_cost >= 0)
);

CREATE TABLE stg_customers (
    customer_id TEXT PRIMARY KEY,
    region TEXT NOT NULL,
    segment TEXT NOT NULL,
    join_date TEXT NOT NULL
);

CREATE TABLE stg_sales (
    invoice_no TEXT NOT NULL,
    line_no INTEGER NOT NULL,
    stock_code TEXT NOT NULL,
    invoice_datetime TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    customer_id TEXT NOT NULL,
    region TEXT NOT NULL,
    segment TEXT NOT NULL,
    PRIMARY KEY (invoice_no, line_no)
);

CREATE TABLE dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date TEXT NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    week_of_year INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    is_weekend INTEGER NOT NULL
);

CREATE TABLE dim_customer (
    customer_key INTEGER PRIMARY KEY,
    customer_id TEXT NOT NULL UNIQUE,
    region TEXT NOT NULL,
    segment TEXT NOT NULL,
    join_date TEXT NOT NULL,
    first_purchase_date TEXT
);

CREATE TABLE dim_product (
    product_key INTEGER PRIMARY KEY,
    stock_code TEXT NOT NULL UNIQUE,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    list_price REAL NOT NULL,
    unit_cost REAL NOT NULL
);

CREATE TABLE fact_sales (
    sale_key INTEGER PRIMARY KEY,
    invoice_no TEXT NOT NULL,
    line_no INTEGER NOT NULL,
    date_key INTEGER NOT NULL,
    customer_key INTEGER NOT NULL,
    product_key INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    gross_amount REAL NOT NULL,
    cost_amount REAL NOT NULL,
    gross_profit REAL NOT NULL,
    is_return INTEGER NOT NULL CHECK (is_return IN (0, 1)),
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
    FOREIGN KEY (customer_key) REFERENCES dim_customer(customer_key),
    FOREIGN KEY (product_key) REFERENCES dim_product(product_key),
    UNIQUE (invoice_no, line_no)
);

CREATE INDEX idx_fact_sales_date ON fact_sales(date_key);
CREATE INDEX idx_fact_sales_customer ON fact_sales(customer_key);
CREATE INDEX idx_fact_sales_product ON fact_sales(product_key);
CREATE INDEX idx_fact_sales_invoice ON fact_sales(invoice_no);