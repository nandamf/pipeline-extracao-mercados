"""
Bronze Layer Integration Examples

Shows how to integrate the Bronze writer with existing scrapers.
Demonstrates the "before and after" patterns.
"""

# ============================================================================
# PATTERN 1: Direct Scraper to Bronze (Simple)
# ============================================================================

from scrapers.registry import get_scraper
from common.bronze_writer import BronzeWriter
import logging

logging.basicConfig(level=logging.INFO)


def example_simple_integration():
    """
    Simplest pattern: Run scraper, write to Bronze.
    
    Before: scraper.search() → CSV/Database
    After:  scraper.search() → Bronze → (Silver/Gold)
    """
    
    # Initialize Bronze writer
    bronze_writer = BronzeWriter()
    
    # Get scraper instance
    scraper = get_scraper("atacadao")
    
    # Search for products
    print("🔍 Searching for 'leite' in Atacadão...")
    results = scraper.search(search_term="leite", cep="04543010", max_pages=1)
    
    print(f"✓ Found {len(results)} products")
    
    # Write to Bronze layer
    print("📦 Writing to Bronze layer...")
    write_result = bronze_writer.write_batch(
        market="atacadao",
        search_term="leite",
        records=results,
        cep="04543010"
    )
    
    # Print results
    print(f"\n{'='*60}")
    print(f"Bronze Write Summary:")
    print(f"  Status: {write_result.status}")
    print(f"  Run ID: {write_result.run_id}")
    print(f"  Records written: {write_result.records_written}")
    print(f"  Duration: {write_result.execution_duration_ms:.2f}ms")
    print(f"  Files created: {len(write_result.files_created)}")
    print(f"  Location: data/bronze/market=atacadao/year=2025/...")
    print(f"{'='*60}\n")
    
    if write_result.errors:
        print(f"⚠️  Errors: {write_result.errors}")


# ============================================================================
# PATTERN 2: Batch Processing Multiple Markets
# ============================================================================

def example_batch_multiple_markets():
    """
    Process multiple markets and write to Bronze.
    Useful for portfolio showcase of scalable ETL.
    """
    
    bronze_writer = BronzeWriter()
    
    markets = [
        {"name": "atacadao", "term": "leite", "cep": "04543010"},
        {"name": "carrefour", "term": "leite"},
        {"name": "mix_mateus", "term": "leite"},
    ]
    
    results_summary = []
    
    for market_config in markets:
        try:
            print(f"\n📦 Processing {market_config['name']}...")
            
            scraper = get_scraper(market_config["name"])
            
            # Search
            results = scraper.search(
                search_term=market_config["term"],
                cep=market_config.get("cep"),
                max_pages=1
            )
            
            if not results:
                print(f"  ⚠️  No results")
                continue
            
            # Write to Bronze
            write_result = bronze_writer.write_batch(
                market=market_config["name"],
                search_term=market_config["term"],
                records=results,
                cep=market_config.get("cep")
            )
            
            results_summary.append({
                "market": market_config["name"],
                "records": write_result.records_written,
                "duration_ms": write_result.execution_duration_ms,
                "status": write_result.status,
                "run_id": write_result.run_id
            })
            
            print(f"  ✓ {write_result.records_written} records written in "
                  f"{write_result.execution_duration_ms:.2f}ms")
        
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    # Print summary table
    print(f"\n{'='*60}")
    print("Summary:")
    print(f"{'='*60}")
    for result in results_summary:
        print(f"{result['market']:15} | {result['records']:4} records | "
              f"{result['duration_ms']:7.2f}ms | {result['status']}")
    print(f"{'='*60}\n")


# ============================================================================
# PATTERN 3: With Raw Payload Preservation (Advanced)
# ============================================================================

from common.bronze_writer import BronzeWriter


class ScraperWithBronze:
    """
    Wrapper class that combines scraper with Bronze writing.
    Captures both parsed results and raw payloads.
    """
    
    def __init__(self, market: str):
        self.scraper = get_scraper(market)
        self.bronze_writer = BronzeWriter()
        self.market = market
    
    def search_and_store(
        self,
        search_term: str,
        cep: str = None,
        max_pages: int = 1
    ):
        """
        Search and automatically store to Bronze with raw payloads.
        """
        print(f"🔍 Searching {self.market} for '{search_term}'...")
        
        # Note: In real implementation, you'd capture raw responses
        # from the HTTP client. For now, just the parsed results.
        results = self.scraper.search(
            search_term=search_term,
            cep=cep,
            max_pages=max_pages
        )
        
        # In production, capture raw API responses here
        raw_payloads = self._capture_raw_payloads()
        
        # Write to Bronze with both parsed and raw data
        write_result = self.bronze_writer.write_batch(
            market=self.market,
            search_term=search_term,
            records=results,
            raw_payloads=raw_payloads,
            cep=cep
        )
        
        return write_result
    
    def _capture_raw_payloads(self):
        """
        In production, integrate with HTTP client to capture raw responses.
        
        Example structure:
        {
            "market": "atacadao",
            "search_term": "leite",
            "raw_response_type": "graphql_response",
            "raw_payload": {... original API response ...},
            "http_status": 200,
            "response_time_ms": 234
        }
        """
        return None


def example_advanced_with_raw_payloads():
    """Example showing raw payload capture."""
    
    scraper = ScraperWithBronze("atacadao")
    result = scraper.search_and_store(
        search_term="leite",
        cep="04543010",
        max_pages=1
    )
    
    print(f"✓ Results stored with run_id: {result.run_id}")


# ============================================================================
# PATTERN 4: Error Handling and Retry Logic
# ============================================================================

def example_with_error_handling():
    """
    Production-ready pattern with error handling.
    """
    
    bronze_writer = BronzeWriter()
    max_retries = 3
    
    search_config = {
        "market": "atacadao",
        "search_term": "leite",
        "cep": "04543010"
    }
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Attempt {attempt}/{max_retries}...")
            
            scraper = get_scraper(search_config["market"])
            results = scraper.search(
                search_term=search_config["search_term"],
                cep=search_config.get("cep"),
                max_pages=1
            )
            
            if not results:
                print(f"  No results found")
                continue
            
            # Write to Bronze
            write_result = bronze_writer.write_batch(
                market=search_config["market"],
                search_term=search_config["search_term"],
                records=results,
                cep=search_config.get("cep")
            )
            
            if write_result.status == "SUCCESS":
                print(f"✓ Success! Wrote {write_result.records_written} records")
                print(f"  Run ID: {write_result.run_id}")
                return write_result
            else:
                print(f"⚠️  Partial success. Errors: {write_result.errors}")
                continue
        
        except Exception as e:
            print(f"  ✗ Error: {e}")
            if attempt < max_retries:
                print(f"  Retrying...")
            else:
                print(f"  Failed after {max_retries} attempts")
                raise


# ============================================================================
# PATTERN 5: Monitoring and Logging
# ============================================================================

def example_with_monitoring():
    """
    Pattern showing how to monitor Bronze writes for production dashboards.
    """
    
    import json
    from pathlib import Path
    
    bronze_writer = BronzeWriter()
    
    # Sample data
    results = [{
        "market": "atacadao",
        "product_name": "Leite Integral 1L",
        "price": 4.50,
        "unit_price": 4.50,
        "category": "Laticínios",
        "brand": "Parmalat",
        "source_product_id": "123",
        "sku": "SKU123",
        "ean": "7894001234567",
        "searched_ean": None,
        "ean_source": "market_response",
        "search_term": "leite",
        "cep": "04543010",
        "collected_at": "2025-03-15T10:45:31Z",
        "source_url": "https://api.atacadao.com.br",
        "image_url": "https://cdn.atacadao.com.br/image.jpg",
        "wholesale_price": 3.99,
    }]
    
    write_result = bronze_writer.write_batch(
        market="atacadao",
        search_term="leite",
        records=results,
        cep="04543010"
    )
    
    # Read and display metadata
    metadata_path = Path(write_result.metadata_path)
    with open(metadata_path) as f:
        metadata = json.load(f)
    
    print(f"\n{'='*60}")
    print("Metadata for Monitoring:")
    print(f"{'='*60}")
    print(f"Run ID: {metadata['run_id']}")
    print(f"Status: {metadata['execution']['status']}")
    print(f"Duration: {metadata['execution']['duration_seconds']}s")
    print(f"Records: {metadata['data_quality']['total_records']}")
    print(f"Batch ID: {metadata['data_quality']['batch_id']}")
    
    if metadata['data_quality']['null_rates']:
        print(f"\nNull Rates:")
        for field, rate in metadata['data_quality']['null_rates'].items():
            print(f"  {field}: {rate*100:.1f}%")
    
    print(f"{'='*60}\n")


# ============================================================================
# PATTERN 6: Real-world ETL Pipeline
# ============================================================================

def example_production_pipeline():
    """
    Production-ready ETL pipeline showing:
    - Error handling
    - Monitoring
    - Multiple markets
    - Idempotency
    """
    
    import json
    from datetime import datetime
    from pathlib import Path
    
    bronze_writer = BronzeWriter()
    pipeline_start = datetime.utcnow()
    
    # Configuration
    search_configs = [
        {"market": "atacadao", "search_term": "leite", "cep": "04543010"},
        {"market": "carrefour", "search_term": "leite"},
        {"market": "mix_mateus", "search_term": "leite"},
    ]
    
    pipeline_results = {
        "pipeline_start": pipeline_start.isoformat(),
        "markets": {}
    }
    
    for config in search_configs:
        market = config["market"]
        pipeline_results["markets"][market] = {
            "status": "PENDING",
            "records": 0,
            "run_id": None,
            "errors": []
        }
        
        try:
            # Get scraper
            scraper = get_scraper(market)
            
            # Execute search
            results = scraper.search(
                search_term=config["search_term"],
                cep=config.get("cep"),
                max_pages=1
            )
            
            if not results:
                pipeline_results["markets"][market]["status"] = "NO_RESULTS"
                continue
            
            # Write to Bronze
            write_result = bronze_writer.write_batch(
                market=market,
                search_term=config["search_term"],
                records=results,
                cep=config.get("cep")
            )
            
            # Update results
            pipeline_results["markets"][market]["status"] = write_result.status
            pipeline_results["markets"][market]["records"] = write_result.records_written
            pipeline_results["markets"][market]["run_id"] = write_result.run_id
            
            if write_result.errors:
                pipeline_results["markets"][market]["errors"] = write_result.errors
        
        except Exception as e:
            pipeline_results["markets"][market]["status"] = "FAILED"
            pipeline_results["markets"][market]["errors"] = [str(e)]
    
    # Print results
    pipeline_end = datetime.utcnow()
    pipeline_duration = (pipeline_end - pipeline_start).total_seconds()
    
    print(f"\n{'='*70}")
    print(f"ETL Pipeline Summary")
    print(f"{'='*70}")
    print(f"Pipeline Duration: {pipeline_duration:.2f}s")
    print(f"\nMarket Results:")
    print(f"{'-'*70}")
    
    for market, result in pipeline_results["markets"].items():
        status_symbol = "✓" if result["status"] == "SUCCESS" else "✗"
        print(f"{status_symbol} {market:15} | Status: {result['status']:10} | "
              f"Records: {result['records']:4}")
    
    print(f"{'='*70}\n")
    
    return pipeline_results


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("Bronze Layer Integration Examples")
    print("="*70 + "\n")
    
    # Uncomment to run examples:
    
    # print("1. Simple Integration")
    # print("-" * 70)
    # example_simple_integration()
    
    # print("\n2. Batch Multiple Markets")
    # print("-" * 70)
    # example_batch_multiple_markets()
    
    # print("\n3. Error Handling")
    # print("-" * 70)
    # example_with_error_handling()
    
    # print("\n4. Monitoring")
    # print("-" * 70)
    # example_with_monitoring()
    
    print("\n5. Production Pipeline")
    print("-" * 70)
    example_production_pipeline()
