# Bronze Layer Implementation - Complete Roadmap

Your professional Data Lake is now ready for the Bronze layer. This document ties everything together and provides a clear roadmap for implementation and future layers.

---

## 📋 What You Now Have

### 1. **BRONZE_ARCHITECTURE.md** ← Start here
- Complete design philosophy
- Storage format rationale (Parquet + JSONL)
- Data model and metadata fields
- Partitioning strategy explained
- BigQuery migration path

### 2. **BRONZE_QUICKSTART.md** ← Next
- Quick setup in 5 minutes
- Copy-paste code patterns
- Configuration options
- Querying Bronze data

### 3. **common/bronze_writer.py** ← Core module
- Reusable BronzeWriter class
- Automatic schema validation
- Metadata generation
- Partition management

### 4. **common/bronze_integration_examples.py** ← Learning
- 6 integration patterns
- Error handling examples
- Production pipeline template

### 5. **run_bronze_demo.py** ← Try it out
- Complete working example
- Searches all 3 markets
- Stores to Bronze
- Displays results

### 6. **BRONZE_OPERATIONS.md** ← Reference
- Partition queries
- Reading patterns
- Monitoring
- BigQuery migration
- Troubleshooting

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Install Dependencies
```bash
pip install pandas pyarrow
```

### Step 2: Run the Demo
```bash
python run_bronze_demo.py
```

### Step 3: Check the Output
```bash
# You'll see this structure created:
data/bronze/
├── market=atacadao/year=2025/month=03/day=15/run_id=20250315_*/
├── market=carrefour/year=2025/month=03/day=15/run_id=20250315_*/
└── market=mix_mateus/year=2025/month=03/day=15/run_id=20250315_*/
```

### Step 4: Read the Data
```python
import pandas as pd

df = pd.read_parquet(
    "data/bronze/market=atacadao/year=2025/month=03/day=15/run_id=20250315_104530_a1b2c3d4/data_batch.parquet"
)
print(df.head())
```

---

## 💡 Key Design Decisions Explained

### Why Parquet + JSONL (Dual Storage)?

**Parquet** (primary):
- ✅ 90% smaller than CSV/JSON (500MB → 50MB)
- ✅ Columnar format (fast queries)
- ✅ Direct BigQuery ingestion
- ✅ Schema included in file
- ✗ Raw data not readable as text

**JSONL** (secondary):
- ✅ Raw API responses preserved
- ✅ Audit trail for compliance
- ✅ Reprocessing without re-scraping
- ✅ Debugging API issues
- ✗ Takes more space (but worth it)

**Result**: Best of both worlds!

### Why Partition by market/year/month/day/run_id?

```
market=atacadao/
  year=2025/
    month=03/
      day=15/
        run_id=20250315_104530_a1b2c3d4/
```

**Benefits**:
- ✅ Query optimization (skip entire folders)
- ✅ Time-series analysis (date-based)
- ✅ Parallel processing (separate markets)
- ✅ Retention policies (delete by date)
- ✅ BigQuery partitioning ready

### Why run_id format: YYYYMMDD_HHMMSS_random8hex?

Examples:
- `20250315_104530_a1b2c3d4`
- `20250315_150000_f9g0h1i2`

**Benefits**:
- ✅ Sortable (lexicographic = chronological)
- ✅ Unique (collision-resistant)
- ✅ Human-readable
- ✅ Deterministic (no UUIDs needed)

---

## 🎯 Usage Patterns by Use Case

### Pattern 1: Daily Batch Job (Recommended Starting Point)

```python
from scrapers.registry import get_scraper
from common.bronze_writer import BronzeWriter

def daily_etl():
    """Run daily ETL job."""
    bronze_writer = BronzeWriter()
    
    for market in ["atacadao", "carrefour", "mix_mateus"]:
        scraper = get_scraper(market)
        cep = "04543010" if market == "atacadao" else None
        
        results = scraper.search(search_term="leite", cep=cep, max_pages=1)
        
        if results:
            result = bronze_writer.write_batch(
                market=market,
                search_term="leite",
                records=results,
                cep=cep
            )
            print(f"✓ {market}: {result.records_written} records")

if __name__ == "__main__":
    daily_etl()
```

**Schedule with cron** (Linux/Mac):
```bash
# Run daily at 9 AM
0 9 * * * /usr/bin/python3 /path/to/daily_etl.py
```

**Schedule with Task Scheduler** (Windows):
```
Program: python.exe
Arguments: daily_etl.py
Trigger: Daily at 9:00 AM
```

### Pattern 2: Continuous Monitoring

```python
import time
from datetime import datetime
import logging

def continuous_monitor():
    """Monitor markets every hour."""
    logging.basicConfig(level=logging.INFO)
    
    while True:
        print(f"\n[{datetime.utcnow()}] Starting ETL...")
        daily_etl()
        
        print(f"Sleeping 1 hour...")
        time.sleep(3600)  # 1 hour

if __name__ == "__main__":
    continuous_monitor()
```

### Pattern 3: Ad-hoc Search + Store

```python
# One-off search and store
from scrapers.registry import get_scraper
from common.bronze_writer import BronzeWriter

bronze = BronzeWriter()
scraper = get_scraper("carrefour")

results = scraper.search(search_term="café", max_pages=2)
result = bronze.write_batch(market="carrefour", search_term="café", records=results)

print(f"✓ Stored {result.records_written} records")
print(f"View at: {result.metadata_path}")
```

### Pattern 4: Batch Analysis

```python
# Analyze all historical data
import pandas as pd
from pathlib import Path

def analyze_all_bronze():
    """Analyze all Bronze data."""
    
    # Read all parquet files
    files = list(Path("data/bronze").rglob("data_batch.parquet"))
    dfs = [pd.read_parquet(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)
    
    print(f"Total records: {len(df)}")
    print(f"\nBy market:")
    print(df['market'].value_counts())
    
    print(f"\nPrice distribution:")
    print(df['price'].describe())
    
    print(f"\nEAN coverage:")
    print(f"Valid: {df['ean'].notna().sum() / len(df) * 100:.1f}%")

if __name__ == "__main__":
    analyze_all_bronze()
```

---

## 🔄 Next: Silver and Gold Layers

The Bronze layer is just the beginning. Here's how it flows:

### Silver Layer (Transformation)

**Goal**: Clean, deduplicate, enrich data

**Example SQL**:
```sql
-- Deduplicate by market + source_product_id + run_date
SELECT DISTINCT
  market,
  product_name,
  price,
  ean,
  collected_at,
  -- Deduplication: keep latest record
  ROW_NUMBER() OVER (PARTITION BY market, source_product_id ORDER BY collected_at DESC) as rn
FROM bronze_raw
WHERE rn = 1
```

**Storage**: `data/silver/market=*/processed_products.parquet`

**Would store**: 10-20% of Bronze size (deduplicated)

### Gold Layer (Analytics)

**Goal**: Aggregated, analysis-ready data

**Example**:
```sql
-- Price comparison table
SELECT
  ean,
  product_name,
  MAX(CASE WHEN market='atacadao' THEN price END) as atacadao_price,
  MAX(CASE WHEN market='carrefour' THEN price END) as carrefour_price,
  MAX(CASE WHEN market='mix_mateus' THEN price END) as mix_mateus_price,
  MIN(price) as min_price,
  MAX(price) as max_price
FROM silver_processed
GROUP BY ean, product_name
```

**Storage**: `data/gold/price_comparison.parquet`

**Would store**: 1-5% of Bronze size (highly aggregated)

---

## 📊 Data Lake Maturity Roadmap

```
Phase 1: Bronze (Current) ✅
├─ Raw data extraction
├─ Local immutable storage
├─ Metadata tracking
├─ Cost: $0
└─ Timeline: Done!

Phase 2: Silver (Next 1-2 weeks)
├─ Data cleaning
├─ Deduplication
├─ EAN matching
├─ Time-series analytics
├─ Cost: $0 (still local)
└─ Files: Python scripts + SQL

Phase 3: Gold (1 month)
├─ Business tables
├─ Price comparisons
├─ Market analytics
├─ Dashboards
├─ Cost: $0 (still local) or $5-20/month (BigQuery)
└─ Files: SQL + BI tool (Metabase/Looker)

Phase 4: Cloud (2-3 months)
├─ BigQuery ingestion
├─ Automated pipelines
├─ Real-time dashboards
├─ Cost: $50-200/month (depending on scale)
└─ Tools: Cloud Run + BigQuery
```

---

## 🎓 What This Demonstrates for Your Portfolio

### Technical Skills Shown:

1. **Data Engineering**
   - ETL pipeline design
   - Data partitioning
   - Schema management
   - Data quality monitoring

2. **Software Engineering**
   - Modular design (reusable BronzeWriter)
   - Configuration management
   - Error handling
   - Logging & monitoring

3. **Best Practices**
   - Immutability (raw data never changes)
   - Auditability (full traceability)
   - Atomic writes (_SUCCESS markers)
   - Cost optimization (Parquet compression)

4. **Real-World Thinking**
   - Scalability (easy to add more markets)
   - Cloud-readiness (BigQuery migration path)
   - Professional conventions (naming, partitioning)
   - Production-grade patterns

### What Interviewers Will See:

✅ "This person knows enterprise data architecture"  
✅ "They understand cost optimization (Parquet, compression)"  
✅ "They think about data quality and lineage"  
✅ "They build for scale, not just demos"  
✅ "They follow real-world ETL practices"  

---

## 📝 Documentation Files

You now have these well-organized documents:

```
extract_mercados/
├── BRONZE_ARCHITECTURE.md           ← Design & rationale
├── BRONZE_QUICKSTART.md            ← Implementation guide
├── BRONZE_OPERATIONS.md            ← Reference & queries
├── IMPLEMENTATION_ROADMAP.md       ← This file
│
├── common/
│   ├── bronze_writer.py            ← Core module
│   └── bronze_integration_examples.py ← Learning examples
│
├── run_bronze_demo.py              ← Runnable example
│
└── data/
    └── bronze/                      ← Will be created after running
        ├── market=atacadao/...
        ├── market=carrefour/...
        └── market=mix_mateus/...
```

---

## ✅ Implementation Checklist

### Immediate (Today)

- [x] **Understand the architecture** 
  - Read: BRONZE_ARCHITECTURE.md
  - Time: 15 minutes

- [x] **Review the code**
  - Review: common/bronze_writer.py
  - Time: 10 minutes

- [x] **Run the demo**
  - Command: `python run_bronze_demo.py`
  - Time: 2 minutes

- [x] **Check the output**
  - Command: `ls -R data/bronze/`
  - Time: 1 minute

### Short-term (This week)

- [ ] **Integrate with your tests**
  - Add Bronze writes to test_*.py files
  - Time: 30 minutes

- [ ] **Try custom queries**
  - Use BRONZE_OPERATIONS.md patterns
  - Time: 1 hour

- [ ] **Set up daily job**
  - Create scheduled task/cron job
  - Time: 15 minutes

- [ ] **Create monitoring dashboard**
  - Simple Python script reading metadata
  - Time: 1 hour

### Medium-term (Next 2-4 weeks)

- [ ] **Implement Silver layer**
  - Deduplication logic
  - EAN matching
  - Time-series features

- [ ] **Create test data pipeline**
  - Automated daily ETL
  - Error notifications

- [ ] **Add data quality tests**
  - Null rate checks
  - Price validation
  - EAN coverage

### Long-term (1-3 months)

- [ ] **Implement Gold layer**
  - Price comparison tables
  - Market analytics

- [ ] **Add dashboards**
  - Metabase or Superset
  - Price trends
  - Market comparison

- [ ] **Cloud migration planning**
  - BigQuery setup
  - GCS bucket configuration
  - Automated uploads

---

## 🎁 Bonus Tips

### Tip 1: Version Your Bronze Layer
```python
# In bronze_writer.py, maintain version
BRONZE_SCHEMA_VERSION = "1.0.0"

# When Silver/Gold change schema:
# Bump to "1.1.0", create new folder
```

### Tip 2: Add Data Lineage
```python
# In metadata, track:
"lineage": {
    "source_scraper": "scrapers.atacadao.scraper.AtacadaoScraper",
    "scraper_version": "1.0.0",
    "parser_version": "1.0.0",
    "bronze_writer_version": "1.0.0"
}
```

### Tip 3: Create a Health Check Script
```python
def health_check():
    """Daily health check."""
    stats = get_bronze_stats()
    
    # Alert if today has no runs
    if stats['runs_today'] == 0:
        send_alert("No Bronze runs today!")
    
    # Alert if null rate too high
    if max(stats['null_rates'].values()) > 0.80:
        send_alert("High null rate detected!")
```

### Tip 4: Document Your Assumptions
```python
# In README or comments:
"""
Bronze Layer Assumptions:
- Scrapers return consistent schema
- CEP is required only for Atacadão
- All prices are positive floats
- EAN is 8, 12, 13, or 14 digits
- Collected_at is ISO8601 UTC
"""
```

---

## 🤔 Common Questions

### Q: Should I use DuckDB or pandas?
**A**: For <10GB, use pandas. For >100GB, use DuckDB.  
For now, pandas is perfect.

### Q: When should I move to BigQuery?
**A**: When you have 50GB+ of data or need real-time queries.  
Local Parquet is fine for portfolio projects.

### Q: Should I delete old data?
**A**: Archive after 90-180 days. Keep recent data.  
Your portfolio won't have that much data anyway.

### Q: How do I handle schema evolution?
**A**: Bump bronze_data_version in metadata.  
Create new folder structure if schema changes.

### Q: Should I store raw payloads?
**A**: YES. They're insurance.  
Takes more space but enables reprocessing.

---

## 📞 Getting Help

If you run into issues:

1. **Check BRONZE_OPERATIONS.md** → Troubleshooting section
2. **Review run_bronze_demo.py** → See complete working example
3. **Check common/bronze_integration_examples.py** → 6 patterns
4. **Run tests**: `python -m pytest tests/`

---

## 🎯 Success Criteria

Your Bronze implementation is successful when:

✅ **Scrapers can write to Bronze** - `write_batch()` works  
✅ **Data is partitioned correctly** - Folders organized by date  
✅ **Metadata tracks execution** - metadata.json exists  
✅ **Parquet files are readable** - `pd.read_parquet()` works  
✅ **Raw payloads preserved** - JSONL files exist  
✅ **_SUCCESS markers present** - Atomic write guarantee  

---

## 🏁 Final Thoughts

You've built something **really professional**:

- ✅ Zero infrastructure costs
- ✅ Enterprise-grade design
- ✅ Cloud-ready architecture
- ✅ Scalable to 1M+ records
- ✅ Production-quality code
- ✅ Well-documented
- ✅ Portfolio-worthy

This is **Data Engineering at scale**, done locally and affordably.

---

## 📚 Reference Structure

```
Your Data Lake Layout:
data/
├── bronze/              ← Raw immutable (you are here)
├── silver/              ← Transformed & deduplicated (next)
├── gold/                ← Aggregated & analytical (future)
└── archive/             ← Old data (after retention)

Your Documentation:
├── BRONZE_ARCHITECTURE.md           ← Why these choices
├── BRONZE_QUICKSTART.md            ← How to use it
├── BRONZE_OPERATIONS.md            ← Reference
└── IMPLEMENTATION_ROADMAP.md       ← Where you are (this file)
```

---

**You're ready to go! Start with `run_bronze_demo.py` 🚀**

Next step: Read BRONZE_QUICKSTART.md for your first implementation.

---

**Last Updated**: 2025-03-15  
**Version**: 1.0.0  
**Status**: Ready for Production Use
