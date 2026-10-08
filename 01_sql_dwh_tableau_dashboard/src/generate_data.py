from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"

CATEGORIES = {
    "数码配件": (39, 499),
    "家用电器": (199, 3999),
    "家居用品": (29, 699),
    "办公用品": (9, 399),
    "服饰鞋包": (59, 799),
    "食品饮料": (9, 199),
    "美妆个护": (29, 499),
    "运动户外": (49, 1299),
}
REGIONS = ["华东", "华南", "华北", "华中", "西南", "西北", "东北"]
REGION_WEIGHTS = [30, 24, 15, 12, 10, 5, 4]
SEGMENTS = ["个人客户", "企业客户", "会员客户"]
SEGMENT_WEIGHTS = [62, 16, 22]
MONTH_WEIGHTS = {
    1: 0.94,
    2: 0.70,
    3: 0.93,
    4: 0.96,
    5: 1.05,
    6: 1.10,
    7: 0.98,
    8: 1.00,
    9: 1.08,
    10: 1.10,
    11: 1.38,
    12: 1.32,
}


def weighted_choice(rng: random.Random, values, weights):
    return rng.choices(values, weights=weights, k=1)[0]


def generate_products(rng: random.Random, count: int = 480):
    rows = []
    for idx in range(1, count + 1):
        category = list(CATEGORIES)[(idx - 1) % len(CATEGORIES)]
        low, high = CATEGORIES[category]
        list_price = round(rng.uniform(low, high), 2)
        cost_rate = rng.uniform(0.52, 0.76)
        rows.append(
            {
                "StockCode": f"P{idx:04d}",
                "ProductName": f"{category}-{idx:04d}",
                "Category": category,
                "ListPrice": f"{list_price:.2f}",
                "UnitCost": f"{list_price * cost_rate:.2f}",
            }
        )
    return rows


def generate_customers(rng: random.Random, count: int = 8000):
    start = date(2021, 1, 1)
    rows = []
    for idx in range(1, count + 1):
        region = weighted_choice(rng, REGIONS, REGION_WEIGHTS)
        segment = weighted_choice(rng, SEGMENTS, SEGMENT_WEIGHTS)
        join_date = start + timedelta(days=rng.randint(0, 1700))
        rows.append(
            {
                "CustomerID": f"C{idx:06d}",
                "Region": region,
                "Segment": segment,
                "JoinDate": join_date.isoformat(),
            }
        )
    return rows


def choose_invoice_date(rng: random.Random, start: date, days: int = 1096):
    while True:
        candidate = start + timedelta(days=rng.randrange(days))
        weight = MONTH_WEIGHTS[candidate.month]
        if candidate.weekday() >= 5:
            weight *= 1.12
        if rng.random() < min(1.0, weight / 1.45):
            return candidate


def generate_sales(rng: random.Random, customers, products, order_count: int):
    start = date(2023, 1, 1)
    for order_no in range(1, order_count + 1):
        customer = rng.choice(customers)
        order_date = choose_invoice_date(rng, start)
        line_count = rng.choices([1, 2, 3, 4, 5], weights=[48, 28, 14, 7, 3], k=1)[0]
        invoice_no = f"INV{order_no:07d}"
        for line_no in range(1, line_count + 1):
            product = rng.choice(products)
            list_price = float(product["ListPrice"])
            discount = rng.choices([0, 0.05, 0.10, 0.15, 0.20], weights=[58, 16, 14, 8, 4], k=1)[0]
            unit_price = round(list_price * (1 - discount), 2)
            quantity = rng.choices([1, 2, 3, 4, 5, 6], weights=[42, 26, 14, 9, 6, 3], k=1)[0]
            if rng.random() < 0.042:
                quantity = -rng.randint(1, min(3, quantity))
            yield {
                "InvoiceNo": invoice_no,
                "LineNo": line_no,
                "StockCode": product["StockCode"],
                "InvoiceDate": f"{order_date.isoformat()} {rng.randint(8, 21):02d}:{rng.randint(0, 59):02d}:00",
                "Quantity": quantity,
                "UnitPrice": f"{unit_price:.2f}",
                "CustomerID": customer["CustomerID"],
                "Region": customer["Region"],
                "Segment": customer["Segment"],
            }


def write_csv(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    if not rows:
        raise ValueError(f"No rows generated for {path}")
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description="Generate deterministic synthetic retail data.")
    parser.add_argument("--seed", type=int, default=20261008)
    parser.add_argument("--orders", type=int, default=60000)
    parser.add_argument("--customers", type=int, default=8000)
    parser.add_argument("--products", type=int, default=480)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    products = generate_products(rng, args.products)
    customers = generate_customers(rng, args.customers)
    sales = list(generate_sales(rng, customers, products, args.orders))

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(RAW_DIR / "raw_products.csv", products)
    write_csv(RAW_DIR / "raw_customers.csv", customers)
    write_csv(RAW_DIR / "raw_sales.csv", sales)
    print(f"products={len(products)} customers={len(customers)} sales_lines={len(sales)}")


if __name__ == "__main__":
    main()