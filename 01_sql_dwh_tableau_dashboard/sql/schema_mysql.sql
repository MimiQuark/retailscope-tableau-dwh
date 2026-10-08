-- MySQL 8.x compatible schema. Run after selecting a target database.
SET FOREIGN_KEY_CHECKS = 0;
DROP VIEW IF EXISTS vw_customer_rfm;
DROP VIEW IF EXISTS vw_product_rank;
DROP VIEW IF EXISTS vw_region_kpi;
DROP VIEW IF EXISTS vw_category_kpi;
DROP VIEW IF EXISTS vw_monthly_kpi;
DROP VIEW IF EXISTS vw_kpi_summary;
DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS stg_sales;
DROP TABLE IF EXISTS stg_customers;
DROP TABLE IF EXISTS stg_products;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE stg_products (
    stock_code VARCHAR(32) PRIMARY KEY,
    product_name VARCHAR(128) NOT NULL,
    category VARCHAR(64) NOT NULL,
    list_price DECIMAL(12,2) NOT NULL,
    unit_cost DECIMAL(12,2) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE stg_customers (
    customer_id VARCHAR(32) PRIMARY KEY,
    region VARCHAR(32) NOT NULL,
    segment VARCHAR(32) NOT NULL,
    join_date DATE NOT NULL
) ENGINE=InnoDB;

CREATE TABLE stg_sales (
    invoice_no VARCHAR(32) NOT NULL,
    line_no INT NOT NULL,
    stock_code VARCHAR(32) NOT NULL,
    invoice_datetime DATETIME NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(12,2) NOT NULL,
    customer_id VARCHAR(32) NOT NULL,
    region VARCHAR(32),
    segment VARCHAR(32),
    PRIMARY KEY (invoice_no, line_no)
) ENGINE=InnoDB;

CREATE TABLE dim_date (
    date_key INT PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    year INT NOT NULL,
    quarter INT NOT NULL,
    month INT NOT NULL,
    month_name VARCHAR(16) NOT NULL,
    week_of_year INT NOT NULL,
    day_of_week INT NOT NULL,
    is_weekend TINYINT NOT NULL
) ENGINE=InnoDB;

CREATE TABLE dim_customer (
    customer_key INT PRIMARY KEY,
    customer_id VARCHAR(32) NOT NULL UNIQUE,
    region VARCHAR(32) NOT NULL,
    segment VARCHAR(32) NOT NULL,
    join_date DATE NOT NULL,
    first_purchase_date DATE NULL
) ENGINE=InnoDB;

CREATE TABLE dim_product (
    product_key INT PRIMARY KEY,
    stock_code VARCHAR(32) NOT NULL UNIQUE,
    product_name VARCHAR(128) NOT NULL,
    category VARCHAR(64) NOT NULL,
    list_price DECIMAL(12,2) NOT NULL,
    unit_cost DECIMAL(12,2) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE fact_sales (
    sale_key BIGINT PRIMARY KEY,
    invoice_no VARCHAR(32) NOT NULL,
    line_no INT NOT NULL,
    date_key INT NOT NULL,
    customer_key INT NOT NULL,
    product_key INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(12,2) NOT NULL,
    gross_amount DECIMAL(14,2) NOT NULL,
    cost_amount DECIMAL(14,2) NOT NULL,
    gross_profit DECIMAL(14,2) NOT NULL,
    is_return TINYINT NOT NULL,
    UNIQUE KEY uq_fact_invoice_line (invoice_no, line_no),
    KEY idx_fact_date (date_key),
    KEY idx_fact_customer (customer_key),
    KEY idx_fact_product (product_key),
    CONSTRAINT fk_fact_date FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
    CONSTRAINT fk_fact_customer FOREIGN KEY (customer_key) REFERENCES dim_customer(customer_key),
    CONSTRAINT fk_fact_product FOREIGN KEY (product_key) REFERENCES dim_product(product_key)
) ENGINE=InnoDB;