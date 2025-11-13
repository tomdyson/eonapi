# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-11-13

### Added
- Initial release
- `eonpy export` command to export consumption data to CSV
- `eonpy stats` command to display consumption statistics
- `eonpy ui` command stub (coming soon)
- Automatic API pagination support
- Support for both electricity and gas meters
- Environment variable authentication
- Command-line credential options
- Progress feedback during data fetching
- Half-hourly (30-minute) consumption intervals
- Multi-meter support with auto-selection

### Features
- JWT authentication with Eon Next GraphQL API
- Automatic token refresh handling
- Configurable date ranges (--days option)
- CSV output to stdout or file
- Detailed consumption statistics:
  - Total consumption
  - Average daily usage
  - Peak usage and timing
- Timezone-aware timestamps

### Documentation
- Comprehensive README with examples
- MIT License
- PyPI publishing guide
- Inline help for all commands

## [Unreleased]

### Planned
- Interactive web UI for data visualization
- Cost analysis features
- Comparison tools
- Additional export formats (JSON, Excel)
- Historical data caching
- Chart generation
- Email reports
- Budget tracking
