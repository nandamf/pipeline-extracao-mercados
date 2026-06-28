# Silver Layer Quickstart

**Bronze → Silver:** Transform raw data into analytics-ready datasets

---

## 5-Minute Setup

### Prerequisites

```bash
# Make sure Bronze layer is populated
python run_bronze_demo.py
```

---

## Basic Usage

### 1. Transform Bronze to Silver

```python
from pathlib import Path
from common.silver_transformer import SilverTransformer, SilverTransformConfig

# Initialize
config = SilverTransformConfig(base_path=Path("data/silver"))
transformer = SilverTransformer(config)

# Transform
result = transformer.transform_bronze(
    bronze_parquet_path="data/bronze/market=atacadao/.../data_batch.parquet",
    market="atacadao",
    search_term="leite"
)

print(f"Status: {result.status}")
print(f"Records: {result.records_output}")
print(f"Quality: {result.quality_score:.1f}/100")
```

---

## Run Full Demo

```bash
python run_silver_demo.py
```

**Output:**
- Phase 1: Discovers Bronze files
- Phase 2: Transforms to Silver
- Phase 3: Inspects results
- Phase 4: Verifies quality
- Phase 5: Displays summary
- Phase 6: Shows metadata

---

## What Silver Does

### Transformations

| Input | Transformation | Output |
|-------|-----------------|--------|
| `"  LEITE  PARMALAT 1L  "` | Normalize | `"Leite Parmalat 1000ml"` |
| `4.50` | Validate | `4.50` (float) |
| `"Laticínios"` | Map | `"Laticínios"` |
| `"PARMALAT S/A"` | Clean | `"Parmalat"` |
| `"7894001234567"` | Validate EAN | `valid=true` |
| Duplicates | Detect | Removed (keep best) |

### Quality Checks

```
✓ Null rates (ean ≤20%, brand ≤30%, price ≤5%)
✓ Price validation (0.01 < price < 100000)
✓ EAN format validation (≥80% valid)
✓ Duplicate detection (exact + fuzzy)
✓ Data completeness (≥50% fields)
```

---

## Data Flow

### Input (Bronze)
```json
{
  "product_name": "  LEITE INTEGRAL  ",
  "price": 4.5,
  "category": "Laticínios",
  "brand": "parmalat",
  "ean": "7894001234567"
}
```

### Output (Silver)
```json
{
  "product_name": "Leite Integral",
  "product_name_normalized": "Leite Integral",
  "price": 4.50,
  "price_normalized": 4.50,
  "category": "Laticínios",
  "category_normalized": "Laticínios",
  "brand": "parmalat",
  "brand_normalized": "Parmalat",
  "ean": "7894001234567",
  "ean_normalized": "7894001234567",
  "ean_valid": true,
  "quality_score": 95.5,
  "data_completeness": 90.0
}
```

---

## Module Reference

### normalizers.py

**Product names**
```python
from common.normalizers import normalize_product_name

normalized = normalize_product_name("  LEITE  PARMALAT 1L  ")
# → "Leite Parmalat 1000ml"
```

**Prices**
```python
from common.normalizers import normalize_price

price = normalize_price("R$ 4,50")
# → 4.50
```

**Units**
```python
from common.normalizers import normalize_unit, convert_to_base_unit

unit = normalize_unit("L")          # → "L"
base = convert_to_base_unit(1, "L") # → 1000 (ml)
```

**Categories**
```python
from common.normalizers import normalize_category

cat = normalize_category("Laticínios")
# → "Laticínios"
```

**Brands**
```python
from common.normalizers import normalize_brand

brand = normalize_brand("PARMALAT S/A")
# → "Parmalat"
```

**EAN Validation**
```python
from common.normalizers import validate_ean

is_valid, cleaned, error = validate_ean("7894001234567")
# → (True, "7894001234567", None)
```

---

### quality_checks.py

**Run quality validation**
```python
from common.quality_checks import DataQualityValidator, generate_quality_report

validator = DataQualityValidator()
result = validator.check_quality(df)

# Print report
report = generate_quality_report(result)
print(report)
```

**Result structure**
```python
QualityCheckResult(
    status='OK',                    # OK, WARNING, ALERT, CRITICAL
    total_checks=7,
    passed_checks=7,
    issues={},                      # Dict of issues found
    quality_score=95.5,             # 0-100
    recommendations=[]              # List of suggestions
)
```

---

### silver_transformer.py

**Transform Bronze file**
```python
from common.silver_transformer import SilverTransformer

transformer = SilverTransformer()

result = transformer.transform_bronze(
    bronze_parquet_path="...",
    market="atacadao",
    search_term="leite"
)

# Result has:
# - transformation_id: unique ID
# - status: SUCCESS/PARTIAL/FAILED
# - records_input, records_output
# - records_deduplicated
# - quality_score
# - files_created
# - errors
```

---

## Configuration

### SilverTransformConfig

```python
from common.silver_transformer import SilverTransformConfig
from pathlib import Path

config = SilverTransformConfig(
    base_path=Path("data/silver"),          # Output folder
    compress=True,                          # Use Snappy compression
    remove_duplicates=True,                 # Detect & remove dups
    validate_quality=True,                  # Run quality checks
    create_master_catalog=True              # Create EAN master
)

transformer = SilverTransformer(config)
```

---

## Folder Structure

### Output

```
data/silver/
├── market=atacadao/
│   ├── year=2025/
│   │   ├── month=03/
│   │   │   ├── day=15/
│   │   │   │   ├── transformation_id=20250315_SV_a1b2/
│   │   │   │   │   ├── products_normalized.parquet    ← Data
│   │   │   │   │   ├── transformation_metadata.json    ← Metadata
│   │   │   │   │   └── _SUCCESS                        ← Completion marker
│   │   │   │   └── ...
│   │   │   └── ...
│   │   └── ...
│   └── ...
├── market=carrefour/
│   └── ...
└── marketplace_catalog/
    └── ean_master.parquet         ← Master EAN catalog
```

---

## Metadata

### transformation_metadata.json

```json
{
  "silver_layer_version": "1.0.0",
  "transformation_id": "20250315_SV_a1b2",
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
    "deduplication_rate": 0.0625
  },
  "quality": {
    "overall_status": "OK",
    "quality_score": 95.5,
    "checks_passed": 7,
    "checks_total": 7,
    "issues": {},
    "recommendations": []
  }
}
```

---

## Common Tasks

### Process All Bronze Data

```python
from pathlib import Path
import glob

transformer = SilverTransformer()

# Find all Bronze files
pattern = "data/bronze/market=*/year=*/month=*/day=*/run_id=*/data_batch.parquet"

for bronze_path in glob.glob(pattern):
    result = transformer.transform_bronze(
        bronze_parquet_path=bronze_path,
        market="unknown",  # Extract from path
        search_term="unknown"
    )
    print(f"{result.market}: {result.records_output} records")
```

### Read Silver Data

```python
import pandas as pd

# Find latest Silver file
import glob
silver_path = sorted(
    glob.glob("data/silver/market=*/year=*/month=*/day=*/transformation_id=*/products_normalized.parquet"),
    reverse=True
)[0]

df = pd.read_parquet(silver_path)
print(f"Records: {len(df)}")
print(df[['product_name_normalized', 'price', 'brand_normalized']].head())
```

### Check Data Quality

```python
from common.quality_checks import DataQualityValidator, generate_quality_report
import pandas as pd

df = pd.read_parquet("data/silver/.../products_normalized.parquet")

validator = DataQualityValidator()
result = validator.check_quality(df)

# Print detailed report
print(generate_quality_report(result))
```

---

## Troubleshooting

### No Silver data produced

**Problem:** Transformation ran but output is empty

**Solution:**
1. Check Bronze data exists: `data/bronze/.../data_batch.parquet`
2. Verify Bronze has valid records
3. Check logs for errors

### Quality score too low

**Problem:** Quality score < 60

**Causes:**
- Too many missing fields
- Invalid EANs (< 80% valid)
- Price outliers
- Missing categories/brands

**Solution:**
1. Review `quality_checks.py` warnings
2. Improve source data quality
3. Adjust normalization rules

### Deduplication too aggressive

**Problem:** Too many records marked as duplicates

**Solution:**
1. Check duplicate detection logic
2. Adjust key fields used for grouping
3. Review priority sorting

---

## Performance

### Typical Performance

| Operation | Time | Input | Output |
|-----------|------|-------|--------|
| Load Bronze | <1s | 1 file | ~50K records |
| Normalize | 0.5-2s | 50K records | Same |
| Detect dups | 0.5-1s | 50K records | 48K deduplicated |
| Validate quality | 0.2-0.5s | 48K records | Quality report |
| Write Parquet | 0.5s | 48K records | ~5MB compressed |
| **Total** | **~3-5s** | 50K records | Normalized + deduplicated |

### Optimization

**For large datasets (1M+)**:
- Use Dask for distributed processing
- Process in batches (100K records)
- Enable multi-threading in pandas
- Use Pyarrow's faster parser

---

## Next: Gold Layer

Silver outputs feed into Gold:

```
Silver (Clean & Normalized)
    ↓
Gold (Aggregated Analytics)
    ↓
BigQuery External Table
    ↓
Looker Studio Dashboard
```

---

## Version

**Silver Layer**: 1.0.0  
**Status**: Production Ready  
**Last Updated**: 2025-03-15

---

## Support

For issues or questions:
1. Check logs: `run_silver_demo.py`
2. Review `SILVER_ARCHITECTURE.md` for design details
3. Inspect metadata: `transformation_metadata.json`
