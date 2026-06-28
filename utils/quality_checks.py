"""
Silver Layer Data Quality Module

Validates and monitors data quality for Silver layer transformations.

Features:
- Null rate tracking
- Price validation
- EAN validation
- Duplicate detection
- Quality scoring
- Comprehensive quality reports
"""

import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

from utils.normalizers import (
    validate_ean,
    calculate_quality_score,
    calculate_data_completeness,
    ean_is_valid_format
)

logger = logging.getLogger(__name__)


@dataclass
class QualityCheckResult:
    """Result of quality checks."""
    status: str  # OK, WARNING, ALERT, CRITICAL
    total_checks: int
    passed_checks: int
    issues: Dict[str, Any]
    quality_score: float  # 0-100
    recommendations: List[str]


class DataQualityValidator:
    """
    Validates Silver layer data quality.
    
    Checks:
    - Null rates
    - Price validation
    - EAN validation
    - Duplicate detection
    - Data completeness
    """
    
    # Quality thresholds
    QUALITY_THRESHOLDS = {
        'null_rates': {
            'market': 0.0,          # No nulls allowed
            'product_name': 0.0,    # No nulls allowed
            'price': 0.05,          # ≤5% nulls
            'ean': 0.20,            # ≤20% nulls
            'brand': 0.30,          # ≤30% nulls
            'category': 0.10,       # ≤10% nulls
        },
        'price_range': {
            'min': 0.01,            # R$0.01 minimum
            'max': 100000,          # R$100k maximum
        },
        'ean_validity': {
            'min_valid_rate': 0.80,  # ≥80% valid EANs
        },
        'data_completeness': {
            'min_score': 50.0,       # ≥50% field completeness
        },
        'quality_score': {
            'min_score': 60.0,       # ≥60 overall quality
        }
    }
    
    def check_quality(self, df: pd.DataFrame, market: str = None) -> QualityCheckResult:
        """
        Run comprehensive quality checks.
        
        Args:
            df: DataFrame with Silver layer data
            market: Market name (for context)
        
        Returns:
            QualityCheckResult with detailed findings
        """
        issues = {}
        checks_passed = 0
        total_checks = 7  # Number of check categories
        
        logger.info(f"Running quality checks on {len(df)} records...")
        
        # 1. Null rate checks
        null_issues = self._check_null_rates(df)
        if null_issues:
            issues['null_rates'] = null_issues
        else:
            checks_passed += 1
        
        # 2. Price validation
        price_issues = self._check_prices(df)
        if price_issues:
            issues['price_validation'] = price_issues
        else:
            checks_passed += 1
        
        # 3. EAN validation
        ean_issues = self._check_eams(df)
        if ean_issues:
            issues['ean_validation'] = ean_issues
        else:
            checks_passed += 1
        
        # 4. Duplicate detection
        dup_issues = self._check_duplicates(df)
        if dup_issues:
            issues['duplicates'] = dup_issues
        else:
            checks_passed += 1
        
        # 5. Data completeness
        completeness_issues = self._check_completeness(df)
        if completeness_issues:
            issues['completeness'] = completeness_issues
        else:
            checks_passed += 1
        
        # 6. Brand validation
        brand_issues = self._check_brands(df)
        if brand_issues:
            issues['brands'] = brand_issues
        else:
            checks_passed += 1
        
        # 7. Category validation
        category_issues = self._check_categories(df)
        if category_issues:
            issues['categories'] = category_issues
        else:
            checks_passed += 1
        
        # Calculate overall quality score
        quality_score = (checks_passed / total_checks) * 100
        
        # Determine status
        status = self._determine_status(checks_passed, total_checks, quality_score)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(issues)
        
        return QualityCheckResult(
            status=status,
            total_checks=total_checks,
            passed_checks=checks_passed,
            issues=issues,
            quality_score=quality_score,
            recommendations=recommendations
        )
    
    def _check_null_rates(self, df: pd.DataFrame) -> Dict:
        """Check null rates against thresholds."""
        issues = {}
        
        for column, threshold in self.QUALITY_THRESHOLDS['null_rates'].items():
            if column not in df.columns:
                continue
            
            null_count = df[column].isna().sum()
            null_rate = null_count / len(df) if len(df) > 0 else 0
            
            if null_rate > threshold:
                issues[column] = {
                    'null_count': int(null_count),
                    'null_rate': round(null_rate, 4),
                    'threshold': threshold,
                    'severity': 'CRITICAL' if threshold == 0.0 else 'WARNING'
                }
        
        return issues if issues else None
    
    def _check_prices(self, df: pd.DataFrame) -> Dict:
        """Validate prices."""
        if 'price' not in df.columns:
            return None
        
        issues = {}
        prices = df['price'].dropna()
        
        if len(prices) == 0:
            return {'all_null': 'All prices are null'}
        
        # Check range
        out_of_range = df[(df['price'] < self.QUALITY_THRESHOLDS['price_range']['min']) |
                          (df['price'] > self.QUALITY_THRESHOLDS['price_range']['max'])]
        
        if len(out_of_range) > 0:
            issues['out_of_range'] = {
                'count': len(out_of_range),
                'rate': round(len(out_of_range) / len(df), 4),
                'examples': out_of_range['price'].head(3).tolist()
            }
        
        # Check outliers (3 std dev)
        mean_price = prices.mean()
        std_price = prices.std()
        outliers = prices[prices > mean_price + 3 * std_price]
        
        if len(outliers) > 0:
            issues['outliers'] = {
                'count': len(outliers),
                'rate': round(len(outliers) / len(prices), 4),
                'mean': round(mean_price, 2),
                'std_dev': round(std_price, 2),
                'threshold': round(mean_price + 3 * std_price, 2)
            }
        
        # Check negative prices
        negative = df[df['price'] < 0]
        if len(negative) > 0:
            issues['negative_prices'] = {
                'count': len(negative),
                'examples': negative['price'].head(3).tolist()
            }
        
        return issues if issues else None
    
    def _check_eams(self, df: pd.DataFrame) -> Dict:
        """Validate EANs."""
        if 'ean' not in df.columns:
            return None
        
        issues = {}
        
        # Count valid EANs
        valid_count = 0
        invalid_eams = []
        
        for idx, ean in df['ean'].items():
            if pd.isna(ean):
                continue
            
            is_valid, cleaned, error = validate_ean(ean)
            if is_valid:
                valid_count += 1
            else:
                if len(invalid_eams) < 5:  # Keep first 5 examples
                    invalid_eams.append({'ean': ean, 'error': error})
        
        total_non_null = df['ean'].notna().sum()
        valid_rate = valid_count / total_non_null if total_non_null > 0 else 0
        
        if valid_rate < self.QUALITY_THRESHOLDS['ean_validity']['min_valid_rate']:
            issues['low_validity_rate'] = {
                'valid_count': valid_count,
                'valid_rate': round(valid_rate, 4),
                'threshold': self.QUALITY_THRESHOLDS['ean_validity']['min_valid_rate'],
                'invalid_examples': invalid_eams
            }
        
        return issues if issues else None
    
    def _check_duplicates(self, df: pd.DataFrame) -> Dict:
        """Detect duplicates."""
        if 'duplicate_count' not in df.columns:
            return None
        
        issues = {}
        
        # Duplicates detected
        dup_count = df['duplicate_count'].sum()
        if dup_count > 0:
            dup_rate = dup_count / len(df)
            issues['duplicates_removed'] = {
                'count': int(dup_count),
                'rate': round(dup_rate, 4),
                'unique_records_removed': int(df[df['duplicate_count'] > 0].shape[0])
            }
        
        # Check if any records marked as is_duplicate
        if 'is_duplicate' in df.columns:
            marked_dups = (df['is_duplicate'] == True).sum()
            if marked_dups > 0:
                issues['marked_duplicates'] = {
                    'count': int(marked_dups),
                    'rate': round(marked_dups / len(df), 4)
                }
        
        return issues if issues else None
    
    def _check_completeness(self, df: pd.DataFrame) -> Dict:
        """Check data completeness."""
        issues = {}
        
        if len(df) == 0:
            return {'no_data': 'Empty dataset'}
        
        # Calculate completeness for each record
        completeness_scores = []
        for _, row in df.iterrows():
            score = calculate_data_completeness(row.to_dict())
            completeness_scores.append(score)
        
        avg_completeness = sum(completeness_scores) / len(completeness_scores)
        min_completeness = min(completeness_scores)
        
        if avg_completeness < self.QUALITY_THRESHOLDS['data_completeness']['min_score']:
            issues['low_completeness'] = {
                'avg_score': round(avg_completeness, 1),
                'min_score': round(min_completeness, 1),
                'threshold': self.QUALITY_THRESHOLDS['data_completeness']['min_score'],
                'incomplete_records': sum(1 for s in completeness_scores if s < 50)
            }
        
        return issues if issues else None
    
    def _check_brands(self, df: pd.DataFrame) -> Dict:
        """Validate brands."""
        if 'brand' not in df.columns:
            return None
        
        issues = {}
        
        # Check for missing brands
        missing_brands = df['brand'].isna().sum()
        if missing_brands > 0:
            missing_rate = missing_brands / len(df)
            if missing_rate > 0.20:  # Alert if >20%
                issues['missing_brands'] = {
                    'count': int(missing_brands),
                    'rate': round(missing_rate, 4),
                    'threshold': 0.20
                }
        
        # Check for 'unknown' or suspicious brands
        if 'brand' in df.columns:
            suspicious = df[df['brand'].str.lower().isin(['unknown', 'not specified', 'n/a', 'none'])].shape[0]
            if suspicious > 0:
                issues['suspicious_brands'] = {
                    'count': suspicious,
                    'rate': round(suspicious / len(df), 4)
                }
        
        return issues if issues else None
    
    def _check_categories(self, df: pd.DataFrame) -> Dict:
        """Validate categories."""
        if 'category_normalized' not in df.columns:
            return None
        
        issues = {}
        
        # Check for uncategorized
        uncategorized = (df['category_normalized'] == 'Uncategorized').sum()
        if uncategorized > 0:
            uncategorized_rate = uncategorized / len(df)
            if uncategorized_rate > 0.10:  # Alert if >10%
                issues['high_uncategorized'] = {
                    'count': uncategorized,
                    'rate': round(uncategorized_rate, 4),
                    'threshold': 0.10
                }
        
        return issues if issues else None
    
    def _determine_status(self, passed: int, total: int, quality_score: float) -> str:
        """Determine overall status."""
        if passed == total and quality_score >= 90:
            return 'OK'
        elif passed >= total * 0.7 and quality_score >= 70:
            return 'WARNING'
        elif passed >= total * 0.5 and quality_score >= 50:
            return 'ALERT'
        else:
            return 'CRITICAL'
    
    def _generate_recommendations(self, issues: Dict) -> List[str]:
        """Generate recommendations based on issues."""
        recommendations = []
        
        if 'null_rates' in issues:
            for col, data in issues['null_rates'].items():
                if data.get('severity') == 'CRITICAL':
                    recommendations.append(
                        f"Fill or remove records with missing {col} (critical field)"
                    )
                else:
                    recommendations.append(
                        f"Investigate missing {col} ({data['null_rate']*100:.1f}% null)"
                    )
        
        if 'price_validation' in issues:
            price_issues = issues['price_validation']
            if 'out_of_range' in price_issues:
                recommendations.append(
                    f"Review {price_issues['out_of_range']['count']} out-of-range prices"
                )
            if 'outliers' in price_issues:
                recommendations.append(
                    f"Investigate {price_issues['outliers']['count']} price outliers"
                )
        
        if 'ean_validation' in issues:
            if 'low_validity_rate' in issues['ean_validation']:
                recommendations.append(
                    "Improve EAN quality - many invalid EANs detected"
                )
        
        if 'duplicates' in issues:
            dup_info = issues['duplicates'].get('duplicates_removed')
            if dup_info:
                recommendations.append(
                    f"Duplicates detected and removed ({dup_info['rate']*100:.1f}%)"
                )
        
        if 'completeness' in issues:
            recommendations.append(
                "Improve data completeness - many records missing key fields"
            )
        
        return recommendations


# ============================================================================
# Summary Report Generation
# ============================================================================

def generate_quality_report(result: QualityCheckResult) -> str:
    """
    Generate human-readable quality report.
    
    Args:
        result: QualityCheckResult from check_quality()
    
    Returns:
        Formatted report string
    """
    report = []
    report.append("\n" + "=" * 70)
    report.append("DATA QUALITY REPORT")
    report.append("=" * 70)
    
    report.append(f"\nStatus: {result.status}")
    report.append(f"Quality Score: {result.quality_score:.1f}/100")
    report.append(f"Checks Passed: {result.passed_checks}/{result.total_checks}")
    
    if result.issues:
        report.append("\nIssues Found:")
        report.append("-" * 70)
        for category, details in result.issues.items():
            report.append(f"\n  {category.upper()}:")
            if isinstance(details, dict):
                for key, value in details.items():
                    report.append(f"    - {key}: {value}")
            else:
                report.append(f"    {details}")
    
    if result.recommendations:
        report.append("\nRecommendations:")
        report.append("-" * 70)
        for i, rec in enumerate(result.recommendations, 1):
            report.append(f"  {i}. {rec}")
    
    report.append("\n" + "=" * 70 + "\n")
    
    return "\n".join(report)


if __name__ == "__main__":
    # Example usage
    import pandas as pd
    from datetime import datetime
    
    # Create sample data
    sample_data = {
        'market': ['atacadao', 'carrefour', 'mix_mateus', None],
        'product_name': ['Leite Integral', 'Café Premium', 'Pão Francês', 'Queijo Meia Cura'],
        'price': [4.50, 15.99, 2.50, 35.00],
        'ean': ['7894001234567', None, '123', '7894567890123'],
        'brand': ['Parmalat', 'Café do Brasil', None, 'Queijaria Mineira'],
        'category_normalized': ['Laticínios', 'Bebidas', 'Padaria', 'Laticínios'],
        'duplicate_count': [0, 0, 1, 0],
    }
    
    df = pd.DataFrame(sample_data)
    
    # Run quality checks
    validator = DataQualityValidator()
    result = validator.check_quality(df)
    
    # Print report
    report = generate_quality_report(result)
    print(report)
