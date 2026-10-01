"""
F1 Star Schema Database Builder

Normalizes extracted CSV files into SQLite database with
proper relationships matching the Jolpica schema.
"""

from pathlib import Path
from typing import Dict, Tuple
import pandas as pd
import pickle
import sqlite3
import sys

def get_extracted_data_path() -> Path:
    """Locate the extracted_data.pkl file."""
    src_folder = Path(__file__).resolve().parent
    output_folder = src_folder.parent / "output"
    return output_folder / "extracted_data.pkl"

def get_sql_folder() -> Path:
    """Return the sql folder, creating it if needed."""
    src_folder = Path(__file__).resolve().parent
    sql_folder = src_folder.parent / "sql"
    sql_folder.mkdir(parents=True, exist_ok=True)
    return sql_folder

def create_complete_schema(conn: sqlite3.Connection) -> None:
    """Create the normalized F1 database schema with FK constraints."""
    
    conn.execute("PRAGMA foreign_keys = OFF;")
    
    schema_sql = """
    -- Dimension tables (created first)
    CREATE TABLE IF NOT EXISTS season (
        id INTEGER PRIMARY KEY,
        year INTEGER UNIQUE,
        api_id INTEGER,
        championship_system_id INTEGER,
        wikipedia TEXT
    );
    
    CREATE TABLE IF NOT EXISTS circuit (
        id INTEGER PRIMARY KEY,
        name TEXT,
        reference TEXT,
        locality TEXT,
        country TEXT,
        country_code TEXT,
        latitude REAL,
        longitude REAL,
        altitude INTEGER,
        wikipedia TEXT,
        api_id INTEGER
    );
    
    CREATE TABLE IF NOT EXISTS driver (
        id INTEGER PRIMARY KEY,
        reference TEXT,
        abbreviation TEXT,
        forename TEXT,
        surname TEXT,
        nationality TEXT,
        country_code TEXT,
        date_of_birth DATE,
        permanent_car_number INTEGER,
        wikipedia TEXT,
        api_id INTEGER
    );
    
    CREATE TABLE IF NOT EXISTS team (
        id INTEGER PRIMARY KEY,
        name TEXT,
        reference TEXT,
        nationality TEXT,
        country_code TEXT,
        base_team_id INTEGER,
        primary_color TEXT,
        wikipedia TEXT,
        api_id INTEGER
    );
    
    -- Fact tables WITH FK constraints
    CREATE TABLE IF NOT EXISTS round (
        id INTEGER PRIMARY KEY,
        season_id INTEGER,
        circuit_id INTEGER,
        number INTEGER,
        race_number INTEGER,
        name TEXT,
        date TEXT,
        is_cancelled INTEGER,
        wikipedia TEXT,
        api_id INTEGER,
        FOREIGN KEY (season_id) REFERENCES season(id),
        FOREIGN KEY (circuit_id) REFERENCES circuit(id)
    );
    
    CREATE TABLE IF NOT EXISTS team_driver (
        id INTEGER PRIMARY KEY,
        season_id INTEGER,
        team_id INTEGER,
        driver_id INTEGER,
        role TEXT,
        api_id INTEGER,
        FOREIGN KEY (season_id) REFERENCES season(id),
        FOREIGN KEY (team_id) REFERENCES team(id),
        FOREIGN KEY (driver_id) REFERENCES driver(id)
    );
    
    CREATE TABLE IF NOT EXISTS roundentry (
        id INTEGER PRIMARY KEY,
        round_id INTEGER,
        team_driver_id INTEGER,
        car_number INTEGER,
        api_id INTEGER,
        FOREIGN KEY (round_id) REFERENCES round(id),
        FOREIGN KEY (team_driver_id) REFERENCES team_driver(id)
    );
    
    CREATE TABLE IF NOT EXISTS session (
        id INTEGER PRIMARY KEY,
        round_id INTEGER,
        type TEXT,
        number INTEGER,
        timestamp TEXT,
        timezone TEXT,
        scheduled_laps INTEGER,
        point_system_id INTEGER,
        is_cancelled INTEGER,
        has_time_data INTEGER,
        api_id INTEGER,
        FOREIGN KEY (round_id) REFERENCES round(id)
    );
    
    CREATE TABLE IF NOT EXISTS session_entry (
        id INTEGER PRIMARY KEY,
        session_id INTEGER,
        round_entry_id INTEGER,
        grid INTEGER,
        position INTEGER,
        points REAL,
        laps_completed INTEGER,
        fastest_lap_rank INTEGER,
        time TEXT,
        detail TEXT,
        status TEXT,
        is_classified INTEGER,
        is_eligible_for_points INTEGER,
        api_id INTEGER,
        FOREIGN KEY (session_id) REFERENCES session(id),
        FOREIGN KEY (round_entry_id) REFERENCES roundentry(id)
    );
    
    CREATE TABLE IF NOT EXISTS driver_championship (
        id INTEGER PRIMARY KEY,
        season_id INTEGER,
        year INTEGER,
        driver_id INTEGER,
        round_id INTEGER,
        position INTEGER,
        points REAL,
        win_count INTEGER,
        highest_finish INTEGER,
        is_eligible INTEGER,
        adjustment_type TEXT,
        session_id INTEGER,
        session_number INTEGER,
        round_number INTEGER,
        FOREIGN KEY (season_id) REFERENCES season(id),
        FOREIGN KEY (driver_id) REFERENCES driver(id),
        FOREIGN KEY (round_id) REFERENCES round(id),
        FOREIGN KEY (session_id) REFERENCES session(id)
    );
    
    CREATE TABLE IF NOT EXISTS team_championship (
        id INTEGER PRIMARY KEY,
        season_id INTEGER,
        year INTEGER,
        team_id INTEGER,
        round_id INTEGER,
        position INTEGER,
        points REAL,
        win_count INTEGER,
        highest_finish INTEGER,
        is_eligible INTEGER,
        adjustment_type TEXT,
        session_id INTEGER,
        session_number INTEGER,
        round_number INTEGER
    );
    
    CREATE TABLE IF NOT EXISTS lap (
        id INTEGER PRIMARY KEY,
        session_entry_id INTEGER,
        number INTEGER,
        position INTEGER,
        time TEXT,
        average_speed TEXT,
        is_entry_fastest_lap INTEGER,
        is_deleted INTEGER,
        api_id INTEGER
    );
    
    CREATE TABLE IF NOT EXISTS pit_stop (
        id INTEGER PRIMARY KEY,
        session_entry_id INTEGER,
        lap_id INTEGER,
        number INTEGER,
        duration TEXT,
        local_timestamp TEXT,
        api_id INTEGER
    );
    
    CREATE TABLE IF NOT EXISTS penalty (
        id INTEGER PRIMARY KEY,
        earned_id INTEGER,
        served_id INTEGER,
        position INTEGER,
        license_points INTEGER,
        is_time_served_in_pit INTEGER,
        time TEXT,
        api_id INTEGER
    );
    
    CREATE TABLE IF NOT EXISTS base_team (
        id INTEGER PRIMARY KEY,
        name TEXT,
        api_id INTEGER
    );
    
    CREATE TABLE IF NOT EXISTS points_system (
        id INTEGER PRIMARY KEY,
        name TEXT,
        reference TEXT,
        partial INTEGER,
        driver_position_points INTEGER,
        driver_fastest_lap INTEGER,
        team_position_points INTEGER,
        team_fastest_lap INTEGER,
        shared_drive INTEGER,
        is_double_points INTEGER,
        api_id INTEGER
    );
    
    CREATE TABLE IF NOT EXISTS championship_system (
        id INTEGER PRIMARY KEY,
        name TEXT,
        reference TEXT,
        driver_best_results INTEGER,
        team_best_results INTEGER,
        driver_season_split INTEGER,
        team_season_split INTEGER,
        team_points_per_session INTEGER,
        eligibility TEXT,
        api_id INTEGER
    );
    
    CREATE TABLE IF NOT EXISTS championship_adjustment (
        id INTEGER PRIMARY KEY,
        adjustment INTEGER,
        api_id INTEGER,
        driver_id INTEGER,
        points REAL,
        season_id INTEGER,
        team_id INTEGER
    );
    
    -- Indexes
    CREATE INDEX IF NOT EXISTS idx_round_season ON round(season_id);
    CREATE INDEX IF NOT EXISTS idx_round_circuit ON round(circuit_id);
    CREATE INDEX IF NOT EXISTS idx_session_round ON session(round_id);
    CREATE INDEX IF NOT EXISTS idx_session_entry_session ON session_entry(session_id);
    CREATE INDEX IF NOT EXISTS idx_driver_champ_season ON driver_championship(season_id);
    CREATE INDEX IF NOT EXISTS idx_team_champ_season ON team_championship(season_id);
    CREATE INDEX IF NOT EXISTS idx_session_entry_round_entry ON session_entry(round_entry_id);
    CREATE INDEX IF NOT EXISTS idx_roundentry_round ON roundentry(round_id);
    CREATE INDEX IF NOT EXISTS idx_roundentry_team_driver ON roundentry(team_driver_id);
    CREATE INDEX IF NOT EXISTS idx_team_driver_driver ON team_driver(driver_id);
    CREATE INDEX IF NOT EXISTS idx_team_driver_team ON team_driver(team_id);
    """
    
    conn.executescript(schema_sql)
    
    conn.execute("PRAGMA foreign_keys = ON;")
    fk_enabled = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
    if fk_enabled:
        print("✓ Foreign key enforcement is ACTIVE")

def insert_table_data( conn: sqlite3.Connection, table_name: str, df: pd.DataFrame ) -> int:
    """Insert data from DataFrame into table - preserves schema with FK constraints."""
    # Map CSV table name to DB table name
    table_name_mapping = {
        'season': 'season',
        'circuit': 'circuit',
        'driver': 'driver',
        'team': 'team',
        'baseteam': 'base_team',
        'round': 'round',
        'roundentry': 'roundentry',
        'session': 'session',
        'sessionentry': 'session_entry',
        'teamdriver': 'team_driver',
        'driverchampionship': 'driver_championship',
        'teamchampionship': 'team_championship',
        'lap': 'lap',
        'pitstop': 'pit_stop',
        'penalty': 'penalty',
        'pointsystem': 'points_system',
        'championshipsystem': 'championship_system',
        'championshipadjustment': 'championship_adjustment'
    }

    target_table = table_name_mapping.get(table_name, table_name)

    # Get DB schema columns
    try:
        cursor = conn.execute(f"PRAGMA table_info({target_table});")
        db_columns = {row[1] for row in cursor.fetchall()}
    except Exception as e:
        print(f"  ✗ {table_name}: Failed to get DB schema: {e}")
        return 0

    csv_columns = set(df.columns)

    # Filter to only columns that exist in both
    cols_to_use = list(db_columns & csv_columns)

    if not cols_to_use:
        print(f"  ✗ {table_name}: NO matching columns between CSV and DB!")
        print(f"    CSV columns: {sorted(csv_columns)}")
        print(f"    DB columns:  {sorted(db_columns)}")
        return 0

    # Create filtered dataframe with matching columns
    df_subset = df[cols_to_use]

    # Attempt insertion
    try:
        df_subset.to_sql(target_table, conn, if_exists='append', index=False)
        row_count = len(df_subset)
        print(f"  ✓ {table_name}: {row_count:,} rows")
        return row_count
    except Exception as e:
        # Only show diagnostics on failure
        print(f"  ✗ {table_name}: Insertion failed: {type(e).__name__}: {e}")
        print(f"    CSV columns ({len(csv_columns)}): {sorted(csv_columns)}")
        print(f"    DB columns ({len(db_columns)}):  {sorted(db_columns)}")
        print(f"    Matching columns: {cols_to_use}")
        raise

def get_table_processing_order(dataframes: Dict[str, pd.DataFrame]) -> list:
    """
    Return tables in dependency order for FK-safe data insertion.
    
    Order rationale:
    1. Independent dimension tables (no FKs needed)
    2. Dimension tables with minimal FKs
    3. Core fact tables (need dimensions loaded)
    4. Transactional tables (need all upstream tables loaded)
    """
    
    # Define explicit dependency hierarchy
    table_order = [
        # Level 1: Independent tables (load first)
        'season', 'circuit', 'driver', 'team', 'points_system', 'championship_system', 'lap', 'penalty', 'pit_stop', 'team_championship', 'base_team', 'championship_adjustment',
        
        # Level 2: Depends on Level 1
        'round', 'team_driver',
        
        # Level 3: Depends on Levels 1-2
        'roundentry', 'session',
        
        # Level 4: Depends on Levels 1-3
        'session_entry', 'driver_championship'
    ]
    
    # Filter to only tables that exist in our data
    available_tables = set(dataframes.keys())
    ordered = [t for t in table_order if t in available_tables]
    
    # Add any tables not in our predefined order (edge case fallback)
    remaining = available_tables - set(ordered)
    ordered.extend(sorted(remaining))
    
    return ordered


def filter_empty_tables(dataframes: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Filter out empty DataFrames from processing."""
    return {name: df for name, df in dataframes.items() if not df.empty}

def build_f1_db(
    extracted_data_path: Path = None,
    output_db_path: Path = None
) -> Path:
    """Build the normalized F1 database with FK-safe ordering."""
    
    # Setup paths
    if extracted_data_path is None:
        extracted_data_path = get_extracted_data_path()
    
    if output_db_path is None:
        sql_folder = get_sql_folder()
        output_db_path = sql_folder / "formula1.db"
    
    if not extracted_data_path.exists():
        raise FileNotFoundError(
            f"Extracted data not found at {extracted_data_path}. "
            "Please run extract.py first."
        )
    
    if output_db_path.exists():
        output_db_path.unlink()
        print(f"Cleared existing database: {output_db_path}")
    
    print(f"\n{'='*60}")
    print("Building F1 Star Schema Database")
    print(f"{'='*60}\n")
    
    print(f"Loading extracted data from: {extracted_data_path}")
    with open(extracted_data_path, "rb") as f:
        dataframes = pickle.load(f)
    
    dataframes = filter_empty_tables(dataframes)
    print(f"Found {len(dataframes)} non-empty tables to process\n")
    
    # Get correct table order
    ordered_tables = get_table_processing_order(dataframes)
    print(f"Processing order ({len(ordered_tables)} tables):\n  {' → '.join(ordered_tables)}\n")
    
    conn = sqlite3.connect(str(output_db_path))
    
    # IMPORTANT: Disable FK during load, re-enable after commit
    conn.execute("PRAGMA foreign_keys = OFF;")
    
    try:
        print("Creating database schema...")
        create_complete_schema(conn)
        
        print("\nInserting data into tables:\n")
        tables_processed = 0
        
        # Process in dependency order
        for table_name in ordered_tables:
            df = dataframes[table_name]
            
            try:
                row_count = insert_table_data(conn, table_name, df)
                
                if row_count > 0:
                    print(f"  ✓ {table_name}: {row_count:,} rows")
                    tables_processed += 1
                else:
                    print(f"  ⊘ {table_name}: No matching columns or zero rows")
                    
            except Exception as e:
                print(f"  ✗ {table_name}: ERROR - {type(e).__name__}: {str(e)[:150]}")
        
        conn.commit()
        
        # NOW enable FK enforcement and verify
        print("\n" + "-"*60)
        print("Post-load FK validation:")
        print("-"*60)
        
        conn.execute("PRAGMA foreign_keys = ON;")
        violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
        
        if violations:
            print(f"⚠ Found {len(violations)} FK violation(s):")
            for v in violations[:10]:
                print(f"    - Table '{v[0]}': row_id={v[1]}, parent_table={v[2]}, parent_key_idx={v[3]}")
            if len(violations) > 10:
                print(f"    ... and {len(violations) - 10} more")
        else:
            print("✓ All foreign key constraints validated successfully")
        
        # Summary
        print("\n" + "-"*60)
        print("Final table row counts:")
        print("-"*60)
        
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        total_rows = 0
        for (table,) in cursor.fetchall():
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            total_rows += count
            status = "✓" if count > 0 else "⊘"
            print(f"  {status} {table}: {count:,} rows")
        
        print(f"\n{'='*60}")
        print("Database creation complete!")
        print(f"{'='*60}")
        
        print(f"\nOutput: {output_db_path.absolute()}")
        print(f"Total rows: {total_rows:,}")
        print(f"Tables loaded: {tables_processed}/{len(dataframes)}")
        
        return output_db_path
        
    finally:
        conn.close()

def create_f1_summary_view(db_path: Path = None) -> int:
    """
    Create (or replace) the f1summary VIEW in the star schema DB.
    
    Returns:
        int: Number of rows in the view
    """

    if db_path is None:
        src_folder = Path(__file__).resolve().parent
        db_path = src_folder.parent / "sql" / "formula1.db"

    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found at {db_path}. Run f1_db.py first."
        )

    countries_path = Path(__file__).resolve().parent / "resources" / "countries_lookup.csv"

    with sqlite3.connect(db_path) as conn:
        # 1. Stage the country lookup table
        countries = pd.read_csv(countries_path)
        countries.to_sql("_countries_lookup", conn, if_exists="replace", index=False)

        # 2. Drop and recreate the VIEW
        conn.execute("DROP VIEW IF EXISTS f1summary")

        conn.execute("""
            CREATE VIEW f1summary AS
            SELECT
                se.id                        AS resultId,
                se.grid                      AS grid,
                se.position                  AS positionOrder,
                dc.points                    AS cumulPoints,
                se.points                    AS points,
                se.laps_completed            AS laps,
                se.fastest_lap_rank          AS "rank",
                CASE
                    WHEN se.detail GLOB '+[0-9][0-9]* Lap'
                        THEN 'Lapsed'
                    WHEN se.detail IN ('107% Rule', 'Did not qualify', 'Did not prequalify')
                        THEN 'Not Qualified'
                    WHEN se.detail IN ('Finished', 'Disqualified', 'Not classified', 'Lapsed')
                        THEN se.detail
                    ELSE 'Abandoned'
                END                          AS status,
                ssn.year                     AS year,
                rnd.number                   AS round,
                rnd.name                     AS circuit,
                d.forename || ' ' || d.surname
                                             AS driverName,
                ssn.year - CAST(strftime('%Y', d.date_of_birth) AS INTEGER)
                                             AS driverAge,
                t.name                       AS constructorName,
                dc_map.country               AS driverCountry,
                tc_map.country               AS constructorCountry,
                'images/icons8-' ||
                    replace(lower(dc_map.country), ' ', '-') ||
                    '-50.png'                AS driverImage,
                'images/icons8-' ||
                    replace(lower(tc_map.country), ' ', '-') ||
                    '-50.png'                AS constructorImage

            FROM session_entry se
            INNER JOIN session s
                ON se.session_id = s.id
            INNER JOIN roundentry re
                ON se.round_entry_id = re.id
            INNER JOIN team_driver td
                ON re.team_driver_id = td.id
            INNER JOIN driver d
                ON td.driver_id = d.id
            INNER JOIN team t
                ON td.team_id = t.id
            INNER JOIN season ssn
                ON td.season_id = ssn.id
            INNER JOIN round rnd
                ON re.round_id = rnd.id
            LEFT JOIN driver_championship dc
                ON dc.driver_id = d.id
               AND dc.session_id = s.id
            LEFT JOIN _countries_lookup dc_map
                ON dc_map.country_code = d.country_code
            LEFT JOIN _countries_lookup tc_map
                ON tc_map.country_code = t.country_code
            WHERE s.type = 'R'
              AND ssn.year < strftime('%Y', 'now')
        """)

        # 3. Get row count from the VIEW (just like querying a table)
        row_count = conn.execute("SELECT COUNT(*) FROM f1summary").fetchone()[0]
        
        print(f"Created f1summary VIEW: {row_count:,} rows in {db_path}")
        return row_count


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Build F1 Star Schema Database"
    )
    parser.add_argument("--input", type=str, default=None, help="Path to extracted_data.pkl")
    parser.add_argument("--output", type=str, default=None, help="Path to output database")
    parser.add_argument("--clean", action="store_true", help="Remove existing database")
    
    args = parser.parse_args()
    
    db_path = Path(args.output) if args.output else Path("sql/star_schema.db")
    
    if args.clean:
        if db_path.exists():
            print(f"Removing: {db_path}")
            db_path.unlink()
    
    try:
        # Step 1: Build the star schema database
        result = build_f1_db(
            extracted_data_path=Path(args.input) if args.input else None,
            output_db_path=Path(args.output) if args.output else None
        )
        
        # Step 2: Create the f1summary VIEW and get row count
        print("\nCreating f1summary VIEW...")
        view_row_count = create_f1_summary_view(db_path=result)
        
        print(f"\n{'='*60}")
        print(f"All outputs ready:")
        print(f"{'='*60}")
        print(f"  ✓ Database: {result.absolute()}")
        print(f"  ✓ VIEW: f1summary ({view_row_count:,} rows)")
        print(f"  ✓ View auto-updates with new data")
        print(f"{'='*60}\n")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
