"""
Silver Layer Normalization Module

Provides reusable normalization functions for cleaning and standardizing
product data from various supermarket sources.

Functions:
- Product names
- Prices
- Units
- Categories
- Brands
- EAN validation
"""

import re
import unicodedata
from typing import Optional, Tuple, Dict
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS & MAPPINGS
# ============================================================================

UNIT_CONVERSIONS = {
    # Liquids (to ml)
    'L': 1000,
    'l': 1000,
    'liter': 1000,
    'litre': 1000,
    'ml': 1,
    'milliliter': 1,
    
    # Weight (to g)
    'kg': 1000,
    'kilogram': 1000,
    'g': 1,
    'gram': 1,
    'mg': 0.001,
    
    # Units (no conversion)
    'un': 1,
    'unit': 1,
    'pc': 1,
    'piece': 1,
    'pcs': 1,
    'pç': 1,
    'pça': 1,
}

CATEGORY_MAPPING = {
    # Dairy & Milk
    'laticínios': 'Laticínios',
    'leite': 'Laticínios',
    'leites': 'Laticínios',
    'leite e derivados': 'Laticínios',
    'queijo': 'Laticínios',
    'queijos': 'Laticínios',
    'iogurte': 'Laticínios',
    'iogurtes': 'Laticínios',
    'derivados do leite': 'Laticínios',
    'mantega': 'Laticínios',
    'manteiga': 'Laticínios',
    'requeijão': 'Laticínios',
    
    # Beverages
    'bebidas': 'Bebidas',
    'bebida': 'Bebidas',
    'bebidas não alcoólicas': 'Bebidas',
    'sucos': 'Bebidas',
    'suco': 'Bebidas',
    'refrigerante': 'Bebidas',
    'refrigerantes': 'Bebidas',
    'água': 'Bebidas',
    'bebida láctea': 'Bebidas',
    'bebidas lácteas': 'Bebidas',
    'café': 'Bebidas',
    'chá': 'Bebidas',
    
    # Meats
    'carnes': 'Carnes',
    'carne': 'Carnes',
    'frango': 'Carnes',
    'peixes': 'Carnes',
    'peixe': 'Carnes',
    'embutidos': 'Carnes',
    'embutido': 'Carnes',
    
    # Fruits & Vegetables
    'frutas': 'Frutas & Vegetais',
    'fruta': 'Frutas & Vegetais',
    'verduras': 'Frutas & Vegetais',
    'verdura': 'Frutas & Vegetais',
    'legumes': 'Frutas & Vegetais',
    'legume': 'Frutas & Vegetais',
    
    # Bakery
    'padaria': 'Padaria',
    'pão': 'Padaria',
    'pães': 'Padaria',
    'bolos': 'Padaria',
    'bolo': 'Padaria',
    'biscoitos': 'Padaria',
    'biscoito': 'Padaria',
    
    # Pantry
    'alimentos': 'Pantry',
    'alimento': 'Pantry',
    'arroz': 'Pantry',
    'feijão': 'Pantry',
    'macarrão': 'Pantry',
    'massa': 'Pantry',
    'óleo': 'Pantry',
    'sal': 'Pantry',
    'açúcar': 'Pantry',
}

BRAND_ALIASES = {
    'Parmalat S/A': 'Parmalat',
    'Parmalat Ltda': 'Parmalat',
    'Nestlé S/A': 'Nestlé',
    'Nestle': 'Nestlé',
    'P&G': 'Procter & Gamble',
    'Kimberly Clark': 'Kimberly-Clark',
    'Unilever Brasil': 'Unilever',
    'Coca Cola': 'Coca-Cola',
    'Ambev': 'Ambev',
    'Pepsico': 'PepsiCo',
}


# ============================================================================
# PRODUCT NAME NORMALIZATION
# ============================================================================

def normalize_product_name(name: Optional[str]) -> Optional[str]:
    """
    Normalize product name for matching and display.
    
    Transformations:
    - Trim whitespace
    - Remove accents
    - Title case
    - Remove extra spaces
    - Keep only alphanumeric, space, dash, parentheses
    
    Args:
        name: Raw product name
    
    Returns:
        Normalized name or None
    """
    if not name or not isinstance(name, str):
        return None
    
    # Trim & lowercase
    normalized = name.strip().lower()
    
    # Remove accents (normalize NFKD form)
    normalized = ''.join(
        c for c in unicodedata.normalize('NFKD', normalized)
        if not unicodedata.combining(c)
    )
    
    # Remove extra whitespace
    normalized = ' '.join(normalized.split())
    
    # Title case
    normalized = normalized.title()
    
    # Keep only alphanumeric, space, dash, parentheses, forward slash
    normalized = re.sub(r'[^a-zA-Z0-9\s\-()\/]', '', normalized)
    
    # Remove multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized if normalized else None


def extract_volume_from_name(name: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Extract volume/quantity from product name.
    
    Examples:
    - "Leite Integral 1L" → (1.0, "L")
    - "Café 500g" → (500.0, "g")
    - "Ovos 12 unidades" → (12.0, "un")
    
    Returns:
        (quantity, unit) or (None, None)
    """
    if not name:
        return None, None
    
    # Pattern: number + unit
    pattern = r'(\d+(?:[.,]\d+)?)\s*(l|ml|kg|g|mg|un|pc|pç|pça)'
    match = re.search(pattern, name.lower())
    
    if match:
        quantity_str = match.group(1).replace(',', '.')
        quantity = float(quantity_str)
        unit = match.group(2)
        return quantity, unit
    
    return None, None


# ============================================================================
# PRICE NORMALIZATION
# ============================================================================

def normalize_price(price: Optional[float]) -> Optional[float]:
    """
    Normalize price to float.
    
    Validations:
    - Must be positive
    - Must be numeric
    - Flags extreme values (< 0.01 or > 100000)
    
    Args:
        price: Raw price (can be int, float, str, None)
    
    Returns:
        Normalized price or None
    """
    if price is None or price == '':
        return None
    
    try:
        if isinstance(price, str):
            # Remove currency symbols & spaces
            price_str = re.sub(r'[R$\s,]', '', price)
            price_str = price_str.replace('.', '').replace(',', '.')
            price = float(price_str)
        else:
            price = float(price)
        
        # Validate range
        if price < 0.01 or price > 100000:
            logger.warning(f"Price out of reasonable range: {price}")
            return None
        
        return round(price, 2)
    
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse price: {price} - {e}")
        return None


def validate_price_consistency(price: float, unit_price: float) -> bool:
    """
    Validate that unit_price <= retail_price.
    
    Args:
        price: Retail price
        unit_price: Unit price (per L, per Kg, etc)
    
    Returns:
        True if valid, False otherwise
    """
    if not price or not unit_price:
        return True  # Can't validate if missing
    
    # Unit price should typically be <= retail price
    if unit_price > price * 1.1:  # Allow 10% margin
        return False
    
    return True


# ============================================================================
# UNIT NORMALIZATION
# ============================================================================

def normalize_unit(unit: Optional[str]) -> Optional[str]:
    """
    Normalize unit abbreviations.
    
    Args:
        unit: Raw unit (L, ml, kg, g, un, pc, etc)
    
    Returns:
        Normalized unit or None
    """
    if not unit:
        return None
    
    unit_clean = unit.strip().lower()
    
    # Direct mapping
    for key, value in UNIT_CONVERSIONS.items():
        if unit_clean == key:
            # Return standard form
            if key in ['L', 'l']:
                return 'L'
            elif key in ['ml']:
                return 'ml'
            elif key in ['kg']:
                return 'kg'
            elif key in ['g']:
                return 'g'
            else:
                return 'un'  # Default to units
    
    return None


def convert_to_base_unit(quantity: float, unit: str) -> float:
    """
    Convert quantity to base unit (ml for liquids, g for weight, un for units).
    
    Args:
        quantity: Numeric quantity
        unit: Unit abbreviation
    
    Returns:
        Quantity in base unit
    """
    if not quantity or not unit:
        return quantity
    
    unit_lower = unit.lower()
    conversion = UNIT_CONVERSIONS.get(unit_lower, 1)
    
    return quantity * conversion


# ============================================================================
# CATEGORY NORMALIZATION
# ============================================================================

def normalize_category(raw_category: Optional[str]) -> str:
    """
    Map raw category to standardized taxonomy.
    
    Args:
        raw_category: Market-specific category
    
    Returns:
        Standardized category or 'Uncategorized'
    """
    if not raw_category:
        return 'Uncategorized'
    
    # Normalize for lookup
    key = raw_category.lower().strip()
    
    # Direct lookup
    if key in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[key]
    
    # Fuzzy matching (contains)
    for pattern, standard_category in CATEGORY_MAPPING.items():
        if pattern in key or key in pattern:
            return standard_category
    
    return 'Uncategorized'


def get_category_hierarchy(category: str) -> list:
    """
    Get category hierarchy for navigation.
    
    Example:
    "Laticínios" → ["Laticínios"]
    
    Could expand to nested hierarchy if needed.
    """
    return [category]


# ============================================================================
# BRAND NORMALIZATION
# ============================================================================

def normalize_brand(raw_brand: Optional[str]) -> Optional[str]:
    """
    Normalize brand name.
    
    Transformations:
    - Trim whitespace
    - Title case
    - Remove legal suffixes (S/A, LTDA, Inc, Ltd)
    - Apply brand aliases
    - Remove duplicates
    
    Args:
        raw_brand: Raw brand name
    
    Returns:
        Normalized brand or None
    """
    if not raw_brand or not isinstance(raw_brand, str):
        return None
    
    # Trim & title case
    brand = raw_brand.strip().title()
    
    # Remove legal suffixes
    suffixes = [' S/A', ' LTDA', ' Ltda', ' Inc', ' Ltd', ' LLC', ' Ltda.', ' S/A.']
    for suffix in suffixes:
        brand = brand.replace(suffix, '').strip()
    
    # Remove extra whitespace
    brand = ' '.join(brand.split())
    
    # Apply aliases
    brand = BRAND_ALIASES.get(brand, brand)
    
    # Remove duplicates (e.g., "Leite Parmalat Leite" → "Leite Parmalat")
    words = brand.split()
    seen = set()
    unique_words = []
    for word in words:
        if word.lower() not in seen:
            unique_words.append(word)
            seen.add(word.lower())
    brand = ' '.join(unique_words)
    
    return brand if brand else None


# ============================================================================
# EAN VALIDATION & NORMALIZATION
# ============================================================================

def normalize_ean(ean: Optional[str]) -> Optional[str]:
    """
    Normalize EAN by removing non-digits.
    
    Args:
        ean: Raw EAN (can have dashes, spaces, etc)
    
    Returns:
        Cleaned EAN (digits only) or None
    """
    if not ean:
        return None
    
    # Remove non-digits
    ean_clean = re.sub(r'\D', '', str(ean))
    
    # Check length
    if len(ean_clean) not in [8, 12, 13, 14]:
        return None
    
    return ean_clean


def validate_ean(ean: Optional[str]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate EAN using check digit algorithm.
    
    Supports: EAN-8, EAN-12, EAN-13, EAN-14
    
    Args:
        ean: EAN to validate
    
    Returns:
        (is_valid, cleaned_ean, error_message)
    """
    if not ean:
        return False, None, "Empty EAN"
    
    # Normalize (remove non-digits)
    ean_clean = normalize_ean(ean)
    
    if not ean_clean:
        return False, None, f"Invalid format: {ean}"
    
    # Check length
    if len(ean_clean) not in [8, 12, 13, 14]:
        return False, ean_clean, f"Invalid length: {len(ean_clean)}"
    
    # Verify check digit for EAN-13 (most common)
    if len(ean_clean) == 13:
        expected_check = calculate_ean13_checksum(ean_clean[:12])
        actual_check = int(ean_clean[12])
        
        if expected_check != actual_check:
            return False, ean_clean, f"Invalid check digit: expected {expected_check}, got {actual_check}"
    
    # Could add EAN-8, EAN-12, EAN-14 validation here
    # For now, accept if format is correct
    
    return True, ean_clean, None


def calculate_ean13_checksum(ean_12: str) -> int:
    """
    Calculate EAN-13 check digit.
    
    Algorithm:
    1. Multiply digits at odd positions by 1, even positions by 3
    2. Sum all products
    3. Check digit = (10 - (sum % 10)) % 10
    
    Args:
        ean_12: First 12 digits of EAN-13
    
    Returns:
        Check digit (0-9)
    """
    total = 0
    for i, digit in enumerate(ean_12):
        weight = 1 if i % 2 == 0 else 3
        total += int(digit) * weight
    
    check_digit = (10 - (total % 10)) % 10
    return check_digit


def ean_is_valid_format(ean: Optional[str]) -> bool:
    """Quick check if EAN has valid format."""
    if not ean:
        return False
    is_valid, _, _ = validate_ean(ean)
    return is_valid


# ============================================================================
# QUALITY SCORING
# ============================================================================

def calculate_data_completeness(record: Dict) -> float:
    """
    Calculate % of non-null fields.
    
    Args:
        record: Data record
    
    Returns:
        Completeness score (0-100)
    """
    if not record:
        return 0.0
    
    # Fields to check
    important_fields = [
        'market', 'product_name', 'price', 'category', 'brand', 'ean'
    ]
    
    non_null_count = sum(1 for field in important_fields if record.get(field))
    
    completeness = (non_null_count / len(important_fields)) * 100
    return round(completeness, 1)


def calculate_quality_score(record: Dict) -> float:
    """
    Calculate overall data quality score (0-100).
    
    Factors:
    - Data completeness (40%)
    - Valid EAN (30%)
    - Valid price (20%)
    - Brand present (10%)
    
    Args:
        record: Data record
    
    Returns:
        Quality score (0-100)
    """
    score = 0.0
    
    # Data completeness (40%)
    completeness = calculate_data_completeness(record)
    score += (completeness / 100) * 40
    
    # Valid EAN (30%)
    ean_valid = ean_is_valid_format(record.get('ean'))
    score += 30 if ean_valid else 0
    
    # Valid price (20%)
    price = record.get('price')
    price_valid = price is not None and 0.01 <= price <= 100000
    score += 20 if price_valid else 0
    
    # Brand present (10%)
    brand_present = bool(record.get('brand'))
    score += 10 if brand_present else 0
    
    return round(score, 1)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def remove_duplicate_words(text: str) -> str:
    """Remove duplicate consecutive words from text."""
    if not text:
        return text
    
    words = text.split()
    result = [words[0]] if words else []
    
    for word in words[1:]:
        if word.lower() != result[-1].lower():
            result.append(word)
    
    return ' '.join(result)


def sanitize_string(text: str) -> str:
    """Remove special characters, keep only alphanumeric and spaces."""
    if not text:
        return text
    
    return re.sub(r'[^a-zA-Z0-9\s\-]', '', text).strip()


if __name__ == "__main__":
    # Example usage
    
    # Product name
    name = "  LEITE  INTEGRAL PARMALAT 1L  "
    print(f"Original: {name}")
    print(f"Normalized: {normalize_product_name(name)}")
    
    # Price
    price = "R$ 4,50"
    print(f"\nOriginal price: {price}")
    print(f"Normalized: {normalize_price(price)}")
    
    # EAN
    ean = "7894001234567"
    valid, clean, error = validate_ean(ean)
    print(f"\nEAN: {ean}")
    print(f"Valid: {valid}, Clean: {clean}, Error: {error}")
    
    # Category
    category = "Laticínios"
    print(f"\nOriginal category: {category}")
    print(f"Normalized: {normalize_category(category)}")
    
    # Brand
    brand = "PARMALAT S/A"
    print(f"\nOriginal brand: {brand}")
    print(f"Normalized: {normalize_brand(brand)}")
