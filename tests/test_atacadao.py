import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from scrapers.atacadao.scraper import AtacadaoScraper


def main():

    scraper = AtacadaoScraper()

    termos = pd.read_csv(
        "inputs/produtos.csv"
    )

    all_records = []

    for termo in termos["termo"]:

        print(f"\nColetando: {termo}")

        try:

            records = scraper.search(
                search_term=str(termo),
                cep="58053024",
                max_pages=1
            )

            print(
                f"Encontrados {len(records)} produtos"
            )

            if records:
                all_records.extend(records)

        except Exception as e:

            print(
                f"Erro ao coletar '{termo}': {e}"
            )

    if not all_records:

        print(
            "Nenhum produto foi coletado."
        )

        return

    df_final = pd.DataFrame(
        all_records
    )

    print(
        f"\nTotal coletado: {len(df_final)}"
    )

    print(
        df_final.head()
    )


if __name__ == "__main__":
    main()
