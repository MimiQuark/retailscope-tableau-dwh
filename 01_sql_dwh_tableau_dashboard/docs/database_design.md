# 数据仓库设计

## ER 图

```mermaid
erDiagram
    dim_date ||--o{ fact_sales : date_key
    dim_customer ||--o{ fact_sales : customer_key
    dim_product ||--o{ fact_sales : product_key

    dim_date {
        INTEGER date_key PK
        TEXT full_date
        INTEGER year
        INTEGER month
        INTEGER is_weekend
    }
    dim_customer {
        INTEGER customer_key PK
        TEXT customer_id
        TEXT region
        TEXT segment
    }
    dim_product {
        INTEGER product_key PK
        TEXT stock_code
        TEXT product_name
        TEXT category
    }
    fact_sales {
        INTEGER sale_key PK
        TEXT invoice_no
        INTEGER date_key FK
        INTEGER customer_key FK
        INTEGER product_key FK
        INTEGER quantity
        REAL gross_amount
        REAL gross_profit
        INTEGER is_return
    }
```

## 处理步骤

1. CSV 进入 staging 表。
2. 清洗日期、金额、数量和客户标识。
3. 生成 `dim_date`、`dim_customer`、`dim_product`。
4. 将客户、商品和日期映射为代理键。
5. 计算销售金额、成本和毛利。
6. 生成 KPI、趋势、品类、区域、商品排名和 RFM 视图。
7. 导出 Tableau 数据文件并打包工作簿。

## 设计取舍

- 本地默认使用 SQLite，便于无服务器复现；同时保留 MySQL 8 脚本作为生产接入参考。
- 退货通过负数量进入事实表，不使用删除数据的方式修正，确保审计可追溯。
- `customer_key` 保留 `UNKNOWN` 占位，避免未知客户导致事实行丢失。