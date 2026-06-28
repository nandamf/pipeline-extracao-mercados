# Bronze Layer Architecture

## Overview

The Bronze layer is the first stage of a professional Data Lake, storing **raw, immutable extracted data** with full traceability. This layer simulates enterprise-grade ETL practices while remaining cost-free and locally managed.

---

## Architecture Design

```
Raw Data (Scrapers)
       ↓
BronzeWriter (Standardization)
       ↓
Bronze Layer (Immutable Storage)
       ↓
Silver Layer (Transformation - future)
       ↓
Gold Layer (Analytics - future)
```

### Data Lake Folder Structure

```
data/
├── bronze/                          # Immutable raw data
│   ├── market=atacadao/
│   │   ├── year=2025/
│   │   │   ├── month=03/
│   │   │   │   ├── day=15/
│   │   │   │   │   ├── run_id=20250315_104530_a1b2c3d4/
│   │   │   │   │   │   ├── data_batch.parquet      # Standardized data (Parquet)
│   │   │   │   │   │   ├── raw_payload.json        # Raw API responses (JSONL)
│   │   │   │   │   │   ├── metadata.json           # Execution metadata
│   │   │   │   │   │   └── _SUCCESS                # Success marker
│   │   │   │   │   ├── run_id=20250315_110045_e5f6g7h8/
│   │   │   │   │   │   └── ...
│   ├── market=carrefour/
│   │   └── year=2025/...
│   └── market=mix_mateus/
│       └── year=2025/...
│
├── silver/                          # Transformed data (future)
│   └── market=*/...
│
└── gold/                            # Aggregated data (future)
    └── products/...
```

---

## Storage Strategy

### Format Selection

| Aspect | JSON | Parquet | CSV |
|--------|------|---------|-----|
| **Efficiency** | Low (text) | HIGH ⭐ | Low (text) |
| **Compression** | Poor | Excellent (80%+) | None |
| **Columnar** | No | YES ⭐ | No |
| **Schema** | Flexible | YES ⭐ | No |
| **Speed** | Slow | FAST ⭐ | Slow |
| **BigQuery** | Native ⭐ | Native ⭐ | Convert needed |
| **Debugging** | Easy ⭐ | Hard | Easy |
| **Size (1M rows)** | ~500MB | ~50-80MB ⭐ | ~300MB |

### Chosen Approach: **Dual Storage**

1. **Primary: Parquet** (`data_batch.parquet`)
   - Standardized extracted data
   - Efficient storage and querying
   - Direct BigQuery ingestion
   - Versioned with run_id

2. **Secondary: JSONL** (`raw_payload.json`)
   - Original API/HTML responses
   - Immutable audit trail
   - Debugging & reprocessing
   - Preserves all original data

3. **Metadata: JSON** (`metadata.json`)
   - Execution tracking
   - Data lineage
   - Processing stats
   - Error logs

---

## Data Model & Metadata

### Bronze Record Schema

**Base fields** (added by BronzeWriter):
```python
{
    # Original scraper fields
    "market": str,
    "product_name": str,
    "price": float,
    "unit_price": float,
    "category": str,
    "brand": str,
    "source_product_id": str,
    "sku": str,
    "ean": str,
    "searched_ean": str,
    "ean_source": str,
    "search_term": str,
    "cep": str | None,
    "collected_at": str,  # ISO8601
    "source_url": str,
    "image_url": str,
    "wholesale_price": float | None,
    
    # Bronze enrichment (added layer)
    "bronze_ingestion_timestamp": str,  # ISO8601, when data entered Bronze
    "bronze_run_id": str,               # Unique run identifier
    "bronze_batch_id": str,             # Hash of batch contents
    "bronze_data_version": str,         # Schema version (v1, v2, etc)
    "bronze_source_count": int,         # Records in this batch
    "bronze_error_flag": bool,          # Any errors in processing
    "bronze_processing_duration_ms": int,
}
```

### Metadata File Structure

**`metadata.json`** per run:
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
    "status": "SUCCESS"  // SUCCESS | PARTIAL | FAILED
  },
  "data_quality": {
    "total_records": 48,
    "valid_records": 48,
    "invalid_records": 0,
    "records_with_errors": 0,
    "null_rates": {
      "ean": 0.15,
      "wholesale_price": 0.0,
      "cep": 0.0
    }
  },
  "data_lineage": {
    "source": "scrapers.atacadao.scraper.AtacadaoScraper",
    "scraper_version": "1.0.0",
    "api_endpoint": "https://api.atacadao.com.br/graphql",
    "http_client_retries": 0,
    "http_client_timeout_seconds": 30
  },
  "files_created": {
    "data_batch": "data_batch.parquet",
    "raw_payload": "raw_payload.json",
    "metadata": "metadata.json"
  },
  "errors": []
}
```

---

## Naming Conventions

### Run ID Format
```
{YYYYMMDD}_{HHMMSS}_{random_8char_hex}
Example: 20250315_104530_a1b2c3d4
```

**Benefits:**
- Sortable by date
- Prevents collisions
- Easily human-readable
- UUID-safe for BigQuery

### Batch ID
```
SHA256(sorted_record_hashes)
Deterministic hash of all records in batch
→ Detects duplicates/changes
```

### File Naming
```
data_batch.parquet       # Standardized product data
raw_payload.json         # Original API/HTML responses (JSONL)
metadata.json            # Execution metadata
_SUCCESS                 # Marker file (empty)
```

---

## Metadata Fields Rationale

| Field | Why It Matters |
|-------|----------------|
| `bronze_run_id` | Audit trail - trace back to execution |
| `bronze_ingestion_timestamp` | Track when data entered system |
| `bronze_batch_id` | Detect duplicates/replays |
| `bronze_data_version` | Schema evolution tracking |
| `ean_source` | Trust scoring for identifiers |
| `collected_at` vs `bronze_ingestion_timestamp` | Distinguish collection from ingestion |
| `null_rates` in metadata | Data quality baseline |
| `_SUCCESS` marker | Atomic write guarantees |

---

## Raw Payload Preservation

### Why Store Raw Payloads?

1. **Auditability**: Prove exactly what API returned
2. **Reprocessing**: Re-parse with updated logic without re-scraping
3. **Debugging**: Troubleshoot parser issues
4. **Compliance**: Archive original sources
5. **Legal**: "We have the original data" defense

### Storage Format: JSONL (JSON Lines)

**Per-record format:**
```json
{
  "market": "atacadao",
  "search_term": "leite",
  "collected_at": "2025-03-15T10:45:31Z",
  "raw_response_type": "graphql_response",
  "raw_payload": {
    "data": {
      "search": {
        "products": {
          "edges": [...]
        }
      }
    }
  },
  "http_status": 200,
  "content_length_bytes": 15234,
  "response_time_ms": 234
}
```

---

## Partitioning Strategy

### Primary Partitioning: `market/year/month/day/run_id`

**Rationale:**
1. **market**: Separates concerns (Atacadão ≠ Carrefour)
2. **year/month/day**: Enables date-range queries
3. **run_id**: Enables per-execution atomic operations

**Query examples:**
```sql
-- All Atacadão data in March 2025
SELECT * FROM bronze WHERE market='atacadao' AND year=2025 AND month=03

-- Specific run audit
SELECT * FROM bronze WHERE run_id='20250315_104530_a1b2c3d4'

-- Data from past 7 days
SELECT * FROM bronze WHERE date BETWEEN '2025-03-08' AND '2025-03-15'
```

### Secondary Partitioning (Future)

When migrating to BigQuery, add:
- **search_term**: Group by product category
- **ean**: Deduplication key

---

## Processing Workflow

### 1. Data Ingestion
```
Scraper.search() → List[Dict]
```

### 2. Bronze Enrichment (BronzeWriter)
```python
bronze_writer.write_batch(
    market="atacadao",
    search_term="leite",
    records=results,
    raw_payloads=api_responses  # Original API responses
)
```

### 3. Storage
```
├── data_batch.parquet      (64MB → 5MB compressed Parquet)
├── raw_payload.json        (64MB JSONL for audit trail)
├── metadata.json           (1KB execution stats)
└── _SUCCESS                (0 bytes - atomic marker)
```

### 4. Validation
- ✓ Schema validation
- ✓ Null rates tracking
- ✓ Duplicate detection
- ✓ Error flagging

---

## Data Quality Checks

### Automatic Checks (BronzeWriter)

1. **Schema Validation**
   - All required fields present
   - Correct data types
   - Valid ranges (price > 0, etc)

2. **Null Rate Tracking**
   - Flag fields with >X% nulls
   - Monitor data quality drift

3. **Duplicate Detection**
   - Batch ID prevents replays
   - Market + source_product_id uniqueness

4. **Price Validation**
   - Prices > 0
   - Unit price <= retail price
   - Wholesale price <= retail price

5. **URL Validation**
   - Valid HTTP(S) URLs

---

## BigQuery Migration Path

### Step 1: Local Bronze (Current)
```
data/bronze/market=*/year=*/month=*/day=*/run_id=*/*.parquet
```

### Step 2: GCS Upload (no code change)
```bash
gsutil -m cp -r data/bronze/market=* gs://your-bucket/bronze/
```

### Step 3: BigQuery External Table
```sql
CREATE EXTERNAL TABLE projeto.bronze_raw (
  market STRING,
  product_name STRING,
  price FLOAT64,
  ...
)
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://your-bucket/bronze/market=*/year=*/month=*/day=*/run_id=*/*.parquet']
);
```

### Step 4: BigQuery Native Table (Copy)
```sql
CREATE TABLE projeto.bronze_raw_native AS
SELECT * FROM `projeto.bronze_raw`;
```

**No data reformation needed** - schema already optimized for BigQuery.

---

## Folder Organization Reference

### Top-Level Structure
```
extract_mercados/
├── scrapers/           # Extraction logic (existing)
├── common/             # Shared utilities (existing)
├── tests/              # Unit tests (existing)
├── data/
│   ├── bronze/         # ← NEW: Raw immutable data
│   ├── silver/         # ← FUTURE: Transformed data
│   └── gold/           # ← FUTURE: Aggregated data
├── BRONZE_ARCHITECTURE.md  # This file
└── README.md
```

### Bronze Directory Permissions
```
data/bronze/  → Read-only (after writing)
             → Append-only (new data)
             → Delete-only via retention policy
```

---

## Summary: Key Design Decisions

| Decision | Rationale | Benefit |
|----------|-----------|---------|
| **Parquet + JSONL** | Efficiency + Audit | 90% smaller storage, full traceability |
| **market/year/month/day/run_id** | Time-series partitioning | Fast date-range queries |
| **run_id with timestamp** | Sortable + unique | Deterministic, no UUID collision |
| **_SUCCESS marker** | Atomic writes | Prevents partial reads |
| **Metadata JSON** | Observable ETL | Data lineage, SLA monitoring |
| **Raw payloads separate** | Auditability | Reprocess without re-scraping |
| **Dual timestamps** | Precision timing | Distinguish collection from ingestion |

---

## Next Steps

1. Implement `BronzeWriter` module
2. Implement `MetadataHandler` for tracking
3. Integrate with existing scrapers
4. Create example usage patterns
5. Add unit tests
6. Document Silver layer transformation rules

---

**Version**: 1.0.0  
**Last Updated**: 2025-03-15  
**Status**: Implementation Ready
