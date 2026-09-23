# src/fetch.py

from pathlib import Path
import requests
import zipfile
import shutil
import os
from datetime import datetime

def fetch_all() -> bool:
    """
    Download and extract the full F1 database dump from Jolpica.
    
    Returns:
        bool: True if download succeeded, False otherwise
    """
    dump_url = "https://api.jolpi.ca/data/dumps/download/delayed/?dump_type=csv"
    output_folder = Path(__file__).resolve().parent.parent / "data" / "raw"
    
    # Ensure output folder exists
    output_folder.mkdir(parents=True, exist_ok=True)
    
    temp_zip_path = output_folder / "jolpica_dump.zip"
    extract_temp_folder = output_folder / "_temp_extract"
    
    try:
        print(f"Downloading F1 database dump from {dump_url}...")
        print("This may take a few minutes depending on connection speed...")
        
        # Download with streaming to handle large file
        response = requests.get(dump_url, stream=True, timeout=300)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(temp_zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"\rDownload progress: {downloaded/1024:.1f} KB / {total_size/1024:.1f} KB ({percent:.1f}%)", end='')
        
        print(f"\nDownload complete: {downloaded/1024:.1f} KB")
        
        # Extract the zip file
        print("Extracting database files...")
        extract_temp_folder.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_temp_folder)
        
        print("Extraction complete")
        
        # Move extracted CSV files to output folder
        extracted_files = list(extract_temp_folder.glob("*.csv"))
        
        if not extracted_files:
            # Check if files are in a subfolder
            for subdir in extract_temp_folder.iterdir():
                if subdir.is_dir():
                    extracted_files.extend(subdir.glob("*.csv"))
        
        if not extracted_files:
            raise ValueError("No CSV files found in the extracted archive")
        
        moved_count = 0
        for csv_file in extracted_files:
            original_name = csv_file.name
            
            # Skip any files starting with underscore (our temp folder)
            if csv_file.name.startswith("_"):
                continue
            
            # Remove formula_one_ prefix if present
            new_name = original_name
            if original_name.startswith("formula_one_"):
                new_name = original_name.replace("formula_one_", "", 1)
            
            dest = output_folder / new_name
            
            # Overwrite existing files
            shutil.move(str(csv_file), str(dest))
            size_kb = dest.stat().st_size / 1024
            row_estimate = dest.stat().st_size / 50  # Rough estimate assuming ~50 bytes per row
            if new_name != original_name:
                print(f"  Renamed and saved: {original_name} -> {new_name} ({size_kb:.1f} KB, ~{row_estimate:,} rows)")
            else:
                print(f"  Saved: {new_name} ({size_kb:.1f} KB, ~{row_estimate:,} rows)")
            moved_count += 1
        
        print(f"\nMoved {moved_count} CSV files to {output_folder}")
        
        # Cleanup temporary files
        print("\nCleaning up temporary files...")
        
        if temp_zip_path.exists():
            temp_zip_path.unlink()
            print("  Removed download ZIP")
        
        if extract_temp_folder.exists():
            shutil.rmtree(extract_temp_folder)
            print("  Removed temporary extraction folder")
        
        # Verify expected tables exist
        expected_tables = [
            "seasons.csv", "drivers.csv", "constructors.csv", "circuits.csv",
            "races.csv", "results.csv", "driver_standings.csv",
            "constructor_standings.csv", "qualifying.csv", "status.csv"
        ]
        
        missing = [t for t in expected_tables if not (output_folder / t).exists()]
        
        if missing:
            print(f"\nWarning: Missing expected files: {missing}")
            print("  They may be named differently in the dump")
        
        print(f"\n" + "="*50)
        print(f"Database download complete: {moved_count} files fetched")
        print("="*50)
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Failed to download database: {e}")
        return False
    except zipfile.BadZipFile as e:
        print(f"Invalid ZIP file: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
    finally:
        # Best-effort cleanup even on error
        if extract_temp_folder.exists():
            try:
                shutil.rmtree(extract_temp_folder)
                print("Cleaned up partial extraction")
            except:
                pass

if __name__ == "__main__":
    success = fetch_all()
    exit(0 if success else 1)
