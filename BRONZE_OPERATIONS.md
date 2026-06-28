# Bronze Layer - Operations Reference

Complete reference for operating and querying the Bronze layer.

---

## Table of Contents

1. [Folder Structure Reference](#folder-structure-reference)
2. [Partition Queries](#partition-queries)
3. [Data Reading Patterns](#data-reading-patterns)
4. [Metadata & Monitoring](#metadata--monitoring)
5. [Maintenance & Retention](#maintenance--retention)
6. [BigQuery Migration](#bigquery-migration)
7. [Troubleshooting](#troubleshooting)

---

## Folder Structure Reference

### Complete Path Breakdown

```
data/bronze/market={MARKET}/year={YEAR}/month={MONTH}/day={DAY}/run_id={RUN_ID}/
│            │                 │          │           │          │            │
│            │                 │          │           │          │            └─ Run directory
│            │                 │          │           │          │
│            │                 │          │           │          └─ Run ID: YYYYMMDD_HHMMSS_random8hex
│            │                 │          │           │
│            │                 │          │           └─ Day (01-31)
│            │                 │          │
│            │                 │          └─ Month (01-12)
│            │                 │
│            │                 └─ Year (YYYY)
│            │
│            └─ Market (atacadao, carrefour, mix_mateus)
│
└─ Bronze layer root
```

### Example Paths

| Path | Meaning |
|------|---------|
| `data/bronze/market=atacadao/year=2025/month=03/day=15/run_id=20250315_104530_a1b2c3d4/` | Atacadão, March 15, 2025, 10:45:30 AM run |
| `data/bronze/market=carrefour/year=2025/month=03/day=*/run_id=*/*.parquet` | All Carrefour data in March 2025 |
| `data/bronze/market=*/year=2025/month=*/day=*/run_id=*/metadata.json` | All metadata in 2025 |

### Files in Each Run

```
run_id=20250315_104530_a1b2c3d4/
├── data_batch.parquet          # Main data file (binary, compressed)
│                                 # Schema: 20+ columns, all market data
│                                 # Size: typically 50KB-5MB per 1000 records
│
├── raw_payload.json            # JSONL audit trail (text, one JSON per line)
│                                 # Original API responses
│                                 # Size: typically 500KB-50MB per 1000 records
│
├── metadata.json               # Execution metadata & stats
│                                 # Size: typically 1-5KB
│
└── _SUCCESS                    # Success marker (0 bytes, empty file)
                                 # Indicates atomic write completion
```

---

## Partition Queries

### Query: All Data from Specific Date

```python
import pandas as pd
from pathlib import Path
import glob

# Read all Atacadão data from March 15, 2025
pattern = "data/bronze/market=atacadao/year=2025/month=03/day=15/run_id=*/data_batch.parquet"
files = glob.glob(pattern)

dfs = [pd.read_parquet(f) for f in files]
df_day = pd.concat(dfs, ignore_index=True)

print(f"Total records: {len(df_day)}")
```

### Query: All Data from Specific Market

```python
# Read all Atacadão data (all dates)
pattern = "data/bronze/market=atacadao/*/*/*/run_id=*/data_batch.parquet"
files = glob.glob(pattern)

dfs = [pd.read_parquet(f) for f in files]
df_market = pd.concat(dfs, ignore_index=True)

print(f"Atacadão total records: {len(df_market)}")
```

### Query: Date Range

```python
from datetime import datetime, timedelta
from pathlib import Path

def read_bronze_date_range(market, start_date, end_date):
    """Read all data from market between two dates."""
    
    dfs = []
    current = start_date
    
    while current <= end_date:
        year = current.strftime("%Y")
        month = current.strftime("%m")
        day = current.strftime("%d")
        
        pattern = f"data/bronze/market={market}/year={year}/month={month}/day={day}/run_id=*/data_batch.parquet"
        files = glob.glob(pattern)
        
        for f in files:
            dfs.append(pd.read_parquet(f))
        
        current += timedelta(days=1)
    
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

# Example: Last 7 days
end = datetime.utcnow()
start = end - timedelta(days=7)

df_week = read_bronze_date_range("atacadao", start, end)
print(f"7-day records: {len(df_week)}")
```

### Query: Specific Search Term

```python
# Find all data for "leite" search
df_all = read_bronze_all_markets()  # (see function below)
df_leite = df_all[df_all['search_term'] == 'leite']

print(f"Leite search results: {len(df_leite)}")
print(f"By market: {df_leite['market'].value_counts()}")
```

### Query: Specific Run

```python
# Read data from specific run
run_id = "20250315_104530_a1b2c3d4"
market = "atacadao"

path = f"data/bronze/market={market}/year=2025/month=03/day=15/run_id={run_id}/data_batch.parquet"
df_run = pd.read_parquet(path)

print(f"Run {run_id}: {len(df_run)} records")
```

### Query: Cross-Market Comparison

```python
def read_bronze_all_markets():
    """Read all Bronze data across all markets."""
    pattern = "data/bronze/market=*/year=*/month=*/day=*/run_id=*/data_batch.parquet"
    files = glob.glob(pattern)
    dfs = [pd.read_parquet(f) for f in files]
    return pd.concat(dfs, ignore_index=True)

df_all = read_bronze_all_markets()

# Compare prices by market
comparison = df_all.groupby(['market', 'product_name']).agg({
    'price': ['min', 'max', 'mean'],
    'product_name': 'count'
}).round(2)

print(comparison)
```

---

## Data Reading Patterns

### Pattern 1: Basic Read

```python
import pandas as pd

df = pd.read_parquet("data/bronze/market=atacadao/year=2025/month=03/day=15/run_id=20250315_104530_a1b2c3d4/data_batch.parquet")

# Info
print(f"Shape: {df.shape}")
print(f"Columns: {df.columns.tolist()}")
print(f"Data types:\n{df.dtypes}")
```

### Pattern 2: Lazy Read (DuckDB - Fast!)

```python
import duckdb

# Fast analysis without loading into memory
result = duckdb.query("""
    SELECT market, COUNT(*) as count, AVG(price) as avg_price
    FROM read_parquet('data/bronze/market=*/year=2025/month=*/day=*/run_id=*/data_batch.parquet')
    GROUP BY market
""").to_df()

print(result)
```

### Pattern 3: Streaming Large Files

```python
import pyarrow.parquet as pq

# Stream large files
parquet_file = pq.ParquetFile("data/bronze/.../data_batch.parquet")

for batch in parquet_file.iter_batches(batch_size=1000):
    df_batch = batch.to_pandas()
    # Process batch
    print(f"Batch: {len(df_batch)} records")
```

### Pattern 4: Read Raw Payloads

```python
import json

jsonl_path = "data/bronze/market=atacadao/year=2025/month=03/day=15/run_id=20250315_104530_a1b2c3d4/raw_payload.json"

payloads = []
with open(jsonl_path) as f:
    for line in f:
        payload = json.loads(line)
        payloads.append(payload)

print(f"Total payloads: {len(payloads)}")
print(f"First payload keys: {payloads[0].keys()}")
```

### Pattern 5: Schema Discovery

```python
import pyarrow.parquet as pq

# Inspect schema without reading data
parquet_file = pq.ParquetFile("data/bronze/.../data_batch.parquet")
schema = parquet_file.schema

for field in schema:
    print(f"{field.name}: {field.type}")
```

---

## Metadata & Monitoring

### Reading Metadata

```python
import json
from pathlib import Path

def read_metadata(run_id, market, year, month, day):
    """Read metadata for a specific run."""
    path = f"data/bronze/market={market}/year={year}/month={month}/day={day}/run_id={run_id}/metadata.json"
    
    with open(path) as f:
        return json.load(f)

# Example
metadata = read_metadata(
    run_id="20250315_104530_a1b2c3d4",
    market="atacadao",
    year="2025",
    month="03",
    day="15"
)

print(f"Records: {metadata['data_quality']['total_records']}")
print(f"Duration: {metadata['execution']['duration_seconds']}s")
print(f"Errors: {metadata['data_quality']['invalid_records']}")
```

### Monitoring Dashboard (Simple)

```python
import json
from pathlib import Path
from datetime import datetime

def get_bronze_stats():
    """Get statistics about Bronze layer."""
    
    stats = {
        "total_runs": 0,
        "total_records": 0,
        "by_market": {},
        "null_rates": {},
        "date_range": {"earliest": None, "latest": None}
    }
    
    bronze_dir = Path("data/bronze")
    
    for metadata_file in bronze_dir.rglob("metadata.json"):
        with open(metadata_file) as f:
            metadata = json.load(f)
        
        stats["total_runs"] += 1
        records = metadata['data_quality']['total_records']
        stats["total_records"] += records
        
        market = metadata['market']
        if market not in stats["by_market"]:
            stats["by_market"][market] = 0
        stats["by_market"][market] += records
        
        # Track null rates
        for field, rate in metadata['data_quality'].get('null_rates', {}).items():
            if field not in stats["null_rates"]:
                stats["null_rates"][field] = []
            stats["null_rates"][field].append(rate)
    
    return stats

stats = get_bronze_stats()
print(f"Total runs: {stats['total_runs']}")
print(f"Total records: {stats['total_records']}")
print(f"By market: {stats['by_market']}")
```

### Data Quality Checks

```python
def check_data_quality(df):
    """Check data quality of Bronze data."""
    
    print(f"\nData Quality Report:")
    print(f"{'='*60}")
    
    # Basic stats
    print(f"Shape: {df.shape}")
    print(f"Memory: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
    
    # Null analysis
    print(f"\nNull values:")
    nulls = df.isnull().sum()
    for col in nulls[nulls > 0].index:
        pct = (nulls[col] / len(df)) * 100
        print(f"  {col}: {nulls[col]} ({pct:.1f}%)")
    
    # Duplicates
    duplicates = df.duplicated(subset=['market', 'source_product_id']).sum()
    print(f"\nDuplicates (market + source_id): {duplicates}")
    
    # Price validation
    invalid_prices = (df['price'] <= 0).sum()
    print(f"Invalid prices (≤0): {invalid_prices}")
    
    # EAN validation
    valid_ean = df['ean'].notna().sum()
    ean_pct = (valid_ean / len(df)) * 100
    print(f"Valid EANs: {valid_ean} ({ean_pct:.1f}%)")
    
    print(f"{'='*60}")

# Usage
df_all = read_bronze_all_markets()
check_data_quality(df_all)
```

---

## Maintenance & Retention

### Archiving Old Data

```python
import shutil
from pathlib import Path
from datetime import datetime, timedelta

def archive_bronze_older_than(days: int):
    """Archive Bronze data older than N days."""
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    bronze_dir = Path("data/bronze")
    archive_dir = Path("archive/bronze")
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    for market_dir in bronze_dir.glob("market=*/"):
        for year_dir in market_dir.glob("year=*/"):
            for month_dir in year_dir.glob("month=*/"):
                for day_dir in month_dir.glob("day=*/"):
                    day_str = day_dir.name.split("=")[1]
                    month_str = month_dir.name.split("=")[1]
                    year_str = year_dir.name.split("=")[1]
                    
                    date = datetime.strptime(f"{year_str}{month_str}{day_str}", "%Y%m%d")
                    
                    if date < cutoff:
                        # Move to archive
                        archive_path = archive_dir / day_dir.parent.parent.parent.name / day_dir.parent.parent.name / day_dir.parent.name / day_dir.name
                        archive_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(day_dir), str(archive_path))
                        print(f"Archived: {day_dir}")

# Archive data older than 30 days
# archive_bronze_older_than(30)
```

### Cleanup Failed Runs

```python
def cleanup_failed_runs():
    """Remove runs that don't have _SUCCESS marker."""
    
    bronze_dir = Path("data/bronze")
    removed_count = 0
    
    for run_dir in bronze_dir.rglob("run_id=*"):
        if run_dir.is_dir():
            success_marker = run_dir / "_SUCCESS"
            
            if not success_marker.exists():
                print(f"Removing incomplete run: {run_dir}")
                shutil.rmtree(run_dir)
                removed_count += 1
    
    print(f"Removed {removed_count} incomplete runs")

# cleanup_failed_runs()
```

### Storage Usage Report

```python
def get_storage_report():
    """Get storage usage by market and date."""
    
    bronze_dir = Path("data/bronze")
    report = {}
    
    for market_dir in bronze_dir.glob("market=*/"):
        market = market_dir.name.split("=")[1]
        report[market] = {
            "size_mb": 0,
            "by_date": {}
        }
        
        for day_dir in market_dir.rglob("day=*/"):
            day_path = day_dir.name.split("=")[1]
            
            size = sum(
                f.stat().st_size 
                for f in day_dir.rglob('*') 
                if f.is_file()
            ) / 1024 / 1024  # to MB
            
            report[market]["size_mb"] += size
            report[market]["by_date"][day_path] = size
    
    return report

report = get_storage_report()
for market, data in report.items():
    print(f"{market}: {data['size_mb']:.2f} MB")
```

---

## BigQuery Migration

### Step 1: Export to Cloud Storage

```bash
# Copy to GCS
gsutil -m cp -r data/bronze/market=* gs://your-bucket/bronze/

# Verify
gsutil ls -r gs://your-bucket/bronze/ | head
```

### Step 2: Create BigQuery External Table

```sql
CREATE OR REPLACE EXTERNAL TABLE `project.dataset.bronze_raw`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://your-bucket/bronze/market=*/year=*/month=*/day=*/run_id=*/data_batch.parquet'],
  skip_leading_rows = 0
);
```

### Step 3: Query External Table

```sql
SELECT 
  market,
  COUNT(*) as record_count,
  APPROX_QUANTILES(price, 100)[OFFSET(50)] as median_price
FROM `project.dataset.bronze_raw`
GROUP BY market;
```

### Step 4: Load to Native Table

```sql
CREATE OR REPLACE TABLE `project.dataset.bronze_raw_native` AS
SELECT * FROM `project.dataset.bronze_raw`;

-- Create partitioned table for future queries
CREATE OR REPLACE TABLE `project.dataset.bronze_raw_partitioned`
PARTITION BY DATE(collected_at)
CLUSTER BY market, search_term AS
SELECT * FROM `project.dataset.bronze_raw`;
```

### Step 5: Automate with Python

```python
from google.cloud import storage, bigquery
from pathlib import Path

def upload_bronze_to_gcs(local_path: str, bucket_name: str, destination_prefix: str):
    """Upload Bronze parquet files to GCS."""
    
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    for parquet_file in Path(local_path).rglob("data_batch.parquet"):
        relative_path = parquet_file.relative_to(local_path)
        blob_path = f"{destination_prefix}/{relative_path}"
        
        blob = bucket.blob(blob_path)
        blob.upload_from_filename(str(parquet_file))
        print(f"Uploaded: {blob_path}")

# Usage
upload_bronze_to_gcs(
    local_path="data/bronze",
    bucket_name="my-data-lake",
    destination_prefix="bronze"
)
```

---

## Troubleshooting

### Issue: "FileNotFoundError" when reading Parquet

**Solution**: Verify the path exists
```python
from pathlib import Path

path = "data/bronze/market=atacadao/year=2025/month=03/day=15/run_id=20250315_104530_a1b2c3d4/data_batch.parquet"
if Path(path).exists():
    df = pd.read_parquet(path)
else:
    print(f"File not found: {path}")
    print("Available runs:")
    for run in Path("data/bronze/market=atacadao").rglob("run_id=*"):
        print(f"  {run.name}")
```

### Issue: Out of Memory Reading Large Files

**Solution**: Use streaming or DuckDB
```python
import duckdb

# DuckDB doesn't load entire file
result = duckdb.query("""
    SELECT COUNT(*) as row_count
    FROM read_parquet('data/bronze/.../data_batch.parquet')
""").to_df()
```

### Issue: Slow Queries on Multiple Files

**Solution**: Use DuckDB or Spark
```python
import duckdb

# DuckDB glob pattern
result = duckdb.query("""
    SELECT market, COUNT(*) as total
    FROM read_parquet('data/bronze/market=*/year=2025/month=*/day=*/run_id=*/data_batch.parquet')
    GROUP BY market
""").to_df()
```

### Issue: "_SUCCESS marker missing" warning

**Solution**: Check for incomplete writes
```python
for run_dir in Path("data/bronze").rglob("run_id=*"):
    if not (run_dir / "_SUCCESS").exists():
        print(f"Incomplete: {run_dir}")
        # Optionally remove or investigate
```

---

## Quick Reference Commands

```bash
# List all Bronze data
ls -R data/bronze/

# Count total records
find data/bronze -name "data_batch.parquet" | wc -l

# Get folder size
du -sh data/bronze/

# Find latest run
find data/bronze -name "metadata.json" | sort | tail -1

# Archive 30+ day old data
find data/bronze -type d -mtime +30 -exec mv {} archive/bronze \;
```

---

## Performance Tips

1. **Use DuckDB for aggregations** - 100x faster than Pandas
2. **Partition queries by date** - Filter before reading
3. **Use glob patterns efficiently** - Avoid reading all files if unnecessary
4. **Compress Parquet files** - Already done by default (Gzip)
5. **Archive old data** - Keep working set small

---

**Last Updated**: 2025-03-15
