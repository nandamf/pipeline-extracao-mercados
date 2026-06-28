# Gold Layer Architecture

## Overview

The Gold layer is the **analytics-ready** stage of your Data Lake. It consumes clean Silver data and produces optimized datasets specifically designed for:
- BI dashboards (Looker Studio)
- Business intelligence and insights
- KPI tracking
- Price comparison analytics
- Market trend analysis

```
Bronze (Raw) ✅
    ↓
Silver (Clean) ✅
    ↓
Gold (Analytics) ← YOU ARE HERE
    ↓
Looker Studio Dashboard
```

---

## Design Principles

### 1. **BI-Ready Denormalization**
Dimensional models optimized for dashboard queries, not normalized OLTP schemas

### 2. **Pre-Computed KPIs**
Calculate expensive metrics once during ETL, not on every dashboard refresh

### 3. **Portfolio Simple**
Easy to understand, explain, and extend - no complex star schemas or slowly changing dimensions

### 4. **BigQuery Native**
Optimized for BigQuery columnar storage and query engine

### 5. **Query Performance**
Aggregations pre-computed, proper partitioning, minimal joins required

### 6. **Looker Studio Ready**
Compatible data types, clean naming, business-friendly terminology

---

## Data Architecture

### Storage Organization

```
data/
├── bronze/
│   └── market=*/year=*/month=*/day=*/run_id=*/
│
├── silver/
│   ├── market=*/year=*/month=*/products_normalized.parquet
│   ├── marketplace_catalog/ean_master.parquet
│   └── quality_metrics/daily_metrics.parquet
│
└── gold/                           ← NEW
    ├── products_dashboard/         ← Current product prices
    │   ├── products_snapshot.parquet
    │   └── metadata.json
    │
    ├── price_comparison/           ← Price analysis
    │   ├── market_prices.parquet
    │
    ├── market_kpis/                ← Market-level KPIs
    │   ├── daily_kpis.parquet
    │
    ├── product_intelligence/       ← Product-level analytics
    │   ├── product_metrics.parquet
    │   └── category_metrics.parquet
    │
    └── transformation_logs/
        └── gold_run_*.json
```

---

## Analytics Tables

### 1. **products_snapshot** (Fact Table)
Current product data with enriched analytics fields

**Primary Use**: Dashboard filters, price lookups, product listings

```
Columns:
- product_id: Unique key (composite from market + ean + cep)
- market: Source market (atacadao, carrefour, mix_mateus)
- ean: Product EAN-13
- product_name: Normalized product name
- category: Normalized category
- brand: Product brand
- current_price: Latest price observed
- previous_price: Price from previous collection
- unit_price: Price per unit (for comparison)
- price_change_pct: % change from previous
- is_cheapest: Boolean - cheapest in category today?
- volume: Extracted volume (liters, kg, etc)
- collected_at: Latest collection timestamp
- collection_date: Date for partitioning
- market_name: Human-friendly market name
- data_quality_score: 0-100 quality metric
```

**Partitioning**: `collection_date` (DATE)

**Example Query**:
```sql
SELECT market, product_name, current_price, is_cheapest
FROM gold.products_snapshot
WHERE collection_date = CURRENT_DATE()
  AND category = 'Leite e Lácteos'
ORDER BY current_price ASC
```

---

### 2. **market_prices** (Pricing Fact Table)
All price observations for price trend analysis

**Primary Use**: Price history, trend charts, volatility analysis

```
Columns:
- price_id: Unique identifier
- market: Source market
- ean: Product EAN
- product_name: Product name
- price: Observed price
- unit_price: Price per unit
- price_date: Date of observation
- collection_timestamp: Full timestamp
- category: Product category
- price_tier: Bucketed price (cheap/medium/expensive)
- is_promotion: Inferred promotion flag
- volume: Product volume
```

**Partitioning**: `price_date` (DATE)

**Example Query**:
```sql
SELECT 
  price_date,
  market,
  AVG(price) as avg_price,
  MIN(price) as min_price,
  MAX(price) as max_price
FROM gold.market_prices
WHERE category = 'Leite e Lácteos'
  AND price_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) AND CURRENT_DATE()
GROUP BY price_date, market
ORDER BY price_date DESC
```

---

### 3. **daily_kpis** (Time-Series Metrics)
Pre-computed daily metrics by market

**Primary Use**: KPI cards, trend lines, performance monitoring

```
Columns:
- kpi_date: Date
- market: Source market
- total_products: Count of unique products
- avg_price: Average product price
- median_price: Median price
- price_std_dev: Price standard deviation
- cheapest_product_price: Minimum observed price
- most_expensive_product_price: Maximum observed price
- price_volatility_index: (std_dev / median) * 100
- data_completeness: % of products with valid prices
- new_products_count: Products first seen today
- price_change_count: Products with price changes
- avg_price_change_pct: Average daily price change %
- market_name: Human-friendly name
```

**Partitioning**: `kpi_date` (DATE)

**Example Query**:
```sql
SELECT 
  kpi_date,
  market,
  avg_price,
  price_volatility_index,
  data_completeness
FROM gold.daily_kpis
WHERE kpi_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY) AND CURRENT_DATE()
ORDER BY kpi_date DESC, market
```

---

### 4. **product_metrics** (Product-Level Analytics)
Aggregated metrics per product across all markets

**Primary Use**: Product comparison cards, best deals

```
Columns:
- product_id: Composite key (ean + category)
- ean: Product EAN-13
- product_name: Normalized name
- category: Product category
- brand: Brand name
- volume: Product volume/quantity
- markets_selling: Count of markets selling this product
- cheapest_market: Which market has lowest price
- cheapest_price: Lowest price observed
- most_expensive_market: Which market has highest price
- most_expensive_price: Highest price observed
- price_spread: Difference between min-max ($ and %)
- avg_price_across_markets: Average price
- last_collected: Most recent collection date
- days_since_update: Days since last price change
- price_competitiveness_score: 0-100 metric
```

**Partitioning**: None (small dimension table)

**Example Query**:
```sql
SELECT 
  product_name,
  cheapest_market,
  cheapest_price,
  most_expensive_price,
  price_spread,
  price_competitiveness_score
FROM gold.product_metrics
WHERE category = 'Leite e Lácteos'
ORDER BY price_spread DESC
LIMIT 20
```

---

### 5. **category_metrics** (Category-Level Analytics)
Aggregated metrics per category per market

**Primary Use**: Category comparison, market positioning

```
Columns:
- category_id: Composite key
- market: Source market
- category: Product category
- product_count: Number of unique products in category
- avg_price: Average category price
- median_price: Median category price
- price_range_min: Lowest product price
- price_range_max: Highest product price
- price_competitiveness: How competitive are prices
- market_share_value: Est. market value in category
- last_updated: Most recent update
- market_name: Human-friendly market name
```

**Partitioning**: None (dimension table)

**Example Query**:
```sql
SELECT 
  category,
  market,
  product_count,
  avg_price,
  price_competitiveness
FROM gold.category_metrics
ORDER BY category, market
```

---

## KPI Definitions

### Daily KPIs (computed every ingestion cycle)

1. **Average Price**: Mean of all product prices
2. **Median Price**: Median of all product prices
3. **Price Std Dev**: Standard deviation of prices
4. **Price Volatility Index**: (Std Dev / Median) * 100
5. **Data Completeness**: % of products with valid prices
6. **New Products Count**: Products first seen today
7. **Price Change Count**: How many products changed price
8. **Avg Price Change %**: Average daily price shift

### Product KPIs

1. **Markets Selling**: How many markets sell this product
2. **Price Spread %**: ((Max - Min) / Min) * 100
3. **Cheapest Market**: Which market offers best deal
4. **Competitiveness Score**: 0-100 based on price consistency

### Category KPIs

1. **Product Count**: Unique products per category
2. **Avg Price**: Category average
3. **Market Positioning**: Relative to other markets

---

## Transformation Pipeline

### Gold ETL Process

```
1. Load Silver Data
   ├─ Read products_normalized.parquet
   ├─ Read ean_master.parquet
   └─ Read daily_metrics.parquet

2. Compute Product Snapshot
   ├─ Latest prices per market/product
   ├─ Calculate price changes
   ├─ Compute quality metrics
   └─ Write: products_snapshot

3. Build Market Prices Table
   ├─ All price observations
   ├─ Add price tiers
   ├─ Infer promotions
   └─ Write: market_prices

4. Calculate Daily KPIs
   ├─ Aggregate by market
   ├─ Compute volatility metrics
   ├─ Track product changes
   └─ Write: daily_kpis

5. Build Product Metrics
   ├─ Cross-market aggregations
   ├─ Price spread analysis
   ├─ Cheapest/expensive markers
   └─ Write: product_metrics

6. Build Category Metrics
   ├─ Category aggregations by market
   ├─ Category statistics
   └─ Write: category_metrics

7. Log Transformation
   └─ Write metadata.json
```

---

## SQL Patterns for Looker Studio

### Pattern 1: Current Prices by Category

```sql
SELECT
  DATE(collected_at) as collection_date,
  market,
  category,
  product_name,
  current_price,
  is_cheapest,
  ROW_NUMBER() OVER (PARTITION BY category, ean ORDER BY current_price ASC) as price_rank
FROM gold.products_snapshot
WHERE collection_date = CURRENT_DATE()
```

### Pattern 2: Price Trend for Product

```sql
SELECT
  price_date,
  market,
  price,
  LAG(price) OVER (PARTITION BY market ORDER BY price_date) as prev_price,
  ROUND(((price - LAG(price) OVER (PARTITION BY market ORDER BY price_date)) / 
         LAG(price) OVER (PARTITION BY market ORDER BY price_date)) * 100, 2) as price_change_pct
FROM gold.market_prices
WHERE ean = '7891000000000'  -- Specific product
  AND price_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
ORDER BY price_date
```

### Pattern 3: Market Comparison Scorecard

```sql
SELECT
  market,
  market_name,
  kpi_date,
  avg_price,
  price_volatility_index,
  data_completeness,
  new_products_count,
  price_change_count
FROM gold.daily_kpis
WHERE kpi_date = CURRENT_DATE()
ORDER BY market
```

### Pattern 4: Best Deals

```sql
SELECT
  product_name,
  category,
  brand,
  cheapest_market,
  cheapest_price,
  most_expensive_price,
  ROUND(price_spread, 2) as potential_savings_pct,
  last_collected
FROM gold.product_metrics
WHERE price_spread > 10  -- 10% or more difference
ORDER BY price_spread DESC
LIMIT 50
```

---

## Configuration

### Looker Studio Connections

**BigQuery Dataset**: `analytics.supermarket`

**Tables to Connect**:
1. `products_snapshot` - Main fact table
2. `daily_kpis` - Time-series metrics
3. `product_metrics` - Product comparisons
4. `category_metrics` - Category analysis
5. `market_prices` - Price history

**Date Fields**: `collection_date`, `kpi_date`, `price_date`
**Metric Fields**: All numeric columns
**Dimension Fields**: market, category, brand, product_name

---

## Performance Optimization

### Indexing Strategy

```
products_snapshot:
  - (collection_date, market)
  - (category, ean)
  - (is_cheapest)

market_prices:
  - (price_date, market)
  - (ean)

daily_kpis:
  - (kpi_date, market)
```

### Query Optimization Tips

1. **Filter by date early** - Use `collection_date >= '2024-01-01'`
2. **Use snapshots for current data** - Faster than aggregating market_prices
3. **Pre-aggregate KPIs** - Don't compute daily metrics in dashboard
4. **Partition pruning** - BigQuery automatically uses date partitioning

---

## Migration to BigQuery

### Steps

1. Create BigQuery dataset: `CREATE DATASET analytics.supermarket`
2. Create tables from Parquet: `LOAD DATA INTO gold.products_snapshot FROM 'gs://bucket/gold/products_snapshot.parquet'`
3. Set partitioning: `ALTER TABLE gold.products_snapshot PARTITION BY collection_date`
4. Connect Looker Studio to BigQuery dataset
5. Create calculated fields in Looker for additional metrics

### Example BigQuery Setup

```sql
CREATE OR REPLACE TABLE `project.analytics.products_snapshot`
PARTITION BY collection_date
CLUSTER BY market, category
AS
SELECT * FROM `project.raw_gold.products_snapshot`
WHERE collection_date >= '2024-01-01';
```

---

## Portfolio Value

This Gold layer demonstrates:
- ✅ Real-world BI data modeling
- ✅ KPI engineering and metrics design
- ✅ Analytics engineering best practices
- ✅ Looker Studio integration
- ✅ BigQuery optimization
- ✅ Clean, maintainable ETL code
- ✅ Production-ready documentation

Perfect for interviews, case studies, and real deployments!
