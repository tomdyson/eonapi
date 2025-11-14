"""Command-line interface for eonapi."""

import asyncio
import csv
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

import click
from dateutil.parser import isoparse

from . import __version__
from .api import EonNextAPI
from .database import ConsumptionDatabase


def get_credentials(username: Optional[str], password: Optional[str]) -> tuple[str, str]:
    """Get credentials from args or environment variables."""
    # Try environment variables first
    env_username = os.environ.get("EON_USERNAME")
    env_password = os.environ.get("EON_PASSWORD")

    # Use provided args, fall back to env vars
    final_username = username or env_username
    final_password = password or env_password

    if not final_username or not final_password:
        raise click.ClickException(
            "Credentials not provided. Set EON_USERNAME and EON_PASSWORD environment variables "
            "or use --username and --password options."
        )

    return final_username, final_password


@click.group()
@click.version_option(version=__version__, prog_name="eonapi")
@click.pass_context
def cli(ctx):
    """
    Eon Next API CLI - Retrieve and analyze your electricity/gas consumption data.

    Set your credentials via environment variables:
        export EON_USERNAME=your@email.com
        export EON_PASSWORD=yourpassword

    Or pass them as options to each command.
    """
    ctx.ensure_object(dict)


@cli.command()
@click.option(
    "--username",
    "-u",
    help="Eon Next account username (email). Can also be set via EON_USERNAME environment variable."
)
@click.option(
    "--password",
    "-p",
    help="Eon Next account password. Can also be set via EON_PASSWORD environment variable."
)
@click.option(
    "--days",
    "-d",
    default=30,
    type=int,
    help="Number of days of historical data to retrieve (default: 30)"
)
@click.option(
    "--meter",
    "-m",
    help="Meter serial number (optional - will prompt if multiple meters found)"
)
@click.option(
    "--output",
    "-o",
    type=click.File('w'),
    default='-',
    help="Output file path (default: stdout)"
)
@click.option(
    "--store",
    is_flag=True,
    help="Store data in SQLite database for incremental updates"
)
@click.option(
    "--db",
    default="./eon-data.db",
    help="Path to SQLite database file (default: ./eon-data.db)"
)
def export(
    username: Optional[str],
    password: Optional[str],
    days: int,
    meter: Optional[str],
    output,
    store: bool,
    db: str
):
    """
    Export consumption data to CSV or store in SQLite database.

    Retrieves electricity/gas consumption data from Eon Next API and outputs as CSV
    or stores in a SQLite database for incremental updates.

    Examples:

        eonapi export --days 30 > data.csv

        eonapi export --days 7 --output last_week.csv

        eonapi export --store --db ./my-data.db

        eonapi export --store  # Uses default ./eon-data.db
    """
    try:
        # Get credentials
        final_username, final_password = get_credentials(username, password)

        # Initialize database if --store is used
        if store:
            click.echo(f"Using database: {db}", err=True)
            database = ConsumptionDatabase(db)

        # Fetch data with optional incremental update
        consumption_data, selected_meter = asyncio.run(
            fetch_data(
                final_username,
                final_password,
                days,
                meter,
                database if store else None
            )
        )

        # Store in database if --store is used
        if store:
            inserted, skipped = database.store_records(
                consumption_data,
                selected_meter["serial"],
                selected_meter["type"]
            )
            click.echo(
                f"\nDatabase updated: {inserted} new records inserted, "
                f"{skipped} duplicates skipped.",
                err=True
            )
            total_records = database.get_record_count(selected_meter["serial"])
            click.echo(
                f"Total records in database for this meter: {total_records}",
                err=True
            )
        else:
            # Output CSV (original behavior)
            writer = csv.writer(output)

            # Write header
            writer.writerow(["interval_start", "interval_end", "consumption_kwh"])

            # Write data rows
            for record in consumption_data:
                writer.writerow([
                    record.get("startAt", ""),
                    record.get("endAt", ""),
                    record.get("value", "")
                ])

            click.echo(f"\nSuccessfully exported {len(consumption_data)} records.", err=True)

    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Error: {str(e)}")


@cli.command()
@click.option(
    "--username",
    "-u",
    help="Eon Next account username (email). Can also be set via EON_USERNAME environment variable."
)
@click.option(
    "--password",
    "-p",
    help="Eon Next account password. Can also be set via EON_PASSWORD environment variable."
)
@click.option(
    "--days",
    "-d",
    default=30,
    type=int,
    help="Number of days of historical data to analyze (default: 30)"
)
@click.option(
    "--meter",
    "-m",
    help="Meter serial number (optional - will prompt if multiple meters found)"
)
def stats(username: Optional[str], password: Optional[str], days: int, meter: Optional[str]):
    """
    Display consumption statistics.

    Analyzes your consumption data and displays useful statistics like:
    - Total consumption
    - Average daily usage
    - Peak usage times
    - Cost estimates

    Example:

        eonpy stats --days 30

        eonpy stats --days 7
    """
    try:
        # Get credentials
        final_username, final_password = get_credentials(username, password)

        # Fetch data
        consumption_data, selected_meter = asyncio.run(
            fetch_data(final_username, final_password, days, meter)
        )

        # Calculate statistics
        if not consumption_data:
            click.echo("No consumption data available for analysis.", err=True)
            return

        total_kwh = sum(float(record.get("value", 0)) for record in consumption_data)
        num_days = len(consumption_data) / 48  # 48 half-hour intervals per day
        avg_daily = total_kwh / num_days if num_days > 0 else 0

        # Find peak usage
        peak_record = max(consumption_data, key=lambda r: float(r.get("value", 0)))
        peak_kwh = float(peak_record.get("value", 0))
        peak_time = peak_record.get("startAt", "")

        # Display statistics
        click.echo("\n" + "="*60)
        click.echo(f"  Consumption Statistics - {selected_meter['type'].title()} Meter")
        click.echo("="*60)
        click.echo(f"\nMeter Serial: {selected_meter['serial']}")
        click.echo(f"Period: {days} days ({len(consumption_data)} half-hour intervals)")
        click.echo(f"\nTotal Consumption: {total_kwh:.2f} kWh")
        click.echo(f"Average Daily: {avg_daily:.2f} kWh/day")
        click.echo(f"Average per interval: {total_kwh/len(consumption_data):.3f} kWh")
        click.echo(f"\nPeak Usage: {peak_kwh:.2f} kWh")
        click.echo(f"Peak Time: {peak_time}")
        click.echo("\n" + "="*60 + "\n")

    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Error: {str(e)}")


@cli.command()
@click.option(
    "--port",
    "-p",
    default=8000,
    type=int,
    help="Port to run the web UI on (default: 8000)"
)
@click.option(
    "--host",
    "-h",
    default="127.0.0.1",
    help="Host to bind the web UI to (default: 127.0.0.1)"
)
def ui(port: int, host: str):
    """
    Launch interactive web UI for data visualization.

    Opens a web browser with interactive charts and visualizations of your
    consumption data.

    Example:

        eonapi ui

        eonapi ui --port 8080 --host 0.0.0.0
    """
    try:
        import uvicorn
        from .server import app

        click.echo(f"Starting eonapi web UI on http://{host}:{port}")
        click.echo("Press CTRL+C to stop the server\n")

        uvicorn.run(app, host=host, port=port, log_level="info")
    except ImportError:
        raise click.ClickException(
            "FastAPI and uvicorn are required for the web UI. "
            "Install them with: pip install 'eonapi[ui]'"
        )
    except Exception as e:
        raise click.ClickException(f"Error starting server: {str(e)}")


async def fetch_data(
    username: str,
    password: str,
    days: int,
    meter_serial: Optional[str],
    database: Optional[ConsumptionDatabase] = None
):
    """Fetch consumption data from Eon Next API.

    Args:
        username: Eon Next username
        password: Eon Next password
        days: Number of days to fetch (used if no database or no existing data)
        meter_serial: Optional meter serial number
        database: Optional database for incremental updates
    """
    api = EonNextAPI()

    # Authenticate
    click.echo("Authenticating...", err=True)
    if not await api.login(username, password):
        raise click.ClickException("Authentication failed. Check your credentials.")

    click.echo("Authentication successful!", err=True)

    # Get accounts
    click.echo("Fetching account information...", err=True)
    accounts = await api.get_account_numbers()

    if not accounts:
        raise click.ClickException("No accounts found.")

    # Use first account (most users have only one)
    account_number = accounts[0]
    click.echo(f"Using account: {account_number}", err=True)

    # Get meters
    click.echo("Fetching meters...", err=True)
    meters = await api.get_meters(account_number)

    if not meters:
        raise click.ClickException("No meters found.")

    # Select meter
    selected_meter = None

    if meter_serial:
        # Find meter by serial number
        for meter in meters:
            if meter["serial"] == meter_serial:
                selected_meter = meter
                break

        if not selected_meter:
            raise click.ClickException(f"Meter with serial {meter_serial} not found.")
    elif len(meters) == 1:
        # Auto-select single meter
        selected_meter = meters[0]
        click.echo(
            f"Auto-selected meter: {selected_meter['serial']} ({selected_meter['type']})",
            err=True
        )
    else:
        # Multiple meters - prompt user
        click.echo("\nAvailable meters:", err=True)
        for idx, meter in enumerate(meters, 1):
            click.echo(
                f"  {idx}. {meter['serial']} - {meter['type']}",
                err=True
            )

        while True:
            try:
                choice = click.prompt("\nSelect meter number", type=int, err=True)
                if 1 <= choice <= len(meters):
                    selected_meter = meters[choice - 1]
                    break
                else:
                    click.echo(f"Please enter a number between 1 and {len(meters)}", err=True)
            except click.Abort:
                raise click.ClickException("Aborted by user.")

    # Calculate date range
    end_date = datetime.now()

    # Check if we should do incremental update
    if database:
        latest_interval = database.get_latest_interval(selected_meter["serial"])
        if latest_interval:
            # Parse the latest interval and start from there
            start_date = isoparse(latest_interval)
            click.echo(
                f"Found existing data up to {latest_interval}",
                err=True
            )
            click.echo(
                f"Fetching incremental data from {start_date.strftime('%Y-%m-%d %H:%M:%S')}...",
                err=True
            )
        else:
            # No existing data, use the days parameter
            start_date = end_date - timedelta(days=days)
            click.echo(
                f"No existing data found. Fetching last {days} days...",
                err=True
            )
    else:
        # Normal mode: fetch last N days
        start_date = end_date - timedelta(days=days)

    click.echo(
        f"Fetching {selected_meter['type']} consumption data from "
        f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...",
        err=True
    )

    # Progress callback to show pagination status
    def show_progress(page_num, record_count):
        click.echo(f"Fetching page {page_num}... ({record_count} records so far)", err=True)

    # Fetch consumption data
    consumption = await api.get_consumption_data(
        account_number=account_number,
        meter_id=selected_meter["id"],
        meter_type=selected_meter["type"],
        start_date=start_date,
        end_date=end_date,
        progress_callback=show_progress
    )

    if not consumption:
        click.echo("Warning: No consumption data returned.", err=True)

    return consumption, selected_meter


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
