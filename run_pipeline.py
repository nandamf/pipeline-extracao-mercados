"""
End-to-End ETL Pipeline Orchestrator

Executes the full Medallion architecture flow:
1. Scrapers (Extraction)
2. Bronze (Raw Immutable Storage)
3. Silver (Normalization & Data Quality)
4. Gold (Analytics & Dashboards Ready)
"""

import logging
import sys
import time
from typing import List, Dict
from pathlib import Path
from datetime import datetime
import pandas as pd

from scrapers.registry import get_scraper
from pipelines.bronze_writer import BronzeWriter
from pipelines.silver_transformer import SilverTransformer
from pipelines.gold_transformer import GoldTransformer

# Configuração Central de Logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"pipeline_run_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
logger = logging.getLogger("ETL_Orchestrator")


def run_pipeline(search_configs: List[Dict]):
    """
    Orchestrates the entire ETL pipeline safely passing exact paths between layers.
    """
    start_time = time.time()
    logger.info("="*80)
    logger.info("STARTING END-TO-END MEDALLION PIPELINE")
    logger.info("="*80)
    
    # Inicialização das classes da pipeline
    bronze_writer = BronzeWriter()
    silver_transformer = SilverTransformer()
    gold_transformer = GoldTransformer()
    
    # Coletor de caminhos Silver para enviar à camada Gold
    silver_output_paths = []
    
    pipeline_status = {"bronze": 0, "silver": 0, "errors": 0}

    # -------------------------------------------------------------------------
    # FASES: SCRAPER -> BRONZE -> SILVER (Por Mercado)
    # -------------------------------------------------------------------------
    for config in search_configs:
        market = config["market"]
        search_term = config["search_term"]
        cep = config.get("cep")
        
        logger.info(f"\nProcessando Mercado: {market.upper()} (Termo: {search_term})")
        
        try:
            # 1. EXTRACT
            scraper = get_scraper(market)
            logger.info(f"[{market}] Extraindo dados...")
            raw_records = scraper.search(search_term=search_term, cep=cep, max_pages=1)
            
            if not raw_records:
                logger.warning(f"[{market}] Nenhum dado encontrado. Pulando etapas seguintes.")
                continue
                
            # 2. BRONZE (Load Raw)
            logger.info(f"[{market}] Escrevendo na Camada Bronze...")
            bronze_result = bronze_writer.write_batch(
                market=market,
                search_term=search_term,
                records=raw_records,
                cep=cep
            )
            
            if bronze_result.status != "SUCCESS":
                logger.error(f"[{market}] Falha ao gravar Bronze. Erros: {bronze_result.errors}")
                pipeline_status["errors"] += 1
                continue
            
            pipeline_status["bronze"] += bronze_result.records_written
            
            # DEDUZIR O CAMINHO EXATO DO PARQUET BRONZE GERADO (Evita usar glob)
            bronze_parquet_path = Path(bronze_result.metadata_path).parent / "data_batch.parquet"
            
            # 3. SILVER (Transform & Normalize)
            logger.info(f"[{market}] Transformando para Camada Silver (Run ID: {bronze_result.run_id})...")
            silver_result = silver_transformer.transform_bronze(
                bronze_parquet_path=str(bronze_parquet_path),
                market=market,
                search_term=search_term
            )
            
            if silver_result.status != "SUCCESS":
                logger.error(f"[{market}] Falha ao gravar Silver. Erros: {silver_result.errors}")
                pipeline_status["errors"] += 1
                continue
                
            pipeline_status["silver"] += silver_result.records_output
            
            # DEDUZIR O CAMINHO EXATO DO PARQUET SILVER GERADO
            silver_parquet_path = Path(silver_result.metadata_path).parent / "products_normalized.parquet"
            silver_output_paths.append(str(silver_parquet_path))
            
        except Exception as e:
            logger.error(f"[{market}] Erro inesperado na pipeline: {e}", exc_info=True)
            pipeline_status["errors"] += 1

    # -------------------------------------------------------------------------
    # FASE: GOLD (Agregação de todos os mercados)
    # -------------------------------------------------------------------------
    if silver_output_paths:
        logger.info("\nIniciando processamento da Camada Gold (Analytics)...")
        gold_result = gold_transformer.transform_silver_to_gold(
            silver_parquet_paths=silver_output_paths
        )
        
        if gold_result.status == "SUCCESS":
            logger.info(f"Camada Gold gerada com sucesso! Tabelas criadas: {gold_result.tables_created}")
        else:
            logger.error("Erros ao gerar Camada Gold.")
            pipeline_status["errors"] += 1
    else:
        logger.warning("\nNenhum arquivo Silver gerado. Pulando camada Gold.")

    # -------------------------------------------------------------------------
    # RESUMO FINAL
    # -------------------------------------------------------------------------
    duration = time.time() - start_time
    logger.info("\n" + "="*80)
    logger.info("RESUMO DO PIPELINE")
    logger.info("="*80)
    logger.info(f"Tempo total     : {duration:.2f} segundos")
    logger.info(f"Registros Bronze: {pipeline_status['bronze']}")
    logger.info(f"Registros Silver: {pipeline_status['silver']} (após deduplicação)")
    logger.info(f"Erros totais    : {pipeline_status['errors']}")
    logger.info("="*80)


if __name__ == "__main__":
    # Configuração de buscas diárias
    SEARCH_CONFIGS = [
        {"market": "atacadao", "search_term": "leite", "cep": "04543010"},
        {"market": "carrefour", "search_term": "leite", "cep": None},
        {"market": "mix_mateus", "search_term": "leite", "cep": None},
    ]
    csv_path = Path("inputs/produtos.csv")
    search_configs = []
    
    if csv_path.exists():
        try:
            # Caso o seu CSV use ponto e vírgula, troque para pd.read_csv(csv_path, sep=';')
            df_produtos = pd.read_csv(csv_path)
            
            if 'ean' in df_produtos.columns:
                # Extrai os EANs únicos, converte para string e remove espaços em branco
                eans = df_produtos['ean'].dropna().astype(str).str.strip().unique()
                markets = ["atacadao", "carrefour", "mix_mateus"]
                
                for ean in eans:
                    if not ean:
                        continue
                    for market in markets:
                        search_configs.append({
                            "market": market,
                            "search_term": ean,
                            "cep": "04543010" if market == "atacadao" else None
                        })
                logger.info(f"Carregados {len(eans)} EANs do arquivo {csv_path}.")
            else:
                logger.error(f"Coluna 'ean' não encontrada no arquivo {csv_path}.")
        except Exception as e:
            logger.error(f"Erro ao ler o arquivo {csv_path}: {e}")
    else:
        logger.warning(f"Arquivo {csv_path} não encontrado. Usando configuração padrão (Leite).")
        search_configs = SEARCH_CONFIGS
        
    # Executa a pipeline se houver configurações válidas
    if search_configs:
        run_pipeline(search_configs)