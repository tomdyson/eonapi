"""Tests for the database module."""

import os
import tempfile
from datetime import datetime, timedelta

import pytest

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
def sample_records():
    """Create sample consumption records for testing."""
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    records = []

    for i in range(10):
        start_time = base_time + timedelta(minutes=30 * i)
        end_time = start_time + timedelta(minutes=30)
        records.append({
            "startAt": start_time.isoformat() + "+00:00",
            "endAt": end_time.isoformat() + "+00:00",
            "value": 0.5 + (i * 0.1)  # Varying consumption values
        })

    return records


class TestConsumptionDatabase:
    """Test suite for ConsumptionDatabase."""

    def test_database_initialization(self, temp_db):
        """Test that database is created and initialized correctly."""
        db = ConsumptionDatabase(temp_db)
        assert os.path.exists(temp_db)

        # Verify table exists by trying to query it
        count = db.get_record_count()
        assert count == 0

    def test_store_records(self, temp_db, sample_records):
        """Test storing records in the database."""
        db = ConsumptionDatabase(temp_db)

        inserted, skipped = db.store_records(
            sample_records,
            meter_serial="TEST123",
            meter_type="electricity"
        )

        assert inserted == 10
        assert skipped == 0
        assert db.get_record_count("TEST123") == 10

    def test_duplicate_records_skipped(self, temp_db, sample_records):
        """Test that duplicate records are skipped."""
        db = ConsumptionDatabase(temp_db)

        # Insert records first time
        inserted1, skipped1 = db.store_records(
            sample_records,
            meter_serial="TEST123",
            meter_type="electricity"
        )
        assert inserted1 == 10
        assert skipped1 == 0

        # Try to insert same records again
        inserted2, skipped2 = db.store_records(
            sample_records,
            meter_serial="TEST123",
            meter_type="electricity"
        )
        assert inserted2 == 0
        assert skipped2 == 10

        # Total count should still be 10
        assert db.get_record_count("TEST123") == 10

    def test_get_latest_interval(self, temp_db, sample_records):
        """Test getting the latest interval for a meter."""
        db = ConsumptionDatabase(temp_db)

        # No data yet
        assert db.get_latest_interval("TEST123") is None

        # Store records
        db.store_records(
            sample_records,
            meter_serial="TEST123",
            meter_type="electricity"
        )

        # Get latest interval
        latest = db.get_latest_interval("TEST123")
        assert latest is not None
        assert latest == sample_records[-1]["startAt"]

    def test_incremental_updates(self, temp_db, sample_records):
        """Test incremental data updates."""
        db = ConsumptionDatabase(temp_db)

        # Store first 5 records
        first_batch = sample_records[:5]
        inserted1, skipped1 = db.store_records(
            first_batch,
            meter_serial="TEST123",
            meter_type="electricity"
        )
        assert inserted1 == 5
        assert skipped1 == 0

        # Get latest interval
        latest = db.get_latest_interval("TEST123")
        assert latest == first_batch[-1]["startAt"]

        # Store next batch (including some overlap)
        second_batch = sample_records[3:]  # 2 duplicates + 5 new
        inserted2, skipped2 = db.store_records(
            second_batch,
            meter_serial="TEST123",
            meter_type="electricity"
        )
        assert inserted2 == 5  # Only new records
        assert skipped2 == 2  # Duplicates skipped

        # Total should be 10
        assert db.get_record_count("TEST123") == 10

    def test_multiple_meters(self, temp_db, sample_records):
        """Test storing data for multiple meters."""
        db = ConsumptionDatabase(temp_db)

        # Store data for first meter
        db.store_records(
            sample_records,
            meter_serial="ELEC123",
            meter_type="electricity"
        )

        # Store data for second meter (same timestamps, different meter)
        db.store_records(
            sample_records,
            meter_serial="GAS456",
            meter_type="gas"
        )

        # Check counts
        assert db.get_record_count("ELEC123") == 10
        assert db.get_record_count("GAS456") == 10
        assert db.get_record_count() == 20  # Total

        # Check latest intervals are independent
        latest_elec = db.get_latest_interval("ELEC123")
        latest_gas = db.get_latest_interval("GAS456")
        assert latest_elec == sample_records[-1]["startAt"]
        assert latest_gas == sample_records[-1]["startAt"]

    def test_get_all_records(self, temp_db, sample_records):
        """Test retrieving all records."""
        db = ConsumptionDatabase(temp_db)

        db.store_records(
            sample_records,
            meter_serial="TEST123",
            meter_type="electricity"
        )

        # Get all records
        records = db.get_all_records("TEST123")
        assert len(records) == 10
        assert records[0]["meter_serial"] == "TEST123"
        assert records[0]["meter_type"] == "electricity"

    def test_get_records_with_date_filter(self, temp_db, sample_records):
        """Test retrieving records with date filters."""
        db = ConsumptionDatabase(temp_db)

        db.store_records(
            sample_records,
            meter_serial="TEST123",
            meter_type="electricity"
        )

        # Filter by start date (middle of the range)
        start_date = datetime(2024, 1, 1, 2, 0, 0)
        records = db.get_all_records("TEST123", start_date=start_date)

        # Should get records from 02:00 onwards (5 records)
        assert len(records) >= 5

    def test_empty_records_list(self, temp_db):
        """Test handling empty records list."""
        db = ConsumptionDatabase(temp_db)

        inserted, skipped = db.store_records(
            [],
            meter_serial="TEST123",
            meter_type="electricity"
        )

        assert inserted == 0
        assert skipped == 0
        assert db.get_record_count("TEST123") == 0

    def test_database_persistence(self, temp_db, sample_records):
        """Test that data persists after closing and reopening database."""
        # Store data with first instance
        db1 = ConsumptionDatabase(temp_db)
        db1.store_records(
            sample_records,
            meter_serial="TEST123",
            meter_type="electricity"
        )

        # Create new instance and verify data exists
        db2 = ConsumptionDatabase(temp_db)
        assert db2.get_record_count("TEST123") == 10
        latest = db2.get_latest_interval("TEST123")
        assert latest == sample_records[-1]["startAt"]

    def test_default_database_path(self):
        """Test that default database path is created correctly."""
        # Clean up if exists
        default_path = "./eon-data.db"
        if os.path.exists(default_path):
            os.unlink(default_path)

        try:
            ConsumptionDatabase()
            assert os.path.exists(default_path)
        finally:
            # Cleanup
            if os.path.exists(default_path):
                os.unlink(default_path)
