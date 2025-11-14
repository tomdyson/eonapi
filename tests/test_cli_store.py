"""Integration tests for the export --store functionality."""

import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from eonapi.cli import cli
from eonapi.database import ConsumptionDatabase


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def sample_consumption_data():
    """Create sample consumption data."""
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    data = []

    for i in range(48):  # One day of half-hour intervals
        start_time = base_time + timedelta(minutes=30 * i)
        end_time = start_time + timedelta(minutes=30)
        data.append({
            "startAt": start_time.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "endAt": end_time.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "value": 0.5 + (i * 0.01)
        })

    return data


@pytest.fixture
def mock_api():
    """Mock the EonNextAPI."""
    with patch("eonapi.cli.EonNextAPI") as mock_api_class:
        mock_api_instance = AsyncMock()
        mock_api_class.return_value = mock_api_instance

        # Mock login
        mock_api_instance.login.return_value = True

        # Mock account numbers
        mock_api_instance.get_account_numbers.return_value = ["ACC123"]

        # Mock meters
        mock_api_instance.get_meters.return_value = [
            {
                "type": "electricity",
                "serial": "METER123",
                "id": "meter-id-123",
                "meter_point_id": "mp-123",
                "mpan": "1234567890",
            }
        ]

        yield mock_api_instance


class TestExportStore:
    """Test suite for export --store functionality."""

    def test_export_store_initial_load(self, temp_db, sample_consumption_data, mock_api):
        """Test initial data load with --store option."""
        # Mock consumption data
        mock_api.get_consumption_data.return_value = sample_consumption_data

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "export",
                "--username", "test@example.com",
                "--password", "testpass",
                "--store",
                "--db", temp_db,
            ],
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Database updated" in result.output
        assert "48 new records inserted" in result.output
        assert "0 duplicates skipped" in result.output

        # Verify data in database
        db = ConsumptionDatabase(temp_db)
        assert db.get_record_count("METER123") == 48

    def test_export_store_incremental_update(self, temp_db, sample_consumption_data, mock_api):
        """Test incremental update with existing data."""
        # Store initial data
        db = ConsumptionDatabase(temp_db)
        initial_data = sample_consumption_data[:24]  # First 12 hours
        db.store_records(initial_data, "METER123", "electricity")

        # Mock API to return overlapping + new data
        mock_api.get_consumption_data.return_value = sample_consumption_data

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "export",
                "--username", "test@example.com",
                "--password", "testpass",
                "--store",
                "--db", temp_db,
            ],
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Found existing data" in result.output
        assert "Database updated" in result.output

        # Should have 48 total records (24 initial + 24 new)
        assert db.get_record_count("METER123") == 48

    def test_export_store_no_duplicates(self, temp_db, sample_consumption_data, mock_api):
        """Test that duplicate records are not inserted."""
        # Store data first time
        db = ConsumptionDatabase(temp_db)
        db.store_records(sample_consumption_data, "METER123", "electricity")

        # Mock API to return same data
        mock_api.get_consumption_data.return_value = sample_consumption_data

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "export",
                "--username", "test@example.com",
                "--password", "testpass",
                "--store",
                "--db", temp_db,
            ],
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "0 new records inserted" in result.output
        assert "48 duplicates skipped" in result.output

        # Should still have 48 records
        assert db.get_record_count("METER123") == 48

    def test_export_store_custom_db_path(self, sample_consumption_data, mock_api):
        """Test using custom database path."""
        mock_api.get_consumption_data.return_value = sample_consumption_data

        # Use a custom path in temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_db = os.path.join(tmpdir, "custom-eon.db")

            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "export",
                    "--username", "test@example.com",
                    "--password", "testpass",
                    "--store",
                    "--db", custom_db,
                ],
                catch_exceptions=False
            )

            assert result.exit_code == 0
            assert os.path.exists(custom_db)

            # Verify data
            db = ConsumptionDatabase(custom_db)
            assert db.get_record_count("METER123") == 48

    def test_export_without_store_still_works(self, sample_consumption_data, mock_api):
        """Test that export without --store still works (CSV output)."""
        mock_api.get_consumption_data.return_value = sample_consumption_data

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "export",
                "--username", "test@example.com",
                "--password", "testpass",
                "--days", "1",
            ],
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "interval_start,interval_end,consumption_kwh" in result.output
        assert "Successfully exported 48 records" in result.output

    def test_export_store_with_credentials_from_env(
        self, temp_db, sample_consumption_data, mock_api, monkeypatch
    ):
        """Test --store with credentials from environment variables."""
        # Set environment variables
        monkeypatch.setenv("EON_USERNAME", "test@example.com")
        monkeypatch.setenv("EON_PASSWORD", "testpass")

        mock_api.get_consumption_data.return_value = sample_consumption_data

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["export", "--store", "--db", temp_db],
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Database updated" in result.output

    def test_latest_interval_detection(self, temp_db, sample_consumption_data, mock_api):
        """Test that the latest interval is correctly detected and used."""
        # Store initial data
        db = ConsumptionDatabase(temp_db)
        initial_data = sample_consumption_data[:10]
        db.store_records(initial_data, "METER123", "electricity")

        latest = db.get_latest_interval("METER123")
        assert latest is not None

        # Mock new data
        mock_api.get_consumption_data.return_value = sample_consumption_data[5:]

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "export",
                "--username", "test@example.com",
                "--password", "testpass",
                "--store",
                "--db", temp_db,
            ],
            catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Found existing data up to" in result.output
        assert "Fetching incremental data" in result.output
