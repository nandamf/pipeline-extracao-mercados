# Silver Layer Operations Guide

**Production operations for Silver layer transformations**

---

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Queries & Analysis](#queries--analysis)
3. [Monitoring & Maintenance](#monitoring--maintenance)
4. [Troubleshooting](#troubleshooting)
5. [Performance Tuning](#performance-tuning)
6. [Data Lineage](#data-lineage)

---

## Daily Operations

### Running Transformations

#### Single Market

```python
from pathlib import Path
from common.silver_transformer import SilverTransformer, SilverTransformConfig

# Setup
config = SilverTransformConfig(base_path=Path("data/silver"))
transformer = SilverTransformer(config)

# Find Bronze file for specific market
import glob
bronze_files = glob.glob("data/bronze/market=atacadao/year=2025/month=03/day=15/run_id=*/data_batch.parquet")

# Transform
for bronze_path in bronze_files:
    result = transformer.transform_bronze(
        bronze_parquet_path=bronze_path,
        market="atacadao",
        search_term="leite"
    )
    print(f"Status: {result.status}")
    print(f"Records: {result.records_output}")
```

#### Batch Processing (All Markets)

```bash
# run_silver_batch.py (create this script)
python run_silver_demo.py
```

**Or create a scheduled task** (Windows):

```batch
# silver_transform_daily.bat
@echo off
cd C:\Users\Lenovo\Documents\Portifolio\extract_mercados
python run_silver_demo.py
```

**Schedule with Task Scheduler:**
- Trigger: Daily at 02:00 AM
- Action: Run `silver_transform_daily.bat`
- Condition: Only if computer is idle

---

### Monitoring Transformations

#### Check Status

```python
from pathlib import Path
import json
import glob
from datetime import datetime, timedelta

# Get latest transformations (last 24 hours)
pattern = "data/silver/market=*/year=*/month=*/day=*/transformation_id=*/transformation_metadata.json"
files = sorted(glob.glob(pattern), reverse=True)

for metadata_file in files[:10]:
    with open(metadata_file) as f:
        metadata = json.load(f)
    
    transformation_id = metadata['transformation_id']
    market = metadata['market']
    status = metadata['execution']['status']
    duration = metadata['execution']['duration_seconds']
    quality = metadata['quality']['quality_score']
    
    print(f"{transformation_id} | {market} | {status} | {quality:.1f}/100 | {duration:.1f}s")
```

#### Extract Metrics

```python
# Create a metrics dashboard
import pandas as pd
import json
import glob

metrics = []

for metadata_file in glob.glob("data/silver/**/transformation_metadata.json", recursive=True):
    with open(metadata_file) as f:
        m = json.load(f)
    
    metrics.append({
        'transformation_id': m['transformation_id'],
        'market': m['market'],
        'records_input': m['transformations']['records_input'],
        'records_output': m['transformations']['records_output'],
        'deduplicated': m['transformations']['records_deduplicated'],
        'quality_score': m['quality']['quality_score'],
        'duration_s': m['execution']['duration_seconds'],
        'status': m['execution']['status'],
        'timestamp': m['execution']['completed_at']
    })

df = pd.DataFrame(metrics)

# Aggregates
print("Summary by Market:")
print(df.groupby('market').agg({
    'records_output': 'sum',
    'deduplicated': 'sum',
    'quality_score': 'mean',
    'duration_s': 'mean'
}))
```

---

## Queries & Analysis

### Reading Silver Data

#### Latest Data for Market

```python
import pandas as pd
import glob

# Find latest
pattern = "data/silver/market=atacadao/year=2025/month=*/day=*/transformation_id=*/products_normalized.parquet"
files = sorted(glob.glob(pattern), reverse=True)

if files:
    df = pd.read_parquet(files[0])
    print(f"Loaded {len(df)} records from {files[0]}")
```

#### Combine All Markets

```python
import pandas as pd
import glob

dfs = []

for market_path in glob.glob("data/silver/market=*/year=*/month=*/day=*/transformation_id=*/products_normalized.parquet"):
    df = pd.read_parquet(market_path)
    dfs.append(df)

combined = pd.concat(dfs, ignore_index=True)
print(f"Combined {len(combined)} records from all markets")
```

### Key Analyses

#### Quality Score Distribution

```python
import matplotlib.pyplot as plt
import pandas as pd
import glob

df = pd.concat([
    pd.read_parquet(f)
    for f in glob.glob("data/silver/.../products_normalized.parquet")
], ignore_index=True)

df['quality_score'].describe()
# Output:
# count    45.000000
# mean     85.333333
# std      10.123456
# min      60.000000
# 25%      80.000000
# 50%      85.000000
# 75%      90.000000
# max     100.000000

# Plot distribution
df['quality_score'].hist(bins=10, edgecolor='black')
plt.xlabel('Quality Score')
plt.ylabel('Count')
plt.title('Silver Layer Data Quality Distribution')
plt.show()
```

#### EAN Validation Rate

```python
df = pd.read_parquet("data/silver/.../products_normalized.parquet")

# By market
print("EAN Validity by Market:")
print(df.groupby('market')['ean_valid'].agg(['sum', 'count']))

# Overall
valid_rate = df['ean_valid'].sum() / len(df)
print(f"Overall valid EAN rate: {valid_rate*100:.1f}%")
```

#### Price Distribution

```python
import pandas as pd

df = pd.read_parquet("data/silver/.../products_normalized.parquet")

print("Price Statistics by Category:")
print(df.groupby('category_normalized')['price'].describe())

# Find outliers
mean_price = df['price'].mean()
std_price = df['price'].std()
outliers = df[df['price'] > mean_price + 3 * std_price]
print(f"\nPrice outliers (>3σ): {len(outliers)} records")
print(outliers[['product_name', 'price', 'category_normalized']])
```

#### Brand Normalization

```python
df = pd.read_parquet("data/silver/.../products_normalized.parquet")

# Distinct brands
distinct_before = df['brand'].nunique()
distinct_after = df['brand_normalized'].nunique()

print(f"Brands before normalization: {distinct_before}")
print(f"Brands after normalization: {distinct_after}")
print(f"Consolidation: {distinct_before - distinct_after} duplicates removed")

# Top brands
print("\nTop 10 brands (after normalization):")
print(df['brand_normalized'].value_counts().head(10))
```

#### Deduplication Impact

```python
df = pd.read_parquet("data/silver/.../products_normalized.parquet")

total_dups = df['duplicate_count'].sum()
total_records = len(df)
unique_before = total_records + total_dups

print(f"Records before deduplication: {unique_before}")
print(f"Duplicates removed: {total_dups}")
print(f"Records after deduplication: {total_records}")
print(f"Deduplication rate: {total_dups/unique_before*100:.1f}%")
```

---

## Monitoring & Maintenance

### Health Checks

```python
def run_health_checks():
    """Daily health check for Silver layer."""
    import glob
    import json
    import pandas as pd
    from datetime import datetime, timedelta
    
    checks = {}
    
    # 1. Recent transformations
    files = glob.glob("data/silver/**/transformation_metadata.json", recursive=True)
    recent = [f for f in files if (datetime.utcnow() - datetime.fromisoformat(
        json.load(open(f))['execution']['completed_at'].replace('Z', '+00:00')
    )).total_seconds() < 86400]
    
    checks['recent_transformations'] = {
        'status': 'OK' if len(recent) > 0 else 'WARNING',
        'count': len(recent)
    }
    
    # 2. Quality scores
    all_quality = []
    for f in files:
        m = json.load(open(f))
        all_quality.append(m['quality']['quality_score'])
    
    avg_quality = sum(all_quality) / len(all_quality) if all_quality else 0
    checks['quality'] = {
        'status': 'OK' if avg_quality > 80 else 'WARNING',
        'avg_score': avg_quality
    }
    
    # 3. EAN validity
    df = pd.concat([
        pd.read_parquet(f)
        for f in glob.glob("data/silver/.../products_normalized.parquet")
    ], ignore_index=True)
    
    valid_rate = df['ean_valid'].sum() / len(df) if len(df) > 0 else 0
    checks['ean_validity'] = {
        'status': 'OK' if valid_rate > 0.80 else 'ALERT',
        'valid_rate': valid_rate
    }
    
    # 4. Disk usage
    import os
    silver_size = sum(
        os.path.getsize(f)
        for f in glob.glob("data/silver/**/*.parquet", recursive=True)
    ) / (1024**3)  # GB
    
    checks['disk_usage'] = {
        'status': 'OK' if silver_size < 100 else 'WARNING',
        'size_gb': silver_size
    }
    
    return checks

# Run checks
checks = run_health_checks()
for check, result in checks.items():
    status = result['status']
    print(f"[{status}] {check}: {result}")
```

### Cleanup Old Data

```python
import glob
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

def cleanup_old_silver(days_to_keep=30):
    """Remove Silver data older than specified days."""
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    removed_count = 0
    
    # Find old transformation folders
    for folder in glob.glob("data/silver/market=*/year=*/month=*/day=*/transformation_id=*"):
        # Extract date from path
        parts = Path(folder).parts
        year = int([p for p in parts if p.startswith('year=')][0].split('=')[1])
        month = int([p for p in parts if p.startswith('month=')][0].split('=')[1])
        day = int([p for p in parts if p.startswith('day=')][0].split('=')[1])
        
        folder_date = datetime(year, month, day)
        
        if folder_date < cutoff_date:
            print(f"Removing old folder: {folder}")
            shutil.rmtree(folder)
            removed_count += 1
    
    print(f"Cleanup complete: removed {removed_count} folders")

# Keep last 30 days
cleanup_old_silver(days_to_keep=30)
```

### Archive to External Storage

```python
import shutil
from pathlib import Path
from datetime import datetime, timedelta

def archive_silver(archive_path="/mnt/archive/silver"):
    """Archive old Silver data."""
    
    cutoff = datetime.utcnow() - timedelta(days=7)
    archive_root = Path(archive_path)
    archive_root.mkdir(parents=True, exist_ok=True)
    
    for silver_folder in Path("data/silver").glob("market=*/year=*/month=*/day=*"):
        # Only archive folders older than 7 days
        if silver_folder.stat().st_mtime < cutoff.timestamp():
            target = archive_root / silver_folder.name
            print(f"Archiving: {silver_folder} → {target}")
            shutil.copytree(silver_folder, target, dirs_exist_ok=True)
```

---

## Troubleshooting

### Transformation Failed

**Error: "No valid records found"**

```python
# Debug: Check Bronze data
import pandas as pd

bronze_path = "data/bronze/market=atacadao/.../data_batch.parquet"
df = pd.read_parquet(bronze_path)

print(f"Records: {len(df)}")
print(f"Columns: {df.columns.tolist()}")
print(f"Null rates:\n{df.isnull().sum()}")
print(f"\nSample:\n{df.head()}")
```

### Low Quality Scores

**Problem: Quality score < 60**

```python
# Investigate issues
from common.quality_checks import DataQualityValidator, generate_quality_report
import pandas as pd

df = pd.read_parquet("data/silver/.../products_normalized.parquet")

validator = DataQualityValidator()
result = validator.check_quality(df)

# Print detailed report
print(generate_quality_report(result))

# Identify problematic records
print("\nRecords with issues:")
for idx, row in df[df['quality_score'] < 60].iterrows():
    print(f"  ID {idx}: {row['product_name']} - Score: {row['quality_score']}")
```

### High Duplication Rate

**Problem: Many records marked as duplicates**

```python
import pandas as pd

df = pd.read_parquet("data/silver/.../products_normalized.parquet")

# Analyze duplicates
total_dups = df['duplicate_count'].sum()
print(f"Total duplicates: {total_dups}")
print(f"Deduplication rate: {total_dups/len(df)*100:.1f}%")

# Check which fields cause duplicates
print("\nDuplicate patterns:")
dup_records = df[df['duplicate_count'] > 0]
print(f"  EANs: {dup_records['ean'].nunique()} unique")
print(f"  Names: {dup_records['product_name_normalized'].nunique()} unique")
print(f"  Markets: {dup_records['market'].unique()}")
```

---

## Performance Tuning

### Optimization Checklist

- [ ] Use Snappy compression (faster than Gzip)
- [ ] Process in batches (100K records)
- [ ] Enable multi-threading in Pandas
- [ ] Use Pyarrow for faster I/O
- [ ] Partition by market (parallel processing)
- [ ] Cache normalization mappings
- [ ] Use Dask for 1M+ records

### Monitoring Performance

```python
import time
import pandas as pd

start = time.time()

df = pd.read_parquet("data/silver/.../products_normalized.parquet")
print(f"Read time: {time.time() - start:.2f}s")

# Analyze by step
transformations = {
    'Load': 0.5,
    'Normalize': 2.0,
    'Deduplicate': 1.0,
    'Quality check': 0.5,
    'Write': 0.5,
}

for step, duration in transformations.items():
    pct = (duration / sum(transformations.values())) * 100
    print(f"{step}: {duration:.2f}s ({pct:.0f}%)")
```

---

## Data Lineage

### Trace Record Origins

```python
import json

# Get transformation metadata
metadata_path = "data/silver/market=atacadao/year=2025/month=03/day=15/transformation_id=20250315_SV_a1b2/transformation_metadata.json"

with open(metadata_path) as f:
    metadata = json.load(f)

print(f"Transformation: {metadata['transformation_id']}")
print(f"Market: {metadata['market']}")
print(f"Bronze sources: {metadata['lineage']['bronze_source']}")

# Trace back to Bronze
bronze_path = metadata['lineage']['bronze_source']
print(f"Original Bronze file: {bronze_path}")

# Read Bronze record
bronze_df = pd.read_parquet(bronze_path)
print(f"Original records: {len(bronze_df)}")
```

### Record Lineage Query

```python
import pandas as pd

# Read Silver
silver_df = pd.read_parquet("data/silver/.../products_normalized.parquet")

# Get one record's lineage
record = silver_df.iloc[0]

print(f"Silver Transformation ID: {record['silver_transformation_id']}")
print(f"Bronze Run ID: {record['bronze_run_id']}")
print(f"Original name: {record['product_name']}")
print(f"Normalized name: {record['product_name_normalized']}")
print(f"Quality score: {record['quality_score']:.1f}")

# Can trace back to exact Bronze file for audit
```

---

## Maintenance Schedule

### Daily
- [ ] Check recent transformations: `run run_silver_demo.py`
- [ ] Monitor quality scores

### Weekly
- [ ] Review deduplication rates
- [ ] Check disk usage
- [ ] Run health checks

### Monthly
- [ ] Archive old data (>30 days)
- [ ] Optimize partitions
- [ ] Review normalization rules
- [ ] Update documentation

### Quarterly
- [ ] Performance tuning review
- [ ] Data quality audit
- [ ] Schema evolution planning

---

## Support Commands

```bash
# Find recent Silver files
find data/silver -name "transformation_metadata.json" -type f | head -5

# Show disk usage
du -sh data/silver/

# Count transformations by market
find data/silver -name "transformation_metadata.json" | xargs grep -l "market" | wc -l

# List transformations (last 10)
ls -lt data/silver/market=*/year=*/month=*/day=*/transformation_id=* | head -10
```

---

## References

- [SILVER_ARCHITECTURE.md](SILVER_ARCHITECTURE.md)
- [SILVER_QUICKSTART.md](SILVER_QUICKSTART.md)
- [common/silver_transformer.py](common/silver_transformer.py)
- [common/quality_checks.py](common/quality_checks.py)

---

**Version**: 1.0.0  
**Status**: Production Ready  
**Last Updated**: 2025-03-15
