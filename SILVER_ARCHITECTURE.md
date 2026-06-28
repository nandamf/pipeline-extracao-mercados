# Silver Layer Architecture

## Overview

The Silver layer is the **transformation and normalization** stage of your Data Lake. It consumes raw Bronze data and produces analytics-ready datasets through:
- Data cleaning & normalization
- Duplicate removal
- Schema standardization
- Quality validation
- Enrichment

```
Bronze (Raw)
    ↓
Silver (Clean) ← YOU ARE HERE
    ↓
Gold (Analytics)
```

---

## Design Principles

### 1. **Data Cleaning**
Remove duplicates, handle nulls, standardize formats

### 2. **Normalization**
Standardize all fields: names, prices, units, categories, brands

### 3. **Quality First**
Validate every field, track quality metrics, flag issues

### 4. **Traceability**
Keep lineage: map Silver record → Bronze source run

### 5. **Immutability**
Silver data is computed from Bronze, never updated

### 6. **Performance**
Optimize for analytics: denormalization, indexing, clustering

---

## Folder Structure

### Storage Organization

```
data/
├── bronze/
│   └── market=*/year=*/month=*/day=*/run_id=*/
│       ├── data_batch.parquet
│       ├── metadata.json
│       └── _SUCCESS
│
├── silver/                          ← NEW
│   ├── market=*/
│   │   ├── year=*/
│   │   │   ├── month=*/
│   │   │   │   ├── products_normalized.parquet
│   │   │   │   ├── transformation_metadata.json
│   │   │   │   └── _SUCCESS
│   │   │   └── year_summary.parquet
│   │   └── deduplication_index.parquet
│   │
│   ├── marketplace_catalog/         ← Deduplicated across markets
│   │   └── ean_master.parquet       (One row per EAN, best price from each market)
│   │
│   └── quality_metrics/
│       └── daily_metrics.parquet
│
└── gold/
    └── analytics_ready/
```

### Key Differences from Bronze

| Aspect | Bronze | Silver |
|--------|--------|--------|
| **Content** | Raw, as-is | Cleaned, normalized |
| **Partitioning** | market/year/month/day/run_id | market/year/month + summary tables |
| **Duplicates** | Preserved | Removed |
| **Format** | Parquet + JSONL | Parquet only |
| **Records** | All collected | Deduplicated best record |
| **Size** | ~100GB for scale | ~5-10GB for scale |
| **Use case** | Audit, reprocessing | Analytics, Gold prep |

---

## Normalization Strategies

### 1. Product Names

**Goal**: Standardize for matching & display

**Transformations**:
```python
# Input: "  LEITE  INTEGRAL PARMALAT 1L  "
# Operations:
1. Trim whitespace
2. Title case → "Leite Integral Parmalat 1L"
3. Remove special chars (keep only alphanumeric, space, dash)
4. Standardize volume units (1L → 1000ml internally)
5. Remove brand duplicates ("Leite Parmalat Leite" → "Leite Parmalat")

# Output: "Leite Integral Parmalat 1000ml"
```

**Code**:
```python
def normalize_product_name(name: str) -> str:
    """Normalize product name for matching."""
    if not name or not isinstance(name, str):
        return None
    
    # Trim & title case
    normalized = name.strip().title()
    
    # Remove extra whitespace
    normalized = ' '.join(normalized.split())
    
    # Keep only alphanumeric, space, dash, parentheses
    normalized = ''.join(c for c in normalized if c.isalnum() or c in ' -()/')
    
    # Standardize volume units (normalize to ml internally)
    volume_map = {'L': 'ml', 'l': 'ml', 'ML': 'ml'}
    for unit, replacement in volume_map.items():
        if f' {unit}' in normalized or f'{unit} ' in normalized:
            normalized = normalized.replace(f' {unit}', ' (1000ml)' if unit in ['L', 'l'] else ' ml')
    
    return normalized
```

### 2. Prices

**Goal**: Standardize currency, remove outliers, calculate metrics

**Transformations**:
```python
# Input: 4.50 (R$)
# Operations:
1. Ensure float type
2. Remove currency symbols & formatting
3. Validate range (0.01 < price < 100000) - flag outliers
4. Calculate price per unit (price / quantity)
5. Handle missing: use market median

# Output: {
#   "price": 4.50,
#   "price_normalized": 4.50,
#   "unit_price": 4.50,
#   "price_quality": "valid"
# }
```

**Validation Rules**:
- Price must be positive
- Price < 100,000 (flag anomalies)
- Unit price <= retail price
- Wholesale price <= retail price

### 3. Units (L, Kg, Ml, etc)

**Goal**: Standardize to base units

**Conversion Map**:
```python
UNIT_CONVERSIONS = {
    # Liquids (to ml)
    'L': 1000,      # 1L = 1000ml
    'ml': 1,
    'Liter': 1000,
    'Litre': 1000,
    
    # Weight (to g)
    'kg': 1000,     # 1kg = 1000g
    'g': 1,
    'mg': 0.001,
    
    # Other
    'un': 1,        # unit (no conversion)
    'pc': 1,        # piece
    'dz': 12,       # dozen
}
```

**Normalization**:
```python
def normalize_unit(product_name: str, quantity: float, unit: str) -> tuple:
    """
    Extract and normalize unit from product name.
    Returns: (normalized_quantity, normalized_unit, base_unit_qty)
    """
    if not unit:
        return quantity, 'un', quantity
    
    unit = unit.strip().lower()
    conversion = UNIT_CONVERSIONS.get(unit, 1)
    base_quantity = quantity * conversion
    
    return quantity, unit, base_quantity
```

### 4. Categories

**Goal**: Map market-specific categories to standard taxonomy

**Strategy**:
```python
# Market-specific → Standard
{
    "Laticínios": ["Laticínios"],
    "Leites": ["Laticínios"],
    "Leite e Derivados": ["Laticínios"],
    "Bebidas": ["Bebidas", "Bebidas Não Alcoólicas"],
    "Bebidas Lácteas": ["Bebidas", "Laticínios"],
}

# Hierarchy:
# Laticínios
#   ├─ Leites
#   ├─ Queijos
#   ├─ Iogurtes
#   └─ Derivados
```

**Implementation**:
```python
CATEGORY_MAPPING = {
    # Market-specific patterns
    'laticínios': 'Laticínios',
    'leite': 'Laticínios',
    'queijo': 'Laticínios',
    'iogurte': 'Laticínios',
    'bebida': 'Bebidas',
    # ... more mappings
}

def normalize_category(raw_category: str, market: str) -> str:
    """Map market-specific category to standard."""
    if not raw_category:
        return 'Uncategorized'
    
    normalized = raw_category.lower().strip()
    return CATEGORY_MAPPING.get(normalized, 'Uncategorized')
```

### 5. Brands

**Goal**: Standardize brand names for matching

**Transformations**:
```python
# Input: "  PARMALAT  ", "parmalat", "PARMALAT S/A"
# Operations:
1. Title case
2. Trim whitespace
3. Remove legal suffixes (S/A, LTDA, Inc, Ltd)
4. Remove duplicates
5. Brand mapping (common aliases)

# Output: "Parmalat"
```

**Mappings**:
```python
BRAND_ALIASES = {
    'Parmalat S/A': 'Parmalat',
    'P&G': 'Procter & Gamble',
    'Nestle': 'Nestlé',
    # ... more
}

def normalize_brand(raw_brand: str) -> str:
    """Normalize brand name."""
    if not raw_brand:
        return None
    
    brand = raw_brand.strip().title()
    
    # Remove legal suffixes
    suffixes = ['S/A', 'LTDA', 'Inc', 'Ltd', 'LLC']
    for suffix in suffixes:
        brand = brand.replace(suffix, '').strip()
    
    # Apply aliases
    brand = BRAND_ALIASES.get(brand, brand)
    
    return brand
```

---

## EAN Validation & Resolution

### EAN Format

Valid EANs:
- **EAN-8**: 8 digits (short form)
- **EAN-12**: 12 digits (UPC-A)
- **EAN-13**: 13 digits (standard)
- **EAN-14**: 14 digits (GTIN-14, case code)

### Validation Strategy

```python
def validate_ean(ean: str) -> tuple:
    """
    Validate EAN using check digit.
    Returns: (is_valid, cleaned_ean, error_message)
    """
    if not ean:
        return False, None, "Empty EAN"
    
    # Remove non-digits
    ean_clean = ''.join(c for c in str(ean) if c.isdigit())
    
    # Check length
    if len(ean_clean) not in [8, 12, 13, 14]:
        return False, None, f"Invalid length: {len(ean_clean)}"
    
    # Verify check digit (EAN-13 algorithm)
    if len(ean_clean) == 13:
        check = calculate_ean13_checksum(ean_clean[:12])
        if int(ean_clean[12]) != check:
            return False, ean_clean, "Invalid check digit"
    
    return True, ean_clean, None

def calculate_ean13_checksum(ean_12: str) -> int:
    """Calculate EAN-13 check digit."""
    total = 0
    for i, digit in enumerate(ean_12):
        weight = 1 if i % 2 == 0 else 3
        total += int(digit) * weight
    check = (10 - (total % 10)) % 10
    return check
```

### Multi-Market EAN Resolution

```python
# Strategy: If EAN differs across markets, keep all but mark duplicates

def resolve_eam_across_markets(records_by_market: Dict) -> Dict:
    """
    Find best EAN when product appears in multiple markets.
    
    Priority:
    1. EAN from Atacadão (typically most reliable)
    2. EAN from Carrefour
    3. EAN from Mix Mateus
    4. No EAN (mark as null)
    """
    best_ean = None
    market_priority = ['atacadao', 'carrefour', 'mix_mateus']
    
    for market in market_priority:
        if market in records_by_market:
            ean = records_by_market[market].get('ean')
            if ean and validate_ean(ean)[0]:
                best_ean = ean
                break
    
    return best_ean
```

---

## Duplicate Detection & Resolution

### Strategy: Exact Match + Fuzzy Match

### Level 1: Exact Duplicates
```python
# Same EAN + market = EXACT duplicate
duplicate_key = (market, ean, date)
```

### Level 2: Same Product, Different Market
```python
# Same EAN across markets = Cross-market match
# Keep: market with lowest price (best for consumers) + highest price (wholesale)
```

### Level 3: Same Product Name + Price
```python
# Different EAN but same normalized name, price within 5% = FUZZY match
fuzzy_key = (market, normalized_name, price_range)
```

### Resolution Algorithm

```python
def detect_duplicates(records: List[Dict], market: str) -> List[Dict]:
    """
    Detect and remove duplicates, keeping best record.
    
    Priority (keep in this order):
    1. Valid EAN (validated with checksum)
    2. Valid product name
    3. Most recent collected_at
    4. Lowest price (within market)
    """
    
    # Group by: (ean, normalized_name, market)
    groups = defaultdict(list)
    
    for record in records:
        key = (
            record.get('ean'),
            normalize_product_name(record['product_name']),
            market
        )
        groups[key].append(record)
    
    deduplicated = []
    
    for key, group in groups.items():
        if len(group) == 1:
            deduplicated.append(group[0])
        else:
            # Keep best record
            best = sorted(group, key=lambda r: (
                -r.get('ean_valid', 0),           # Valid EAN first
                -r.get('collected_at', ''),       # Most recent
                r.get('price', float('inf'))      # Lowest price
            ))[0]
            
            best['duplicate_count'] = len(group)
            deduplicated.append(best)
    
    return deduplicated
```

---

## Data Quality Checks

### Automated Quality Metrics

```python
class DataQualityCheck:
    """Validate Silver layer data quality."""
    
    QUALITY_RULES = {
        'null_rates': {
            'ean': 0.20,          # Allow ≤20% nulls
            'brand': 0.30,        # Allow ≤30% nulls
            'category': 0.10,     # Allow ≤10% nulls
            'price': 0.05,        # Allow ≤5% nulls (critical)
        },
        'price_validation': {
            'min': 0.01,          # No prices below R$0.01
            'max': 100000,        # Flag prices > R$100k
            'outlier_threshold': 3.0  # 3x std dev
        },
        'ean_validation': {
            'valid_format': 0.80,    # ≥80% valid EANs
        }
    }
    
    def check_quality(self, df: pd.DataFrame) -> Dict:
        """Run all quality checks."""
        issues = {
            'null_rates': self._check_null_rates(df),
            'price_validation': self._check_prices(df),
            'ean_validation': self._check_eams(df),
            'duplicates': self._check_duplicates(df),
        }
        return issues
    
    def _check_null_rates(self, df: pd.DataFrame) -> Dict:
        """Check null rates against thresholds."""
        nulls = {}
        for col, threshold in self.QUALITY_RULES['null_rates'].items():
            null_rate = df[col].isna().sum() / len(df)
            if null_rate > threshold:
                nulls[col] = {
                    'null_rate': null_rate,
                    'threshold': threshold,
                    'status': 'ALERT'
                }
        return nulls
    
    def _check_prices(self, df: pd.DataFrame) -> Dict:
        """Validate prices."""
        issues = {}
        
        # Check range
        invalid_range = df[(df['price'] < 0.01) | (df['price'] > 100000)]
        if len(invalid_range) > 0:
            issues['out_of_range'] = len(invalid_range)
        
        # Check outliers (3 std dev)
        mean_price = df['price'].mean()
        std_price = df['price'].std()
        outliers = df[(df['price'] > mean_price + 3 * std_price)]
        if len(outliers) > 0:
            issues['outliers'] = len(outliers)
        
        return issues
    
    def _check_eams(self, df: pd.DataFrame) -> Dict:
        """Validate EANs."""
        valid_count = df['ean'].apply(lambda x: validate_ean(x)[0] if x else False).sum()
        valid_rate = valid_count / len(df)
        
        return {
            'valid_count': valid_count,
            'valid_rate': valid_rate,
            'status': 'OK' if valid_rate >= 0.80 else 'ALERT'
        }
    
    def _check_duplicates(self, df: pd.DataFrame) -> Dict:
        """Detect duplicates."""
        dup_count = df['duplicate_count'].sum() if 'duplicate_count' in df.columns else 0
        
        return {
            'duplicate_count': dup_count,
            'duplicate_rate': dup_count / len(df) if len(df) > 0 else 0
        }
```

---

## Transformation Pipeline Architecture

### Execution Flow

```
Bronze Data (Parquet)
    ↓
1. Load & Schema Validation
    ↓
2. Normalization (Names, Prices, Units, Categories, Brands)
    ↓
3. EAN Validation & Resolution
    ↓
4. Duplicate Detection & Removal
    ↓
5. Quality Checks & Flagging
    ↓
6. Enrichment (Add normalized fields)
    ↓
7. Write to Silver (Parquet)
    ↓
8. Generate Metadata & Quality Report
```

### Metadata Structure

```json
{
  "silver_layer_version": "1.0.0",
  "transformation_id": "20250315_SV_001",
  "bronze_run_ids": ["20250315_104530_a1b2c3d4", "20250315_105000_x1y2z3a4"],
  "market": "atacadao",
  "execution": {
    "started_at": "2025-03-15T10:45:40Z",
    "completed_at": "2025-03-15T10:45:50Z",
    "duration_seconds": 10,
    "status": "SUCCESS"
  },
  "transformations": {
    "records_input": 48,
    "records_deduplicated": 3,
    "records_output": 45,
    "normalization": {
      "product_names_updated": 45,
      "prices_validated": 48,
      "brands_normalized": 40,
      "categories_mapped": 48
    },
    "duplicates": {
      "detected": 3,
      "removed": 3
    }
  },
  "quality_checks": {
    "null_rates": {...},
    "price_validation": {...},
    "ean_validation": {...},
    "overall_status": "OK"
  }
}
```

---

## Storage Strategy

### Parquet Partitioning

```
data/silver/
├── market=atacadao/
│   ├── year=2025/
│   │   ├── month=03/
│   │   │   ├── day=15/
│   │   │   │   ├── products_normalized.parquet
│   │   │   │   ├── transformation_metadata.json
│   │   │   │   └── _SUCCESS
│   │   │   └── ...
│   │   └── year_summary.parquet (monthly aggregates)
│   └── market_summary.parquet (all-time for market)
├── market=carrefour/...
└── marketplace_catalog/
    └── ean_master.parquet (deduped by EAN)
```

### Schema (Silver Records)

```python
{
    # Original Bronze fields
    "market": str,
    "source_product_id": str,
    "collected_at": str,
    "search_term": str,
    
    # Normalized fields (Silver additions)
    "product_name": str,              # Normalized
    "product_name_normalized": str,   # For matching
    "price": float,
    "price_normalized": float,
    "unit_price": float,
    "unit": str,
    "unit_normalized": str,
    "category": str,
    "category_normalized": str,
    "brand": str,
    "brand_normalized": str,
    "ean": str,
    "ean_valid": bool,
    "ean_source": str,
    
    # Deduplication fields
    "is_duplicate": bool,
    "duplicate_of_id": str,           # Reference to kept record
    "duplicate_count": int,
    
    # Quality flags
    "quality_score": float,           # 0-100
    "quality_flags": List[str],       # ['price_outlier', 'missing_ean', ...]
    "data_completeness": float,       # % non-null fields
    
    # Lineage
    "bronze_run_id": str,
    "silver_transformation_id": str,
    "silver_ingestion_timestamp": str,
}
```

---

## BigQuery Migration

### Step 1: Export Silver to GCS
```bash
gsutil -m cp -r data/silver/market=*/*.parquet gs://your-bucket/silver/
```

### Step 2: Create BigQuery Tables

```sql
-- External table
CREATE EXTERNAL TABLE `project.dataset.silver_products`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://your-bucket/silver/market=*/year=*/month=*/day=*/products_normalized.parquet']
);

-- Native table with clustering
CREATE TABLE `project.dataset.silver_products_native`
PARTITION BY DATE(collected_at)
CLUSTER BY market, ean_normalized AS
SELECT 
  *,
  FARM_FINGERPRINT(CONCAT(market, product_name_normalized)) as product_id
FROM `project.dataset.silver_products`;
```

### Step 3: Create Gold Views

```sql
CREATE VIEW `project.dataset.gold_product_catalog` AS
SELECT
  product_id,
  product_name,
  category,
  brand,
  ean,
  MIN(price) as min_price,
  MAX(price) as max_price,
  AVG(price) as avg_price,
  ARRAY_AGG(STRUCT(market, price, collected_at ORDER BY collected_at DESC LIMIT 1)) as latest_by_market,
  COUNT(DISTINCT market) as market_count
FROM `project.dataset.silver_products_native`
WHERE ean IS NOT NULL
GROUP BY product_id, product_name, category, brand, ean;
```

---

## Performance Considerations

### Indexing Strategy
- **For Joins**: ean, source_product_id, market
- **For Filtering**: market, category, brand, collected_at
- **For Aggregations**: market, category, price range

### Compression
- Parquet Snappy compression (faster than Gzip)
- Reduces ~90MB → ~10MB for typical 1M records

### Memory Management
- Process in batches (10k-100k records)
- Stream reads with pandas chunksize
- Use Dask for very large datasets (1B+ records)

---

## Naming Conventions

### File Naming

| Type | Convention | Example |
|------|-----------|---------|
| Normalized products | `products_normalized.parquet` | `products_normalized.parquet` |
| Metadata | `transformation_metadata.json` | `transformation_metadata.json` |
| Dedup index | `deduplication_index.parquet` | `deduplication_index.parquet` |
| Master catalog | `ean_master.parquet` | `ean_master.parquet` |

### Transformation ID

Format: `YYYYMMDD_SV_XXX`

Example: `20250315_SV_001` (Silver transformation #1 on 2025-03-15)

### Column Naming

| Original | Normalized | Purpose |
|----------|-----------|---------|
| `product_name` | `product_name_normalized` | Matching |
| `category` | `category_normalized` | Analysis |
| `price` | `price_normalized` | Calculations |
| `ean` | `ean_valid` | Validation flag |

---

## Next: Gold Layer

Silver outputs feed into Gold:
- Deduplicated catalog
- Cross-market price comparisons
- Aggregated analytics

**Gold = Analytics-ready tables**

---

## Summary

| Aspect | Design |
|--------|--------|
| **Deduplication** | Exact + Fuzzy matching, keep best record |
| **Normalization** | Standardize all fields, create normalized columns |
| **Validation** | EAN checksum, price ranges, null rates |
| **Storage** | Parquet, partitioned by market/date |
| **Quality** | Automated checks + quality scores |
| **Lineage** | Map back to Bronze run_id |
| **BigQuery Ready** | Direct upload, no transformation |

**This creates analytics-ready data for Gold layer while maintaining full auditability.**

---

**Version**: 1.0.0  
**Status**: Design Complete  
**Last Updated**: 2025-03-15
