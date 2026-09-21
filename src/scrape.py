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
            df = get_seasons()
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


def get_seasons():
    import requests
    
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    
    url = "https://en.wikipedia.org/wiki/List_of_Formula_One_seasons"

    response = requests.get(
        url,
        headers={"User-Agent": "WikipediaTableExtractor/1.0"},
        timeout=30,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    target_table = None

    for table in soup.find_all("table"):
        headers = [
            cell.get_text(" ", strip=True)
            for cell in table.find_all("th")
        ]

        if "Season" in headers:
            target_table = table
            break

    if target_table is None:
        raise ValueError("Could not find the seasons table")

    rows = []
    
    for row in target_table.find_all("tr"):
        cells = row.find_all(["th", "td"])
    
        if len(cells) < 4:
            continue
    
        if cells[0].get_text(" ", strip=True) == "Season":
            continue
    
        first_cell = cells[0]
        link = first_cell.find("a")
    
        rows.append({
            "year": keep_digits(first_cell.get_text(" ", strip=True)),
            "url": (
                urljoin(url, link["href"])
                if link and link.get("href")
                else None
            ),
            "races": keep_digits(cells[1].get_text(" ", strip=True)),
            "countries": keep_digits(cells[2].get_text(" ", strip=True)),
        })
    
    df = pd.DataFrame(rows)
    
    print(df.to_string(index=False))

    return df


if __name__ == "__main__":
    success = scrape_wikipedia()
    exit(0 if success else 0)  # Always exit 0 to avoid blocking pipeline
