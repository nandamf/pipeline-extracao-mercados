MARKET_NAME = "carrefour"

SOURCE_URL = "https://mercado.carrefour.com.br/"
SEARCH_URL = "https://mercado.carrefour.com.br/busca/{search_term}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0.0.0 Safari/537.36"
    )
}

DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
