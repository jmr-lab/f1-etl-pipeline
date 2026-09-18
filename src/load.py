from pathlib import Path
import pandas as pd
import sqlite3

def get_output_folder() -> Path:
    """Return the project's output folder and create it if necessary."""
    src_folder = Path(__file__).resolve().parent
    output_folder = src_folder.parent / "output"
    output_folder.mkdir(parents=True, exist_ok=True)
    return output_folder


def save_formula1_csv(formula1: pd.DataFrame) -> None:
    """Save the Formula 1 DataFrame as a CSV file."""
    output_folder = get_output_folder()
    output_file = output_folder / "formula1.csv"
    
    formula1.to_csv(output_file, index=False)
    print(f"Saved CSV: {output_file} ({len(formula1):,} rows)")


def sql_value(value):
    """Convert a pandas/Python value into a MariaDB SQL value."""

    if pd.isna(value):
        return "NULL"

    if isinstance(value, str):
        escaped_value = value.replace("'", "''")
        return f"'{escaped_value}'"

    return str(value)


def save_formula1_sql(formula1: pd.DataFrame) -> None:
    """Save the Formula 1 DataFrame as a MariaDB-compatible SQL file."""

    output_folder = get_output_folder()
    output_file = output_folder / "formula1.sql"

    column_definitions = {
        "resultId": "INT",
        "grid": "INT",
        "positionOrder": "INT",
        "cumulPoints": "DOUBLE",
        "points": "DOUBLE",
        "year": "INT",
        "round": "INT",
        "circuit": "VARCHAR(255)",
        "driverName": "VARCHAR(255)",
        "driverAge": "INT",
        "constructorName": "VARCHAR(255)",
        "driverCountry": "VARCHAR(100)",
        "constructorCountry": "VARCHAR(100)",
        "driverImage": "VARCHAR(255)",
        "constructorImage": "VARCHAR(255)",
    }

    columns = list(column_definitions.keys())

    with output_file.open("w", encoding="utf-8") as file:
        file.write("DROP TABLE IF EXISTS formula1;\n\n")

        definitions = ",\n".join(
            f"    {column} {data_type}"
            for column, data_type in column_definitions.items()
        )

        file.write(
            "CREATE TABLE formula1 (\n"
            f"{definitions}\n"
            ");\n\n"
        )

        column_names = ", ".join(columns)

        # Batched INSERT for efficiency
        BATCH_SIZE = 1000
        total_rows = len(formula1)

        for batch_start in range(0, total_rows, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total_rows)
            batch = formula1.iloc[batch_start:batch_end]

            values_blocks = []
            for _, row in batch.iterrows():
                values = ", ".join(
                    sql_value(row[column])
                    for column in columns
                )
                values_blocks.append("(" + values + ")")

            # FIXED: Join values outside f-string
            values_section = ",\n".join(values_blocks)

            file.write("INSERT INTO formula1 (" + column_names + ") VALUES\n")
            file.write(values_section + ";\n\n")

    print(f"Saved SQL file: {output_file}")


def save_formula1_db(formula1: pd.DataFrame) -> None:
    """Save the Formula 1 DataFrame as a SQLite database file."""

    output_folder = get_output_folder()
    output_file = output_folder / "formula1.db"

    with sqlite3.connect(output_file) as connection:
        formula1.to_sql(
            "formula1",
            connection,
            if_exists="replace",
            index=False,
        )

        # Indexes for common queries
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_formula1_race
            ON formula1 (year, round)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_formula1_driver
            ON formula1 (driverName)
            """
        )

        connection.commit()

    print(f"Saved database: {output_file} ({len(formula1):,} rows)")


def save_formula1(formula1: pd.DataFrame) -> None:
    """Save the Formula 1 DataFrame as CSV and SQL."""
    save_formula1_csv(formula1)
    save_formula1_sql(formula1)
    save_formula1_db(formula1)


if __name__ == "__main__":
    import pickle
    from pathlib import Path

    output_folder = Path(__file__).resolve().parent.parent / "output"

    with open(output_folder / "validated_data.pkl", "rb") as f:
        formula1 = pickle.load(f)

    save_formula1(formula1)
