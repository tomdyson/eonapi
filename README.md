# eonapi

[![PyPI version](https://badge.fury.io/py/eonapi.svg)](https://badge.fury.io/py/eonapi)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python CLI tool for retrieving and analyzing electricity/gas consumption data from the E.ON Next API.

## Features

- **Automatic Pagination**: Fetches all available data for your requested time period
- **30-minute intervals**: Retrieves half-hourly consumption data
- **Multiple Commands**:
  - `export`: Export raw data to CSV or store in SQLite database
  - `stats`: Display consumption statistics and analysis
  - `ui`: Interactive web UI with charts and visualizations
- **Database Storage**: SQLite storage with automatic incremental updates
- **Multiple meter support**: Auto-selects single meter, prompts for selection with multiple
- **Flexible authentication**: Environment variables (recommended) or command-line arguments
- **Progress feedback**: Shows pagination progress while fetching large datasets

## Installation

### From PyPI (recommended)

```bash
pip install eonapi
```

### From source

```bash
git clone https://github.com/tomdyson/eonapi.git
cd eonapi
pip install -e .
```

### Using uv (for development)

```bash
git clone https://github.com/tomdyson/eonapi.git
cd eonapi
uv sync
```

## Quick Start

### Set up credentials

```bash
export EON_USERNAME=your@email.com
export EON_PASSWORD=yourpassword
```

### Export data to CSV

```bash
# Export last 30 days to stdout
eonapi export > consumption.csv

# Export last 7 days to file
eonapi export --days 7 --output last_week.csv

# Export with inline credentials
eonapi export --username your@email.com --password yourpass --days 30 > data.csv
```

### View statistics

```bash
# Display statistics for last 30 days
eonapi stats

# Statistics for last 7 days
eonapi stats --days 7
```

## Database Storage

The `--store` option enables SQLite database storage for your consumption data, with automatic incremental updates.

### Features

- **Incremental Updates**: Only fetches new data since the last run, saving time and API calls
- **Automatic Detection**: Checks the latest timestamp in your database and fetches only newer records
- **Duplicate Handling**: Safely skips duplicate records if they already exist
- **Multiple Meters**: Supports storing data from multiple meters in the same database
- **Local Storage**: All data stored locally in a single SQLite database file

### Usage

```bash
# First run: fetches last 30 days (default)
eonapi export --store

# Subsequent runs: automatically fetches only new data
eonapi export --store

# Use custom database location
eonapi export --store --db /path/to/my-data.db

# Specify initial days on first run
eonapi export --store --days 90
```

### Example Session

```bash
$ eonapi export --store
Using database: ./eon-data.db
Authenticating...
Authentication successful!
...
No existing data found. Fetching last 30 days...
Fetching electricity consumption data from 2025-10-15 to 2025-11-14...
Fetching page 1... (0 records so far)
...
Database updated: 1440 new records inserted, 0 duplicates skipped.
Total records in database for this meter: 1440

$ eonapi export --store
Using database: ./eon-data.db
Authenticating...
Authentication successful!
...
Found existing data up to 2025-11-14T23:30:00+00:00
Fetching incremental data from 2025-11-14 23:30:00...
Fetching electricity consumption data from 2025-11-14 to 2025-11-14...
Fetching page 1... (0 records so far)
Database updated: 48 new records inserted, 0 duplicates skipped.
Total records in database for this meter: 1488
```

## Commands

### `eonapi export`

Export consumption data to CSV format or store in SQLite database.

**Options:**
- `--username`, `-u`: E.ON Next account username (email)
- `--password`, `-p`: E.ON Next account password
- `--days`, `-d`: Number of days to retrieve (default: 30)
- `--meter`, `-m`: Meter serial number (if you have multiple)
- `--output`, `-o`: Output file path (default: stdout)
- `--store`: Store data in SQLite database for incremental updates
- `--db`: Path to SQLite database file (default: ./eon-data.db)

**Examples:**
```bash
# Basic export to CSV
eonapi export > data.csv

# Last 7 days to file
eonapi export --days 7 --output weekly.csv

# Store in database (incremental updates)
eonapi export --store

# Store in custom database location
eonapi export --store --db /path/to/my-data.db

# First run: fetches last 30 days
# Subsequent runs: only fetch new data since last update

# Specific meter
eonapi export --meter 12345678 --days 30 > meter1.csv
```

### `eonapi stats`

Display consumption statistics and analysis.

**Options:**
- `--username`, `-u`: E.ON Next account username (email)
- `--password`, `-p`: E.ON Next account password
- `--days`, `-d`: Number of days to analyze (default: 30)
- `--meter`, `-m`: Meter serial number (if you have multiple)

**Examples:**
```bash
# View stats for last 30 days
eonapi stats

# View stats for last 7 days
eonapi stats --days 7
```

**Output:**
```
============================================================
  Consumption Statistics - Electricity Meter
============================================================

Meter Serial: 21E1025777
Period: 30 days (1363 half-hour intervals)

Total Consumption: 432.50 kWh
Average Daily: 14.42 kWh/day
Average per interval: 0.317 kWh

Peak Usage: 5.17 kWh
Peak Time: 2025-10-14T17:00:00+01:00

============================================================
```

### `eonapi ui`

Launch interactive web UI with data visualization.

**Installation:**

The web UI requires additional dependencies. Install them with:

```bash
pip install 'eonapi[ui]'
```

**Options:**
- `--port`, `-p`: Port to run on (default: 8000)
- `--host`, `-h`: Host to bind to (default: 127.0.0.1)

**Examples:**
```bash
# Start web UI on default port (8000)
eonapi ui

# Start on custom port
eonapi ui --port 8080

# Make accessible from all network interfaces
eonapi ui --host 0.0.0.0
```

**Features:**
- Interactive login form for secure credential entry
- Real-time data visualization with ApexCharts
- Statistics dashboard showing:
  - Total consumption
  - Average daily usage
  - Peak usage times and values
  - Meter information
- Interactive drill-down chart:
  - Daily consumption bar chart with clickable bars
  - Click any day to see half-hourly breakdown for that day
  - Navigate back to daily view with a single click
- Credential persistence using localStorage (no need to re-login on refresh)
- Responsive design with Tailwind CSS
- Single-page Vue.js application (no build step required)

## Authentication

You can provide credentials in two ways:

### Environment Variables (Recommended)

```bash
export EON_USERNAME=your@email.com
export EON_PASSWORD=yourpassword
```

### Command-line Arguments

```bash
eonapi export --username your@email.com --password yourpassword
```

**Note**: Environment variables are recommended for security. Command-line arguments may be visible in shell history.

## Output Format

CSV data includes the following columns:

- `interval_start`: Start timestamp (ISO 8601 with timezone)
- `interval_end`: End timestamp
- `consumption_kwh`: Energy consumption in kWh

**Example:**
```csv
interval_start,interval_end,consumption_kwh
2025-10-14T16:00:00+01:00,2025-10-14T16:30:00+01:00,0.432000
2025-10-14T16:30:00+01:00,2025-10-14T17:00:00+01:00,5.127000
2025-10-14T17:00:00+01:00,2025-10-14T17:30:00+01:00,5.166000
```

## Notes

- Data is available in 30-minute intervals (48 intervals per day)
- For 30 days, expect approximately 1,440 records (30 × 48)
- Dates include timezone information (`+00:00` for UTC, `+01:00` for BST)
- Progress messages are written to stderr, CSV data to stdout
- The tool automatically handles API pagination

## Example Session

```bash
$ export EON_USERNAME=user@example.com
$ export EON_PASSWORD=mypassword

$ eonapi export --days 30 > consumption.csv
Authenticating...
Authentication successful!
Fetching account information...
Using account: A-8A9D52EC
Fetching meters...
Auto-selected meter: 21E1025777 (electricity)
Fetching electricity consumption data from 2025-10-14 to 2025-11-13...
Fetching page 1... (0 records so far)
Fetching page 2... (100 records so far)
Fetching page 3... (200 records so far)
...
Fetching page 14... (1300 records so far)

Successfully exported 1363 records.

$ eonapi stats --days 7
Authenticating...
Authentication successful!
...
============================================================
  Consumption Statistics - Electricity Meter
============================================================

Meter Serial: 21E1025777
Period: 7 days (336 half-hour intervals)

Total Consumption: 98.45 kWh
Average Daily: 14.06 kWh/day
Average per interval: 0.293 kWh

Peak Usage: 3.74 kWh
Peak Time: 2025-11-11T16:30:00+00:00

============================================================
```

## GraphQL API

This tool uses the E.ON Next GraphQL API (Kraken platform). The API requires JWT authentication and supports querying consumption data at various granularities.

## Requirements

- Python 3.9+
- E.ON Next account with smart meter

## Development

### Setup

```bash
git clone https://github.com/tomdyson/eonapi.git
cd eonapi
uv sync
```

### Run from source

```bash
uv run eonapi export --days 7
uv run eonapi stats
```

## Releasing

The project uses GitHub Actions to automatically publish to PyPI when version tags are pushed.

### Release Steps

1. **Update Version**: Edit `pyproject.toml` and change the version number
2. **Commit Changes**:
   ```bash
   git add pyproject.toml
   git commit -m "Bump version to 0.2.0"
   git push
   ```
3. **Create and Push Tag**:
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```
4. **Automatic Publishing**: GitHub Actions will automatically build and publish to PyPI

### Prerequisites

A PyPI API token must be added to the repository's GitHub secrets as `PYPI_API_TOKEN`. You can create one at https://pypi.org/manage/account/token/.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This is an unofficial tool and is not affiliated with, endorsed by, or connected to E.ON Next or E.ON. Use at your own risk.

## Support

If you encounter any issues or have questions, please [open an issue](https://github.com/tomdyson/eonapi/issues) on GitHub.
