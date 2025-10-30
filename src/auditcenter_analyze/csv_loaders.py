"""CSV loaders for importing auditcenter data into SQLite.

This module provides functions to load and import CSV files from the auditcenter
export into the normalized database schema.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Any

from .normalize import normalize_county_name, normalized_county_key


# All known variations of ballot count column names in manifests
MANIFEST_COUNT_COLUMNS = [
    "# in Batch",
    "# of Ballot Cards",
    "# of ballot cards",
    "#of Ballot Cards",
    "# Ballot Cards",
    "# of Ballots Cards",
    "# of Ballots",
    "# of Ballot",
    "# Cards",
    "# Ballots",
    "# of cards",
    ". of Ballots",
]


def load_manifest_batches(manifest_file: Path) -> list[dict[str, Any]]:
    """Load ballot manifest batches from a single county file.

    Returns list of batch records with normalized column names.
    Handles all known variations in column naming across counties.

    Args:
        manifest_file: Path to county manifest CSV file

    Returns:
        List of dictionaries with keys: tabulator_id, batch_number,
        ballot_count, location

    Raises:
        ValueError: If no valid ballot count column found
    """
    batches = []
    with open(manifest_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Find the ballot count column (handles variations)
            ballot_count = None
            for col in MANIFEST_COUNT_COLUMNS:
                if col in row and row[col]:
                    try:
                        ballot_count = int(row[col])
                        break
                    except (ValueError, AttributeError):
                        continue

            if ballot_count is None:
                raise ValueError(f"No valid ballot count column found in {manifest_file}")

            # Extract other fields (may have variations too)
            tabulator_id = row.get("Tabulator") or row.get("Tabulator ID", "")
            batch_number = row.get("Batch") or row.get("Batch Number", "")
            location = row.get("Location") or row.get("Storage Location", "")

            batches.append(
                {
                    "tabulator_id": tabulator_id.strip(),
                    "batch_number": batch_number.strip(),
                    "ballot_count": ballot_count,
                    "location": location.strip(),
                }
            )

    return batches


def import_counties_and_manifests(
    conn: sqlite3.Connection, manifests_dir: Path, progress_callback: Any = None
) -> dict[str, int]:
    """Import counties and their ballot manifests into database.

    Args:
        conn: SQLite database connection
        manifests_dir: Directory containing county manifest files
        progress_callback: Optional function to call with progress updates

    Returns:
        Dictionary mapping normalized county key to county_id
    """
    county_map = {}  # normalized_key -> county_id

    # Find all manifest files
    manifest_files = sorted(manifests_dir.glob("*BallotManifest.csv"))
    total_files = len(manifest_files)

    cursor = conn.cursor()

    for idx, manifest_file in enumerate(manifest_files, 1):
        # Extract county from filename
        county_stem = manifest_file.stem.replace("BallotManifest", "")
        county_key = normalized_county_key(county_stem)
        county_canonical = normalize_county_name(county_stem)

        if progress_callback:
            progress_callback(f"Loading {county_canonical} ({idx}/{total_files})")

        # Load manifest batches
        try:
            batches = load_manifest_batches(manifest_file)
        except ValueError as e:
            if progress_callback:
                progress_callback(f"Warning: {e}")
            continue

        # Calculate total ballot count
        total_ballots = sum(b["ballot_count"] for b in batches)

        # Insert or update county
        cursor.execute(
            """
            INSERT INTO counties (name, normalized_name, ballot_card_count)
            VALUES (?, ?, ?)
            ON CONFLICT(normalized_name) DO UPDATE
            SET ballot_card_count = excluded.ballot_card_count
        """,
            (county_canonical, county_key, total_ballots),
        )

        # Get county_id
        cursor.execute("SELECT county_id FROM counties WHERE normalized_name = ?", (county_key,))
        county_id = cursor.fetchone()[0]
        county_map[county_key] = county_id

        # Insert manifest batches
        current_position = 1
        for batch in batches:
            end_position = current_position + batch["ballot_count"] - 1

            cursor.execute(
                """
                INSERT OR REPLACE INTO ballot_manifests
                    (county_id, tabulator_id, batch_number, ballot_count, location, start_position, end_position)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    county_id,
                    batch["tabulator_id"],
                    batch["batch_number"],
                    batch["ballot_count"],
                    batch["location"],
                    current_position,
                    end_position,
                ),
            )

            current_position = end_position + 1

    conn.commit()
    return county_map


def import_contests_and_contest_counties(
    conn: sqlite3.Connection,
    contests_by_county_file: Path,
    county_map: dict[str, int],
    progress_callback: Any = None,
) -> dict[str, int]:
    """Import contests and contest-county mappings.

    Args:
        conn: SQLite database connection
        contests_by_county_file: Path to contestsByCounty.csv
        county_map: Dictionary mapping normalized county key to county_id
        progress_callback: Optional function to call with progress updates

    Returns:
        Dictionary mapping contest_name to contest_id
    """
    import csv

    contest_map = {}  # contest_name -> contest_id

    with open(contests_by_county_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if progress_callback:
        progress_callback(f"Loading {len(rows)} contest-county mappings...")

    cursor = conn.cursor()

    # Get unique contests
    unique_contests = set(row["contest_name"] for row in rows)

    # Insert contests (we don't have round info yet, so insert with round=-1 as placeholder)
    for idx, contest_name in enumerate(sorted(unique_contests), 1):
        # We'll update round info when loading round-specific data
        cursor.execute(
            """
            INSERT OR IGNORE INTO contests (round, name, normalized_name)
            VALUES (-1, ?, ?)
        """,
            (contest_name, contest_name.lower()),
        )

        cursor.execute("SELECT contest_id FROM contests WHERE name = ?", (contest_name,))
        contest_id = cursor.fetchone()[0]
        contest_map[contest_name] = contest_id

    # Insert contest-county mappings
    for row in rows:
        county_name = row["county_name"]
        county_key = normalized_county_key(county_name)

        if county_key not in county_map:
            if progress_callback:
                progress_callback(
                    f"Warning: Unknown county '{county_name}' in contestsByCounty.csv"
                )
            continue

        county_id = county_map[county_key]
        contest_name = row["contest_name"]
        contest_id = contest_map[contest_name]

        cursor.execute(
            """
            INSERT OR IGNORE INTO contest_counties (contest_id, county_id)
            VALUES (?, ?)
        """,
            (contest_id, county_id),
        )

    conn.commit()
    return contest_map


def import_vote_totals(
    conn: sqlite3.Connection,
    tabulate_file: Path,
    tabulate_county_file: Path,
    contest_map: dict[str, int],
    county_map: dict[str, int],
    progress_callback: Any = None,
) -> None:
    """Import vote totals from tabulate files.

    Args:
        conn: SQLite database connection
        tabulate_file: Path to tabulate.csv (state-wide totals)
        tabulate_county_file: Path to tabulateCounty.csv (county-level totals)
        contest_map: Dictionary mapping contest_name to contest_id
        county_map: Dictionary mapping normalized county key to county_id
        progress_callback: Optional function to call with progress updates
    """
    import csv

    cursor = conn.cursor()

    # Load state-wide totals
    if progress_callback:
        progress_callback("Loading state-wide vote totals...")

    with open(tabulate_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for row in rows:
        contest_name = row["contest_name"]
        if contest_name not in contest_map:
            continue

        contest_id = contest_map[contest_name]
        choice = row["choice"]
        votes = int(row["votes"])

        cursor.execute(
            """
            INSERT OR REPLACE INTO vote_totals 
                (contest_id, county_id, choice, votes, source)
            VALUES (?, NULL, ?, ?, 'tabulate')
        """,
            (contest_id, choice, votes),
        )

    # Load county-level totals
    if progress_callback:
        progress_callback("Loading county-level vote totals...")

    with open(tabulate_county_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for row in rows:
        contest_name = row["contest_name"]
        if contest_name not in contest_map:
            continue

        county_name = row["county_name"]
        county_key = normalized_county_key(county_name)
        if county_key not in county_map:
            continue

        contest_id = contest_map[contest_name]
        county_id = county_map[county_key]
        choice = row["choice"]
        votes = int(row["votes"])

        cursor.execute(
            """
            INSERT OR REPLACE INTO vote_totals 
                (contest_id, county_id, choice, votes, source)
            VALUES (?, ?, ?, ?, 'tabulateCounty')
        """,
            (contest_id, county_id, choice, votes),
        )

    conn.commit()


def import_seed(
    conn: sqlite3.Connection, seed_file: Path, round_num: int = 1, progress_callback: Any = None
) -> None:
    """Import audit random seed.

    Args:
        conn: SQLite database connection
        seed_file: Path to seed.csv
        round_num: Round number (default 1)
        progress_callback: Optional function to call with progress updates
    """
    import csv

    with open(seed_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        row = next(reader)
        seed = row["seed"]

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO audit_random_seed (round, seed)
        VALUES (?, ?)
    """,
        (round_num, seed),
    )

    conn.commit()

    if progress_callback:
        progress_callback(f"Imported seed for round {round_num}: {seed}")


def import_round_data(
    conn: sqlite3.Connection,
    round_dir: Path,
    round_num: int,
    contest_map: dict[str, int],
    county_map: dict[str, int],
    progress_callback: Any = None,
) -> None:
    """Import round-specific data: contest metadata, ballot comparisons, selections.

    Args:
        conn: SQLite database connection
        round_dir: Directory containing round CSV files
        round_num: Round number
        contest_map: Dictionary mapping contest_name to contest_id
        county_map: Dictionary mapping normalized county key to county_id
        progress_callback: Optional function to call with progress updates
    """
    cursor = conn.cursor()

    # Import contest.csv
    contest_file = round_dir / "contest.csv"
    if contest_file.exists():
        if progress_callback:
            progress_callback(f"Loading contest metadata for round {round_num}...")

        import csv

        with open(contest_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                contest_name = row["contest_name"]
                if contest_name not in contest_map:
                    continue

                contest_id = contest_map[contest_name]

                # Update contest with round-specific data
                cursor.execute(
                    """
                    UPDATE contests SET 
                        round = ?,
                        winners = ?,
                        min_margin = ?,
                        contest_ballot_card_count = ?,
                        diluted_margin = ?,
                        audit_reason = ?,
                        two_vote_over_count = ?,
                        one_vote_over_count = ?,
                        one_vote_under_count = ?,
                        two_vote_under_count = ?,
                        disagreement_count = ?,
                        other_count = ?,
                        gamma = ?
                    WHERE contest_id = ?
                """,
                    (
                        round_num,
                        row.get("winners"),
                        int(row["min_margin"]) if row.get("min_margin") else None,
                        (
                            int(row["contest_ballot_card_count"])
                            if row.get("contest_ballot_card_count")
                            else None
                        ),
                        float(row["diluted_margin"]) if row.get("diluted_margin") else None,
                        row.get("audit_reason"),
                        int(row["two_vote_over_count"]) if row.get("two_vote_over_count") else None,
                        int(row["one_vote_over_count"]) if row.get("one_vote_over_count") else None,
                        (
                            int(row["one_vote_under_count"])
                            if row.get("one_vote_under_count")
                            else None
                        ),
                        (
                            int(row["two_vote_under_count"])
                            if row.get("two_vote_under_count")
                            else None
                        ),
                        int(row["disagreement_count"]) if row.get("disagreement_count") else None,
                        int(row["other_count"]) if row.get("other_count") else None,
                        float(row["gamma"]) if row.get("gamma") else None,
                        contest_id,
                    ),
                )

    # Import contestComparison.csv
    comparison_file = round_dir / "contestComparison.csv"
    if comparison_file.exists():
        if progress_callback:
            progress_callback(f"Loading ballot comparisons for round {round_num}...")

        import csv

        with open(comparison_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                contest_name = row["contest_name"]
                if contest_name not in contest_map:
                    continue

                county_name = row["county_name"]
                county_key = normalized_county_key(county_name)
                if county_key not in county_map:
                    continue

                contest_id = contest_map[contest_name]
                county_id = county_map[county_key]

                cursor.execute(
                    """
                    INSERT INTO ballot_comparisons
                        (contest_id, county_id, round, imprinted_id, cvr_choice, 
                         audit_choice, consensus, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        contest_id,
                        county_id,
                        round_num,
                        row["imprinted_id"],
                        row.get("choice_per_voting_computer", ""),
                        row.get("audit_board_selection", ""),
                        row.get("consensus", "YES"),
                        row.get("timestamp"),
                    ),
                )
                count += 1

            if progress_callback:
                progress_callback(f"  Loaded {count} ballot comparisons")

    # Import contestSelection.csv
    selection_file = round_dir / "contestSelection.csv"
    if selection_file.exists():
        if progress_callback:
            progress_callback(f"Loading contest selections for round {round_num}...")

        import csv

        with open(selection_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                contest_name = row["contest_name"]
                if contest_name not in contest_map:
                    continue

                contest_id = contest_map[contest_name]

                # We don't have direct county mapping for CVR IDs, so skip for now
                # This could be expanded later if needed
                if progress_callback and count == 0:
                    progress_callback("  Skipping CVR ID selections (not yet implemented)")
                count += 1

    conn.commit()
