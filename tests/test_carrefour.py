import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from scrapers.carrefour.scraper import (
    CarrefourScraper
)

scraper = CarrefourScraper()

produtos = pd.read_csv(
    "inputs/produtos.csv"
)

for ean in produtos["ean"]:

    records = scraper.search(
        search_term=str(ean),
        cep="58053024"
    )

    print(
        records[:5]
    )
