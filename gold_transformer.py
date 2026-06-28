"""
Gold Layer Transformer

Orchestrates transformation from Silver to Gold layer:
- Loads Silver analytics-ready data
- Computes BI-optimized datasets
- Pre-calculates KPIs for dashboards
- Creates Looker Studio-ready tables
- Writes to Gold layer with metadata

Produces analytics tables:
1. products_snapshot - Current prices
2. market_prices - Price history
3. daily_kpis - Market-level KPIs
4. product_metrics - Product cross-market analysis
5. category_metrics - Category aggregations
"""

import json
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import hashlib
import time

from metrics.gold_kpis import GoldKPIEngine

logger = logging.getLogger(__name__)


@dataclass
class GoldTransformConfig:
    """Configuration for Gold layer transformations."""
    base_path: Path = Path("data/gold")
    compress: bool = True
    engine: str = "pyarrow"  # pandas.options.mode.write_engine


@dataclass
class GoldTransformationResult:
    """Result of Gold transformation."""
    transformation_id: str
    status: str  # SUCCESS, PARTIAL, FAILED
    records_input: int
    tables_created: int
    duration_ms: float
    files_created: Dict[str, str]
    errors: List[str]
    metadata_path: str
    kpi_summary: Dict


class GoldTransformer:
    """
    Transforms Silver analytics-ready data into Gold BI datasets.
    
    Creates optimized tables for Looker Studio and BigQuery:
    - products_snapshot: Current product prices and metrics
    - market_prices: Price history for trend analysis
    - daily_kpis: Market-level KPIs
    - product_metrics: Cross-market product analytics
    - category_metrics: Category-level aggregations
    """
    
    def __init__(self, config: GoldTransformConfig = None):
        """Initialize Gold transformer."""
        self.config = config or GoldTransformConfig()
        self.config.base_path.mkdir(parents=True, exist_ok=True)
        self.kpi_engine = GoldKPIEngine()
        logger.info(f"GoldTransformer initialized: base_path={self.config.base_path}")
    
    def transform_silver_to_gold(
        self,
        silver_parquet_paths: List[str],
        transformation_date: str = None
    ) -> GoldTransformationResult:
        """
        Transform Silver data to Gold analytics layer.
        
        Args:
            silver_parquet_paths: List of paths to Silver products_normalized.parquet files
            transformation_date: Date for transformation (defaults to today)
        
        Returns:
            GoldTransformationResult with operation details
        """
        
        start_time = time.time()
        transformation_id = self._generate_transformation_id()
        
        logger.info("=" * 70)
        logger.info(f"Starting Gold Transformation: {transformation_id}")
        logger.info(f"Silver Inputs: {len(silver_parquet_paths)} files")
        logger.info("=" * 70)
        
        try:
            # 1. Load Silver data
            logger.info("\n1. Loading Silver data...")
            silver_df = self._load_silver_data(silver_parquet_paths)
            records_input = len(silver_df)
            logger.info(f"   Loaded {records_input} records from Silver")
            
            if len(silver_df) == 0:
                raise ValueError("No data in Silver layer")
            
            errors = []
            files_created = {}
            
            # 2. Compute product snapshot
            logger.info("\n2. Creating products_snapshot...")
            try:
                products_snapshot = self.kpi_engine.compute_product_snapshot(silver_df)
                snapshot_path = self._write_parquet(
                    products_snapshot,
                    "products_dashboard/products_snapshot.parquet"
                )
                files_created['products_snapshot'] = snapshot_path
                logger.info(f"   {len(products_snapshot)} snapshot records")
            except Exception as e:
                errors.append(f"products_snapshot: {str(e)}")
                logger.error(f"   Error: {str(e)}")
            
            # 3. Compute market prices
            logger.info("\n3. Creating market_prices table...")
            try:
                market_prices = self.kpi_engine.compute_market_prices(silver_df)
                prices_path = self._write_parquet(
                    market_prices,
                    "price_comparison/market_prices.parquet"
                )
                files_created['market_prices'] = prices_path
                logger.info(f"   {len(market_prices)} price records")
            except Exception as e:
                errors.append(f"market_prices: {str(e)}")
                logger.error(f"   Error: {str(e)}")
            
            # 4. Compute daily KPIs
            logger.info("\n4. Computing daily_kpis...")
            try:
                daily_kpis = self.kpi_engine.compute_daily_kpis(silver_df)
                kpis_path = self._write_parquet(
                    daily_kpis,
                    "market_kpis/daily_kpis.parquet"
                )
                files_created['daily_kpis'] = kpis_path
                logger.info(f"   {len(daily_kpis)} KPI records")
                kpi_summary = daily_kpis.to_dict('records') if len(daily_kpis) > 0 else []
            except Exception as e:
                errors.append(f"daily_kpis: {str(e)}")
                logger.error(f"   Error: {str(e)}")
                kpi_summary = []
            
            # 5. Compute product metrics
            logger.info("\n5. Computing product_metrics...")
            try:
                product_metrics = self.kpi_engine.compute_product_metrics(silver_df)
                product_metrics_path = self._write_parquet(
                    product_metrics,
                    "product_intelligence/product_metrics.parquet"
                )
                files_created['product_metrics'] = product_metrics_path
                logger.info(f"   {len(product_metrics)} product metrics")
            except Exception as e:
                errors.append(f"product_metrics: {str(e)}")
                logger.error(f"   Error: {str(e)}")
            
            # 6. Compute category metrics
            logger.info("\n6. Computing category_metrics...")
            try:
                category_metrics = self.kpi_engine.compute_category_metrics(silver_df)
                category_metrics_path = self._write_parquet(
                    category_metrics,
                    "product_intelligence/category_metrics.parquet"
                )
                files_created['category_metrics'] = category_metrics_path
                logger.info(f"   {len(category_metrics)} category metrics")
            except Exception as e:
                errors.append(f"category_metrics: {str(e)}")
                logger.error(f"   Error: {str(e)}")
            
            # 7. Write metadata
            logger.info("\n7. Writing transformation metadata...")
            metadata_path = self._write_metadata(
                transformation_id,
                files_created,
                records_input
            )
            
            # Determine status
            if len(errors) == 0:
                status = "SUCCESS"
            elif len(errors) < len(files_created):
                status = "PARTIAL"
            else:
                status = "FAILED"
            
            duration_ms = (time.time() - start_time) * 1000
            
            result = GoldTransformationResult(
                transformation_id=transformation_id,
                status=status,
                records_input=records_input,
                tables_created=len(files_created),
                duration_ms=duration_ms,
                files_created=files_created,
                errors=errors,
                metadata_path=metadata_path,
                kpi_summary=kpi_summary
            )
            
            # Print summary
            logger.info("\n" + "=" * 70)
            logger.info("Gold Transformation Complete!")
            logger.info("=" * 70)
            logger.info(f"Status: {status}")
            logger.info(f"Input Records: {records_input:,}")
            logger.info(f"Tables Created: {len(files_created)}")
            logger.info(f"Duration: {duration_ms:.0f}ms ({duration_ms/1000:.1f}s)")
            logger.info(f"Metadata: {metadata_path}")
            
            if errors:
                logger.warning(f"Warnings/Errors: {len(errors)}")
                for error in errors:
                    logger.warning(f"  - {error}")
            
            logger.info("=" * 70)
            
            return result
            
        except Exception as e:
            logger.error(f"Gold transformation failed: {str(e)}", exc_info=True)
            duration_ms = (time.time() - start_time) * 1000
            
            return GoldTransformationResult(
                transformation_id=transformation_id,
                status="FAILED",
                records_input=0,
                tables_created=0,
                duration_ms=duration_ms,
                files_created={},
                errors=[str(e)],
                metadata_path="",
                kpi_summary={}
            )
    
    def _load_silver_data(self, parquet_paths: List[str]) -> pd.DataFrame:
        """Load Silver Parquet data."""
        try:
            dfs = []
            for path in parquet_paths:
                df = pd.read_parquet(path)
            
                # Ensure required columns exist
                required_cols = [
                    'market', 'product_name_normalized', 'price_normalized',
                    'unit_price', 'category_normalized', 'ean', 'collected_at'
                ]
                
                missing = [col for col in required_cols if col not in df.columns]
                if missing:
                    raise ValueError(f"Missing columns in Silver data for {path}: {missing}")
                
                # Convert collected_at to datetime if needed
                if df['collected_at'].dtype == 'object':
                    df['collected_at'] = pd.to_datetime(df['collected_at'])
                    
                dfs.append(df)
            
            return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error loading Silver data: {str(e)}")
            raise
    
    def _write_parquet(
        self,
        df: pd.DataFrame,
        relative_path: str
    ) -> str:
        """
        Write dataframe to Parquet file.
        
        Args:
            df: DataFrame to write
            relative_path: Path relative to base_path
        
        Returns:
            Full path to written file
        """
        
        file_path = self.config.base_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write Parquet
        df.to_parquet(
            str(file_path),
            compression='snappy' if self.config.compress else None,
            index=False
        )
        
        logger.debug(f"Wrote {len(df)} rows to {file_path}")
        
        return str(file_path)
    
    def _write_metadata(
        self,
        transformation_id: str,
        files_created: Dict[str, str],
        records_input: int
    ) -> str:
        """Write transformation metadata."""
        
        metadata = {
            'transformation_id': transformation_id,
            'timestamp': datetime.now().isoformat(),
            'records_input': records_input,
            'tables_created': len(files_created),
            'files': files_created,
            'schema_version': '1.0',
        }
        
        metadata_path = self.config.base_path / f"transformation_logs/gold_run_{transformation_id}.json"
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        
        def default_converter(o):
            if hasattr(o, 'item'):
                return o.item()
            if hasattr(o, 'isoformat'):
                return o.isoformat()
            raise TypeError(f'Object of type {o.__class__.__name__} is not JSON serializable')
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=default_converter)
        
        return str(metadata_path)
    
    def _generate_transformation_id(self) -> str:
        """Generate unique transformation ID."""
        timestamp = datetime.now().isoformat()
        hash_input = f"{timestamp}_{pd.Timestamp.now().nanosecond}".encode()
        hash_value = hashlib.md5(hash_input).hexdigest()[:8]
        return f"gold_{hash_value}"
