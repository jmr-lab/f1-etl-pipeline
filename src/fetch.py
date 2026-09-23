# src/fetch.py

from pathlib import Path
import pandas as pd
import requests
import time
from datetime import datetime

def fetch_ergast_data(endpoint_url: str, record_type: str) -> pd.DataFrame:
    """
    Generic function to fetch and flatten all records from Ergast API endpoint.
    
    Args:
        endpoint_url: The base API URL
        record_type: The type name used in the JSON response
    
    Returns:
        pd.DataFrame with flattened records (objects → IDs, arrays exploded)
    """
    api_base = endpoint_url.rstrip('/')
    version = "1.0.0"
    
    # Step 1: Get total count with a minimal request
    try:
        print(f"Fetching metadata from {api_base}...")
        meta_response = requests.get(
            api_base,
            params={"format": "json"},
            headers={"User-Agent": f"F1ETLScraper/{version}"},
            timeout=30,
        )
        meta_response.raise_for_status()
        meta_data = meta_response.json()
        
        total = int(meta_data.get("MRData", {}).get("total", 0))
        
        if total == 0:
            print(f"WARNING: No records found for {record_type}")
            return pd.DataFrame()
        
        print(f"Total {record_type}(s) available: {total}")
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to fetch metadata from Ergast API: {e}")
    except ValueError as e:
        raise RuntimeError(f"Failed to parse JSON metadata: {e}")
    
    time.sleep(1)
    
    # Step 2: Fetch all records with limit=total
    try:
        print(f"Fetching all {total} {record_type}(s)...")
        data_response = requests.get(
            api_base,
            params={"limit": total, "format": "json"},
            headers={"User-Agent": f"F1ETLScraper/{version}"},
            timeout=60,
        )
        data_response.raise_for_status()
        
        data = data_response.json()
        
        mrdata = data.get("MRData", {})
        table_key = None
        table_data = None
        
        for key in mrdata.keys():
            if key.endswith("Table"):
                table_key = key
                table_data = mrdata[key].get(record_type + "s", [])
                break
        
        if table_data is None or not table_data:
            print(f"WARNING: No table data found for {record_type}")
            return pd.DataFrame()
        
        print(f"API returned {len(table_data)} of {total} {record_type}(s)")
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to fetch {record_type} data from Ergast API: {e}")
    except ValueError as e:
        raise RuntimeError(f"Failed to parse JSON data: {e}")
    
    # Step 3: Flatten and explode the data
    def flatten_record(record, prefix=""):
        """Recursively flatten a record, extracting IDs from objects."""
        result = {}
        
        for key, value in record.items():
            new_key = f"{prefix}{key}" if prefix else key
            
            if isinstance(value, dict):
                # Object: extract only the ID field if it exists
                if "Id" in value:
                    result[f"{new_key}Id"] = str(value["Id"]) if value["Id"] else ""
                # Also handle special case of nested Location
                elif "lat" in value:
                    for loc_key, loc_value in value.items():
                        # No prefix - just use the field name directly
                        result[loc_key] = str(loc_value) if loc_value else ""
                else:
                    # For other objects, flatten all fields without prefix
                    result.update(flatten_record(value))
            elif isinstance(value, list):
                # Array: return marker to signal explosion
                result[new_key] = value
            elif value is not None:
                result[new_key] = str(value)
            else:
                result[new_key] = ""
        
        return result
    
    def explode_arrays(row_dict):
        """Explode all array fields in a record into multiple rows."""
        array_fields = [k for k, v in row_dict.items() if isinstance(v, list)]
        
        if not array_fields:
            return [row_dict]
        
        # Take first array field to explode (typically QualifyingResults, Results, etc.)
        first_array = array_fields[0]
        array_items = row_dict[first_array]
        
        # If array is empty, return single row with None/empty values
        if not array_items:
            row_copy = {k: ("" if v is None else v) for k, v in row_dict.items()}
            row_copy[first_array] = None
            return [row_copy]
        
        # For each array item, create a new row with array content merged
        rows = []
        for item in array_items:
            if isinstance(item, dict):
                # Flatten the array item (extract IDs from nested objects)
                flattened_item = flatten_record(item)
                
                # Merge with parent data (excluding the array field itself)
                merged_row = {
                    k: ("" if v is None else v) 
                    for k, v in row_dict.items() 
                    if k != first_array and not isinstance(v, list)
                }
                merged_row.update(flattened_item)
                rows.append(merged_row)
            else:
                # Non-dict array item (primitive value)
                merged_row = {
                    k: ("" if v is None else v) 
                    for k, v in row_dict.items() 
                    if k != first_array and not isinstance(v, list)
                }
                merged_row[first_array] = str(item)
                rows.append(merged_row)
        
        return rows
    
    # Process all top-level records
    all_rows = []
    
    for record in table_data:
        # First flatten the record (extract IDs from objects)
        flattened = flatten_record(record)
        
        # Then explode any arrays (create multiple rows if needed)
        exploded_rows = explode_arrays(flattened)
        all_rows.extend(exploded_rows)
    
    # Create DataFrame
    if not all_rows:
        return pd.DataFrame()
    
    df = pd.DataFrame(all_rows)
    
    # Sort columns alphabetically
    cols = sorted([col for col in df.columns])
    df = df.reindex(cols, axis=1)
    
    print(f"Extracted {len(df)} rows with fields: {[c for c in df.columns]}")
    
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

def get_results() -> pd.DataFrame:
    return fetch_ergast_data(
        endpoint_url="https://api.jolpi.ca/ergast/f1/results/",
        record_type="Result"
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

def fetch_all() -> bool:
    """
    Main fetching function that orchestrates all Ergast API calls.
    
    Returns:
        bool: True if all tables succeeded, False otherwise
    """
    output_folder = Path(__file__).resolve().parent.parent / "data" / "raw"
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Define all tables to fetch from Ergast API
    tables_to_fetch = {
        "seasons": get_seasons,
        "drivers": get_drivers,
        "constructors": get_constructors,
        "circuits": get_circuits,
        "races": get_races,
        "results": get_results,
        "driver_standings": get_standings_drivers,
        "constructor_standings": get_standings_constructors,
        "qualifying": get_qualifying,
        "status": get_status,
    }
    
    fetch_results = {}
    
    for table_name, fetch_func in tables_to_fetch.items():
        try:
            print(f"Fetching {table_name}...")
            df = fetch_func()
            
            # Validate that the DataFrame is not empty - skip if empty, DO NOT FAIL SCRIPT
            if df.empty:
                raise ValueError(f"No data retrieved for {table_name} - skipping file save")
            
            output_file = output_folder / f"{table_name}.csv"
            df.to_csv(output_file, index=False)
            fetch_results[table_name] = "success"
            
            size_kb = output_file.stat().st_size / 1024 if output_file.exists() else 0
            print(f"✓ Saved {table_name}.csv ({len(df)} rows, {size_kb:.1f} KB)")
            
        except Exception as e:
            print(f"✗ Failed to fetch {table_name}: {e}")
            print(f"→ Continuing with remaining tables...")
            fetch_results[table_name] = "failed"
        
        # Wait before next API call (respect rate limits)
        time.sleep(1)
    
    # Log summary
    success_count = sum(1 for v in fetch_results.values() if v == "success")
    failed_count = sum(1 for v in fetch_results.values() if v == "failed")
    total_count = len(fetch_results)
    print(f"\n{'='*50}")
    print(f"Fetch complete: {success_count}/{total_count} tables succeeded, {failed_count} failed")
    print(f"{'='*50}")
    
    # Return False if any failed, but don't raise - script continues anyway
    return success_count == total_count

if __name__ == "__main__":
    success = fetch_all()
    # Always exit 0 to avoid blocking the pipeline on partial failures
    exit(0)
