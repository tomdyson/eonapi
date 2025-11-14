# Copilot Instructions for eonapi

## Project Overview

eonapi is a Python CLI tool and web interface for retrieving and analyzing electricity/gas consumption data from the E.ON Next API. The project uses the E.ON Next GraphQL API (Kraken platform) with JWT authentication to fetch smart meter data at 30-minute intervals.

## Architecture

- **CLI Application**: Built with Click for command-line interface
- **API Client**: Async HTTP client using httpx for GraphQL API communication
- **Web UI**: Optional FastAPI server with Vue.js frontend (requires `ui` extras)
- **Package Manager**: Uses `uv` for dependency management and development

## Code Style and Conventions

### Python Code Standards

- **Python Version**: Minimum Python 3.9, support through Python 3.13
- **Type Hints**: Use type hints for function parameters and return types (see existing code)
- **Async/Await**: Use async patterns for all API calls (`asyncio`, `httpx.AsyncClient`)
- **Error Handling**: Raise `click.ClickException` for user-facing errors in CLI
- **Docstrings**: Use triple-quoted docstrings for modules, classes, and functions

### Code Organization

- `eonapi/api.py`: API client for E.ON Next GraphQL API
- `eonapi/cli.py`: Click-based CLI commands (export, stats, ui)
- `eonapi/server.py`: FastAPI server for web UI
- `eonapi/__init__.py`: Version string and package exports

### Naming Conventions

- **Functions/Methods**: Use `snake_case`
- **Classes**: Use `PascalCase`
- **Constants**: Use `UPPER_SNAKE_CASE`
- **Private Methods**: Prefix with single underscore `_method_name`

## Development Setup

### Installation for Development

```bash
git clone https://github.com/tomdyson/eonapi.git
cd eonapi
uv sync
```

### Running from Source

```bash
uv run eonapi export --days 7
uv run eonapi stats
uv run eonapi ui
```

### Building the Package

```bash
uv build
```

## Dependencies

### Core Dependencies

- **click**: CLI framework (≥8.0.0)
- **httpx**: Async HTTP client (≥0.23.0)

### Optional Dependencies (UI)

- **fastapi**: Web framework (≥0.104.0)
- **uvicorn**: ASGI server (≥0.24.0)

### Development Dependencies

- **build**: Package building (≥1.3.0)
- **twine**: PyPI publishing (≥6.2.0)

## Authentication and Security

### Credential Handling

- **Environment Variables** (preferred): `EON_USERNAME`, `EON_PASSWORD`
- **CLI Arguments**: `--username`, `--password` flags
- Priority: CLI args override environment variables
- Never commit credentials to source control
- Web UI stores credentials in browser localStorage (client-side only)

### API Authentication

- Uses JWT token authentication with E.ON Next Kraken API
- Implements token refresh logic when tokens expire
- Tokens are managed in memory (not persisted)

## API Patterns

### GraphQL Requests

- All API calls go through `_graphql_request()` method
- Operation name, query string, and variables are passed separately
- Authentication header: `JWT {token}` format
- Timeout: 30 seconds for all requests

### Pagination

- E.ON API returns paginated consumption data
- Implement pagination loops to fetch all available data
- Show progress to stderr while fetching (e.g., "Fetching page 1... (0 records so far)")

### Date Handling

- Use ISO 8601 format with timezone information
- E.ON API uses timezone-aware timestamps (UTC, BST)
- Default date range: last 30 days from current date

## CLI Commands

### Command Structure

```python
@click.command()
@click.option('--username', '-u', help='E.ON Next username')
@click.option('--password', '-p', help='E.ON Next password')
@click.option('--days', '-d', default=30, help='Number of days')
@click.option('--meter', '-m', help='Meter serial number')
```

### Output Conventions

- **Success Messages**: Write to stderr
- **Data Output**: Write CSV to stdout (for `export` command)
- **Progress**: Write to stderr with clear status updates
- **Errors**: Raise `click.ClickException` with helpful messages

## Web UI

### Technology Stack

- **Backend**: FastAPI with Pydantic models
- **Frontend**: Vue.js 3 (CDN version, no build step)
- **Charts**: ApexCharts for data visualization
- **Styling**: Tailwind CSS (CDN version)

### UI Features

- Single-page application embedded in Python string
- Interactive daily/half-hourly drill-down charts
- Client-side credential storage using localStorage
- Responsive design

## Testing

**Note**: This project currently has no automated test suite. When adding tests:

- Use `pytest` as the testing framework
- Test CLI commands with Click's testing utilities
- Mock httpx calls for API client tests
- Test both environment variable and CLI argument authentication paths

## Release Process

### Version Management

- Version is stored in `pyproject.toml`
- Also update `__version__` in `eonapi/__init__.py` to match

### Publishing to PyPI

1. Update version in `pyproject.toml`
2. Commit changes: `git commit -m "Bump version to X.Y.Z"`
3. Create and push tag: `git tag vX.Y.Z && git push origin vX.Y.Z`
4. GitHub Actions automatically builds and publishes to PyPI

### GitHub Actions

- Workflow: `.github/workflows/publish.yml`
- Triggered on version tags (`v*`)
- Uses trusted publishing (no manual token in workflow)
- Requires `PYPI_API_TOKEN` secret in repository settings

## Common Patterns

### Async Function Structure

```python
async def fetch_data(self, param: str) -> dict:
    """Fetch data from API."""
    query = """
    query MyQuery($param: String!) {
        field(param: $param) { ... }
    }
    """
    return await self._graphql_request(
        "MyQuery",
        query,
        {"param": param}
    )
```

### Meter Selection Logic

- If single meter: auto-select
- If multiple meters: prompt user or use `--meter` flag
- Electricity meters: type "ELECTRICITY"
- Gas meters: type "GAS"

### CSV Output Format

```csv
interval_start,interval_end,consumption_kwh
2025-10-14T16:00:00+01:00,2025-10-14T16:30:00+01:00,0.432000
```

## Project-Specific Considerations

- **API Base URL**: `https://api.eonnext-kraken.energy/v1/graphql/`
- **Data Granularity**: 30-minute intervals (48 per day)
- **Meter Types**: Support both electricity and gas meters
- **Progress Feedback**: Always provide user feedback for long-running operations
- **Timezone Handling**: Preserve timezone information from API responses
- **Error Messages**: Be specific about authentication, API, and data retrieval errors

## Documentation

- **README.md**: Primary user-facing documentation
- Keep README examples up-to-date with CLI changes
- Document all CLI options and commands
- Include example output in documentation
- Link to GitHub issues for support

## Contributing Guidelines

- Maintain backward compatibility with Python 3.9+
- Minimize dependencies (keep core lightweight)
- UI dependencies are optional extras
- Follow existing code patterns and style
- Update README for user-facing changes
