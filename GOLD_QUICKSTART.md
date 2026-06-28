# Gold Layer Quickstart

**Silver → Gold:** Transform clean Silver data into BI-ready analytics datasets for dashboards and BigQuery.

---

## 5-Minute Setup

### Prerequisites

```bash
# Make sure Silver layer is populated
python run_silver_demo.py
```

### 1. Run Gold Demo

```bash
python run_gold_demo.py
```

### 2. Inspect Output

Gold outputs are written under `data/gold/`:

- `data/gold/products_dashboard/products_snapshot.parquet`
- `data/gold/price_comparison/market_prices.parquet`
- `data/gold/market_kpis/daily_kpis.parquet`
- `data/gold/product_intelligence/product_metrics.parquet`
- `data/gold/product_intelligence/category_metrics.parquet`

---

## Tables Generated

### products_snapshot
Current product pricing snapshot for dashboard filters and price comparisons.

### market_prices
Price history table for trend analysis and timeseries charts.

### daily_kpis
Daily market KPI metrics for Looker Studio scorecards.

### product_metrics
Cross-market product insights including cheapest market and price spread.

### category_metrics
Category-level analytics by market.

---

## How to Use in Looker Studio

1. Connect to BigQuery or a Parquet-to-GCS pipeline.
2. Use `collection_date`, `kpi_date`, and `price_date` as report date fields.
3. Use `market`, `category`, `brand`, and `product_name` as dimensions.
4. Use numeric fields like `current_price`, `avg_price`, `price_spread`, and `price_volatility_index` as metrics.

---

## BigQuery Preparation

1. Create dataset: `analytics.supermarket`
2. Load Parquet files directly into BigQuery or via GCS.
3. Partition `products_snapshot` and `daily_kpis` by date fields.
4. Use `market`, `category`, and `ean` as clustering fields.

---

## Notes

- This Gold layer is intentionally simple and portfolio-focused.
- It demonstrates analytics engineering and dashboard-ready dataset design.
- The Gold layer is optimized for BI consumption, not for transactional updates.
