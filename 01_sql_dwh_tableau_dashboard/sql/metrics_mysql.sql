-- MySQL 8.x metric views. Run after schema_mysql.sql.
DROP VIEW IF EXISTS vw_kpi_summary;
DROP VIEW IF EXISTS vw_monthly_kpi;
DROP VIEW IF EXISTS vw_category_kpi;
DROP VIEW IF EXISTS vw_region_kpi;
DROP VIEW IF EXISTS vw_product_rank;
DROP VIEW IF EXISTS vw_customer_rfm;

CREATE VIEW vw_kpi_summary AS
SELECT
    ROUND((SELECT SUM(gross_amount) FROM fact_sales), 2) AS net_gmv,
    ROUND((SELECT SUM(CASE WHEN is_return = 0 THEN gross_amount ELSE 0 END) FROM fact_sales), 2) AS gross_sales,
    (SELECT COUNT(DISTINCT invoice_no) FROM fact_sales WHERE is_return = 0) AS order_count,
    ROUND(
        (SELECT SUM(gross_amount) FROM fact_sales) /
        NULLIF((SELECT COUNT(DISTINCT invoice_no) FROM fact_sales WHERE is_return = 0), 0),
        2
    ) AS avg_order_value,
    ROUND((SELECT SUM(gross_profit) FROM fact_sales), 2) AS gross_profit,
    ROUND(
        (SELECT SUM(CASE WHEN is_return = 1 THEN ABS(gross_amount) ELSE 0 END) FROM fact_sales) /
        NULLIF((SELECT SUM(CASE WHEN is_return = 0 THEN gross_amount ELSE 0 END) FROM fact_sales), 0),
        4
    ) AS return_amount_rate,
    ROUND(
        (
            SELECT 1.0 * SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) / COUNT(*)
            FROM (
                SELECT customer_key, COUNT(DISTINCT invoice_no) AS order_count
                FROM fact_sales
                WHERE is_return = 0
                GROUP BY customer_key
            ) x
        ),
        4
    ) AS repeat_customer_rate;

CREATE VIEW vw_monthly_kpi AS
WITH monthly AS (
    SELECT
        d.year,
        d.month,
        DATE_FORMAT(d.full_date, '%Y-%m') AS year_month,
        ROUND(SUM(f.gross_amount), 2) AS net_gmv,
        ROUND(SUM(f.gross_profit), 2) AS gross_profit,
        COUNT(DISTINCT CASE WHEN f.is_return = 0 THEN f.invoice_no END) AS order_count,
        ROUND(SUM(f.gross_amount) / NULLIF(COUNT(DISTINCT CASE WHEN f.is_return = 0 THEN f.invoice_no END), 0), 2) AS avg_order_value
    FROM fact_sales f
    JOIN dim_date d ON d.date_key = f.date_key
    GROUP BY d.year, d.month, DATE_FORMAT(d.full_date, '%Y-%m')
)
SELECT
    year,
    month,
    year_month,
    net_gmv,
    gross_profit,
    order_count,
    avg_order_value,
    ROUND((net_gmv - LAG(net_gmv) OVER (ORDER BY year, month)) / NULLIF(LAG(net_gmv) OVER (ORDER BY year, month), 0), 4) AS mom_rate,
    ROUND((net_gmv - LAG(net_gmv, 12) OVER (ORDER BY year, month)) / NULLIF(LAG(net_gmv, 12) OVER (ORDER BY year, month), 0), 4) AS yoy_rate
FROM monthly;

CREATE VIEW vw_category_kpi AS
WITH category AS (
    SELECT
        p.category,
        ROUND(SUM(CASE WHEN f.is_return = 0 THEN f.gross_amount ELSE 0 END), 2) AS gross_sales,
        ROUND(SUM(f.gross_amount), 2) AS net_gmv,
        ROUND(SUM(f.gross_profit), 2) AS gross_profit,
        SUM(CASE WHEN f.is_return = 0 THEN f.quantity ELSE 0 END) AS units_sold,
        COUNT(DISTINCT CASE WHEN f.is_return = 0 THEN f.invoice_no END) AS order_count
    FROM fact_sales f
    JOIN dim_product p ON p.product_key = f.product_key
    GROUP BY p.category
)
SELECT category, gross_sales, net_gmv, gross_profit, units_sold, order_count,
       ROUND(gross_profit / NULLIF(gross_sales, 0), 4) AS gross_margin,
       RANK() OVER (ORDER BY net_gmv DESC) AS revenue_rank
FROM category;

CREATE VIEW vw_region_kpi AS
WITH region AS (
    SELECT
        c.region,
        ROUND(SUM(CASE WHEN f.is_return = 0 THEN f.gross_amount ELSE 0 END), 2) AS gross_sales,
        ROUND(SUM(f.gross_amount), 2) AS net_gmv,
        ROUND(SUM(f.gross_profit), 2) AS gross_profit,
        COUNT(DISTINCT CASE WHEN f.is_return = 0 THEN f.invoice_no END) AS order_count,
        COUNT(DISTINCT f.customer_key) AS active_customers
    FROM fact_sales f
    JOIN dim_customer c ON c.customer_key = f.customer_key
    GROUP BY c.region
)
SELECT region, gross_sales, net_gmv, gross_profit, order_count, active_customers,
       ROUND(net_gmv / NULLIF(order_count, 0), 2) AS avg_order_value,
       ROUND(net_gmv / SUM(net_gmv) OVER (), 4) AS revenue_contribution,
       RANK() OVER (ORDER BY net_gmv DESC) AS revenue_rank
FROM region;

CREATE VIEW vw_product_rank AS
WITH product AS (
    SELECT
        p.stock_code,
        p.product_name,
        p.category,
        ROUND(SUM(CASE WHEN f.is_return = 0 THEN f.gross_amount ELSE 0 END), 2) AS gross_sales,
        ROUND(SUM(f.gross_amount), 2) AS net_gmv,
        ROUND(SUM(f.gross_profit), 2) AS gross_profit,
        SUM(CASE WHEN f.is_return = 0 THEN f.quantity ELSE 0 END) AS units_sold
    FROM fact_sales f
    JOIN dim_product p ON p.product_key = f.product_key
    GROUP BY p.stock_code, p.product_name, p.category
)
SELECT stock_code, product_name, category, gross_sales, net_gmv, gross_profit, units_sold,
       RANK() OVER (ORDER BY net_gmv DESC) AS revenue_rank
FROM product;

CREATE VIEW vw_customer_rfm AS
WITH max_date AS (
    SELECT MAX(d.full_date) AS as_of_date
    FROM fact_sales f
    JOIN dim_date d ON d.date_key = f.date_key
),
customer_metrics AS (
    SELECT
        f.customer_key,
        c.customer_id,
        c.region,
        c.segment,
        DATEDIFF((SELECT as_of_date FROM max_date), MAX(d.full_date)) AS recency_days,
        COUNT(DISTINCT f.invoice_no) AS frequency,
        ROUND(SUM(f.gross_amount), 2) AS monetary
    FROM fact_sales f
    JOIN dim_customer c ON c.customer_key = f.customer_key
    JOIN dim_date d ON d.date_key = f.date_key
    WHERE f.is_return = 0
    GROUP BY f.customer_key, c.customer_id, c.region, c.segment
),
scored AS (
    SELECT *,
           5 - NTILE(4) OVER (ORDER BY recency_days ASC) AS r_score,
           NTILE(4) OVER (ORDER BY frequency ASC, monetary ASC) AS f_score,
           NTILE(4) OVER (ORDER BY monetary ASC, frequency ASC) AS m_score
    FROM customer_metrics
)
SELECT customer_key, customer_id, region, segment, recency_days, frequency, monetary,
       r_score, f_score, m_score, r_score + f_score + m_score AS rfm_score,
       CASE
           WHEN r_score >= 4 AND f_score >= 3 AND m_score >= 3 THEN '高价值客户'
           WHEN r_score >= 3 AND m_score >= 3 THEN '重要保持客户'
           WHEN r_score >= 3 AND f_score <= 2 THEN '新客/潜力客户'
           WHEN r_score <= 2 AND m_score >= 3 THEN '重要挽留客户'
           ELSE '一般客户'
       END AS customer_segment
FROM scored;