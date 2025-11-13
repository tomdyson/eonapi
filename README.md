# eonapi

[![PyPI version](https://badge.fury.io/py/eonapi.svg)](https://badge.fury.io/py/eonapi)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python CLI tool for retrieving and analyzing electricity/gas consumption data from the Eon Next API.

## Features

- **Automatic Pagination**: Fetches all available data for your requested time period
- **30-minute intervals**: Retrieves half-hourly consumption data
- **Multiple Commands**:
  - `export`: Export raw data to CSV
  - `stats`: Display consumption statistics and analysis
  - `ui`: Interactive web UI (coming soon)
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
git clone https://github.com/yourusername/eonapi.git
cd eonapi
pip install -e .
```

### Using uv (for development)

```bash
git clone https://github.com/yourusername/eonapi.git
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

## Commands

### `eonapi export`

Export consumption data to CSV format.

**Options:**
- `--username`, `-u`: Eon Next account username (email)
- `--password`, `-p`: Eon Next account password
- `--days`, `-d`: Number of days to retrieve (default: 30)
- `--meter`, `-m`: Meter serial number (if you have multiple)
- `--output`, `-o`: Output file path (default: stdout)

**Examples:**
```bash
# Basic export
eonapi export > data.csv

# Last 7 days
eonapi export --days 7 --output weekly.csv

# Specific meter
eonapi export --meter 12345678 --days 30 > meter1.csv
```

### `eonapi stats`

Display consumption statistics and analysis.

**Options:**
- `--username`, `-u`: Eon Next account username (email)
- `--password`, `-p`: Eon Next account password
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

Launch interactive web UI (coming soon).

**Options:**
- `--port`, `-p`: Port to run on (default: 8000)
- `--host`, `-h`: Host to bind to (default: 127.0.0.1)

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

This tool uses the Eon Next GraphQL API (Kraken platform). The API requires JWT authentication and supports querying consumption data at various granularities.

## Requirements

- Python 3.9+
- Eon Next account with smart meter

## Development

### Setup

```bash
git clone https://github.com/yourusername/eonapi.git
cd eonapi
uv sync
```

### Run from source

```bash
uv run eonapi export --days 7
uv run eonapi stats
```

### Building for PyPI

```bash
# Install build tools
pip install build twine

# Build distribution
python -m build

# Upload to PyPI (test)
twine upload --repository testpypi dist/*

# Upload to PyPI (production)
twine upload dist/*
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This is an unofficial tool and is not affiliated with, endorsed by, or connected to Eon Next or E.ON. Use at your own risk.

## Support

If you encounter any issues or have questions, please [open an issue](https://github.com/yourusername/eonapi/issues) on GitHub.
