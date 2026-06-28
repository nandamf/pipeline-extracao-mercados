"""
Gold Layer KPI Engine

Computes business metrics and KPIs from Silver data:
- Daily market KPIs (average price, volatility, etc)
- Product-level analytics (price spread, competitiveness)
- Category-level metrics
- Data quality indicators

Optimized for Looker Studio dashboarding.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MarketKPI:
    """Daily KPI for a market."""
    kpi_date: str
    market: str
    market_name: str
    total_products: int
    avg_price: float
    median_price: float
    price_std_dev: float
    price_min: float
    price_max: float
    price_volatility_index: float
    data_completeness: float
    new_products_count: int
    price_change_count: int
    avg_price_change_pct: float


class GoldKPIEngine:
    """
    Computes business KPIs from Silver analytics-ready data.
    
    Process:
    1. Load Silver products_normalized
    2. Group by market and date
    3. Calculate daily KPIs per market
    4. Calculate product-level metrics
    5. Calculate category-level metrics
    """
    
    # Market friendly names
    MARKET_NAMES = {
        'atacadao': 'Atacadão',
        'carrefour': 'Carrefour',
        'mix_mateus': 'Mix Mateus',
    }
    
    def __init__(self):
        """Initialize KPI engine."""
        logger.info("GoldKPIEngine initialized")
    
    def compute_daily_kpis(
        self,
        silver_df: pd.DataFrame,
        collection_date: str = None
    ) -> pd.DataFrame:
        """
        Compute daily market KPIs.
        
        Args:
            silver_df: Silver layer products_normalized dataframe
            collection_date: Target date (defaults to latest in data)
        
        Returns:
            DataFrame with daily KPIs per market
            
        Columns:
            kpi_date, market, market_name, total_products, avg_price,
            median_price, price_std_dev, price_min, price_max,
            price_volatility_index, data_completeness, new_products_count,
            price_change_count, avg_price_change_pct
        """
        
        if collection_date is None:
            collection_date = silver_df['collected_at'].dt.date.max()
        
        logger.info(f"Computing daily KPIs for date: {collection_date}")
        
        # Filter to specific date
        target_date = pd.Timestamp(collection_date).date()
        daily_data = silver_df[
            silver_df['collected_at'].dt.date == target_date
        ].copy()
        
        if len(daily_data) == 0:
            logger.warning(f"No data for date {collection_date}")
            return pd.DataFrame()
        
        kpis = []
        
        for market in daily_data['market'].unique():
            market_data = daily_data[daily_data['market'] == market].copy()
            
            # Calculate metrics
            prices = market_data['price_normalized'].dropna()
            unit_prices = market_data['unit_price'].dropna()
            
            if len(prices) == 0:
                continue
            
            # Basic statistics
            total_products = len(market_data)
            avg_price = float(prices.mean())
            median_price = float(prices.median())
            price_std_dev = float(prices.std()) if len(prices) > 1 else 0.0
            if pd.isna(price_std_dev):
                price_std_dev = 0.0
            price_min = float(prices.min())
            price_max = float(prices.max())
            
            # Volatility index: coefficient of variation
            if median_price > 0 and price_std_dev > 0:
                volatility_index = (price_std_dev / median_price) * 100
            else:
                volatility_index = 0.0
            
            # Data completeness
            has_price = market_data['price_normalized'].notna().sum()
            data_completeness = (has_price / total_products * 100) if total_products > 0 else 0
            
            # Price changes (if quality flags are available)
            if 'quality_flags' in market_data.columns:
                price_change_count = market_data[
                    market_data['quality_flags'].astype(str).str.contains('PRICE_CHANGE', na=False)
                ].shape[0]
            else:
                price_change_count = 0
            
            # Average price change percentage
            if 'price_change_pct' in market_data.columns:
                avg_price_change_pct = float(
                    market_data['price_change_pct'].dropna().mean()
                ) if market_data['price_change_pct'].notna().sum() > 0 else 0.0
            else:
                avg_price_change_pct = 0.0
            
            # New products (EANs not seen before)
            # Simplified: check if product_name contains 'novo' or similar
            new_products = 0
            
            kpi = {
                'kpi_date': str(collection_date),
                'market': market,
                'market_name': self.MARKET_NAMES.get(market, market.title()),
                'total_products': total_products,
                'avg_price': round(avg_price, 2),
                'median_price': round(median_price, 2),
                'price_std_dev': round(price_std_dev, 2),
                'price_min': round(price_min, 2),
                'price_max': round(price_max, 2),
                'price_volatility_index': round(volatility_index, 2),
                'data_completeness': round(data_completeness, 2),
                'new_products_count': new_products,
                'price_change_count': price_change_count,
                'avg_price_change_pct': round(avg_price_change_pct, 2),
            }
            
            kpis.append(kpi)
            
            logger.info(
                f"  {market}: {total_products} products, "
                f"avg=${avg_price:.2f}, volatility={volatility_index:.1f}%"
            )
        
        return pd.DataFrame(kpis)
    
    def compute_product_metrics(
        self,
        silver_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Compute product-level analytics across markets.
        
        Args:
            silver_df: Silver layer dataframe
        
        Returns:
            DataFrame with product metrics
            
        Columns:
            product_id, ean, product_name, category, brand, volume,
            markets_selling, cheapest_market, cheapest_price,
            most_expensive_market, most_expensive_price, price_spread,
            price_spread_pct, avg_price_across_markets,
            last_collected, days_since_update, price_competitiveness_score
        """
        
        logger.info("Computing product-level metrics")
        
        # Group by product (using EAN as key, but also track by name for consistency)
        product_metrics = []
        
        # Get latest collection date
        latest_date = silver_df['collected_at'].max()
        
        for ean, ean_data in silver_df.groupby('ean'):
            if pd.isna(ean):
                continue
            
            # Get latest record per market
            latest_records = ean_data.sort_values('collected_at').groupby('market').tail(1)
            
            if len(latest_records) == 0:
                continue
            
            # Aggregate across markets
            prices = latest_records['price_normalized'].dropna()
            
            if len(prices) == 0:
                continue
            
            markets_selling = len(latest_records)
            cheapest_idx = prices.idxmin()
            cheapest_market = latest_records.loc[cheapest_idx, 'market']
            cheapest_price = float(prices.min())
            
            most_expensive_idx = prices.idxmax()
            most_expensive_market = latest_records.loc[most_expensive_idx, 'market']
            most_expensive_price = float(prices.max())
            
            price_spread_dollars = most_expensive_price - cheapest_price
            if cheapest_price > 0:
                price_spread_pct = (price_spread_dollars / cheapest_price) * 100
            else:
                price_spread_pct = 0.0
            
            avg_price = float(prices.mean())
            
            # Competitiveness score: how consistent are prices?
            # High consistency (low variation) = high score
            price_variance = float(prices.var())
            if price_variance > 0:
                competitiveness = max(0, 100 - (price_variance * 10))
            else:
                competitiveness = 100.0
            
            product_name = latest_records['product_name_normalized'].iloc[0]
            category = latest_records['category_normalized'].iloc[0]
            brand = latest_records['brand_normalized'].iloc[0]
            last_collected = latest_records['collected_at'].max()
            
            days_since = (latest_date - last_collected).days
            
            metric = {
                'product_id': f"{ean}",
                'ean': ean,
                'product_name': product_name,
                'category': category,
                'brand': brand,
                'volume': latest_records['unit_normalized'].iloc[0],
                'markets_selling': markets_selling,
                'cheapest_market': self.MARKET_NAMES.get(cheapest_market, cheapest_market),
                'cheapest_price': round(cheapest_price, 2),
                'most_expensive_market': self.MARKET_NAMES.get(most_expensive_market, most_expensive_market),
                'most_expensive_price': round(most_expensive_price, 2),
                'price_spread': round(price_spread_dollars, 2),
                'price_spread_pct': round(price_spread_pct, 2),
                'avg_price_across_markets': round(avg_price, 2),
                'last_collected': str(last_collected),
                'days_since_update': days_since,
                'price_competitiveness_score': round(competitiveness, 1),
            }
            
            product_metrics.append(metric)
        
        logger.info(f"  Computed metrics for {len(product_metrics)} products")
        
        return pd.DataFrame(product_metrics)
    
    def compute_category_metrics(
        self,
        silver_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Compute category-level analytics by market.
        
        Args:
            silver_df: Silver layer dataframe
        
        Returns:
            DataFrame with category metrics
            
        Columns:
            category_id, market, market_name, category, product_count,
            avg_price, median_price, price_range_min, price_range_max,
            price_competitiveness, last_updated
        """
        
        logger.info("Computing category-level metrics")
        
        category_metrics = []
        
        # Group by market and category
        for (market, category), group in silver_df.groupby(['market', 'category_normalized']):
            
            prices = group['price_normalized'].dropna()
            
            if len(prices) == 0:
                continue
            
            product_count = group['ean'].nunique()
            avg_price = float(prices.mean())
            median_price = float(prices.median())
            price_min = float(prices.min())
            price_max = float(prices.max())
            last_updated = group['collected_at'].max()
            
            # Competitiveness: std dev relative to median
            price_std = float(prices.std())
            if median_price > 0:
                competitiveness = max(0, 100 - (price_std / median_price * 100))
            else:
                competitiveness = 100.0
            
            metric = {
                'category_id': f"{market}_{category}",
                'market': market,
                'market_name': self.MARKET_NAMES.get(market, market.title()),
                'category': category,
                'product_count': product_count,
                'avg_price': round(avg_price, 2),
                'median_price': round(median_price, 2),
                'price_range_min': round(price_min, 2),
                'price_range_max': round(price_max, 2),
                'price_competitiveness': round(competitiveness, 1),
                'last_updated': str(last_updated),
            }
            
            category_metrics.append(metric)
        
        logger.info(f"  Computed metrics for {len(category_metrics)} market-category combinations")
        
        return pd.DataFrame(category_metrics)
    
    def compute_product_snapshot(
        self,
        silver_df: pd.DataFrame,
        collection_date: str = None
    ) -> pd.DataFrame:
        """
        Create current products snapshot for dashboard.
        
        Args:
            silver_df: Silver layer dataframe
            collection_date: Target date (defaults to latest)
        
        Returns:
            DataFrame with current product prices
            
        Columns:
            product_id, market, ean, product_name, category, brand,
            current_price, previous_price, price_change_pct, is_cheapest,
            volume, collected_at, collection_date, market_name,
            data_quality_score
        """
        
        if collection_date is None:
            collection_date = silver_df['collected_at'].dt.date.max()
        
        logger.info(f"Creating product snapshot for {collection_date}")
        
        # Filter to target date
        target_date = pd.Timestamp(collection_date).date()
        snapshot_data = silver_df[
            silver_df['collected_at'].dt.date == target_date
        ].copy()
        
        if len(snapshot_data) == 0:
            logger.warning(f"No data for {collection_date}")
            return pd.DataFrame()
        
        # Get latest price per market/product
        latest = snapshot_data.sort_values('collected_at').groupby(['market', 'ean']).tail(1)
        
        # Determine cheapest per category
        cheapest_per_category = latest.loc[
            latest.groupby('category_normalized')['price_normalized'].idxmin(),
            ['category_normalized', 'ean']
        ].reset_index(drop=True)
        cheapest_per_category.columns = ['category_normalized', 'cheapest_ean']
        
        # Merge to mark cheapest products
        latest = latest.merge(
            cheapest_per_category,
            on='category_normalized',
            how='left'
        )
        latest['is_cheapest'] = (latest['ean'] == latest['cheapest_ean']).astype(int)
        
        # Build snapshot
        snapshot = []
        for idx, row in latest.iterrows():
            item = {
                'product_id': f"{row['market']}_{row['ean']}",
                'market': row['market'],
                'ean': row['ean'],
                'product_name': row['product_name_normalized'],
                'category': row['category_normalized'],
                'brand': row['brand_normalized'],
                'current_price': round(row['price_normalized'], 2),
                'previous_price': None,  # Would need historical data
                'price_change_pct': row.get('price_change_pct', 0),
                'is_cheapest': row['is_cheapest'],
                'volume': row.get('unit_normalized', ''),
                'collected_at': str(row['collected_at']),
                'collection_date': str(collection_date),
                'market_name': self.MARKET_NAMES.get(row['market'], row['market'].title()),
                'data_quality_score': round(row.get('quality_score', 0), 1),
            }
            snapshot.append(item)
        
        logger.info(f"  Created snapshot for {len(snapshot)} product-market combinations")
        
        return pd.DataFrame(snapshot)
    
    def compute_market_prices(
        self,
        silver_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Create price history table for trend analysis.
        
        Args:
            silver_df: Silver layer dataframe
        
        Returns:
            DataFrame with all price observations
            
        Columns:
            price_id, market, ean, product_name, price, unit_price,
            price_date, collection_timestamp, category, volume
        """
        
        logger.info("Creating market prices table")
        
        prices_table = []
        
        for idx, row in silver_df.iterrows():
            # Infer price tier
            price = row['price_normalized']
            if pd.isna(price):
                continue
            
            if price < 10:
                price_tier = 'Budget'
            elif price < 50:
                price_tier = 'Standard'
            else:
                price_tier = 'Premium'
            
            item = {
                'price_id': f"{idx}_{row['market']}_{row['ean']}",
                'market': row['market'],
                'ean': row['ean'],
                'product_name': row['product_name_normalized'],
                'price': round(price, 2),
                'unit_price': round(row['unit_price'], 2),
                'price_date': str(row['collected_at'].date()),
                'collection_timestamp': str(row['collected_at']),
                'category': row['category_normalized'],
                'price_tier': price_tier,
                'volume': row.get('unit_normalized', ''),
            }
            
            prices_table.append(item)
        
        logger.info(f"  Created market prices table with {len(prices_table)} records")
        
        return pd.DataFrame(prices_table)
