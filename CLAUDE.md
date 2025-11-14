# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

eonapi is a Python CLI tool for retrieving and analyzing electricity/gas consumption data from the E.ON Next API (Kraken platform). It features CSV export, SQLite database storage with incremental updates, and an optional web UI with interactive charts.

## Development Commands

```bash
# Setup
git clone https://github.com/tomdyson/eonapi.git
cd eonapi
uv sync

# Run from source
uv run eonapi export --days 7
uv run eonapi stats
uv run eonapi ui

# Testing
uv run pytest                           # All tests
uv run pytest -v                        # Verbose
uv run pytest tests/test_database.py    # Specific file
uv run pytest tests/test_database.py::TestConsumptionDatabase::test_store_records  # Specific test

# Build
uv build                                # Creates wheel + sdist in dist/
```

## Release Process

```bash
# 1. Update version in pyproject.toml (and __init__.py if needed)
# 2. Commit and push
git add pyproject.toml
git commit -m "Bump version to X.Y.Z"
git push

# 3. Create and push tag
git tag vX.Y.Z
git push origin vX.Y.Z

# GitHub Actions will automatically build and publish to PyPI
# Requires PYPI_API_TOKEN secret in repository settings
```

## Architecture Overview

### Component Layers

**Four main modules working together:**

1. **API Client** (`api.py`): `EonNextAPI` class handles JWT authentication and GraphQL queries to E.ON Next Kraken API
2. **CLI** (`cli.py`): Three Click commands (`export`, `stats`, `ui`) orchestrate the flow
3. **Database** (`database.py`): `ConsumptionDatabase` class manages SQLite storage with incremental updates
4. **Web Server** (`server.py`): FastAPI app with embedded Vue.js SPA (optional, requires `ui` extras)

### Data Flow Architecture

```
CLI Command
    ↓
EonNextAPI (async GraphQL client)
    ↓
JWT Auth → Fetch Accounts → Fetch Meters → Fetch Consumption (paginated)
    ↓
Raw consumption records (list of dicts)
    ↓
    ├─→ CSV export (stdout/file)
    └─→ SQLite storage → Web UI visualization
```

### Key Architectural Patterns

**Async/Await Pattern:**
- All API calls use `asyncio` and `httpx.AsyncClient`
- CLI wraps async operations: `asyncio.run(fetch_data(...))`
- Enables efficient pagination through large datasets

**Incremental Update Pattern:**
- Database stores latest `interval_start` timestamp per meter
- Subsequent runs call `db.get_latest_interval(meter_serial)` and only fetch newer data
- `--days` parameter only used on first run (when no existing data found)
- Unique constraint `(meter_serial, interval_start)` prevents duplicates

**Pagination Pattern:**
- API returns 100 records per page with `pageInfo.endCursor`
- Client loops: `while pageInfo.hasNextPage`, updating `after: cursor`
- Progress callbacks to stderr: "Fetching page N... (X records so far)"

**GraphQL Client Pattern:**
- Centralized `_graphql_request(operation_name, query, variables)` method
- No GraphQL client library - raw queries as strings
- Error extraction from GraphQL `errors` array

**Output Separation:**
- Data (CSV) → stdout
- Progress/status → stderr
- Errors → `click.ClickException` (exit code 1)
- Enables Unix pipeline composition: `eonapi export | grep 2025-11`

## Database Architecture

### Schema Design

```sql
CREATE TABLE consumption (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meter_serial TEXT NOT NULL,
    meter_type TEXT NOT NULL,           -- "electricity" or "gas"
    interval_start TEXT NOT NULL,       -- ISO 8601: "2025-11-14T16:00:00+00:00"
    interval_end TEXT NOT NULL,
    consumption_kwh REAL NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(meter_serial, interval_start)  -- Automatic duplicate prevention
)
```

### Storage Strategy

- **No ORM**: Direct `sqlite3` module usage for minimal dependencies
- **Flat structure**: No foreign keys, one table stores all meters
- **Timezone preservation**: Timestamps stored as ISO 8601 strings with timezone
- **Incremental updates**: `get_latest_interval()` returns max `interval_start` for meter
- **Duplicate handling**: `INSERT OR IGNORE` skips duplicates, returns counts

### Key Database Methods

```python
db = ConsumptionDatabase("./eon-data.db")

# Get latest timestamp for incremental updates
latest = db.get_latest_interval("METER123")  # Returns ISO string or None

# Store records (automatic duplicate detection)
inserted, skipped = db.store_records(
    records,              # List of dicts from API
    meter_serial="...",
    meter_type="electricity"
)

# Query stored data
total = db.get_record_count("METER123")
```

## API Integration

### Authentication Flow

```python
# 1. Login mutation
response = await api.login(username, password)
# Returns: {"obtainKrakenToken": {"token": "...", "payload": {"exp": 1234567890}}}

# 2. Store token and expiry in memory (not persisted)
self.token = token
self.token_expiry = datetime.fromtimestamp(exp)

# 3. Add to all subsequent requests
headers = {"Authorization": f"JWT {self.token}"}
```

### GraphQL Operations

**Key mutations/queries:**
- `obtainKrakenToken` - Login mutation (email + password)
- `headerGetLoggedInUser` - Get account numbers
- `getAccountMeterSelector` - Fetch all meters (electricity + gas)
- `getElectricityConsumption` / `getGasConsumption` - Paginated consumption data

**Pagination structure:**
```graphql
query getElectricityConsumption($accountNumber: String!, $meterId: String!, $after: String) {
  account(accountNumber: $accountNumber) {
    electricityAgreements {
      meterPoint(mpan: $meterId) {
        consumptionUnits(first: 100, after: $after) {
          pageInfo { hasNextPage endCursor }
          edges {
            node {
              startAt
              endAt
              value  # kWh
            }
          }
        }
      }
    }
  }
}
```

### Date Handling

**Critical: Always use timezone-aware ISO 8601:**
- API requires: `2025-11-14T00:00:00+00:00` (note timezone suffix)
- Use `dateutil.parser.isoparse()` for parsing (handles BST/UTC, more robust than manual parsing)
- Data granularity: 30-minute intervals (48 per day)
- Timestamps in Europe/London timezone (BST in summer, UTC in winter)

## CLI Command Structure

### Three Commands

**1. export** - Fetch and output consumption data
- CSV mode: Write to stdout (default) or `--output file.csv`
- Database mode: `--store` flag enables SQLite storage
- Optional `--db path.db` (default: `./eon-data.db`)
- Smart date range: Uses `--days` on first run, auto-incremental on subsequent runs

**2. stats** - Display consumption statistics
- Total/average consumption calculations
- Peak usage detection (max value + timestamp)
- Formatted table output to stdout

**3. ui** - Launch web interface
- Requires optional `ui` extras: `pip install 'eonapi[ui]'`
- FastAPI server with embedded Vue.js SPA (no build step)
- Default: `http://127.0.0.1:8000`
- Options: `--port`, `--host`

### Shared Logic: fetch_data()

```python
async def fetch_data(
    username: str,
    password: str,
    days: int,
    meter_serial: Optional[str],
    database: Optional[ConsumptionDatabase] = None
):
    """
    Core data fetching logic used by all commands.

    - Authenticates with API
    - Fetches accounts and meters
    - Handles meter selection (auto-select single, prompt for multiple)
    - Calculates date range (incremental if database provided)
    - Fetches paginated consumption data
    - Returns (consumption_data, selected_meter)
    """
```

### Credential Priority

1. CLI arguments: `--username`, `--password`
2. Environment variables: `EON_USERNAME`, `EON_PASSWORD`
3. Error if neither provided: `click.ClickException`

## Testing Patterns

### Test Organization

- `tests/test_database.py` - Unit tests for `ConsumptionDatabase` class (18 tests)
- `tests/test_cli_store.py` - Integration tests for `export --store` functionality

### Common Fixtures

```python
@pytest.fixture
def temp_db():
    """Create temporary database file, cleanup after test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)

@pytest.fixture
def sample_records():
    """Sample consumption data matching API response format."""
    return [
        {
            "startAt": "2025-11-14T00:00:00+00:00",
            "endAt": "2025-11-14T00:30:00+00:00",
            "value": "1.234"
        },
        # ...
    ]
```

### Mocking Async API Calls

```python
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_api():
    with patch("eonapi.cli.EonNextAPI") as mock_class:
        mock_instance = AsyncMock()
        mock_class.return_value = mock_instance

        # Mock async methods
        mock_instance.login.return_value = True
        mock_instance.get_account_numbers.return_value = ["ACC123"]
        mock_instance.get_meters.return_value = [
            {"serial": "METER1", "type": "electricity", "id": "ID1"}
        ]
        mock_instance.get_consumption_data.return_value = [
            {"startAt": "...", "endAt": "...", "value": "1.234"}
        ]

        yield mock_instance
```

### CLI Testing with CliRunner

```python
from click.testing import CliRunner
from eonapi.cli import cli

runner = CliRunner()
result = runner.invoke(cli, ['export', '--store', '--db', db_path])

assert result.exit_code == 0
assert "Database updated" in result.output
```

## Web UI Architecture

### Technology Stack

- **Backend**: FastAPI (ASGI framework)
- **Frontend**: Vue.js 3 (CDN, no build step)
- **Charts**: ApexCharts
- **Styling**: Tailwind CSS (CDN)
- **Storage**: localStorage for credential persistence

### Single-File HTML Pattern

Entire UI embedded as Python string in `server.py`:
```python
html_content = """
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/vue@3/dist/vue.global.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    ...
</head>
<body>
    <div id="app">{{ Vue.js template }}</div>
    <script>
        const { createApp } = Vue;
        createApp({ ... }).mount('#app');
    </script>
</body>
</html>
"""
```

**Design rationale:**
- No build step required
- All dependencies from CDN
- Simple deployment (single Python file)
- Trade-off: Larger file size, but easier maintenance

### API Endpoints

```python
POST /api/login              # Authenticate and get token
GET  /api/meters             # List available meters
GET  /api/consumption        # Fetch consumption data (paginated)
GET  /                       # Serve HTML app
```

## Dependencies and Packaging

### Dependency Strategy

**Core (minimal):**
- `click>=8.0.0` - CLI framework
- `httpx>=0.23.0` - Async HTTP client
- `python-dateutil>=2.8.0` - Robust date parsing

**Optional UI extras:**
```bash
pip install 'eonapi[ui]'  # Adds fastapi + uvicorn
```

**Development:**
- `pytest>=7.0.0` - Testing
- `build>=1.3.0` - Package building
- `twine>=6.2.0` - PyPI publishing

### Build Configuration

- **Build backend**: `hatchling` (modern, fast)
- **Package manager**: `uv` (recommended for development)
- **Python support**: 3.9 through 3.13
- **Entry point**: `eonapi = eonapi.cli:main`

## Code Style Conventions

### Naming

- Functions/methods: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_method_name`

### Type Hints

Use type hints throughout (see existing code):
```python
def fetch_data(
    username: str,
    password: str,
    days: int,
    meter_serial: Optional[str],
    database: Optional[ConsumptionDatabase] = None
) -> tuple[list[dict], dict]:
    ...
```

### Error Handling

- User-facing errors: `raise click.ClickException("Clear message")`
- API errors: Extract message from GraphQL errors array
- Progress messages: Write to stderr with `click.echo(..., err=True)`

## Important Constants

- **API Base URL**: `https://api.eonnext-kraken.energy/v1/graphql/`
- **Request timeout**: 30 seconds
- **Page size**: 100 records per API call
- **Data granularity**: 30-minute intervals (48 per day)
- **Default days**: 30 days on first run
- **Default database**: `./eon-data.db`
- **Default web UI**: `http://127.0.0.1:8000`

## Common Development Tasks

### Adding a New CLI Command

1. Add `@cli.command()` decorated function to `cli.py`
2. Use existing credential/meter selection patterns from `fetch_data()`
3. Write progress to stderr, data to stdout
4. Update README.md with command documentation
5. Add tests to `tests/` directory

### Extending Database Schema

1. Update `ConsumptionDatabase.__init__()` CREATE TABLE statement
2. Add migration logic for existing databases (check if column exists)
3. Add accessor methods following existing patterns
4. Update tests in `tests/test_database.py`

### Adding GraphQL Queries

1. Add new method to `EonNextAPI` class in `api.py`
2. Define GraphQL query string (use triple quotes)
3. Call `self._graphql_request(operation_name, query, variables)`
4. Handle pagination if needed (follow existing consumption patterns)
5. Parse response and extract data from nested structure

## Deployment Options

### PyPI Installation (End Users)

```bash
pip install eonapi           # Core + CLI
pip install 'eonapi[ui]'     # With web UI
```

### Docker Deployment

```bash
docker-compose up -d         # Runs web UI on port 8000
```

**Dockerfile pattern:**
- Multi-stage build (uv builder → slim runtime)
- Python 3.12 slim base
- Installs with UI extras: `uv pip install --extra ui`
- Entry point: `uvicorn eonapi.server:app`

## Security Considerations

- Never commit credentials to source control
- Environment variables preferred over CLI args (shell history)
- JWT tokens stored in memory only (not persisted to disk)
- Web UI stores credentials in browser localStorage (client-side only)
- No server-side session storage
