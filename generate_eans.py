"""
Utilitário para gerar lista de EANs confiáveis a partir do Mix Mateus.

Este script pesquisa termos genéricos no Mix Mateus, extrai os EANs e nomes,
e salva no arquivo inputs/produtos.csv para alimentar a pipeline principal.
"""

import pandas as pd
import logging
from pathlib import Path

from scrapers.registry import get_scraper
from utils.normalizers import validate_ean

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)

def generate_ean_list(search_terms, output_path="inputs/produtos.csv", cep=None):
    scraper = get_scraper("mix_mateus")
    all_products = []

    for term in search_terms:
        logger.info(f"Buscando produtos genéricos para: '{term}'")
        # Busca apenas 1 página de resultados para cada termo
        records = scraper.search(search_term=term, cep=cep, max_pages=1)
        
        for r in records:
            # Pega o EAN bruto retornado pelo scraper
            ean_raw = r.get("ean")
            if ean_raw:
                # Passa pelo validador oficial do projeto para ter certeza de que é um EAN real
                is_valid, clean_ean, _ = validate_ean(str(ean_raw))
                if is_valid:
                    all_products.append({
                        "ean": clean_ean,
                        "descricao_referencia": r.get("product_name", "")
                    })

    if not all_products:
        logger.warning("Nenhum produto com EAN encontrado.")
        return

    # Cria DataFrame, remove EANs duplicados e cria a pasta de destino
    df = pd.DataFrame(all_products)
    df = df.drop_duplicates(subset=["ean"])
    
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Salva no formato CSV esperado pela pipeline
    df.to_csv(out_file, index=False)
    logger.info(f"SUCESSO: Foram salvos {len(df)} EANs únicos no arquivo {output_path}")

if __name__ == "__main__":
    # Categorias e produtos populares para extração de EANs
    TERMOS_GENERICOS = [
        "arroz",
        "feijão",
        "leite",
        "café",
        "óleo",
        "macarrão",
        "açúcar",
        "sal",
        "farinha",
        "manteiga",
        "margarina",
        "requeijão",
        "queijo",
        "presunto",
        "frango",
        "carne",
        "picanha",
        "linguiça",
        "ovo",
        "iogurte",
        "creme de leite",
        "leite condensado",
        "achocolatado",
        "chocolate",
        "biscoito",
        "bolacha",
        "pão",
        "mortadela",
        "salsicha",
        "hambúrguer",
        "pizza",
        "lasanha",
        "refrigerante",
        "coca cola",
        "guaraná",
        "fanta",
        "sprite",
        "água mineral",
        "suco",
        "banana",
        "maçã",
        "laranja",
        "uva",
        "mamão",
        "melancia",
        "abacaxi",
        "batata",
        "cebola",
        "alho",
        "tomate",
        "cenoura",
        "alface",
        "repolho",
        "pepino",
        "sabão em pó",
        "amaciante",
        "detergente",
        "água sanitária",
        "papel higiênico",
        "shampoo",
        "condicionador",
        "sabonete",
        "creme dental",
        "desodorante",
        "absorvente",
        "fralda",
        "ração para gato",
        "ração para cachorro",
        "cerveja",
        "vinho",
        "energético",
        "cereal",
        "aveia",
        "granola",
        "mel",
        "maionese",
        "ketchup",
        "mostarda",
        "molho de tomate",
        "atum",
        "sardinha",
        "milho verde",
        "ervilha",
        "pipoca",
        "amendoim",
        "castanha",
        "sorvete",
        "açaí"
    ]
    generate_ean_list(TERMOS_GENERICOS)