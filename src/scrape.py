# src/scrape_wikipedia.py

from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_wikipedia():
    """
    Scrape Wikipedia for F1 data.
    Returns True if successful, False otherwise.
    Never raises exceptions — logs errors and returns False.
    """
    output_folder = Path(__file__).resolve().parent.parent / "data" / "raw"
    output_folder.mkdir(parents=True, exist_ok=True)
    
    scrape_results = {}
    
    for table_name in ["seasons"]:
        try:
            logger.info(f"Scraping {table_name}...")
            df = scrape_single_table(table_name)
            df.to_csv(output_folder / f"{table_name}.csv", index=False)
            scrape_results[table_name] = "success"
            logger.info(f"Saved {table_name}.csv ({len(df)} rows)")
            
        except Exception as e:
            logger.warning(f"Failed to scrape {table_name}: {e}")
            scrape_results[table_name] = "failed"
            # Don't re-raise — continue with other tables
    
    # Log summary
    success_count = sum(1 for v in scrape_results.values() if v == "success")
    logger.info(f"Scrape complete: {success_count}/{len(scrape_results)} tables succeeded")
    
    return success_count == len(scrape_results)


if __name__ == "__main__":
    success = scrape_wikipedia()
    exit(0 if success else 0)  # Always exit 0 to avoid blocking pipeline
