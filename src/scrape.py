# src/scrape.py

from pathlib import Path
import pandas as pd
import requests
import time
from datetime import datetime

def fetch_ergast_data(endpoint_url: str, record_type: str) -> pd.DataFrame:
    """
    Generic function to fetch all records from Ergast API endpoint.
    
    Args:
        endpoint_url: The base API URL (e.g., 'https://api.jolpi.ca/ergast/f1/seasons/')
        record_type: The type name used in the JSON response (e.g., 'Season', 'Driver', 'Constructor')
    
    Returns:
        pd.DataFrame with all records and all available fields as text
    """
    api_base = endpoint_url.rstrip('/')
    version = "1.0.0"
    
    # Step 1: Get total count with a minimal request
    try:
        print(f"Fetching metadata from {api_base}...")
        meta_response = requests.get(
            api_base,
            headers={"User-Agent": f"F1ETLScraper/{version}"},
            timeout=30,
        )
        meta_response.raise_for_status()
        meta_data = meta_response.json()
        
        # Extract total from MRData.total
        total = int(meta_data.get("MRData", {}).get("total", 0))
        
        if total == 0:
            print(f"WARNING: No records found for {record_type}")
            return pd.DataFrame()
        
        print(f"Total {record_type}(s) available: {total}")
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to fetch metadata from Ergast API: {e}")
    except ValueError as e:
        raise RuntimeError(f"Failed to parse JSON metadata: {e}")
    
    # Wait before fetching actual data (respect rate limits)
    time.sleep(1)
    
    # Step 2: Fetch all records with limit=total
    try:
        print(f"Fetching all {total} {record_type}(s)...")
        data_response = requests.get(
            api_base,
            params={"limit": total},
            headers={"User-Agent": f"F1ETLScraper/{version}"},
            timeout=60,
        )
        data_response.raise_for_status()
        
        data = data_response.json()
        
        # Extract the table - look for any key ending with "Table"
        mrdata = data.get("MRData", {})
        table_key = None
        table_data = None
        
        for key in mrdata.keys():
            if key.endswith("Table"):
                table_key = key
                table_data = mrdata[key].get(record_type + "s", [])
                break
        
        if table_data is None or not table_data:
            print(f"WARNING: No table data found for {record_type} in {table_key}")
            return pd.DataFrame()
        
        print(f"API returned {len(table_data)} of {total} {record_type}(s)")
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to fetch {record_type} data from Ergast API: {e}")
    except ValueError as e:
        raise RuntimeError(f"Failed to parse JSON data: {e}")
    
    # Step 3: Extract all fields from each record (preserving as text)
    rows = []
    all_keys = set()
    
    for record in table_data:
        entry = {
            "_source": "ergast_api",
            "_fetched_at": datetime.utcnow().isoformat(),
            "_endpoint": api_base,
        }
        
        for key, value in record.items():
            entry[key] = str(value) if value is not None else ""
            all_keys.add(key)
        
        rows.append(entry)
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Ensure consistent column order (metadata first, then alphabetically sorted fields)
    cols = [col for col in df.columns if col.startswith("_")] + sorted([col for col in df.columns if not col.startswith("_")])
    df = df.reindex(cols, axis=1)
    
    print(f"Extracted {len(df)} {record_type}(s) with fields: {[c for c in df.columns if not c.startswith('_')]}")
    
    return df

# ============================================================================
# TABLE-SPECIFIC FETCHERS
# ============================================================================

def get_seasons() -> pd.DataFrame:
    return fetch_ergast_data(
        endpoint_url="https://api.jolpi.ca/ergast/f1/seasons/",
        record_type="Season"
    )

def get_drivers() -> pd.DataFrame:
    return fetch_ergast_data(
        endpoint_url="https://api.jolpi.ca/ergast/f1/drivers/",
        record_type="Driver"
    )

def get_constructors() -> pd.DataFrame:
    return fetch_ergast_data(
        endpoint_url="https://api.jolpi.ca/ergast/f1/constructors/",
        record_type="Constructor"
    )

def get_circuits() -> pd.DataFrame:
    return fetch_ergast_data(
        endpoint_url="https://api.jolpi.ca/ergast/f1/circuits/",
        record_type="Circuit"
    )

def get_races() -> pd.DataFrame:
    return fetch_ergast_data(
        endpoint_url="https://api.jolpi.ca/ergast/f1/races/",
        record_type="Race"
    )

def get_grid() -> pd.DataFrame:
    return fetch_ergast_data(
        endpoint_url="https://api.jolpi.ca/ergast/f1/grid/",
        record_type="Grid"
    )

def get_results() -> pd.DataFrame:
    return fetch_ergast_data(
        endpoint_url="https://api.jolpi.ca/ergast/f1/results/",
        record_type="Result"
    )

def get_podiums() -> pd.DataFrame:
    return fetch_ergast_data(
        endpoint_url="https://api.jolpi.ca/ergast/f1/podiums/",
        record_type="Podium"
    )

def get_fastest_laps() -> pd.DataFrame:
    return fetch_ergast_data(
        endpoint_url="https://api.jolpi.ca/ergast/f1/fastest/",
        record_type="Fastest"
    )

def get_standings_drivers() -> pd.DataFrame:
    return fetch_ergast_data(
        endpoint_url="https://api.jolpi.ca/ergast/f1/driverStandings/",
        record_type="Standing"
    )

def get_standings_constructors() -> pd.DataFrame:
    return fetch_ergast_data(
        endpoint_url="https://api.jolpi.ca/ergast/f1/constructorStandings/",
        record_type="Standing"
    )

def get_qualifying() -> pd.DataFrame:
    return fetch_ergast_data(
        endpoint_url="https://api.jolpi.ca/ergast/f1/qualifying/",
        record_type="Qualifying"
    )

def get_status() -> pd.DataFrame:
    return fetch_ergast_data(
        endpoint_url="https://api.jolpi.ca/ergast/f1/status/",
        record_type="Status"
    )

# ============================================================================
# MAIN ORCHESTRATION
# ============================================================================

def scrape_all() -> bool:
    """
    Main scraping function that orchestrates all Ergast API calls.
    
    Returns:
        bool: True if all tables succeeded, False otherwise
    """
    output_folder = Path(__file__).resolve().parent.parent / "data" / "raw"
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Define all tables to fetch from Ergast API
    tables_to_scrape = {
        "seasons": get_seasons,
        "drivers": get_drivers,
        "constructors": get_constructors,
        "circuits": get_circuits,
        "races": get_races,
        "grid": get_grid,
        "results": get_results,
        "podiums": get_podiums,
        "fastest_laps": get_fastest_laps,
        "driver_standings": get_standings_drivers,
        "constructor_standings": get_standings_constructors,
        "qualifying": get_qualifying,
        "status": get_status,
    }
    
    scrape_results = {}
    
    for table_name, scrape_func in tables_to_scrape.items():
        try:
            print(f"Fetching {table_name}...")
            df = scrape_func()
            output_file = output_folder / f"{table_name}.csv"
            df.to_csv(output_file, index=False)
            scrape_results[table_name] = "success"
            
            size_kb = output_file.stat().st_size / 1024 if output_file.exists() else 0
            print(f"✓ Saved {table_name}.csv ({len(df)} rows, {size_kb:.1f} KB)")
            
        except Exception as e:
            print(f"✗ Failed to fetch {table_name}: {e}")
            scrape_results[table_name] = "failed"
        
        # Wait before next API call (respect rate limits)
        time.sleep(1)
    
    # Log summary
    success_count = sum(1 for v in scrape_results.values() if v == "success")
    total_count = len(scrape_results)
    print(f"Scrape complete: {success_count}/{total_count} tables succeeded")
    
    return success_count == total_count

if __name__ == "__main__":
    success = scrape_all()
    exit(0)  # Always exit 0 to avoid blocking pipeline even on partial failure
