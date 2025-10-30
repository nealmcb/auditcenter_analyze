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
