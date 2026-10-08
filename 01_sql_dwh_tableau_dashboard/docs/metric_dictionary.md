# 指标字典

| 指标 | 英文/字段 | 口径 | 数据源 |
|---|---|---|---|
| 净 GMV | `net_gmv` | `SUM(gross_amount)`，含退货负向冲减 | `fact_sales` |
| 毛销售额 | `gross_sales` | 仅统计 `is_return = 0` 的销售额 | `fact_sales` |
| 订单量 | `order_count` | 有效销售订单去重数 | `fact_sales.invoice_no` |
| 客单价 | `avg_order_value` | 净 GMV / 有效订单量 | KPI 视图 |
| 毛利 | `gross_profit` | 销售收入 - 销售成本 | `fact_sales` |
| 退货金额率 | `return_amount_rate` | 退货金额绝对值 / 毛销售额 | `fact_sales` |
| 复购客户率 | `repeat_customer_rate` | 有效订单数大于 1 的客户 / 有订单客户 | `fact_sales` |
| 环比 | `mom_rate` | 本月净 GMV / 上月净 GMV - 1 | `vw_monthly_kpi` |
| 同比 | `yoy_rate` | 本月净 GMV / 去年同月净 GMV - 1 | `vw_monthly_kpi` |
| 区域贡献 | `revenue_contribution` | 区域净 GMV / 全部净 GMV | `vw_region_kpi` |
| RFM 分层 | `customer_segment` | R/F/M 四分位评分后按规则分层 | `vw_customer_rfm` |

## 数据粒度

- `fact_sales`：一行代表一张订单中的一个商品行。
- `dim_date`：一行代表一个自然日。
- `dim_customer`：一行代表一个客户。
- `dim_product`：一行代表一个商品。