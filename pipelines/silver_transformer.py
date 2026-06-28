"""
Silver Layer Transformer

Orchestrates transformation from Bronze to Silver layer:
- Loads Bronze Parquet data
- Applies normalization transformations
- Detects and removes duplicates
- Validates data quality
- Writes to Silver layer with metadata

Follows enterprise-grade ETL patterns.
"""

import json
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import hashlib
from collections import defaultdict

from utils.normalizers import (
    normalize_product_name,
    normalize_price,
    normalize_unit,
    normalize_category,
    normalize_brand,
    normalize_ean,
    validate_ean,
    ean_is_valid_format,
    calculate_quality_score,
    calculate_data_completeness,
    extract_volume_from_name,
)
from utils.quality_checks import (
    DataQualityValidator,
    generate_quality_report,
)

logger = logging.getLogger(__name__)


@dataclass
class SilverTransformConfig:
    """Configuration for Silver layer transformations."""
    base_path: Path = Path("data/silver")
    compress: bool = True
    remove_duplicates: bool = True
    validate_quality: bool = True
    create_master_catalog: bool = True


@dataclass
class TransformationResult:
    """Result of Silver transformation."""
    transformation_id: str
    market: str
    status: str  # SUCCESS, PARTIAL, FAILED
    records_input: int
    records_output: int
    records_deduplicated: int
    duration_ms: float
    quality_score: float
    files_created: Dict[str, str]
    errors: List[str]
    metadata_path: str


class SilverTransformer:
    """
    Transforms raw Bronze data into analytics-ready Silver data.
    
    Process:
    1. Read Bronze Parquet files
    2. Validate schema
    3. Apply normalization transformations
    4. Detect duplicates
    5. Run quality checks
    6. Write to Silver with metadata
    """
    
    # Silver data schema
    SILVER_SCHEMA = {
        # Original fields
        'market': str,
        'product_name': str,
        'price': float,
        'unit_price': float,
        'category': str,
        'brand': str,
        'source_product_id': str,
        'sku': str,
        'ean': str,
        'searched_ean': str,
        'ean_source': str,
        'search_term': str,
        'cep': str,
        'collected_at': str,
        'source_url': str,
        'image_url': str,
        'wholesale_price': float,
        
        # Silver normalization fields
        'product_name_normalized': str,
        'price_normalized': float,
        'unit_normalized': str,
        'category_normalized': str,
        'brand_normalized': str,
        'ean_normalized': str,
        'ean_valid': bool,
        
        # Quality & deduplication
        'is_duplicate': bool,
        'duplicate_count': int,
        'quality_score': float,
        'quality_flags': str,  # JSON array as string
        'data_completeness': float,
        
        # Lineage
        'bronze_run_id': str,
        'silver_transformation_id': str,
        'silver_ingestion_timestamp': str,
    }
    
    def __init__(self, config: SilverTransformConfig = None):
        """Initialize Silver transformer."""
        self.config = config or SilverTransformConfig()
        self.config.base_path.mkdir(parents=True, exist_ok=True)
        self.quality_validator = DataQualityValidator()
        logger.info(f"SilverTransformer initialized: base_path={self.config.base_path}")
    
    def transform_bronze(
        self,
        bronze_parquet_path: str,
        market: str,
        search_term: str,
    ) -> TransformationResult:
        """
        Transform Bronze Parquet to Silver.
        
        Args:
            bronze_parquet_path: Path to Bronze data_batch.parquet
            market: Market name
            search_term: Search term used for extraction
        
        Returns:
            TransformationResult with operation details
        """
        start_time = datetime.utcnow()
        errors = []
        
        try:
            # Generate transformation ID
            transformation_id = self._generate_transformation_id()
            
            logger.info(f"Starting transformation: {transformation_id}")
            logger.info(f"  Market: {market}")
            logger.info(f"  Search term: {search_term}")
            
            # 1. Load Bronze data
            logger.info("Loading Bronze data...")
            df_bronze = pd.read_parquet(bronze_parquet_path)
            records_input = len(df_bronze)
            logger.info(f"  Loaded {records_input} records")
            
            # 2. Apply transformations
            logger.info("Applying transformations...")
            df_transformed = self._apply_transformations(df_bronze)
            
            # 3. Detect duplicates
            logger.info("Detecting duplicates...")
            df_dedup, dup_count = self._remove_duplicates(df_transformed)
            records_output = len(df_dedup)
            
            # 4. Validate quality
            logger.info("Running quality checks...")
            quality_result = self.quality_validator.check_quality(df_dedup, market)
            
            if quality_result.status == 'CRITICAL':
                errors.append(f"Critical quality issues: {quality_result.issues}")
            
            # 5. Create partition folder
            transformation_path = self._create_transformation_folder(market, transformation_id)
            
            # 6. Write Silver data
            files_created = {}
            
            # Write Parquet
            parquet_path = transformation_path / "products_normalized.parquet"
            self._write_parquet(df_dedup, parquet_path)
            files_created['products'] = str(parquet_path)
            logger.info(f"  Written {records_output} records to Parquet")
            
            # 7. Generate metadata
            metadata = self._generate_metadata(
                transformation_id=transformation_id,
                market=market,
                search_term=search_term,
                records_input=records_input,
                records_output=records_output,
                records_deduplicated=dup_count,
                start_time=start_time,
                quality_result=quality_result,
                errors=errors,
                bronze_path=bronze_parquet_path,
            )
            
            metadata_path = transformation_path / "transformation_metadata.json"
            self._write_metadata(metadata, metadata_path)
            files_created['metadata'] = str(metadata_path)
            
            # 8. Write _SUCCESS marker
            success_marker = transformation_path / "_SUCCESS"
            success_marker.touch()
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            status = "PARTIAL" if errors else "SUCCESS"
            
            result = TransformationResult(
                transformation_id=transformation_id,
                market=market,
                status=status,
                records_input=records_input,
                records_output=records_output,
                records_deduplicated=dup_count,
                duration_ms=duration_ms,
                quality_score=quality_result.quality_score,
                files_created=files_created,
                errors=errors,
                metadata_path=str(metadata_path)
            )
            
            logger.info(
                f"Transformation complete: "
                f"{records_output} records (deduplicated {dup_count}) "
                f"in {duration_ms:.2f}ms"
            )
            
            return result
        
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            error_msg = f"Transformation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return TransformationResult(
                transformation_id="",
                market=market,
                status="FAILED",
                records_input=0,
                records_output=0,
                records_deduplicated=0,
                duration_ms=duration_ms,
                quality_score=0.0,
                files_created={},
                errors=[error_msg],
                metadata_path=""
            )
    
    def _apply_transformations(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply all normalization transformations."""
        df = df.copy()
        
        # Normalize product names
        df['product_name_normalized'] = df['product_name'].apply(normalize_product_name)
        
        # Normalize prices
        df['price_normalized'] = df['price'].apply(normalize_price)
        
        # Normalize units
        df['unit_normalized'] = df.apply(
            lambda row: normalize_unit(self._extract_unit(row['product_name'])),
            axis=1
        )
        
        # Normalize categories
        df['category_normalized'] = df['category'].apply(normalize_category)
        
        # Normalize brands
        df['brand_normalized'] = df['brand'].apply(normalize_brand)
        
        # Normalize EANs
        df['ean_normalized'] = df['ean'].apply(normalize_ean)
        df['ean_valid'] = df['ean'].apply(ean_is_valid_format)
        
        # Calculate quality scores
        df['quality_score'] = df.apply(
            lambda row: calculate_quality_score(row.to_dict()),
            axis=1
        )
        
        df['data_completeness'] = df.apply(
            lambda row: calculate_data_completeness(row.to_dict()),
            axis=1
        )
        
        # Initialize deduplication flags
        df['is_duplicate'] = False
        df['duplicate_count'] = 0
        df['quality_flags'] = df.apply(self._get_quality_flags, axis=1)
        
        return df
    
    def _remove_duplicates(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """
        Detect and remove duplicates.
        
        Priority (keep):
        1. Valid EAN
        2. Higher data completeness
        3. Most recent (by collected_at)
        4. Lower price (best for consumers)
        """
        if not self.config.remove_duplicates:
            return df, 0
        
        # Group by: (market, ean_normalized, normalized_name)
        groups = defaultdict(list)
        dup_count = 0
        
        for idx, row in df.iterrows():
            key = (
                row['market'],
                row['ean_normalized'],
                row['product_name_normalized']
            )
            groups[key].append(idx)
        
        indices_to_keep = []
        
        for key, indices in groups.items():
            if len(indices) == 1:
                # No duplicate
                indices_to_keep.append(indices[0])
            else:
                # Duplicates found - keep best
                records = df.loc[indices]
                
                # Sort by priority
                best_idx = records.sort_values(
                    by=[
                        'ean_valid',           # Valid EAN first
                        'data_completeness',   # More complete second
                        'collected_at',        # Most recent third
                        'price'                # Lowest price last
                    ],
                    ascending=[False, False, False, True]
                ).index[0]
                
                indices_to_keep.append(best_idx)
                dup_count += len(indices) - 1
                
                # Mark duplicates
                for idx in indices:
                    if idx != best_idx:
                        df.at[idx, 'is_duplicate'] = True
                        df.at[idx, 'duplicate_of_id'] = best_idx
                
                # Record duplicate count
                df.loc[best_idx, 'duplicate_count'] = len(indices) - 1
        
        # Return only non-duplicates
        df_dedup = df.loc[indices_to_keep].copy()
        
        logger.info(f"Removed {dup_count} duplicates")
        
        return df_dedup, dup_count
    
    def _create_transformation_folder(self, market: str, transformation_id: str) -> Path:
        """Create partition folder for transformation."""
        now = datetime.utcnow()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")
        
        path = (
            self.config.base_path
            / f"market={market}"
            / f"year={year}"
            / f"month={month}"
            / f"day={day}"
            / f"transformation_id={transformation_id}"
        )
        
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created folder: {path}")
        
        return path
    
    def _write_parquet(self, df: pd.DataFrame, path: Path) -> None:
        """Write DataFrame to Parquet."""
        compression = "snappy" if self.config.compress else None
        df.to_parquet(path, engine="pyarrow", compression=compression, index=False)
        logger.debug(f"Written Parquet to {path}")
    
    def _write_metadata(self, metadata: Dict, path: Path) -> None:
        """Write metadata JSON."""
        def default_converter(o):
            if hasattr(o, 'item'):
                return o.item()
            if hasattr(o, 'isoformat'):
                return o.isoformat()
            raise TypeError(f'Object of type {o.__class__.__name__} is not JSON serializable')
            
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=default_converter)
        logger.debug(f"Written metadata to {path}")
    
    def _generate_transformation_id(self) -> str:
        """Generate unique transformation ID: YYYYMMDD_SV_random4hex"""
        now = datetime.utcnow()
        timestamp = now.strftime("%Y%m%d")
        random_hex = hashlib.md5(str(datetime.utcnow()).encode()).hexdigest()[:4]
        return f"{timestamp}_SV_{random_hex}"
    
    def _extract_unit(self, product_name: str) -> Optional[str]:
        """Extract unit from product name."""
        if not product_name:
            return None
        
        _, unit = extract_volume_from_name(product_name)
        return unit
    
    def _get_quality_flags(self, row: dict) -> str:
        """Generate quality flags for record."""
        flags = []
        
        # Check for issues
        if row.get('ean_valid') == False and row.get('ean'):
            flags.append('invalid_ean')
        
        if row.get('price', 0) < 0.01 or row.get('price', 0) > 100000:
            flags.append('price_outlier')
        
        if row.get('brand') is None:
            flags.append('missing_brand')
        
        if row.get('data_completeness', 100) < 50:
            flags.append('low_completeness')
        
        if row.get('category_normalized') == 'Uncategorized':
            flags.append('uncategorized')
        
        return json.dumps(flags)
    
    def _generate_metadata(
        self,
        transformation_id: str,
        market: str,
        search_term: str,
        records_input: int,
        records_output: int,
        records_deduplicated: int,
        start_time: datetime,
        quality_result,
        errors: List[str],
        bronze_path: str,
    ) -> Dict:
        """Generate comprehensive transformation metadata."""
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        metadata = {
            'silver_layer_version': '1.0.0',
            'transformation_id': transformation_id,
            'market': market,
            'search_term': search_term,
            'execution': {
                'started_at': start_time.isoformat() + 'Z',
                'completed_at': end_time.isoformat() + 'Z',
                'duration_seconds': round(duration, 3),
                'status': 'FAILED' if errors else 'SUCCESS'
            },
            'transformations': {
                'records_input': records_input,
                'records_deduplicated': records_deduplicated,
                'records_output': records_output,
                'deduplication_rate': round(records_deduplicated / records_input, 4) if records_input > 0 else 0,
            },
            'quality': {
                'overall_status': quality_result.status,
                'quality_score': quality_result.quality_score,
                'checks_passed': quality_result.passed_checks,
                'checks_total': quality_result.total_checks,
                'issues': quality_result.issues,
                'recommendations': quality_result.recommendations,
            },
            'lineage': {
                'bronze_source': str(bronze_path),
            },
            'errors': errors if errors else None
        }
        
        return metadata


# ============================================================================
# Convenience Functions
# ============================================================================

def get_silver_transformer(base_path: str = "data/silver") -> SilverTransformer:
    """Factory function to create SilverTransformer."""
    config = SilverTransformConfig(base_path=Path(base_path))
    return SilverTransformer(config)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    transformer = SilverTransformer()
    
    # Example: Find a Bronze parquet and transform it
    bronze_path = "data/bronze/market=atacadao/year=2025/month=03/day=15/run_id=*/data_batch.parquet"
    
    import glob
    files = glob.glob(bronze_path)
    
    if files:
        result = transformer.transform_bronze(
            bronze_parquet_path=files[0],
            market="atacadao",
            search_term="leite"
        )
        
        print(f"\n{'='*60}")
        print(f"Transformation Result:")
        print(f"  Status: {result.status}")
        print(f"  Transformation ID: {result.transformation_id}")
        print(f"  Input: {result.records_input} records")
        print(f"  Output: {result.records_output} records")
        print(f"  Deduplicated: {result.records_deduplicated}")
        print(f"  Quality Score: {result.quality_score:.1f}/100")
        print(f"  Duration: {result.duration_ms:.2f}ms")
        print(f"{'='*60}")
    else:
        print(f"No Bronze Parquet files found at {bronze_path}")
