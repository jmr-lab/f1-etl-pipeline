# F1 ETL Pipeline

ETL pipeline that transforms raw Ergast F1 CSV data into an analytics-ready dataset for Formula 1 analytics and driver GOAT analysis.

## Overview

This pipeline ingests raw CSV files from the [Ergast F1 API dataset](https://relational.fel.cvut.cz/dataset/ErgastF1), validates data quality, applies transformations, and outputs a unified `formula1.csv` file. The cleaned dataset feeds the companion [Formula-1 Analytics](https://github.com/jmr-lab/Formula-1) R project for exploratory analysis and GOAT modelling.

## Pipeline Architecture

┌────────────┐ ┌─────────────┐ ┌──────────────┐ ┌────────────┐
│ Extract │→ │ Transform │→ │ Validate │→ │ Load │
└────────────┘ └─────────────┘ └──────────────┘ └────────────┘
↓ ↓ ↓ ↓
10 CSVs Unified schema Quality checks CSV + SQL

## Features

- **Extract**: Loads 10+ CSV tables from the Ergast F1 dataset with encoding resilience
- **Transform**: Normalises schemas, merges relationships, calculates derived fields (driver age, cumulative points, image paths)
- **Validate**: 3 automated quality checks (year range, race winners, status-points consistency)
- **Load**: Exports both CSV and MariaDB-compatible SQL formats

## Installation

Clone this repository and ensure Python 3.11+ is installed:

```bash
git clone https://github.com/jmr-lab/f1-etl-pipeline.git
cd f1-etl-pipeline
pip install pandas
Usage

Run:
python run_pipeline.py

Directory Structure:
f1-etl-pipeline/
├── src/
│   ├── extract.py
│   ├── transform.py
│   ├── validate.py
│   └── load.py
├── data/
├── output/            ← Generated formula1.csv and formula1.sql
├── run_pipeline.py
└── README.md

Outputs
File	Description
output/formula1.csv	Analytics-ready dataset
output/formula1.sql	MariaDB import script

Data Schema

The formula1.csv file contains the following columns:
Column	Type	Description
resultId	INT	Unique result identifier
grid	INT	Starting grid position
positionOrder	INT	Finishing position order
cumulPoints	DOUBLE	Cumulative driver points at race
points	DOUBLE	Points awarded for the race
year	INT	Season year
round	INT	Round number within season
circuit	VARCHAR(255)	Circuit name
driverName	VARCHAR(255)	Full driver name
driverAge	INT	Driver age in years at race date
constructorName	VARCHAR(255)	Team name
driverCountry	VARCHAR(100)	Driver's country of origin
constructorCountry	VARCHAR(100)	Constructor's country of origin
driverImage	VARCHAR(255)	Path to flag icon
constructorImage	VARCHAR(255)	Path to flag icon
Technologies

    Python 3.11+
    pandas (>= 2.0)
    No external API calls (offline CSV processing)

Related Projects
Project	Language	Purpose
Formula-1 Analytics	R (tidyverse)	EDA, visualisations, GOAT modelling

Why Two Languages?

This pipeline uses Python for production-grade ETL (data extraction, transformation, validation, export), while the R project focuses on statistical analysis and visualisation. This demonstrates language-agnostic engineering patterns and lets analysts work in their preferred ecosystem.

Validation Checks

The pipeline enforces these data quality rules:

    Year Range: All races must be between 1950 and the current year
    Race Winners: Every race (year, round combination) must have at least one winner
    Status-Points Consistency: Drivers marked "Not Qualified" or "Not Classified" must have 0 points
