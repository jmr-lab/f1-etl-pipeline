# src/scrape.py

from pathlib import Path
import logging
from datetime import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_wikipedia():
    """Scrape Wikipedia for F1 data. Returns True if successful, False otherwise."""
    output_folder = Path(__file__).resolve().parent.parent / "data" / "raw"
    output_folder.mkdir(parents=True, exist_ok=True)
    
    scrape_results = {}
    tables_to_scrape = {
        "seasons": get_seasons,
        "drivers": get_drivers,
        "constructors": get_constructors,
        # Add more as you implement them
    }
    
    for table_name, scrape_func in tables_to_scrape.items():
        try:
            logger.info(f"Scraping {table_name}...")
            df = scrape_func()  # Each function returns its own DataFrame
            output_file = output_folder / f"{table_name}.csv"
            df.to_csv(output_file, index=False)
            scrape_results[table_name] = "success"
            logger.info(f"Saved {table_name}.csv ({len(df)} rows, {output_file.stat().st_size / 1024:.1f} KB)")
            
        except Exception as e:
            logger.warning(f"Failed to scrape {table_name}: {e}")
            scrape_results[table_name] = "failed"
    
    # Log summary
    success_count = sum(1 for v in scrape_results.values() if v == "success")
    logger.info(f"Scrape complete: {success_count}/{len(scrape_results)} tables succeeded")

    return success_count == len(scrape_results)

def keep_digits(value):
    digits = re.sub(r"\D", "", str(value))
    return int(digits) if digits else None

def get_seasons():
    url = "https://en.wikipedia.org/wiki/List_of_Formula_One_seasons"

    response = requests.get(
        url,
        headers={"User-Agent": "F1ETLScraper/1.0"},
        timeout=30,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    target_table = None

    for table in soup.find_all("table"):
        headers = [cell.get_text(" ", strip=True) for cell in table.find_all("th")]

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


def get_driver_id(index):
    """Generate a unique numeric driver ID based on list index."""
    return index + 1

def get_code(driver_ref):
    """
    Generate F1-style driver code from driver reference.
    Format: 1 letter from forename + 2-3 letters from surnames
    
    Examples:
        "max_verstappen" -> "VER"
        "lewis_hamilton" -> "HAM"
        "charles_leclerc" -> "LEC"
        "fernando_alonso" -> "ALO"
    """
    parts = driver_ref.split("_")
    forename = parts[0] if len(parts) > 0 else ""
    surname = parts[1] if len(parts) > 1 else ""
    
    # Take first letter of forename
    code = forename[0].upper() if forename else ""
    
    # Take up to 3 letters from surname (or multiple surname parts)
    surname_parts = surname.replace("-", "_").split("_")
    for i, part in enumerate(surname_parts[:2]):  # Max 2 surname parts
        if i == 0:
            code += part[:2].upper()
        else:
            code += part[:1].upper()
    
    return code[:4] if len(code) <= 4 else code[:3]  # F1 codes are 3 chars, cap at 4

def get_drivers():
    """
    Scrape the List of Formula One drivers table from Wikipedia.
    
    Returns:
        pd.DataFrame with columns: driverId, driverRef, code, forename, surname, nationality, url
    """
    url = "https://en.wikipedia.org/wiki/List_of_Formula_One_drivers"
    
    response = requests.get(
        url,
        headers={"User-Agent": "F1ETLScraper/1.0"},
        timeout=30,
    )
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "lxml")
    
    # Find the table with "Driver name" header
    target_table = None
    
    for table in soup.find_all("table"):
        headers = [
            cell.get_text(" ", strip=True).lower()
            for cell in table.find_all("th")
        ]
        
        # Look for table with "Driver name" in headers
        if any("driver name" in h for h in headers):
            target_table = table
            break
    
    if target_table is None:
        raise ValueError("Could not find the drivers table (expected 'Driver name' header)")
    
    rows = []
    
    for idx, row in enumerate(target_table.find_all("tr")[1:]):  # Skip header row
        cells = row.find_all(["th", "td"])
        
        # Need at least 2 columns (Driver name, Nationality)
        if len(cells) < 2:
            continue
        
        # Column 0 = Driver name
        driver_cell = cells[0]
        driver_link = driver_cell.find("a")
        
        driver_name_full = driver_link.get_text(" ", strip=True) if driver_link else driver_cell.get_text(" ", strip=True).strip()
        
        # Skip if no valid driver name
        if not driver_name_full or len(driver_name_full.split()) < 1:
            continue
        
        # Split into forename and surname
        name_parts = driver_name_full.split()
        forename = name_parts[0] if name_parts else ""
        surname = name_parts[-1] if len(name_parts) > 1 else forename
        
        # Generate identifiers
        driver_ref = f"{forename.lower()}_{surname.lower()}"
        driver_id = idx + 1
        code = get_code(driver_ref)
        
        # URL from driver link
        url_path = driver_link["href"] if driver_link and driver_link.get("href") else None
        driver_url = urljoin(url, url_path) if url_path else None
        
        # Column 1 = Nationality
        nat_cell = cells[1]
        img = nat_cell.find("img")
        if img and img.get("alt"):
            nationality = img.get("alt").replace("Flag of ", "").replace("flagicon ", "")
        else:
            nationality = nat_cell.get_text(" ", strip=True)
        
        rows.append({
            "driverId": driver_id,
            "driverRef": driver_ref,
            "code": code,
            "forename": forename,
            "surname": surname,
            "nationality": nationality,
            "url": driver_url,
        })
    
    df = pd.DataFrame(rows)
    logger.info(f"Extracted {len(df)} drivers from Wikipedia")
    print(df.to_string(index=False))
    
    return df


def get_constructors():
    """Scrape constructors table from Wikipedia."""
    # Similar to get_seasons()
    # Return a DataFrame
    pass


def get_circuits():
    """Scrape circuits table from Wikipedia."""
    # Similar to get_seasons()
    # Return a DataFrame
    pass


if __name__ == "__main__":
    success = scrape_wikipedia()
    exit(0)  # Always exit 0 to avoid blocking pipeline
