"""
Script de Depuração - API do Atacadão

Faz uma requisição direta à API do Atacadão e exibe o payload bruto (Raw JSON)
para investigarmos em qual campo o verdadeiro EAN está escondido.
"""

import json
from scrapers.registry import get_scraper

def debug_atacadao(search_term="leite", cep="04543010"):
    print("=" * 60)
    print("Iniciando Depuração do Atacadão")
    print("=" * 60)
    
    scraper = get_scraper("atacadao")
    
    print(f"1. Resolvendo CEP {cep}...")
    region = scraper.client.get_region(cep)
    print(f"   Region ID: {region.get('region_id')} | Seller ID: {region.get('seller_id')}")
    
    print(f"2. Buscando 1 produto com o termo '{search_term}'...")
    raw_data = scraper.client.search(
        search_term=search_term,
        region_id=region["region_id"],
        seller_id=region["seller_id"],
        offset=0,
        limit=1  # Trazemos apenas 1 para não poluir a tela
    )
    
    print("\n3. PAYLOAD BRUTO DA API:")
    print(json.dumps(raw_data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    debug_atacadao()