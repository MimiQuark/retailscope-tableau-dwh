# SQL 数据仓库与 Tableau 经营看板

面向“数据专员 / 数据分析师”岗位的可复现项目。项目使用固定随机种子的脱敏零售数据，完成 Excel/CSV 采集、Python 清洗、SQL 数据仓库建模、经营指标计算、Tableau 工作簿打包和自动验证。

## 项目目标

- 数据工程：生成并清洗约 11 万行销售明细。
- 数据仓库：建立 `dim_date`、`dim_customer`、`dim_product`、`fact_sales` 星型模型。
- 指标分析：GMV、订单量、客单价、毛利、退货率、复购率、环比、同比、品类排名、区域贡献和 RFM。
- 数据可视化：输出 4 个 Tableau 工作表、4 个 Tableau 看板页面及静态预览。
- 质量保障：自动校验主外键、金额公式、指标对账和视图完整性。

## 架构

```text
CSV/Excel
   -> Python 清洗与标准化
   -> SQLite 本地数据仓库 / MySQL 兼容 DDL
   -> dim_date + dim_customer + dim_product + fact_sales
   -> SQL 指标视图
   -> Tableau .twb + 数据源打包 .twbx
   -> 静态 HTML 预览与验证报告
```

## 目录

```text
data/raw/                 源数据 CSV
sql/                      建表、指标和 MySQL 兼容脚本
src/generate_data.py      固定种子数据生成
src/build_dwh.py          清洗、建模和视图构建
src/export_dashboard_data.py
                           导出 Tableau 数据文件
src/build_tableau_workbook.py
                           构建四页 Tableau 工作簿和 .twbx
src/build_preview.py      生成 HTML 看板预览
src/validate_dwh.py       数据仓库质量验证
tests/test_pipeline.py    集成测试
output/                   数据库、CSV、预览和 Tableau 交付物
```

## 运行

推荐使用项目独立依赖目录，不修改全局 Python：

```powershell
$env:PYTHON_EXE = "C:\path\to\python.exe"
.\run.ps1
```

脚本按顺序执行数据生成、仓库构建、Tableau 打包、预览、质量验证和测试。

## 核心指标口径

- 净 GMV：`SUM(gross_amount)`，退货行使用负数冲减。
- 毛销售额：仅统计 `is_return = 0`。
- 客单价：净 GMV / 有效销售订单数。
- 退货金额率：退货金额绝对值 / 毛销售额。
- 复购客户率：有效订单数大于 1 的客户 / 有订单客户。
- RFM：按最近购买、购买频次、消费金额使用四分位打分。

## Tableau 交付物

- `output/tableau/RetailSalesDashboard.twb`
- `output/tableau/RetailSalesDashboard.twbx`
- `output/tableau/sales_flat.csv`
- `output/tableau/monthly_kpi.csv`
- `output/tableau/category_kpi.csv`
- `output/tableau/region_kpi.csv`
- `output/tableau/customer_rfm.csv`

四页看板分别覆盖经营趋势、品类结构、区域贡献和客户价值。`.twbx` 已包含 CSV 数据源，可直接用 Tableau Desktop 或 Tableau Public 打开；由于当前机器只安装了 Tableau 驱动、没有 Tableau Desktop，工作簿通过 XML 与 ZIP 结构验证，最终视觉样式仍需在本机 Tableau 中打开确认。

## 验证

`src/validate_dwh.py` 和 `tests/test_pipeline.py` 会检查：

- 事实表记录数和日期范围。
- 日期、客户、产品主外键完整性。
- 销售额与利润公式。
- 月度、品类、RFM 视图可用性。
- 事实表 GMV 与 KPI 视图对账。
- Tableau 工作簿 XML 和工作表、仪表板结构。

本地验证结果以 `output/validation_report.json` 和 `output/tableau/tableau_validation.json` 为准。