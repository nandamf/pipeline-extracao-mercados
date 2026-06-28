"""
Bronze Layer Writer

Handles immutable storage of raw extracted data with full traceability.
Implements enterprise-grade ETL practices for portfolio projects.

Features:
- Automatic folder partitioning (market/year/month/day/run_id)
- Dual storage: Parquet (efficient) + JSONL (audit trail)
- Metadata tracking and data quality checks
- Atomic writes with _SUCCESS markers
- Schema validation and null rate tracking
"""

import json
import hashlib
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
import logging
import uuid
from dataclasses import dataclass, asdict
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)


@dataclass
class BronzeWriteConfig:
    """Configuration for Bronze layer writes."""
    base_path: Path = Path("data/bronze")
    compress: bool = True  # Gzip compression for Parquet
    schema_validation: bool = True
    null_rate_threshold: float = 0.50  # Flag fields with >50% nulls
    preserve_raw_payloads: bool = True


@dataclass
class WriteResult:
    """Result of a Bronze write operation."""
    run_id: str
    market: str
    search_term: str
    records_written: int
    files_created: Dict[str, str]
    execution_duration_ms: float
    status: str  # SUCCESS, PARTIAL, FAILED
    errors: List[str]
    metadata_path: str


class BronzeWriter:
    """
    Manages immutable writes to Bronze layer with full traceability.
    
    Design principles:
    - Immutable: Once written, data never changes
    - Atomic: All-or-nothing writes
    - Auditable: Raw payloads preserved
    - Observable: Complete metadata tracked
    """
    
    # Bronze data schema (required fields + types)
    BRONZE_SCHEMA = {
        "market": str,
        "product_name": str,
        "price": (float, type(None)),
        "unit_price": (float, type(None)),
        "category": (str, type(None)),
        "brand": (str, type(None)),
        "source_product_id": (str, type(None)),
        "sku": (str, type(None)),
        "ean": (str, type(None)),
        "searched_ean": (str, type(None)),
        "ean_source": (str, type(None)),
        "search_term": str,
        "cep": (str, type(None)),
        "collected_at": str,
        "source_url": (str, type(None)),
        "image_url": (str, type(None)),
        "wholesale_price": (float, type(None)),
    }
    
    # Fields that must not be null
    REQUIRED_FIELDS = {"market", "product_name", "search_term", "collected_at"}
    
    def __init__(self, config: BronzeWriteConfig = None):
        """Initialize Bronze writer."""
        self.config = config or BronzeWriteConfig()
        self.config.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"BronzeWriter initialized: base_path={self.config.base_path}")
    
    def write_batch(
        self,
        market: str,
        search_term: str,
        records: List[Dict[str, Any]],
        raw_payloads: Optional[List[Dict[str, Any]]] = None,
        cep: Optional[str] = None,
    ) -> WriteResult:
        """
        Write a batch of records to Bronze layer.
        
        Args:
            market: Market name (atacadao, carrefour, mix_mateus)
            search_term: What was searched
            records: List of product records
            raw_payloads: Original API responses (optional, for audit trail)
            cep: CEP used for search (optional)
        
        Returns:
            WriteResult with operation details
        """
        start_time = datetime.utcnow()
        errors = []
        
        try:
            # Validate inputs
            if not records:
                logger.warning(f"Empty batch for {market}/{search_term}")
                return WriteResult(
                    run_id="",
                    market=market,
                    search_term=search_term,
                    records_written=0,
                    files_created={},
                    execution_duration_ms=0,
                    status="FAILED",
                    errors=["Empty batch"],
                    metadata_path=""
                )
            
            # Generate unique run ID
            run_id = self._generate_run_id()
            
            # Create folder structure: market/year/month/day/run_id/
            run_path = self._create_run_folder(market, run_id)
            
            # Enrich records with Bronze metadata
            enriched_records = self._enrich_records(records, market, run_id)
            
            # Validate schema
            if self.config.schema_validation:
                validation_errors = self._validate_schema(enriched_records)
                if validation_errors:
                    errors.extend(validation_errors)
            
            # Write files
            files_created = {}
            
            # 1. Write Parquet data
            parquet_path = run_path / "data_batch.parquet"
            df = pd.DataFrame(enriched_records)
           
            self._write_parquet(df, parquet_path)
            files_created["data_batch"] = str(parquet_path)
            logger.info(f"  Written {len(df)} records to {parquet_path}")
            
            # 2. Write raw payloads (JSONL for audit)
            if self.config.preserve_raw_payloads and raw_payloads:
                jsonl_path = run_path / "raw_payload.json"
                self._write_jsonl(raw_payloads, jsonl_path)
                files_created["raw_payload"] = str(jsonl_path)
                logger.info(f" Written raw payloads to {jsonl_path}")
            
            # 3. Write metadata
            metadata = self._generate_metadata(
                run_id=run_id,
                market=market,
                search_term=search_term,
                records=enriched_records,
                files_created=files_created,
                start_time=start_time,
                errors=errors,
                raw_payloads=raw_payloads,
                cep=cep
            )
            metadata_path = run_path / "metadata.json"
            self._write_metadata(metadata, metadata_path)
            files_created["metadata"] = str(metadata_path)
            
            # 4. Write _SUCCESS marker (atomic write indicator)
            success_marker = run_path / "_SUCCESS"
            success_marker.touch()
            logger.info(f"  Write successful - marker created")
            
            # Calculate duration
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            status = "PARTIAL" if errors else "SUCCESS"
            
            result = WriteResult(
                run_id=run_id,
                market=market,
                search_term=search_term,
                records_written=len(enriched_records),
                files_created=files_created,
                execution_duration_ms=duration_ms,
                status=status,
                errors=errors,
                metadata_path=str(metadata_path)
            )
            
            logger.info(
                f"  Bronze write complete: {result.records_written} records in "
                f"{result.execution_duration_ms:.2f}ms"
            )
            
            return result
        
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            error_msg = f"Bronze write failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return WriteResult(
                run_id="",
                market=market,
                search_term=search_term,
                records_written=0,
                files_created={},
                execution_duration_ms=duration_ms,
                status="FAILED",
                errors=[error_msg],
                metadata_path=""
            )
    
    def _generate_run_id(self) -> str:
        """
        Generate unique run ID: YYYYMMDD_HHMMSS_random8char
        
        Benefits:
        - Sortable by datetime
        - Collision-resistant
        - Human-readable
        """
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        random_hex = uuid.uuid4().hex[:8]
        return f"{timestamp}_{random_hex}"
    
    def _create_run_folder(self, market: str, run_id: str) -> Path:
        """
        Create partitioned folder: market/year/month/day/run_id/
        
        Example: data/bronze/market=atacadao/year=2025/month=03/day=15/run_id=20250315_104530_a1b2c3d4/
        """
        now = datetime.utcnow()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")
        
        run_path = (
            self.config.base_path
            / f"market={market}"
            / f"year={year}"
            / f"month={month}"
            / f"day={day}"
            / f"run_id={run_id}"
        )
        
        run_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created folder structure: {run_path}")
        return run_path
    
    def _enrich_records(
        self,
        records: List[Dict[str, Any]],
        market: str,
        run_id: str
    ) -> List[Dict[str, Any]]:
        """Add Bronze metadata to each record."""
        bronze_ingestion_timestamp = datetime.utcnow().isoformat() + "Z"
        enriched = []
        
        for record in records:
            enriched_record = record.copy()
            enriched_record.update({
                "bronze_ingestion_timestamp": bronze_ingestion_timestamp,
                "bronze_run_id": run_id,
                "bronze_data_version": "1.0.0",
                "bronze_error_flag": False,
            })
            enriched.append(self._normalize_record_types(enriched_record))
        
        return enriched
    
    def _normalize_record_types(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize record types ahead of schema validation."""
        normalized = record.copy()
        for field, expected_type in self.BRONZE_SCHEMA.items():
            value = normalized.get(field)
            if value is None:
                continue

            if expected_type == str or (isinstance(expected_type, tuple) and str in expected_type):
                if not isinstance(value, str):
                    normalized[field] = str(value)

            if expected_type == float or (isinstance(expected_type, tuple) and float in expected_type):
                if isinstance(value, int):
                    normalized[field] = float(value)
                elif isinstance(value, str):
                    try:
                        normalized[field] = float(value.replace(',', '.'))
                    except ValueError:
                        pass

        return normalized

    def _validate_schema(self, records: List[Dict[str, Any]]) -> List[str]:
        """Validate records against schema."""
        errors = []
        
        if not records:
            return errors
        
        for i, record in enumerate(records):
            # Check required fields
            for required_field in self.REQUIRED_FIELDS:
                if required_field not in record or record[required_field] is None:
                    errors.append(
                        f"Record {i}: Missing required field '{required_field}'"
                    )
            
            # Check field types
            for field, expected_type in self.BRONZE_SCHEMA.items():
                if field not in record:
                    continue
                
                value = record[field]
                if value is None:
                    continue
                
                # Handle nullable types
                if isinstance(expected_type, tuple):
                    if not isinstance(value, expected_type):
                        errors.append(
                            f"Record {i}: Field '{field}' expected "
                            f"{expected_type}, got {type(value)}"
                        )
                else:
                    if not isinstance(value, expected_type):
                        errors.append(
                            f"Record {i}: Field '{field}' expected "
                            f"{expected_type}, got {type(value)}"
                        )
        
        return errors
    
    def _write_parquet(self, df: pd.DataFrame, path: Path) -> None:
        """Write DataFrame to Parquet with compression."""
        compression = "gzip" if self.config.compress else None
        df.to_parquet(
            path,
            engine="pyarrow",
            compression=compression,
            index=False
        )
        logger.debug(f"Parquet written to {path}")
    
    def _write_jsonl(self, payloads: List[Dict[str, Any]], path: Path) -> None:
        """Write raw payloads as JSONL (one JSON per line)."""
        with open(path, "w", encoding="utf-8") as f:
            for payload in payloads:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        logger.debug(f"JSONL written to {path}")
    
    def _write_metadata(self, metadata: Dict[str, Any], path: Path) -> None:
        """Write metadata JSON."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.debug(f"Metadata written to {path}")
    
    def _generate_metadata(
        self,
        run_id: str,
        market: str,
        search_term: str,
        records: List[Dict[str, Any]],
        files_created: Dict[str, str],
        start_time: datetime,
        errors: List[str],
        raw_payloads: Optional[List[Dict[str, Any]]] = None,
        cep: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive metadata for audit trail."""
        
        # Calculate null rates
        df = pd.DataFrame(records)
        null_rates = {}
        for col in df.columns:
            null_count = df[col].isna().sum()
            null_rate = null_count / len(df) if len(df) > 0 else 0
            if null_rate > 0:
                null_rates[col] = round(null_rate, 4)
        
        # Calculate batch hash for duplicate detection
        batch_id = self._calculate_batch_id(records)
        
        now = datetime.utcnow()
        duration_seconds = (now - start_time).total_seconds()
        
        metadata = {
            "bronze_layer_version": "1.0.0",
            "run_id": run_id,
            "market": market,
            "search_term": search_term,
            "cep": cep,
            "execution": {
                "started_at": start_time.isoformat() + "Z",
                "completed_at": now.isoformat() + "Z",
                "duration_seconds": round(duration_seconds, 3),
                "status": "FAILED" if errors else "SUCCESS"
            },
            "data_quality": {
                "total_records": len(records),
                "valid_records": len(records) - len(errors),
                "invalid_records": len(errors),
                "null_rates": null_rates,
                "batch_id": batch_id
            },
            "files_created": files_created,
            "errors": errors if errors else None
        }
        
        return metadata
    
    def _calculate_batch_id(self, records: List[Dict[str, Any]]) -> str:
        """
        Calculate SHA256 hash of batch for duplicate detection.
        Deterministic: same records = same hash.
        """
        # Sort records for deterministic hashing
        sorted_data = json.dumps(
            sorted(records, key=lambda x: json.dumps(x, sort_keys=True, default=str)),
            sort_keys=True,
            default=str
        )
        return hashlib.sha256(sorted_data.encode()).hexdigest()


# ============================================================================
# Convenience Functions
# ============================================================================

def get_bronze_writer(base_path: str = "data/bronze") -> BronzeWriter:
    """Factory function to create BronzeWriter."""
    config = BronzeWriteConfig(base_path=Path(base_path))
    return BronzeWriter(config)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    writer = BronzeWriter()
    
    # Sample data from scraper
    sample_records = [
        {
            "market": "atacadao",
            "product_name": "Leite Integral Parmalat 1L",
            "price": 4.50,
            "unit_price": 4.50,
            "category": "Laticínios",
            "brand": "Parmalat",
            "source_product_id": "123456789",
            "sku": "SKU123",
            "ean": "7894001234567",
            "searched_ean": None,
            "ean_source": "market_response",
            "search_term": "leite",
            "cep": "04543010",
            "collected_at": "2025-03-15T10:45:31Z",
            "source_url": "https://api.atacadao.com.br",
            "image_url": "https://cdn.atacadao.com.br/image.jpg",
            "wholesale_price": 3.99,
        }
    ]
    
    result = writer.write_batch(
        market="atacadao",
        search_term="leite",
        records=sample_records,
        cep="04543010"
    )
    
    print(f"\n{'='*60}")
    print(f"Write Result:")
    print(f"  Status: {result.status}")
    print(f"  Run ID: {result.run_id}")
    print(f"  Records: {result.records_written}")
    print(f"  Duration: {result.execution_duration_ms:.2f}ms")
    print(f"  Metadata: {result.metadata_path}")
    print(f"{'='*60}")
