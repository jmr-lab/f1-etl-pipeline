import sys
from pathlib import Path

from src.extract import load_csv_files
from src.transform import transform_data
from src.validate import validate_formula1
from src.load import save_formula1

def main() -> int:
    """Main pipeline orchestration."""

    print("=" * 60)
    print("F1 ETL Pipeline")
    print("=" * 60)
    print()

    try:
        print("[1/4] Extracting data...")
        dataframes = load_csv_files()
        print()

        print("[2/4] Transforming data...")
        formula1 = transform_data(dataframes)
        print(f"  Output shape: {formula1.shape[0]:,} rows x {formula1.shape[1]} columns")
        print(f"  Columns: {list(formula1.columns)}")
        print()

        print("[3/4] Validating data...")
        validate_formula1(formula1)
        print()

        print("[4/4] Saving outputs...")
        save_formula1(formula1)
        print()

    except FileNotFoundError as e:
        print(f"\n[ERROR] File error: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure data folder exists at ./data/")
        print("  2. Download ErgastF1 CSV files and extract to data/")
        return 1

    except KeyError as e:
        print(f"\n[ERROR] Data structure error: {e}")
        return 1

    except ValueError as e:
        print(f"\n[ERROR] Validation failed: {e}")
        print("\n[STOPPING] Pipeline aborted due to validation failure.")
        return 1

    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("=" * 60)
    print("Pipeline completed successfully!")
    print("=" * 60)

    return 0

if __name__ == "__main__":
    main()