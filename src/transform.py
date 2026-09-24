from datetime import date
import pandas as pd


def build_image_path(country):
    """
    Convert a country name to an image path slug.

    Mirrors R logic: paste0("images/icons8-", gsub(" ", "-", tolower(country)), "-50.png")

    Parameters
    ----------
    country : str or NaN
        Country name to convert.

    Returns
    -------
    str or pd.NA
        Image path string, or pd.NA for missing values.
    """

    if pd.isna(country) or str(country).strip() == "":
        return pd.NA

    slug = (
        str(country)
        .strip()
        .lower()
        .replace(" ", "-")
    )
    return f"images/icons8-{slug}-50.png"


def build_country_image_paths(formula1: pd.DataFrame) -> pd.DataFrame:
    """
    Add driverImage and constructorImage columns mapping country names
    to icon file paths.

    Parameters
    ----------
    formula1 : pd.DataFrame
        DataFrame with driverCountry and constructorCountry columns.

    Returns
    -------
    pd.DataFrame
        DataFrame with new driverImage and constructorImage columns added.
    """

    formula1["driverImage"] = formula1["driverCountry"].apply(build_image_path)
    formula1["constructorImage"] = formula1["constructorCountry"].apply(build_image_path)

    return formula1


def transform_data(dataframes: dict) -> pd.DataFrame:
    """
    Transform the extracted Ergast F1 data into the formula1 dataset.

    Parameters
    ----------
    dataframes : dict
        Dictionary of pandas DataFrames loaded from CSV files.

    Returns
    -------
    pandas.DataFrame
        Transformed Formula 1 dataset.
    """

#    for name, df in dataframes.items():
#        print(f"DataFrame '{name}':")
#        print("Columns:", list(df.columns))
#        print()

    import pandas as pd
    
    # Make local copies
    sessionentry = dataframes["sessionentry"].copy()
    roundentry = dataframes["roundentry"].copy().rename(columns={'id': 'round_entry_id'})
    session = dataframes["session"].copy().rename(columns={'id': 'session_id'})
    teamdriver = dataframes["teamdriver"].copy().rename(columns={'id': 'team_driver_id'})
    driver = dataframes["driver"].copy().rename(columns={'id': 'driver_id', 'country_code': 'driver_country_code'})
    team = dataframes["team"].copy().rename(columns={'id': 'team_id', 'country_code': 'team_country_code', 'name': 'team_name'})
    season = dataframes["season"].copy().rename(columns={'id': 'season_id'})
    round = dataframes["round"].copy().rename(columns={'id': 'round_id', 'name': 'round_name'})
    circuit = dataframes["circuit"].copy().rename(columns={'id': 'circuit_id', 'name': 'circuit_name'})
    driverchampionship = dataframes["driverchampionship"].copy().rename(columns={'points': 'cumul_points'})
    
    # Simple merge: sessionentry LEFT JOIN roundentry
    # All rows from sessionentry, matching rows from roundentry
    final_df = sessionentry.merge(
        roundentry[['round_entry_id', 'team_driver_id', 'round_id']],
        left_on='round_entry_id',
        right_on='round_entry_id',
        how='left'
    )
    
    final_df = final_df.merge(
        session[['session_id', 'type']],
        left_on='session_id',
        right_on='session_id',
        how='left'
    )

    final_df = final_df.query("type == 'R'")

    final_df = final_df.merge(
        teamdriver[['team_driver_id', 'driver_id', 'season_id', 'team_id']],
        left_on='team_driver_id',
        right_on='team_driver_id',
        how='left'
    )

    final_df = final_df.merge(
        driver[['driver_id', 'driver_country_code', 'date_of_birth', 'forename', 'surname']],
        left_on='driver_id',
        right_on='driver_id',
        how='left'
    )

    final_df = final_df.merge(
        team[['team_id', 'team_country_code', 'team_name']],
        left_on='team_id',
        right_on='team_id',
        how='left'
    )

    final_df = final_df.merge(
        season[['season_id', 'year']],
        left_on='season_id',
        right_on='season_id',
        how='left'
    )

    final_df = final_df.merge(
        round[['round_id', 'circuit_id', 'round_name', 'number']],
        left_on='round_id',
        right_on='round_id',
        how='left'
    )

    final_df = final_df.merge(
        circuit[['circuit_id', 'circuit_name']],
        left_on='circuit_id',
        right_on='circuit_id',
        how='left'
    )

    final_df = final_df.merge(
        driverchampionship[['driver_id', 'session_id', 'cumul_points']],
        left_on=['driver_id', 'session_id'],
        right_on=['driver_id', 'session_id'],
        how='left'
    )

    # 1. Select and create the transformed columns
    final_df = final_df[['id', 'grid', 'position', 'cumul_points', 'points',
                         'laps_completed', 'fastest_lap_rank', 'detail',
                         'year', 'number', 'round_name', 'forename', 
                         'surname', 'date_of_birth', 'team_name', 
                         'driver_country_code', 'team_country_code']].copy()
    
    # 2. Concatenate forename + surname into driver_name
    final_df['driver_name'] = final_df['forename'].fillna('') + ' ' + final_df['surname'].fillna('')
    
    # 3. Calculate driver_age from date_of_birth and year
    def calc_age(date_of_birth, year):
        if pd.isna(date_of_birth) or pd.isna(year):
            return None
        try:
            birth_year = pd.to_datetime(date_of_birth).year
            return int(year) - birth_year
        except:
            return None
    
    final_df['driver_age'] = final_df.apply(
        lambda row: calc_age(row['date_of_birth'], row['year']),
        axis=1
    )
    
    # 4. Drop the original columns used for transformation
    final_df = final_df.drop(columns=['forename', 'surname', 'date_of_birth'])
    
    # 5. Reorder columns in the desired order
    final_df = final_df[[
        'id',
        'grid',
        'position',
        'points',
        'laps_completed',
        'fastest_lap_rank',
        'year',
        'number',
        'round_name',
        'team_name',
        'detail',
        'cumul_points',
        'driver_age',
        'driver_name',
        'driver_country_code',
        'team_country_code'
    ]]

    final_df = final_df.rename(columns={'position': 'positionOrder',
                                        'cumul_points': 'cumulPoints',
                                        'round_name': 'circuit',
                                        'laps_completed': 'laps',
                                        'fastest_lap_rank': 'rank',
                                        'detail': 'status',
                                        'driver_name': 'driverName',
                                        'driver_age': 'driverAge',
                                        'team_name': 'constructorName'})

    # Load the countries lookup table
    countries_path = Path(__file__).resolve().parent / "resources" / "countries_lookup.csv"
    countries = pd.read_csv(countries_path)

    # Create mapping dictionary from countries DataFrame
    country_map = dict(zip(countries['country_code'], countries['country']))
    
    # Map codes to country names
    final_df['driverCountry'] = final_df['driver_country_code'].map(country_map)
    final_df['constructorCountry'] = final_df['team_country_code'].map(country_map)

    # Drop the two country code columns
    final_df = final_df.drop(columns=['driver_country_code', 'team_country_code'])

    # Build country image paths
    final_df = build_country_image_paths(final_df)

    # Update the status column
    finished_statuses = [
        "Finished",
        "Disqualified",
        "Not classified",
        "Lapsed"
    ]
    
    not_qualified_statuses = [
        "107% Rule",
        "Did not qualify",
        "Did not prequalify",
    ]
    
    # FIRST: Catch lapsed statuses (+1 Lap, +3 Laps, etc.)
    lapsed_mask = final_df["status"].str.match(
        r"^\+\d+ Laps?$",
        na=False
    )
    final_df.loc[lapsed_mask, "status"] = "Lapsed"
    
    # THEN: Handle not-qualified statuses
    not_qualified_mask = final_df["status"].isin(not_qualified_statuses)
    final_df.loc[not_qualified_mask, "status"] = "Not Qualified"
    
    # LAST: Everything else becomes "Abandoned" (except finished_statuses)
    final_df["status"] = final_df["status"].where(
        final_df["status"].isin(finished_statuses),
        "Abandoned"
    )

    # Get the current year
    current_year = date.today().year
    # Filter to keep only years before current year (i.e., <= 2025)
    final_df = final_df[final_df["year"] < current_year]

    # Make Alfa Romeo an Italian constructor
#    constructors_df.loc[
#        constructors_df["name"] == "Alfa Romeo",
#        "nationality"
#    ] = "Italian"

    # ==========================================
    # SAVE the formula1 data set as a CSV file
    # ==========================================

    """Return the data/processed folder and create it if necessary."""
    src_folder = Path(__file__).resolve().parent
    processed_folder = src_folder.parent / "data" / "processed"
    processed_folder.mkdir(parents=True, exist_ok=True)

    output_file = processed_folder / "formula1.csv"
    
    final_df.to_csv(output_file, index=False)
    print(f"Saved CSV: {output_file} ({len(final_df):,} rows)")
    
    return final_df


if __name__ == "__main__":
    import pickle
    from pathlib import Path

    output_folder = Path(__file__).resolve().parent.parent / "output"

    with open(output_folder / "extracted_data.pkl", "rb") as f:
        dataframes = pickle.load(f)

    formula1 = transform_data(dataframes)
    print(f"Output shape: {formula1.shape[0]:,} rows x {formula1.shape[1]} columns")

    with open(output_folder / "transformed_data.pkl", "wb") as f:
        pickle.dump(formula1, f)
