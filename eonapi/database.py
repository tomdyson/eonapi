"""SQLite database module for storing consumption data."""

import sqlite3
from datetime import datetime
from typing import Optional


class ConsumptionDatabase:
    """Database manager for storing and retrieving consumption data."""

    def __init__(self, db_path: str = "./eon-data.db"):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Create database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS consumption (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meter_serial TEXT NOT NULL,
                    meter_type TEXT NOT NULL,
                    interval_start TEXT NOT NULL,
                    interval_end TEXT NOT NULL,
                    consumption_kwh REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(meter_serial, interval_start)
                )
            """)

            # The UNIQUE constraint on (meter_serial, interval_start) already creates an index.
            conn.commit()

    def get_latest_interval(self, meter_serial: str) -> Optional[str]:
        """Get the latest interval_start timestamp for a meter.

        Args:
            meter_serial: The meter serial number

        Returns:
            Latest interval_start timestamp as ISO string, or None if no data exists
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT interval_start
                FROM consumption
                WHERE meter_serial = ?
                ORDER BY interval_start DESC
                LIMIT 1
            """, (meter_serial,))

            result = cursor.fetchone()
            return result[0] if result else None

    def store_records(
        self,
        records: list[dict],
        meter_serial: str,
        meter_type: str
    ) -> tuple[int, int]:
        """Store consumption records in the database.

        Args:
            records: List of consumption records with startAt, endAt, value fields
            meter_serial: The meter serial number
            meter_type: Type of meter (electricity or gas)

        Returns:
            Tuple of (inserted_count, skipped_count)
        """
        inserted = 0
        skipped = 0
        created_at = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            for record in records:
                try:
                    conn.execute("""
                        INSERT INTO consumption
                        (meter_serial, meter_type, interval_start, interval_end,
                         consumption_kwh, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        meter_serial,
                        meter_type,
                        record.get("startAt", ""),
                        record.get("endAt", ""),
                        float(record.get("value", 0)),
                        created_at
                    ))
                    inserted += 1
                except sqlite3.IntegrityError:
                    # Record already exists, skip it
                    skipped += 1

            conn.commit()

        return inserted, skipped

    def get_all_records(
        self,
        meter_serial: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> list[dict]:
        """Retrieve consumption records from the database.

        Args:
            meter_serial: Optional meter serial to filter by
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of consumption records
        """
        query = "SELECT * FROM consumption WHERE 1=1"
        params = []

        if meter_serial:
            query += " AND meter_serial = ?"
            params.append(meter_serial)

        if start_date:
            query += " AND interval_start >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND interval_start <= ?"
            params.append(end_date.isoformat())

        query += " ORDER BY interval_start"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def get_record_count(self, meter_serial: Optional[str] = None) -> int:
        """Get the total number of records in the database.

        Args:
            meter_serial: Optional meter serial to filter by

        Returns:
            Number of records
        """
        query = "SELECT COUNT(*) FROM consumption"
        params = []

        if meter_serial:
            query += " WHERE meter_serial = ?"
            params.append(meter_serial)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchone()[0]
