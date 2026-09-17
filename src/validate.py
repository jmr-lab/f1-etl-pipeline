import pandas as pd
from datetime import date
from typing import List, Dict

# Constants (uppercase, as per Java convention)
MIN_F1_YEAR = 1950
CURRENT_YEAR = date.today().year
LAST_EXPECTED_YEAR = CURRENT_YEAR - 1
MAX_SHARED_WINNERS = 2

# Global error accumulator
validation_errors: List[Dict] = []

def _add_error(check_name: str, message: str) -> None:
    """Add an error to the global list."""
    validation_errors.append({"check": check_name, "message": message})

def validate_year(formula1: pd.DataFrame) -> bool:
    """Validate the year column."""

    if "year" not in formula1.columns:
        _add_error("year", "'year' column is missing.")
        return False

    year_raw = formula1["year"].astype("string").str.strip()

    invalid_format = (
        year_raw.isna()
        | year_raw.eq("")
        | ~year_raw.str.fullmatch(r"\d{4}", na=False)
    )

    year_numeric = pd.to_numeric(year_raw, errors="coerce")

    invalid_range = (
        year_numeric.isna()
        | (year_numeric < MIN_F1_YEAR)
        | (year_numeric > LAST_EXPECTED_YEAR)
    )

    invalid_rows = formula1.loc[
        invalid_format | invalid_range,
        ["year"]
    ]

    if not invalid_rows.empty:
        invalid_values = invalid_rows["year"].tolist()[:20]
        _add_error(
            "year",
            f"Expected four-digit years from {MIN_F1_YEAR} through {LAST_EXPECTED_YEAR}. "
            f"Invalid values (first 20): {invalid_values}"
        )
        return False

    return True

def validate_winners(formula1: pd.DataFrame) -> bool:
    """Ensure every year/round combination has at least one winner."""

    required_columns = {"year", "round", "positionOrder"}
    missing_columns = required_columns - set(formula1.columns)

    if missing_columns:
        _add_error(
            "winners",
            f"Missing columns: {sorted(missing_columns)}"
        )
        return False

    if formula1[["year", "round"]].isna().any().any():
        _add_error(
            "winners",
            "year or round contains missing values"
        )
        return False

    position_order = pd.to_numeric(
        formula1["positionOrder"],
        errors="coerce"
    )

    winner_counts = (
        formula1.loc[position_order.eq(1)]
        .groupby(["year", "round"])
        .size()
        .rename("winner_count")
        .reset_index()
    )

    all_races = (
        formula1[["year", "round"]]
        .drop_duplicates()
    )

    race_check = all_races.merge(
        winner_counts,
        on=["year", "round"],
        how="left"
    )

    race_check["winner_count"] = (
        race_check["winner_count"]
        .fillna(0)
        .astype(int)
    )

    no_winners = race_check[
        race_check["winner_count"] == 0
    ]

    if not no_winners.empty:
        missing_wins = len(no_winners)
        sample_races = no_winners.head(5).to_dict(orient="records")
        _add_error(
            "winners",
            f"{missing_wins} races have ZERO winners. "
            f"First 5 examples: {sample_races}"
        )
        return False

    excessive_wins = race_check[
        race_check["winner_count"] > MAX_SHARED_WINNERS
    ]

    if not excessive_wins.empty:
        excessive = len(excessive_wins)
        sample_excessive = excessive_wins.head(3).to_dict(orient="records")
        _add_error(
            "winners",
            f"{excessive} races have more than {MAX_SHARED_WINNERS} winners (suspicious). "
            f"Examples: {sample_excessive}"
        )
        return False

    shared_victories = race_check[
        (race_check["winner_count"] == 2)
    ]

    if not shared_victories.empty:
        print(f"  INFO: Found {len(shared_victories)} races with shared victories")

    return True

def validate_status_points(formula1: pd.DataFrame) -> bool:
    """
    Validate that drivers marked as Not Qualified or Not classified
    received zero points.
    """

    required_columns = {"status", "points"}
    missing_columns = required_columns - set(formula1.columns)

    if missing_columns:
        _add_error(
            "status_points",
            f"Missing columns: {sorted(missing_columns)}"
        )
        return False

    status = (
        formula1["status"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    points = pd.to_numeric(
        formula1["points"],
        errors="coerce"
    )

    relevant_statuses = {
        "not qualified",
        "not classified",
    }

    invalid_rows = formula1.loc[
        status.isin(relevant_statuses)
        & (points != 0),
        ["year", "round", "status", "points"]
    ]

    if not invalid_rows.empty:
        sample = invalid_rows.head(5).to_dict(orient="records")
        _add_error(
            "status_points",
            f"Drivers with status 'Not Qualified' or 'Not classified' must have zero points. "
            f"{len(invalid_rows)} violations found. First 5 examples: {sample}"
        )
        return False

    return True

def validate_formula1(formula1: pd.DataFrame) -> bool:
    """
    Main validation function.

    Returns
    -------
    bool
        True if all validations pass, False otherwise.

    Raises
    ------
    ValueError
        If any validation fails.
    """

    if not isinstance(formula1, pd.DataFrame):
        _add_error("type", "Input must be a pandas DataFrame")
        raise ValueError(f"Validation FAILED: {_get_error_summary()}")

    validation_errors.clear()

    validators = [
        ("Year validation", validate_year),
        ("Winner validation", validate_winners),
        ("Status/Points validation", validate_status_points),
    ]

    for validator_name, validator_fn in validators:
        try:
            passed = validator_fn(formula1)
            print(f"  {validator_name}: {'PASS' if passed else 'FAIL'}")
            if not passed:
                break
        except Exception as e:
            _add_error(validator_name, f"Exception raised: {str(e)}")
            print(f"  {validator_name}: EXCEPTION - {e}")

    print()

    if validation_errors:
        print("Validation ERRORS:")
        for err in validation_errors:
            print(f"  - [{err['check']}] {err['message']}")
        print()
        raise ValueError(f"Validation FAILED: {_get_error_summary()}")

    print("All Formula 1 validations passed.")
    return True

def _get_error_summary() -> str:
    """Return a concise summary of accumulated errors."""
    if not validation_errors:
        return "No errors"

    summaries = []
    for err in validation_errors:
        summaries.append(f"{err['check']}: {err['message'][:100]}")

    return "; ".join(summaries[:5])