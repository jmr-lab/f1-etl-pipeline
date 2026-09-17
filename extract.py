from pathlib import Path
import pandas as pd

# Define required input files
REQUIRED_TABLES = {
    "circuits",
    "constructor_results",
    "constructors",
    "constructor_standings",
    "driver_standings",
    "drivers",
    "races",
    "results",
    "status",
    "Countries"
}

def load_csv_files(required_tables: set = REQUIRED_TABLES) -> dict:
    """
    Load all CSV files from the project's data folder.
    
    Args:
        required_tables: Set of expected table names (CSV filenames without extension)
    
    Returns:
        dict: Dictionary mapping table name to DataFrame
    
    Raises:
        FileNotFoundError: If any required table is missing
        ValueError: If CSV parsing fails
    """
    
    # Locate data folder relative to this file
    src_folder = Path(__file__).resolve().parent
    data_folder = src_folder.parent / "data"
    
    if not data_folder.exists():
        raise FileNotFoundError(
            f"Data folder not found at {data_folder}. "
            "Expected structure: data/*.csv"
        )
    
    # Find all CSV files
    csv_files = list(data_folder.glob("*.csv"))
    
    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in {data_folder}. "
            "Download the ErgastF1 dataset and extract to data/"
        )
    
    # Check for required tables
    found_tables = {csv_file.stem for csv_file in csv_files}
    missing_tables = required_tables - found_tables
    
    if missing_tables:
        raise FileNotFoundError(
            f"Missing required CSV files: {sorted(missing_tables)}. "
            f"Found: {sorted(found_tables)}"
        )
    
    # Load all CSVs with error handling
    dataframes = {}
    total_memory_mb = 0
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, encoding='utf-8')
            dataframes[csv_file.stem] = df
            
            memory_kb = df.memory_usage(deep=True).sum() / 1024
            total_memory_mb += memory_kb / 1024
            
            print(f"Loaded {csv_file.stem}: {len(df):,} rows, {memory_kb:.1f} KB")
            
        except pd.errors.EmptyDataError:
            raise ValueError(f"Empty CSV file: {csv_file.name}")
        except Exception as e:
            raise ValueError(f"Failed to parse {csv_file.name}: {e}")
    
    print(f"\nTotal: {len(dataframes)} tables, {total_memory_mb:.2f} MB")
    return dataframes