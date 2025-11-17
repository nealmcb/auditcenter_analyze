#!/usr/bin/env python3
"""Validate county-wide targeted contest draws against manifest RNG.

For each county-wide targeted contest we:

1. Re-create the pseudo-random selections using the official round seed,
   SHA-256 RNG, and the combined manifest domain.
2. Compare the expected ballot cards with what appears in contestComparison.
3. Report any discrepancies (missing cards and extra logged cards).

Extras are recorded for later investigation, but only contests with missing
ballot cards are highlighted in the primary report.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from .normalize import normalize_county_name, normalized_county_key
from .verify_any_contest import (
    ballot_to_imprinted_id,
    generate_random_numbers,
    load_ballot_manifest,
    resolve_manifest_file,
)

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]
DATA_ROOT = REPO_ROOT / "data" / "2024" / "general"
DB_PATH = REPO_ROOT / "output" / "colorado_rla.db"
OUTPUT_DIR = REPO_ROOT / "output" / "reconstructed"


def load_round_seeds(cursor: sqlite3.Cursor) -> Dict[int, str]:
    seeds: Dict[int, str] = {
        row["round"]: row["seed"]
        for row in cursor.execute(
            "SELECT round, seed FROM audit_random_seed WHERE seed IS NOT NULL"
        )
    }
    if not seeds:
        raise RuntimeError("No seeds found in audit_random_seed.")
    return seeds


def load_selection_counts() -> Dict[int, Dict[str, int]]:
    round_counts: Dict[int, Dict[str, int]] = defaultdict(dict)
    for round_dir in sorted(DATA_ROOT.glob("round*")):
        if not round_dir.is_dir():
            continue
        try:
            round_num = int(round_dir.name.replace("round", ""))
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
                    count = 0
                else:
                    tokens = [
                        token.strip() for token in raw_ids.strip("[]").split(",") if token.strip()
                    ]
                    count = len(tokens)
                round_counts[round_num][contest_name] = count
    return round_counts


def chunked(sequence: Sequence[int], size: int = 900) -> Iterable[List[int]]:
    for start in range(0, len(sequence), size):
        yield list(sequence[start : start + size])


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    seeds_by_round = load_round_seeds(cur)
    selection_counts = load_selection_counts()

    county_lookup = {
        row["county_id"]: normalize_county_name(row["name"])
        for row in cur.execute("SELECT county_id, name FROM counties")
    }

    targeted_contests = cur.execute(
        """
        SELECT contest_id, name
        FROM contests
        WHERE audit_reason = 'county_wide_contest'
        ORDER BY contest_id
        """
    ).fetchall()

    contest_counties: Dict[int, List[str]] = defaultdict(list)
    for row in cur.execute(
        """
        SELECT cc.contest_id, co.name
        FROM contest_counties cc
        JOIN counties co ON cc.county_id = co.county_id
        """
    ):
        contest_counties[row["contest_id"]].append(normalize_county_name(row["name"]))

    manifest_cache: Dict[str, List[Tuple[str, str, str, int]]] = {}

    def load_manifest_for_county(county_name: str) -> List[Tuple[str, str, str, int]]:
        canonical = normalize_county_name(county_name)
        key = normalized_county_key(canonical)
        if key in manifest_cache:
            return manifest_cache[key]
        manifest_path = resolve_manifest_file(DATA_ROOT, canonical)
        if manifest_path is None:
            raise FileNotFoundError(f"Could not find manifest for {canonical}")
        ballots = load_ballot_manifest(str(manifest_path))
        manifest_cache[key] = ballots
        return ballots

    rounds_order = sorted({1, 2, 3} | set(seeds_by_round.keys()))

    missing_rows: List[Dict[str, str]] = []
    extras_rows: List[Dict[str, str]] = []
    contest_summaries: Dict[str, Dict[str, int]] = {}

    for contest in targeted_contests:
        contest_id = contest["contest_id"]
        contest_name = contest["name"]
        counties = contest_counties.get(contest_id)
        summary = {
            "expected_total": 0,
            "actual_total": 0,
            "missing": 0,
            "extras": 0,
            "manifest_missing": 0,
        }

        if not counties:
            summary["manifest_missing"] = -1
            contest_summaries[contest_name] = summary
            continue

        canonical_counties = sorted({normalize_county_name(c) for c in counties})
        combined_manifest: List[Tuple[str, str, str, int]] = []
        for county in canonical_counties:
            try:
                ballots = load_manifest_for_county(county)
            except FileNotFoundError:
                summary["manifest_missing"] += 1
                continue
            target_key = normalized_county_key(county)
            for entry in ballots:
                entry_county = normalize_county_name(entry[0])
                if normalized_county_key(entry_county) == target_key:
                    combined_manifest.append(entry)

        if not combined_manifest:
            contest_summaries[contest_name] = summary
            continue

        domain_size = len(combined_manifest)
        processed_count = 0
        expected_records: List[Dict[str, str]] = []

        for round_num in rounds_order:
            seed = seeds_by_round.get(round_num)
            if seed is None:
                seed = seeds_by_round[min(seeds_by_round)]

            declared_count = selection_counts.get(round_num, {}).get(contest_name, 0)
            additional = declared_count - processed_count
            if additional <= 0:
                continue

            selections = generate_random_numbers(seed, declared_count, domain_size)
            for offset, pick in enumerate(selections[processed_count:declared_count], start=1):
                sequence_number = processed_count + offset
                record: Dict[str, str] = {
                    "contest_name": contest_name,
                    "sequence": str(sequence_number),
                    "round": str(round_num),
                    "county": "",
                    "imprinted_id": "",
                    "status": "ok",
                    "reason": "",
                }
                if pick < 1 or pick > domain_size:
                    record["status"] = "out_of_range"
                    record["reason"] = f"pick {pick} > domain {domain_size}"
                    expected_records.append(record)
                    summary["missing"] += 1
                    continue
                county_name, tabulator, batch, position = combined_manifest[pick - 1]
                canonical_county = normalize_county_name(county_name)
                imprinted = ballot_to_imprinted_id(
                    canonical_county.replace(" ", ""), tabulator, batch, position
                )
                record["county"] = canonical_county
                record["imprinted_id"] = imprinted
                expected_records.append(record)

            processed_count = declared_count

        expected_pairs = {
            (normalized_county_key(rec["county"]), rec["imprinted_id"])
            for rec in expected_records
            if rec["imprinted_id"]
        }
        summary["expected_total"] = len(expected_pairs)

        actual_pairs = {
            (
                normalized_county_key(county_lookup.get(row["county_id"], "")),
                row["imprinted_id"],
            )
            for row in cur.execute(
                """
                SELECT DISTINCT bc.imprinted_id, bc.county_id
                FROM ballot_comparisons bc
                WHERE bc.contest_id = ? AND bc.imprinted_id IS NOT NULL
                """,
                (contest_id,),
            )
        }
        summary["actual_total"] = len(actual_pairs)

        # Missing cards
        for rec in expected_records:
            key = (normalized_county_key(rec["county"]), rec["imprinted_id"])
            if not rec["imprinted_id"] or key not in actual_pairs:
                rec_copy = rec.copy()
                missing_rows.append(rec_copy)
                summary["missing"] += 1

        # Extras (present in audit log but not in expected picks)
        extra_pairs = actual_pairs - expected_pairs
        summary["extras"] = len(extra_pairs)
        if extra_pairs:
            for county_key, imprinted_id in sorted(extra_pairs):
                county_display = next(
                    (
                        rec["county"]
                        for rec in expected_records
                        if normalized_county_key(rec["county"]) == county_key
                    ),
                    None,
                )
                if county_display is None:
                    county_display = county_lookup.get(
                        next(
                            (
                                row["county_id"]
                                for row in cur.execute(
                                    """
                                    SELECT DISTINCT county_id
                                    FROM ballot_comparisons
                                    WHERE contest_id = ? AND imprinted_id = ?
                                    LIMIT 1
                                    """,
                                    (contest_id, imprinted_id),
                                )
                            ),
                            0,
                        ),
                        "",
                    )
                extras_rows.append(
                    {
                        "contest_name": contest_name,
                        "county": county_display,
                        "imprinted_id": imprinted_id,
                    }
                )

        contest_summaries[contest_name] = summary

    conn.close()

    missing_output = OUTPUT_DIR / "targeted_missing_ballots.csv"
    with missing_output.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "contest_name",
                "sequence",
                "round",
                "county",
                "imprinted_id",
                "status",
                "reason",
            ],
        )
        writer.writeheader()
        for row in sorted(
            missing_rows,
            key=lambda r: (r["contest_name"], int(r["sequence"] or "0")),
        ):
            writer.writerow(row)

    extras_output = OUTPUT_DIR / "targeted_extra_ballots.csv"
    with extras_output.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["contest_name", "county", "imprinted_id"])
        writer.writeheader()
        for row in sorted(
            extras_rows, key=lambda r: (r["contest_name"], r["county"], r["imprinted_id"])
        ):
            writer.writerow(row)

    summary_output = OUTPUT_DIR / "targeted_validation_summary.json"
    summary_output.write_text(json.dumps(contest_summaries, indent=2, sort_keys=True))

    contests_with_missing = [
        (name, data) for name, data in contest_summaries.items() if data["missing"] > 0
    ]

    print(f"Wrote missing ballot report to {missing_output}")
    print(f"Wrote extras list to {extras_output}")
    print(f"Wrote summary to {summary_output}")
    if contests_with_missing:
        print("Contests with missing ballot cards detected:")
        for name, data in contests_with_missing:
            print(
                f"  - {name}: expected {data['expected_total']}, "
                f"actual {data['actual_total']}, missing {data['missing']}"
            )
    else:
        print("All county-wide targeted contests reconciled (no missing ballot cards).")


if __name__ == "__main__":
    main()
