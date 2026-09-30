"""
F1 Star Schema Database Builder

Normalizes extracted CSV files into SQLite database with
proper relationships matching the Jolpica schema.
"""

from pathlib import Path
import sqlite3
import pickle
import sys
import pandas as pd

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
    """Create the normalized F1 database schema using id for all primary keys."""
    
    # Disable FK temporarily to allow schema creation
    conn.execute("PRAGMA foreign_keys = OFF;")
    
    schema_sql = """
    -- Dimension tables (must be created before fact tables with FKs to them)
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
    
    -- Fact tables with FK constraints (from R script: 14 total)
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
    
    -- Lookup tables
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
    
    # Enable FK enforcement AFTER schema creation
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Verify FK constraints are active
    fk_enabled = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
    if fk_enabled:
        print("✓ Foreign key enforcement is ACTIVE")
    else:
        print("✗ WARNING: Foreign key enforcement is DISABLED")
    
    # Check for any FK violations in existing data
    violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
    if violations:
        print(f"⚠ Foreign key violations found: {violations}")
    else:
        print("✓ All foreign key constraints validated successfully")

def insert_table_data(
    conn: sqlite3.Connection,
    table_name: str,
    df: pd.DataFrame
) -> int:
    """Insert data from DataFrame into table - preserves schema with FK constraints."""
    
    # Map from CSV table name to DB table name
    table_name_mapping = {
        'season': 'season',
        'circuit': 'circuit',
        'driver': 'driver',
        'team': 'team',
        'base_team': 'base_team',
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
    
    # Valid columns for each table (matching the actual schema above)
    valid_columns = {
        'season': ['id', 'year', 'api_id', 'championship_system_id', 'wikipedia'],
        'circuit': ['id', 'name', 'reference', 'locality', 'country', 'country_code', 'latitude', 'longitude', 'altitude', 'wikipedia', 'api_id'],
        'driver': ['id', 'reference', 'abbreviation', 'forename', 'surname', 'nationality', 'country_code', 'date_of_birth', 'permanent_car_number', 'wikipedia', 'api_id'],
        'team': ['id', 'name', 'reference', 'nationality', 'country_code', 'base_team_id', 'primary_color', 'wikipedia', 'api_id'],
        'base_team': ['id', 'name', 'api_id'],
        'round': ['id', 'season_id', 'circuit_id', 'number', 'race_number', 'name', 'date', 'is_cancelled', 'wikipedia', 'api_id'],
        'roundentry': ['id', 'round_id', 'team_driver_id', 'car_number', 'api_id'],
        'session': ['id', 'round_id', 'type', 'number', 'timestamp', 'timezone', 'scheduled_laps', 'point_system_id', 'is_cancelled', 'has_time_data', 'api_id'],
        'session_entry': ['id', 'session_id', 'round_entry_id', 'grid', 'position', 'points', 'laps_completed', 'fastest_lap_rank', 'time', 'detail', 'status', 'is_classified', 'is_eligible_for_points', 'api_id'],
        'team_driver': ['id', 'season_id', 'team_id', 'driver_id', 'role', 'api_id'],
        'driver_championship': ['id', 'season_id', 'year', 'driver_id', 'round_id', 'position', 'points', 'win_count', 'highest_finish', 'is_eligible', 'adjustment_type', 'session_id', 'session_number', 'round_number'],
        'team_championship': ['id', 'season_id', 'year', 'team_id', 'round_id', 'position', 'points', 'win_count', 'highest_finish', 'is_eligible', 'adjustment_type', 'session_id', 'session_number', 'round_number'],
        'lap': ['id', 'session_entry_id', 'number', 'position', 'time', 'average_speed', 'is_entry_fastest_lap', 'is_deleted', 'api_id'],
        'pit_stop': ['id', 'session_entry_id', 'lap_id', 'number', 'duration', 'local_timestamp', 'api_id'],
        'penalty': ['id', 'earned_id', 'served_id', 'position', 'license_points', 'is_time_served_in_pit', 'time', 'api_id'],
        'points_system': ['id', 'name', 'reference', 'partial', 'driver_position_points', 'driver_fastest_lap', 'team_position_points', 'team_fastest_lap', 'shared_drive', 'is_double_points', 'api_id'],
        'championship_system': ['id', 'name', 'reference', 'driver_best_results', 'team_best_results', 'driver_season_split', 'team_season_split', 'team_points_per_session', 'eligibility', 'api_id'],
        'championship_adjustment': ['id', 'adjustment', 'api_id', 'driver_id', 'points', 'season_id', 'team_id']
    }
    
    if target_table in valid_columns:
        existing_cols = set(df.columns)
        cols_to_keep = [col for col in valid_columns[target_table] if col in existing_cols]
        
        if len(cols_to_keep) < len(valid_columns[target_table]):
            missing = set(valid_columns[target_table]) - existing_cols
            print(f"  ⚠ Missing columns for {target_table}: {missing}")
        
        df = df[cols_to_keep]
    
    # CHANGE HERE: Use 'append' instead of 'replace' to preserve FK constraints!
    df.to_sql(target_table, conn, if_exists='append', index=False)
    return len(df)

def build_f1_db(
    extracted_data_path: Path = None,
    output_db_path: Path = None
) -> Path:
    """Build the normalized F1 database."""
    
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
    
    # DELETE EXISTING DATABASE TO START FRESH
    if output_db_path.exists():
        output_db_path.unlink()
        print(f"Cleared existing database: {output_db_path}")
    
    print(f"\n{'='*60}")
    print("Building F1 Star Schema Database from Extracted Data")
    print(f"{'='*60}\n")
    
    print(f"Loading extracted data from: {extracted_data_path}")
    with open(extracted_data_path, "rb") as f:
        dataframes = pickle.load(f)
    
    print(f"Found {len(dataframes)} tables to process\n")
    
    conn = sqlite3.connect(str(output_db_path))
    conn.execute("PRAGMA foreign_keys = ON;")  # Enable FK enforcement
    
    try:
        print("Creating database schema...")
        create_complete_schema(conn)
        
        print("\nInserting data into tables:\n")
        tables_processed = 0
        
        for table_name, df in sorted(dataframes.items()):
            if df.empty:
                print(f"  ⊘ {table_name}: Skipped (empty)")
                continue
            
            try:
                row_count = insert_table_data(conn, table_name, df)
                print(f"  ✓ {table_name}: {row_count:,} rows")
                tables_processed += 1
            except Exception as e:
                print(f"  ✗ {table_name}: ERROR - {e}")
        
        conn.commit()
        
        # Verify FK constraints AFTER data insertion
        print("\n" + "-"*60)
        print("Verifying foreign key constraints:")
        print("-"*60)
        fk_enabled = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        print(f"FK enforcement: {'ENABLED' if fk_enabled else 'DISABLED'}")
        
        violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
        if violations:
            print(f"⚠ FK violations: {violations}")
        else:
            print("✓ All FK constraints valid")
        
        # Print summary with row counts
        print("\n" + "-"*60)
        print("Final table row counts:")
        print("-"*60)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        for (table,) in cursor.fetchall():
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {count:,} rows")
        
        print(f"\n{'='*60}")
        print(f"Database creation complete!")
        print(f"{'='*60}")
        print(f"\nOutput: {output_db_path.absolute()}")
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
