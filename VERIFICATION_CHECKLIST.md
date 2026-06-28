# ✅ Bronze Layer Implementation Checklist

Use this checklist to verify your Bronze layer is properly set up and working.

---

## 🔧 Installation & Dependencies

- [ ] Python 3.7+ installed (`python --version`)
- [ ] pandas installed (`pip install pandas`)
- [ ] pyarrow installed (`pip install pyarrow`)
- [ ] Verify: `python -c "import pandas, pyarrow; print('✓ OK')"`

---

## 📁 File Structure

### Core Module
- [ ] `common/bronze_writer.py` exists (400+ lines)
- [ ] File contains `BronzeWriter` class
- [ ] File contains `BronzeWriteConfig` dataclass
- [ ] File contains `WriteResult` dataclass

### Examples & Demo
- [ ] `common/bronze_integration_examples.py` exists (300+ lines)
- [ ] `run_bronze_demo.py` exists (300+ lines)

### Documentation
- [ ] `BRONZE_ARCHITECTURE.md` exists
- [ ] `BRONZE_QUICKSTART.md` exists
- [ ] `BRONZE_OPERATIONS.md` exists
- [ ] `IMPLEMENTATION_ROADMAP.md` exists
- [ ] `BRONZE_LAYER_SUMMARY.md` exists
- [ ] `README.md` updated with Bronze info

---

## 🧪 Code Quality

### BronzeWriter Module
```python
# From Python, verify these exist:
from common.bronze_writer import BronzeWriter, BronzeWriteConfig, WriteResult

# Verify instantiation
bronze = BronzeWriter()
print(bronze)  # Should print BronzeWriter instance
```

- [ ] Module imports without errors
- [ ] `BronzeWriter()` instantiates successfully
- [ ] `BronzeWriteConfig()` can be created
- [ ] `WriteResult` has expected fields

### Schema Definition
```python
from common.bronze_writer import BronzeWriter

bronze = BronzeWriter()
print(bronze.BRONZE_SCHEMA)  # Should show schema
print(bronze.REQUIRED_FIELDS)  # Should show: market, product_name, search_term, collected_at
```

- [ ] `BRONZE_SCHEMA` defined (20+ fields)
- [ ] `REQUIRED_FIELDS` defined (4 fields)

---

## 🚀 Running the Demo

### Execute
```bash
python run_bronze_demo.py
```

### Expected Output
- [ ] Shows "Phase 1: Data Extraction"
- [ ] Shows "Phase 2: Bronze Layer Ingestion"
- [ ] Shows "Phase 3: Metadata Inspection"
- [ ] Shows "📈 Pipeline Summary" table
- [ ] Shows successful write results
- [ ] Completes without errors

### Verify Output
```bash
# Check folder was created
ls -R data/bronze/

# Check structure
ls data/bronze/market=*/year=*/month=*/day=*/
```

- [ ] `data/bronze/` folder exists
- [ ] Folder structure: `market=*/year=*/month=*/day=*/run_id=*/`
- [ ] Each run_id folder contains 4 files:
  - [ ] `data_batch.parquet`
  - [ ] `raw_payload.json` (optional)
  - [ ] `metadata.json`
  - [ ] `_SUCCESS`

---

## 📊 Reading Bronze Data

### Simple Read Test
```python
import pandas as pd
from pathlib import Path

# Find first parquet file
parquet_files = list(Path("data/bronze").rglob("data_batch.parquet"))
print(f"Found {len(parquet_files)} parquet files")

if parquet_files:
    df = pd.read_parquet(parquet_files[0])
    print(f"✓ Successfully read {len(df)} records")
    print(f"  Columns: {df.columns.tolist()[:5]}...")
```

- [ ] Can find parquet files
- [ ] Can read parquet file with pandas
- [ ] Data has expected columns
- [ ] Data has records (rows > 0)

### Metadata Read Test
```python
import json
from pathlib import Path

metadata_file = list(Path("data/bronze").rglob("metadata.json"))[0]
with open(metadata_file) as f:
    metadata = json.load(f)

print(f"Run ID: {metadata['run_id']}")
print(f"Records: {metadata['data_quality']['total_records']}")
print(f"Duration: {metadata['execution']['duration_seconds']}s")
print(f"Status: {metadata['execution']['status']}")
```

- [ ] Can find metadata.json
- [ ] Metadata is valid JSON
- [ ] Contains `run_id` field
- [ ] Contains `data_quality` stats
- [ ] Status is "SUCCESS" or "PARTIAL"

---

## 🏛️ Integration Test

### With Existing Scrapers
```python
from scrapers.registry import get_scraper
from common.bronze_writer import BronzeWriter

# Initialize
bronze = BronzeWriter()
scraper = get_scraper("atacadao")

# Search
results = scraper.search(search_term="leite", cep="04543010", max_pages=1)

# Write to Bronze
result = bronze.write_batch(
    market="atacadao",
    search_term="leite",
    records=results,
    cep="04543010"
)

# Verify
assert result.status in ["SUCCESS", "PARTIAL"]
assert result.records_written > 0
assert result.run_id != ""
```

- [ ] Can instantiate `BronzeWriter`
- [ ] Can get scraper instance
- [ ] Can run scraper search
- [ ] Can write to Bronze successfully
- [ ] `WriteResult` has correct status
- [ ] Records were written (count > 0)
- [ ] Run ID was generated

---

## 💾 Storage Verification

### Parquet File Check
```bash
# Check file exists and has size
ls -lh data/bronze/market=*/year=*/month=*/day=*/run_id=*/data_batch.parquet

# Expected: File size > 1KB (not empty)
```

- [ ] Parquet file exists
- [ ] File size > 1 KB (not empty)
- [ ] File is readable

### JSONL File Check
```bash
# Check if exists (optional)
ls data/bronze/market=*/year=*/month=*/day=*/run_id=*/raw_payload.json 2>/dev/null

# If exists, verify it's valid
python -c "import json; [json.loads(line) for line in open('data/bronze/.../raw_payload.json')]"
```

- [ ] Metadata.json exists in each run folder
- [ ] Metadata.json is valid JSON
- [ ] Can parse each line as JSON

### _SUCCESS Marker
```bash
# Verify marker exists
ls data/bronze/market=*/year=*/month=*/day=*/run_id=*/_SUCCESS
```

- [ ] `_SUCCESS` file exists
- [ ] File is empty (0 bytes)
- [ ] Marker indicates completed write

---

## 📋 Documentation Verification

### Check All Docs Exist
```bash
ls -1 *.md | grep BRONZE
```

- [ ] `BRONZE_ARCHITECTURE.md` - Exists, 2000+ words
- [ ] `BRONZE_QUICKSTART.md` - Exists, 1500+ words
- [ ] `BRONZE_OPERATIONS.md` - Exists, 2000+ words
- [ ] `IMPLEMENTATION_ROADMAP.md` - Exists, 1500+ words
- [ ] `BRONZE_LAYER_SUMMARY.md` - Exists
- [ ] `README.md` - Updated

### Documentation Quality
- [ ] Docs have clear structure (headers, sections)
- [ ] Docs include code examples
- [ ] Docs include diagrams/ASCII art
- [ ] Docs mention BigQuery migration
- [ ] Docs include troubleshooting

---

## 🎯 Feature Verification

### Schema Validation
```python
from common.bronze_writer import BronzeWriter

bronze = BronzeWriter()

# Test with invalid record (missing required field)
invalid_records = [{"product_name": "Test"}]  # missing market, search_term, collected_at

result = bronze.write_batch(
    market="test",
    search_term="test",
    records=invalid_records
)

# Should have errors
assert len(result.errors) > 0
print(f"✓ Schema validation works: {len(result.errors)} errors detected")
```

- [ ] Schema validation detects missing fields
- [ ] Schema validation reports errors clearly

### Metadata Generation
```python
import json
from pathlib import Path

# Read metadata from last run
metadata_files = list(Path("data/bronze").rglob("metadata.json"))
if metadata_files:
    metadata = json.load(open(metadata_files[-1]))
    
    # Verify required fields
    assert "run_id" in metadata
    assert "market" in metadata
    assert "execution" in metadata
    assert "data_quality" in metadata
    
    print("✓ Metadata contains all required fields")
```

- [ ] Metadata has `run_id`
- [ ] Metadata has `market`
- [ ] Metadata has `execution` with start/end times
- [ ] Metadata has `data_quality` stats

### Partition Structure
```bash
# Verify partition levels
find data/bronze -type d | head -10
```

- [ ] Folders include `market=*`
- [ ] Folders include `year=*`
- [ ] Folders include `month=*`
- [ ] Folders include `day=*`
- [ ] Folders include `run_id=*`

---

## 🔍 Data Quality Checks

### Null Rates
```python
import pandas as pd

df = pd.read_parquet("data/bronze/.../data_batch.parquet")

print("Null rates:")
for col in df.columns:
    null_pct = df[col].isna().sum() / len(df) * 100
    if null_pct > 0:
        print(f"  {col}: {null_pct:.1f}%")
```

- [ ] Can calculate null rates
- [ ] High null rates are tracked
- [ ] Metadata includes null rate summary

### Required Fields Present
```python
import pandas as pd

df = pd.read_parquet("data/bronze/.../data_batch.parquet")

required = ["market", "product_name", "search_term", "collected_at"]
for field in required:
    assert field in df.columns, f"Missing {field}"
    assert df[field].notna().all(), f"Nulls in {field}"

print("✓ All required fields present and non-null")
```

- [ ] All required fields present in data
- [ ] No nulls in required fields

### Bronze Enrichment Fields
```python
import pandas as pd

df = pd.read_parquet("data/bronze/.../data_batch.parquet")

bronze_fields = ["bronze_ingestion_timestamp", "bronze_run_id", "bronze_data_version", "bronze_error_flag"]
for field in bronze_fields:
    assert field in df.columns, f"Missing Bronze field: {field}"

print("✓ All Bronze enrichment fields present")
```

- [ ] `bronze_ingestion_timestamp` present
- [ ] `bronze_run_id` present
- [ ] `bronze_data_version` present
- [ ] `bronze_error_flag` present

---

## 🎓 Example Usage Verification

### Pattern 1: Simple Integration
```python
from scrapers.registry import get_scraper
from common.bronze_writer import BronzeWriter

bronze = BronzeWriter()
scraper = get_scraper("carrefour")
results = scraper.search(search_term="leite", max_pages=1)

if results:
    result = bronze.write_batch(market="carrefour", search_term="leite", records=results)
    assert result.status in ["SUCCESS", "PARTIAL"]
```

- [ ] Simple pattern works

### Pattern 2: Error Handling
```python
# Test that errors are caught
result = bronze.write_batch(market="test", search_term="test", records=[])

assert result.status == "FAILED"
assert len(result.errors) > 0
```

- [ ] Empty batch handled gracefully
- [ ] Error is tracked

### Pattern 3: Configuration
```python
from common.bronze_writer import BronzeWriter, BronzeWriteConfig
from pathlib import Path

config = BronzeWriteConfig(
    base_path=Path("custom/bronze"),
    compress=True
)
bronze = BronzeWriter(config)

assert bronze.config.base_path == Path("custom/bronze")
```

- [ ] Custom configuration works
- [ ] Configuration is applied

---

## ✨ Final Verification

### Overall Project Health
- [ ] No Python syntax errors
- [ ] All imports resolve without errors
- [ ] Module can be imported: `from common.bronze_writer import BronzeWriter`
- [ ] Demo runs to completion
- [ ] Data is generated and stored
- [ ] Documentation is complete and clear
- [ ] Code is production-ready

### Portfolio Readiness
- [ ] Code demonstrates enterprise patterns
- [ ] Documentation shows deep understanding
- [ ] Examples are comprehensive
- [ ] Handles edge cases
- [ ] Professional quality throughout

---

## 🎯 Sign-Off

When all items are checked, you have successfully implemented:

✅ **Professional Bronze layer**  
✅ **Production-ready code**  
✅ **Enterprise architecture**  
✅ **Complete documentation**  
✅ **Working examples**  
✅ **Portfolio-worthy project**  

---

## 📞 Troubleshooting

If any item fails, check:

1. **Import errors** → Reinstall dependencies: `pip install pandas pyarrow`
2. **File not found** → Check paths are correct, demo was run
3. **Schema errors** → Check scraper output format, review `bronze_writer.py`
4. **Metadata missing** → Verify write was successful, check for `_SUCCESS`
5. **Documentation issues** → Check file was created, view in text editor

See `BRONZE_OPERATIONS.md` for detailed troubleshooting.

---

**Last Updated**: 2025-03-15
**Status**: Ready for Verification
