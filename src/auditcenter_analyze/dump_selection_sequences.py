#!/usr/bin/env python3
"""Dump targeted contest selection sequences and compare against audit data.

This utility reproduces the targeted selection order for every contest whose
`audit_reason` is `county_wide_contest` or `state_wide_contest`. It parses the
official `contestSelection.csv` exports, maps each CVR identifier to its
corresponding `(county, imprinted_id)` in the SQLite database, and writes
repeatable artifacts to `output/` describing the selections.

Generated files:

* `output/contest_comparison_all_pairs.csv`
    All distinct `(county, imprinted_id)` pairs present anywhere in
    `contestComparison.csv`.
* `output/targeted_selection_sequences.csv`
    Ordered list of draws for every targeted contest (one row per draw).
* `output/targeted_selection_summary.json`
    High-level counts for targeted, statewide, and residual selections.
* `output/contest_comparison_residual_pairs.csv`
    Remaining `(county, imprinted_id)` pairs that never appear under a targeted
    contest (currently dominated by opportunistic contests).

The script is designed to be deterministic and fast enough to re-run during
analysis sessions.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

# Repository layout --------------------------------------------------------

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]
DATA_ROOT = REPO_ROOT / "data" / "2024" / "general"
DB_PATH = REPO_ROOT / "output" / "colorado_rla.db"
OUTPUT_DIR = REPO_ROOT / "output"


def load_contest_selections(data_root: Path) -> Dict[str, Tuple[int, List[str]]]:
    """Return the ordered CVR id list for each contest, keyed by contest name.

    Multiple rounds of `contestSelection.csv` exist. Later rounds replace prior
    rounds. The return value maps contest name to a tuple of (round_number,
    [cvr_id strings in order]).
    """

    selections: Dict[str, Tuple[int, List[str]]] = {}
    if not data_root.exists():
        raise FileNotFoundError(f"Expected data root at {data_root}")

    for round_dir in sorted(data_root.glob("round*")):
        if not round_dir.is_dir():
            continue
        round_label = round_dir.name
        try:
            round_number = int(round_label.replace("round", ""))
        except ValueError:
            continue

        selection_path = round_dir / "contestSelection.csv"
        if not selection_path.exists():
            continue

        with selection_path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                contest_name = row["contest_name"].strip()
                raw_ids = row["contest_cvr_ids"].strip()
                if not raw_ids or raw_ids == "[]":
                    continue
                tokens = [
                    token.strip()
                    for token in raw_ids.strip("[]").split(",")
                    if token.strip()
                ]
                if not tokens:
                    continue
                selections[contest_name] = (round_number, tokens)

    return selections


def chunked(sequence: Sequence[str], size: int = 900) -> Iterable[List[str]]:
    """Yield chunks of `sequence` up to `size` items (SQLite has 999 parameter limit)."""

    for start in range(0, len(sequence), size):
        yield list(sequence[start : start + size])


def fetch_cvr_mappings(
    cursor: sqlite3.Cursor, contest_id: int, cvr_ids: Sequence[str]
) -> Dict[str, List[Tuple[int, str]]]:
    """Return mapping of CVR id -> list[(county_id, imprinted_id)] for a contest.

    The mapping is derived from `ballot_comparisons`. We do not restrict to the
    specific contest because opportunistic logging means the CVR may only appear
    under a different contest even though the ballot card was part of the
    targeted draw.
    """

    del contest_id  # not needed for the lookup but kept for caller symmetry
    mapping: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
    for chunk in chunked(cvr_ids):
        placeholders = ",".join("?" for _ in chunk)
        rows = cursor.execute(
            f"""
            SELECT cvr_id, county_id, imprinted_id
            FROM ballot_comparisons
            WHERE imprinted_id IS NOT NULL
              AND cvr_id IN ({placeholders})
            """,
            chunk,
        ).fetchall()
        for row in rows:
            mapping[str(row["cvr_id"])].append((row["county_id"], row["imprinted_id"]))
    return mapping


def fetch_all_pairs(cursor: sqlite3.Cursor) -> List[Tuple[int, str]]:
    """Return all distinct `(county_id, imprinted_id)` pairs from contestComparison."""

    rows = cursor.execute(
        """
        SELECT DISTINCT county_id, imprinted_id
        FROM ballot_comparisons
        WHERE imprinted_id IS NOT NULL
        ORDER BY county_id, imprinted_id
        """
    ).fetchall()
    return [(row["county_id"], row["imprinted_id"]) for row in rows]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    selections = load_contest_selections(DATA_ROOT)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    targeted_contests = cur.execute(
        """
        SELECT contest_id, name, audit_reason, round
        FROM contests
        WHERE audit_reason IN ('county_wide_contest', 'state_wide_contest')
        ORDER BY contest_id
        """
    ).fetchall()

    county_lookup = {
        row["county_id"]: row["name"]
        for row in cur.execute("SELECT county_id, name FROM counties")
    }

    targeted_records: List[Dict[str, object]] = []
    missing_selection: List[Tuple[str, int]] = []
    missing_mappings: List[Tuple[str, int, str]] = []

    for contest_row in targeted_contests:
        contest_id = contest_row["contest_id"]
        contest_name = contest_row["name"]
        audit_reason = contest_row["audit_reason"]
        round_number = contest_row["round"]

        if contest_name not in selections:
            missing_selection.append((contest_name, contest_id))
            continue

        round_from_export, ordered_cvr_ids = selections[contest_name]
        cvr_mapping = fetch_cvr_mappings(cur, contest_id, ordered_cvr_ids)

        for seq_index, cvr_id in enumerate(ordered_cvr_ids, start=1):
            mapped = cvr_mapping.get(cvr_id)
            if not mapped:
                missing_mappings.append((contest_name, contest_id, cvr_id))
                continue
            for occurrence_index, (county_id, imprinted_id) in enumerate(
                mapped, start=1
            ):
                targeted_records.append(
                    {
                        "contest_id": contest_id,
                        "contest_name": contest_name,
                        "audit_reason": audit_reason,
                        "contest_round": round_number,
                        "selection_round": round_from_export,
                        "sequence": seq_index,
                        "occurrence": occurrence_index,
                        "cvr_id": cvr_id,
                        "county_id": county_id,
                        "county_name": county_lookup.get(county_id, f"county_{county_id}"),
                        "imprinted_id": imprinted_id,
                    }
                )

    # Dump targeted sequence records
    targeted_path = OUTPUT_DIR / "targeted_selection_sequences.csv"
    if targeted_records:
        fieldnames = [
            "contest_id",
            "contest_name",
            "audit_reason",
            "contest_round",
            "selection_round",
            "sequence",
            "occurrence",
            "cvr_id",
            "county_id",
            "county_name",
            "imprinted_id",
        ]
        with targeted_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for record in targeted_records:
                writer.writerow(record)
    else:
        targeted_path.write_text("contest_id,contest_name,audit_reason\n")

    # Compute pair sets
    all_pairs = fetch_all_pairs(cur)
    targeted_pairs = {
        (record["county_id"], record["imprinted_id"])
        for record in targeted_records
        if record["imprinted_id"]
    }
    residual_pairs = [
        pair for pair in all_pairs if pair not in targeted_pairs
    ]

    # Dump all pairs
    all_pairs_path = OUTPUT_DIR / "contest_comparison_all_pairs.csv"
    with all_pairs_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["county_id", "county_name", "imprinted_id"])
        for county_id, imprinted in all_pairs:
            writer.writerow([county_id, county_lookup.get(county_id, ""), imprinted])

    # Dump residual pairs
    residual_path = OUTPUT_DIR / "contest_comparison_residual_pairs.csv"
    with residual_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["county_id", "county_name", "imprinted_id"])
        for county_id, imprinted in residual_pairs:
            writer.writerow([county_id, county_lookup.get(county_id, ""), imprinted])

    # Summary JSON
    summary = {
        "counts": {
            "all_pairs": len(all_pairs),
            "targeted_pairs": len(targeted_pairs),
            "residual_pairs": len(residual_pairs),
            "targeted_records": len(targeted_records),
        },
        "missing_selection_entries": missing_selection,
        "missing_cvr_mappings": missing_mappings,
        "residual_distribution": Counter(
            county_lookup.get(cid, f"county_{cid}") for cid, _ in residual_pairs
        ),
    }
    summary_path = OUTPUT_DIR / "targeted_selection_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))

    conn.close()

    print(f"Wrote targeted sequence details to {targeted_path}")
    print(f"Wrote all pair list to {all_pairs_path}")
    print(f"Wrote residual pair list to {residual_path}")
    print(f"Wrote summary to {summary_path}")

    if missing_selection:
        print("\nMissing contestSelection entries for targeted contests:")
        for name, contest_id in missing_selection:
            print(f"  - {name} (contest_id={contest_id})")

    if missing_mappings:
        print("\nCVR IDs without imprinted mapping:")
        for name, contest_id, cvr_id in missing_mappings[:20]:
            print(f"  - {name} (contest_id={contest_id}) CVR {cvr_id}")
        if len(missing_mappings) > 20:
            print(f"  ... and {len(missing_mappings) - 20} more")


if __name__ == "__main__":
    main()

