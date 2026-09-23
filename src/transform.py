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

    # Make local copies so the original extracted data is not modified
    circuits = dataframes["circuits"].copy()
    constructor_results = dataframes["constructor_results"].copy()
    constructor_standings = dataframes["constructor_standings"].copy()
    constructors = dataframes["constructors"].copy()
    driver_standings = dataframes["driver_standings"].copy()
    drivers = dataframes["drivers"].copy()
    races = dataframes["races"].copy()
    results = dataframes["results"].copy()
    status = dataframes["status"].copy()

    countries_path = Path(__file__).resolve().parent / "resources" / "countries_lookup.csv"
    countries = pd.read_csv(countries_path)

    # Remove unnecessary columns
    circuits_df = circuits.drop(
        columns=["lat", "lng", "url"],
        errors="ignore"
    )

    constructor_results_df = constructor_results.drop(
        columns=["status"],
        errors="ignore"
    )

    constructor_standings_df = constructor_standings.drop(
        columns=["positionText"],
        errors="ignore"
    )

    constructors_df = constructors.drop(
        columns=["url"],
        errors="ignore"
    )

    # Make Alfa Romeo an Italian constructor
    constructors_df.loc[
        constructors_df["name"] == "Alfa Romeo",
        "nationality"
    ] = "Italian"

    # Driver standings columns
    driver_standings_df = driver_standings[
        ["driverStandingsId", "raceId", "driverId", "points"]
    ].rename(columns={"points": "cumulPoints"})

    # Driver columns
    drivers_df = drivers.drop(
        columns=["number", "url"],
        errors="ignore"
    )

    # Race columns
    races_df = races[
        ["raceId", "year", "round", "circuitId", "raceName", "date"]
    ]

    # Results columns
    result_columns_to_remove = [
        "number",
        "time",
        "milliseconds",
        "fastestLap",
        "fastestLapTime",
        "fastestLapSpeed",
        "position",
        "positionText",
    ]

    results_df = results.drop(
        columns=result_columns_to_remove,
        errors="ignore"
    )

    # Convert status values
    status_df = status.copy()

    finished_statuses = [
        "Finished",
        "Disqualified",
        "Not classified",
    ]

    not_qualified_statuses = [
        "107% Rule",
        "Did not qualify",
        "Did not prequalify",
    ]

    status_df["status"] = status_df["status"].where(
        status_df["status"].isin(finished_statuses),
        "Abandoned"
    )

    # Statuses such as "+1 Lap" or "+3 Laps" become "Lapsed"
    lapsed_mask = status["status"].str.match(
        r"^\+\d+ Laps?$",
        na=False
    )

    status_df.loc[lapsed_mask, "status"] = "Lapsed"

    # Not-qualified statuses become "Not Qualified"
    not_qualified_mask = status["status"].isin(
        not_qualified_statuses
    )

    status_df.loc[not_qualified_mask, "status"] = "Not Qualified"

    # Join results with races, drivers, constructors, and status
    formula1 = (
        results_df
        .merge(races_df, on="raceId", how="left")
        .merge(drivers_df, on="driverId", how="left")
        .merge(constructors_df, on="constructorId", how="left")
        .merge(status_df, on="statusId", how="left")
        .merge(
            driver_standings_df,
            on=["raceId", "driverId"],
            how="left"
        )
    )

    # Replace missing cumulative points with zero
    formula1["cumulPoints"] = (
        formula1["cumulPoints"]
        .fillna(0)
    )

    # Remove unneeded columns
    columns_to_remove = [
        "raceId",
        "driverId",
        "constructorId",
        "circuitId",
        "statusId",
        "driverRef",
        "code",
        "constructorRef",
    ]

    formula1 = formula1.drop(
        columns=columns_to_remove,
        errors="ignore"
    )

    # Rename columns created by joins
    formula1 = formula1.rename(
        columns={
            "name_x": "circuit",
            "name_y": "constructorName",
            "nationality_x": "driverNationality",
            "nationality_y": "constructorNationality",
        }
    )

    # Calculate driver age
    formula1["date"] = pd.to_datetime(
        formula1["date"],
        errors="coerce"
    )

    formula1["dob"] = pd.to_datetime(
        formula1["dob"],
        errors="coerce"
    )

    formula1["driverAge"] = (
        (formula1["date"] - formula1["dob"]).dt.days / 365.25
    ).floordiv(1)

    # Remove date columns
    formula1 = formula1.drop(
        columns=["date", "dob"],
        errors="ignore"
    )

    # Merge first and last name into driverName
    formula1["driverName"] = (
        formula1["forename"].fillna("").str.strip()
        + " "
        + formula1["surname"].fillna("").str.strip()
    ).str.strip()

    formula1 = formula1.drop(
        columns=["forename", "surname"],
        errors="ignore"
    )

    # Clean nationality values
    formula1["driverNationality"] = (
        formula1["driverNationality"]
        .fillna("")
        .str.strip()
    )

    formula1["constructorNationality"] = (
        formula1["constructorNationality"]
        .fillna("")
        .str.strip()
    )

    # Rename country lookup column for driver nationality
    driver_countries = countries.rename(
        columns={
            "Adjective": "driverNationality",
            "Country": "driverCountry",
        }
    )

    formula1 = formula1.merge(
        driver_countries[
            ["driverNationality", "driverCountry"]
        ],
        on="driverNationality",
        how="left"
    )

    formula1 = formula1.drop(
        columns=["driverNationality"],
        errors="ignore"
    )

    # Rename country lookup column for constructor nationality
    constructor_countries = countries.rename(
        columns={
            "Adjective": "constructorNationality",
            "Country": "constructorCountry",
        }
    )

    formula1 = formula1.merge(
        constructor_countries[
            ["constructorNationality", "constructorCountry"]
        ],
        on="constructorNationality",
        how="left"
    )

    formula1 = formula1.drop(
        columns=["constructorNationality"],
        errors="ignore"
    )

    # Build country image paths
    formula1 = build_country_image_paths(formula1)

    # Keep only previous years
    current_year = date.today().year

    formula1 = formula1[
        formula1["year"] < current_year
    ].copy()

    return formula1


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
