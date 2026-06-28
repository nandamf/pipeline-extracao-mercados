# Bronze Layer - Quick Start Implementation Guide

## Quick Overview

The Bronze layer is your **immutable raw data storage**. It's like an archive vault:
- ✅ Everything goes in as-is
- ✅ Raw API responses preserved
- ✅ Full audit trail
- ✅ Zero transformation

**Path**: `data/bronze/market={market}/year={year}/month={month}/day={day}/run_id={run_id}/`

---

## Installation

### 1. Install Required Dependencies

```bash
# If not already installed
pip install pandas pyarrow
```

Verify installation:
```bash
python -c "import pyarrow; import pandas; print('✓ Ready')"
```

### 2. Verify File Structure

```
✓ common/
  ✓ bronze_writer.py         ← NEW
  ✓ bronze_integration_examples.py  ← NEW
  └ ... (existing files)
```

---

## Usage Patterns

### Pattern 1: Simplest (Recommended for Starting)

```python
from scrapers.registry import get_scraper
from common.bronze_writer import BronzeWriter

# Initialize once
bronze_writer = BronzeWriter()

# Get scraper
scraper = get_scraper("atacadao")

# Run search as normal
results = scraper.search(search_term="leite", cep="04543010", max_pages=1)

# Write to Bronze (one line!)
write_result = bronze_writer.write_batch(
    market="atacadao",
    search_term="leite",
    records=results,
    cep="04543010"
)

# Check result
print(f"✓ Written {write_result.records_written} records to {write_result.run_id}")
```

### Pattern 2: All Three Markets

```python
from scrapers.registry import get_scraper
from common.bronze_writer import BronzeWriter

bronze_writer = BronzeWriter()

markets = ["atacadao", "carrefour", "mix_mateus"]

for market in markets:
    scraper = get_scraper(market)
    
    # Skip CEP for non-Atacadão
    cep = "04543010" if market == "atacadao" else None
    
    results = scraper.search(search_term="leite", cep=cep, max_pages=1)
    
    if results:
        write_result = bronze_writer.write_batch(
            market=market,
            search_term="leite",
            records=results,
            cep=cep
        )
        print(f"✓ {market}: {write_result.records_written} records")
```

### Pattern 3: Check Metadata (Monitoring)

```python
import json
from pathlib import Path

# After writing to Bronze, read metadata
metadata_path = write_result.metadata_path
with open(metadata_path) as f:
    metadata = json.load(f)

# Use metadata for dashboards/monitoring
print(f"Run ID: {metadata['run_id']}")
print(f"Duration: {metadata['execution']['duration_seconds']}s")
print(f"Records: {metadata['data_quality']['total_records']}")
print(f"Null rates: {metadata['data_quality']['null_rates']}")
print(f"Status: {metadata['execution']['status']}")
```

---

## Understanding the Folder Structure

### After First Run

```
data/
└── bronze/
    └── market=atacadao/
        └── year=2025/
            └── month=03/
                └── day=15/
                    └── run_id=20250315_104530_a1b2c3d4/
                        ├── data_batch.parquet       # ← Standardized data
                        ├── raw_payload.json         # ← Raw API responses
                        ├── metadata.json            # ← Audit trail
                        └── _SUCCESS                 # ← Success marker
```

### Key Files

| File | Purpose | Format | Size |
|------|---------|--------|------|
| `data_batch.parquet` | Extracted products | Binary (Parquet) | ~5-50MB per 100k rows |
| `raw_payload.json` | Original API responses | Text (JSONL) | ~50-500MB per 100k rows |
| `metadata.json` | Execution stats | Text (JSON) | ~1-10KB |
| `_SUCCESS` | Atomic write marker | Empty | 0 bytes |

---

## Data Quality & Metadata

### Automatic Checks (you don't need to do anything)

The `BronzeWriter` automatically:
- ✅ Validates schema
- ✅ Tracks null rates
- ✅ Calculates batch hash (detects duplicates)
- ✅ Records execution time
- ✅ Preserves raw payloads
- ✅ Creates atomic write markers

### Metadata Example

```json
{
  "bronze_layer_version": "1.0.0",
  "run_id": "20250315_104530_a1b2c3d4",
  "market": "atacadao",
  "search_term": "leite",
  "execution": {
    "started_at": "2025-03-15T10:45:30.123456Z",
    "completed_at": "2025-03-15T10:45:35.456789Z",
    "duration_seconds": 5.33,
    "status": "SUCCESS"
  },
  "data_quality": {
    "total_records": 48,
    "valid_records": 48,
    "invalid_records": 0,
    "null_rates": {
      "ean": 0.15,
      "wholesale_price": 0.0
    },
    "batch_id": "a1b2c3d4e5f6g7h8..."
  }
}
```

---

## Configuration Options

### Default Configuration (Recommended)

```python
from common.bronze_writer import BronzeWriter

# Uses defaults:
# - Base path: data/bronze
# - Compression: Yes (Gzip)
# - Schema validation: Yes
# - Preserve raw payloads: Yes

bronze_writer = BronzeWriter()
```

### Custom Configuration

```python
from common.bronze_writer import BronzeWriter, BronzeWriteConfig
from pathlib import Path

config = BronzeWriteConfig(
    base_path=Path("/custom/data/bronze"),
    compress=True,  # Gzip compression
    schema_validation=True,
    null_rate_threshold=0.50,  # Flag if >50% nulls
    preserve_raw_payloads=True
)

bronze_writer = BronzeWriter(config)
```

---

## Integration with Existing Tests

### Update test_atacadao.py

```python
# Before
def test_search():
    scraper = AtacadaoScraper()
    results = scraper.search(search_term="leite", cep="04543010")
    assert len(results) > 0

# After (still tests scraper, now also stores in Bronze)
from common.bronze_writer import BronzeWriter

def test_search_with_bronze():
    scraper = AtacadaoScraper()
    bronze_writer = BronzeWriter()
    
    results = scraper.search(search_term="leite", cep="04543010")
    assert len(results) > 0
    
    # Now also store in Bronze
    write_result = bronze_writer.write_batch(
        market="atacadao",
        search_term="leite",
        records=results,
        cep="04543010"
    )
    
    assert write_result.status == "SUCCESS"
    assert write_result.records_written > 0
```

---

## Querying Bronze Data

### Read Parquet with Pandas

```python
import pandas as pd

# Read all data from one run
df = pd.read_parquet(
    "data/bronze/market=atacadao/year=2025/month=03/day=15/run_id=20250315_104530_a1b2c3d4/data_batch.parquet"
)

print(f"Shape: {df.shape}")
print(df.head())
print(df.dtypes)
```

### Read All Atacadão Data

```python
import pandas as pd
from pathlib import Path

# Read all Atacadão parquet files
parquet_files = list(Path("data/bronze/market=atacadao").rglob("data_batch.parquet"))
dfs = [pd.read_parquet(f) for f in parquet_files]
df_all = pd.concat(dfs, ignore_index=True)

print(f"Total records: {len(df_all)}")
print(df_all.groupby('search_term').size())
```

### Read Raw Payloads (JSONL)

```python
import json

jsonl_path = "data/bronze/market=atacadao/year=2025/month=03/day=15/run_id=20250315_104530_a1b2c3d4/raw_payload.json"

with open(jsonl_path) as f:
    for line in f:
        payload = json.loads(line)
        print(payload["raw_response_type"])
        # One JSON object per line
```

---

## Error Handling

### The Write Result Object

```python
write_result = bronze_writer.write_batch(...)

# Check attributes:
write_result.status              # "SUCCESS", "PARTIAL", or "FAILED"
write_result.records_written     # Number of records stored
write_result.run_id              # Unique identifier
write_result.execution_duration_ms  # How long it took
write_result.errors              # List of validation errors
write_result.files_created       # Dict of created files
write_result.metadata_path       # Path to metadata.json
```

### Example: Handle Errors

```python
write_result = bronze_writer.write_batch(
    market="atacadao",
    search_term="leite",
    records=results
)

if write_result.status == "SUCCESS":
    print(f"✓ All {write_result.records_written} records stored")
elif write_result.status == "PARTIAL":
    print(f"⚠️  {write_result.records_written} records stored, but errors:")
    for error in write_result.errors:
        print(f"   - {error}")
else:  # FAILED
    print(f"✗ Write failed: {write_result.errors}")
```

---

## Folder Structure After Multiple Runs

```
data/bronze/
├── market=atacadao/
│   └── year=2025/
│       └── month=03/
│           ├── day=14/
│           │   ├── run_id=20250314_150000_x1y2z3a4/
│           │   │   ├── data_batch.parquet
│           │   │   ├── raw_payload.json
│           │   │   ├── metadata.json
│           │   │   └── _SUCCESS
│           │   └── run_id=20250314_170000_b5c6d7e8/
│           │       └── ...
│           └── day=15/
│               ├── run_id=20250315_104530_a1b2c3d4/
│               │   └── ...
│               └── run_id=20250315_150000_f9g0h1i2/
│                   └── ...
├── market=carrefour/
│   └── year=2025/
│       └── month=03/
│           └── day=15/
│               └── run_id=20250315_105000_j3k4l5m6/
│                   └── ...
└── market=mix_mateus/
    └── year=2025/
        └── month=03/
            └── day=15/
                └── run_id=20250315_110000_n7o8p9q0/
                    └── ...
```

**Result**: Immutable, append-only, easily queryable data lake!

---

## Storage Estimates

### For 1,000 products per market per day

| Format | Size | Compressed |
|--------|------|-----------|
| CSV | ~500 KB | ~100 KB |
| JSON | ~800 KB | ~150 KB |
| Parquet | ~100 KB | ~50 KB ⭐ |

**For 100 days, 3 markets = 300 runs:**
- CSV: 150 MB
- Parquet: **15 MB** ← 90% savings!

---

## Next Steps

### 1. Try It Out
```python
# Run the example
python common/bronze_integration_examples.py
```

### 2. Integrate with Your Tests
```python
# Update existing tests to use Bronze
# See INTEGRATION GUIDE above
```

### 3. Prepare for Silver Layer
- Use Bronze as input for transformations
- Silver = cleaned, deduplicated data
- Gold = aggregated, analytical data

### 4. Plan BigQuery Migration
- Parquet files already BigQuery-ready
- JSONL for full auditability
- Metadata for SLA tracking

---

## Troubleshooting

### "No module named 'pyarrow'"
```bash
pip install pyarrow pandas
```

### "Bronze folder not created"
- Check write permissions in `data/` directory
- Verify path is correct

### "Metadata shows high null rates"
- Check scraper output format
- Verify market is returning expected fields
- Check parser logic

### "Records written = 0"
- Verify scraper returned results: `print(len(results))`
- Check search term is valid
- Verify CEP format (for Atacadão)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   Your Scrapers                          │
│  (Carrefour, Atacadão, Mix Mateus)                      │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
         ┌───────────────┐
         │ scrapers.py   │
         │ .search()     │
         └───────┬───────┘
                 │
                 ▼
     ┌─────────────────────────┐
     │  BronzeWriter.write()   │  ← YOU ARE HERE
     │  (enrichment + storage) │
     └─────────┬───────────────┘
               │
         ┌─────┴──────┬──────────┐
         ▼            ▼          ▼
    ┌────────┐   ┌────────┐  ┌────────┐
    │Parquet │   │ JSONL  │  │Metadata│
    │(Queried)   │(Audit) │  │(SLA)   │
    └────────┘   └────────┘  └────────┘
         │            │          │
         └─────┬──────┴──────────┘
               ▼
    ┌──────────────────────────┐
    │   Silver Layer (Future)   │  ← Deduplicate, enrich
    │   Transformations        │
    └──────────────────────────┘
               │
               ▼
    ┌──────────────────────────┐
    │   Gold Layer (Future)     │  ← Aggregations, analytics
    │   Business Intelligence  │
    └──────────────────────────┘
```

---

## Key Takeaways

✅ **Bronze layer = immutable raw data vault**  
✅ **Dual storage: Parquet (efficient) + JSONL (audit)**  
✅ **Automatic metadata, validation, error tracking**  
✅ **Partition-friendly for BigQuery migration**  
✅ **Zero infrastructure cost, all local**  
✅ **Portfolio-grade quality**  

---

## Questions?

See:
- `BRONZE_ARCHITECTURE.md` - Full design details
- `common/bronze_writer.py` - Implementation
- `common/bronze_integration_examples.py` - Code examples
