"""
SQLite schema setup for importing auditcenter CSVs.

This module defines functions to create the normalized database schema used to
load auditcenter CSV data and expose it via Datasette. Per-ballot expansion is
explicitly out of scope; manifests are stored at batch level.
"""

from __future__ import annotations

import sqlite3
from typing import Iterable


def execute_script(connection: sqlite3.Connection, statements: Iterable[str]) -> None:
    """Execute multiple SQL statements inside a transaction.

    Parameters:
        connection: Open sqlite3 connection.
        statements: Iterable of SQL statements to execute.
    """
    with connection:
        cursor = connection.cursor()
        for statement in statements:
            cursor.execute(statement)


def create_schema(connection: sqlite3.Connection) -> None:
    """Create all tables, indexes, and constraints for the CSV import schema.

    This is idempotent and uses IF NOT EXISTS to safely re-run.
    """
    statements: list[str] = [
        # Counties
        """
        CREATE TABLE IF NOT EXISTS counties (
            county_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            normalized_name TEXT NOT NULL UNIQUE,
            ballot_card_count INTEGER
        );
        """,
        # Contests
        """
        CREATE TABLE IF NOT EXISTS contests (
            contest_id INTEGER PRIMARY KEY,
            round INTEGER NOT NULL,
            name TEXT NOT NULL,
            normalized_name TEXT NOT NULL,
            winners TEXT,
            min_margin INTEGER,
            contest_ballot_card_count INTEGER,
            diluted_margin REAL,
            audit_reason TEXT,
            two_vote_over_count INTEGER,
            one_vote_over_count INTEGER,
            one_vote_under_count INTEGER,
            two_vote_under_count INTEGER,
            disagreement_count INTEGER,
            other_count INTEGER,
            gamma REAL
        );
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_contests_round_name ON contests(round, normalized_name);",
        # Contest to county mapping
        """
        CREATE TABLE IF NOT EXISTS contest_counties (
            contest_id INTEGER NOT NULL,
            county_id INTEGER NOT NULL,
            original_county_id TEXT,
            original_contest_id TEXT,
            original_county_name TEXT,
            original_contest_name TEXT,
            PRIMARY KEY (contest_id, county_id),
            FOREIGN KEY (contest_id) REFERENCES contests(contest_id),
            FOREIGN KEY (county_id) REFERENCES counties(county_id)
        );
        """,
        # Manifests (batch-level only)
        """
        CREATE TABLE IF NOT EXISTS ballot_manifests (
            county_id INTEGER NOT NULL,
            tabulator_id TEXT,
            batch_number TEXT,
            ballot_count INTEGER,
            location TEXT,
            start_position INTEGER,
            end_position INTEGER,
            raw_row TEXT,
            PRIMARY KEY (county_id, tabulator_id, batch_number),
            FOREIGN KEY (county_id) REFERENCES counties(county_id)
        );
        """,
        # Ballot comparisons (from contestComparison.csv)
        """
        CREATE TABLE IF NOT EXISTS ballot_comparisons (
            comparison_id INTEGER PRIMARY KEY,
            contest_id INTEGER NOT NULL,
            county_id INTEGER,
            round INTEGER NOT NULL,
            imprinted_id TEXT,
            cvr_choice TEXT,
            audit_choice TEXT,
            consensus TEXT,
            discrepancy_type TEXT,
            timestamp TEXT,
            ballot_type TEXT,
            record_type TEXT,
            audit_board_comment TEXT,
            cvr_id TEXT,
            audit_reason TEXT,
            raw_row TEXT,
            FOREIGN KEY (contest_id) REFERENCES contests(contest_id),
            FOREIGN KEY (county_id) REFERENCES counties(county_id)
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_ballot_comparisons_contest ON ballot_comparisons(contest_id);",
        "CREATE INDEX IF NOT EXISTS idx_ballot_comparisons_county ON ballot_comparisons(county_id);",
        "CREATE INDEX IF NOT EXISTS idx_ballot_comparisons_round ON ballot_comparisons(round);",
        "CREATE INDEX IF NOT EXISTS idx_ballot_comparisons_consensus ON ballot_comparisons(consensus);",
        # Contest selections
        """
        CREATE TABLE IF NOT EXISTS contest_selections (
            contest_id INTEGER NOT NULL,
            county_id INTEGER,
            round INTEGER NOT NULL,
            imprinted_id TEXT,
            PRIMARY KEY (contest_id, round, imprinted_id),
            FOREIGN KEY (contest_id) REFERENCES contests(contest_id),
            FOREIGN KEY (county_id) REFERENCES counties(county_id)
        );
        """,
        # Contest selections raw data (contestSelection.csv)
        """
        CREATE TABLE IF NOT EXISTS contest_selection_rows (
            selection_id INTEGER PRIMARY KEY AUTOINCREMENT,
            contest_id INTEGER NOT NULL,
            round INTEGER NOT NULL,
            min_margin INTEGER,
            contest_cvr_ids TEXT,
            raw_row TEXT,
            FOREIGN KEY (contest_id) REFERENCES contests(contest_id)
        );
        """,
        # Vote totals (contest-level and county-level)
        """
        CREATE TABLE IF NOT EXISTS vote_totals (
            row_id INTEGER PRIMARY KEY,
            contest_id INTEGER NOT NULL,
            county_id INTEGER,  -- NULL for state-wide totals
            choice TEXT NOT NULL,
            votes INTEGER NOT NULL,
            source TEXT NOT NULL CHECK(source IN ('tabulate','tabulateCounty')),
            FOREIGN KEY (contest_id) REFERENCES contests(contest_id),
            FOREIGN KEY (county_id) REFERENCES counties(county_id)
        );
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_vote_totals_unique ON vote_totals(contest_id, county_id, choice, source);",
        # Random seed
        """
        CREATE TABLE IF NOT EXISTS audit_random_seed (
            round INTEGER PRIMARY KEY,
            seed TEXT NOT NULL,
            hash TEXT
        );
        """,
        # Name mappings (normalization diagnostics)
        """
        CREATE TABLE IF NOT EXISTS county_name_mapping (
            original TEXT PRIMARY KEY,
            normalized TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS contest_name_mapping (
            original TEXT PRIMARY KEY,
            normalized TEXT NOT NULL
        );
        """,
    ]

    execute_script(connection, statements)

    # Ensure legacy tables gain any newly required columns
    cursor = connection.cursor()

    # Contests extra columns
    cursor.execute("PRAGMA table_info(contests)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    required_columns = {
        "random_audit_status": "TEXT",
        "winners_allowed": "INTEGER",
        "ballot_card_count": "INTEGER",
        "risk_limit": "REAL",
        "audited_sample_count": "INTEGER",
        "overstatements": "INTEGER",
        "optimistic_samples_to_audit": "INTEGER",
        "estimated_samples_to_audit": "INTEGER",
    }

    for column_name, column_type in required_columns.items():
        if column_name not in existing_columns:
            cursor.execute(
                f"ALTER TABLE contests ADD COLUMN {column_name} {column_type}"
            )

    # Contest counties original columns
    cursor.execute("PRAGMA table_info(contest_counties)")
    contest_county_columns = {row[1] for row in cursor.fetchall()}
    contest_county_required = {
        "original_county_id": "TEXT",
        "original_contest_id": "TEXT",
        "original_county_name": "TEXT",
        "original_contest_name": "TEXT",
    }
    for column_name, column_type in contest_county_required.items():
        if column_name not in contest_county_columns:
            cursor.execute(
                f"ALTER TABLE contest_counties ADD COLUMN {column_name} {column_type}"
            )

    # Ballot manifests raw row storage
    cursor.execute("PRAGMA table_info(ballot_manifests)")
    ballot_manifest_columns = {row[1] for row in cursor.fetchall()}
    if "raw_row" not in ballot_manifest_columns:
        cursor.execute("ALTER TABLE ballot_manifests ADD COLUMN raw_row TEXT")

    # Ballot comparisons additional columns
    cursor.execute("PRAGMA table_info(ballot_comparisons)")
    ballot_comparison_columns = {row[1] for row in cursor.fetchall()}
    ballot_comparison_required = {
        "ballot_type": "TEXT",
        "record_type": "TEXT",
        "audit_board_comment": "TEXT",
        "cvr_id": "TEXT",
        "audit_reason": "TEXT",
        "raw_row": "TEXT",
    }
    for column_name, column_type in ballot_comparison_required.items():
        if column_name not in ballot_comparison_columns:
            cursor.execute(
                f"ALTER TABLE ballot_comparisons ADD COLUMN {column_name} {column_type}"
            )

    connection.commit()
