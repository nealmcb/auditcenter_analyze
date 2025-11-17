#!/usr/bin/env python3
"""Reconstruct targeted ballot selections round-by-round from manifests.

This script audits the official draw process without relying on the
`contestComparison.csv` CVR/imprinted_id mapping. For every targeted
county-wide contest we:

1. Trust the published contestSelection counts (per round) to determine how
   many draws occurred.
2. Regenerate the pseudo-random selections directly from the round seed.
3. Map each selection to an imprinted ballot identifier using the county
   ballot manifests.

Each reconstructed draw is emitted as a row:

    county, imprinted_id, contest_name, round, selection

If a ballot card does not match any targeted draw, we still include it with
an empty contest/round/selection so that every `(county, imprinted_id)` present
in `contestComparison.csv` appears at least once in the output. This allows
analysts to see which ballots lack an identified targeted contest.
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
OUTPUT_DIR = REPO_ROOT / "output"


def load_round_seeds(cursor: sqlite3.Cursor) -> Dict[int, str]:
    """Return mapping of round number -> seed string."""

    seeds: Dict[int, str] = {
        row["round"]: row["seed"]
        for row in cursor.execute(
            "SELECT round, seed FROM audit_random_seed WHERE seed IS NOT NULL"
        )
    }
    if not seeds:
        raise RuntimeError("No random seeds found in audit_random_seed table.")
    return seeds


def load_selection_counts() -> Dict[int, Dict[str, int]]:
    """Return round->contest_name->selection_count from contestSelection exports."""

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


def chunked(sequence: Sequence[int], size: int = 1000) -> Iterable[List[int]]:
    """Yield chunks to avoid sqlite parameter limits when needed."""

    for start in range(0, len(sequence), size):
        yield list(sequence[start : start + size])


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    analysis_dir = OUTPUT_DIR / "reconstructed"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    county_lookup = {
        row["county_id"]: normalize_county_name(row["name"])
        for row in cur.execute("SELECT county_id, name FROM counties")
    }

    seeds_by_round = load_round_seeds(cur)
    selection_counts = load_selection_counts()

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

    # Cache manifests per canonical county name
    manifest_cache: Dict[str, List[Tuple[str, str, str, int]]] = {}

    def load_manifest_for_county(county_name: str) -> List[Tuple[str, str, str, int]]:
        canonical = normalize_county_name(county_name)
        normalized_key = normalized_county_key(county_name)
        if normalized_key in manifest_cache:
            return manifest_cache[normalized_key]
        manifest_path = resolve_manifest_file(DATA_ROOT, canonical)
        if manifest_path is None:
            raise FileNotFoundError(f"Could not find manifest file for {canonical}")
        ballots = load_ballot_manifest(str(manifest_path))
        manifest_cache[normalized_key] = ballots
        return ballots

    reconstructed_rows: List[Dict[str, str]] = []
    produced_pairs: Dict[Tuple[str, str], List[Dict[str, str]]] = defaultdict(list)

    rounds_to_process = sorted({1, 2, 3} | set(seeds_by_round.keys()))
    processed_counts: Dict[int, int] = defaultdict(int)

    for round_num in rounds_to_process:
        seed = seeds_by_round.get(round_num)
        if seed is None:
            # Fall back to the lowest available seed
            fallback_round = min(seeds_by_round.keys())
            seed = seeds_by_round[fallback_round]

        for contest in targeted_contests:
            contest_id = contest["contest_id"]
            contest_name = contest["name"]
            declared_count = selection_counts.get(round_num, {}).get(contest_name, 0)
            previous_count = processed_counts.get(contest_id, 0)

            additional_draws = declared_count - previous_count
            if additional_draws <= 0:
                continue

            counties = contest_counties.get(contest_id)
            if not counties:
                print(
                    f"⚠️  Skipping contest '{contest_name}' (id {contest_id}) "
                    f"round {round_num}: no counties found."
                )
                continue

            canonical_counties = sorted({normalize_county_name(c) for c in counties})

            combined_manifest: List[Tuple[str, str, str, int]] = []
            for county in canonical_counties:
                ballots = load_manifest_for_county(county)
                target_key = normalized_county_key(county)
                for entry in ballots:
                    entry_county_key = normalized_county_key(entry[0])
                    if entry_county_key == target_key:
                        combined_manifest.append(entry)

            if not combined_manifest:
                print(
                    f"⚠️  Skipping contest '{contest_name}' round {round_num}: "
                    "no manifest entries found."
                )
                continue

            domain_size = len(combined_manifest)
            selections = generate_random_numbers(seed, declared_count, domain_size)

            for offset, pick in enumerate(
                selections[previous_count : previous_count + additional_draws], start=1
            ):
                selection_number = previous_count + offset
                if pick < 1 or pick > domain_size:
                    print(
                        f"⚠️  Selection out of range for contest '{contest_name}' "
                        f"round {round_num}: pick {pick} > domain {domain_size}"
                    )
                    continue
                county_name, tabulator, batch, position = combined_manifest[pick - 1]
                canonical_county = normalize_county_name(county_name)
                imprinted = ballot_to_imprinted_id(
                    canonical_county.replace(" ", ""), tabulator, batch, position
                )
                record = {
                    "county": canonical_county,
                    "imprinted_id": imprinted,
                    "contest_name": contest_name,
                    "round": str(round_num),
                    "selection": str(selection_number),
                }
                reconstructed_rows.append(record)
                produced_pairs[(canonical_county, imprinted)].append(record)

            processed_counts[contest_id] = declared_count

    # Ensure every ballot seen in contestComparison is represented at least once
    all_pairs = [
        (
            normalize_county_name(county_lookup.get(row["county_id"], "")),
            row["imprinted_id"],
        )
        for row in cur.execute(
            """
            SELECT DISTINCT county_id, imprinted_id
            FROM ballot_comparisons
            WHERE imprinted_id IS NOT NULL
            """
        )
    ]

    for county_name, imprinted in all_pairs:
        if not county_name or not imprinted:
            continue
        if (county_name, imprinted) not in produced_pairs:
            reconstructed_rows.append(
                {
                    "county": county_name,
                    "imprinted_id": imprinted,
                    "contest_name": "",
                    "round": "",
                    "selection": "",
                }
            )

    conn.close()

    reconstructed_rows.sort(
        key=lambda row: (
            row["county"],
            row["imprinted_id"],
            row["round"] or "",
            row["selection"] or "",
        )
    )

    output_csv = analysis_dir / "reconstructed_targeted_selections.csv"
    with output_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["county", "imprinted_id", "contest_name", "round", "selection"]
        )
        writer.writeheader()
        for row in reconstructed_rows:
            writer.writerow(row)

    summary = {
        "total_rows": len(reconstructed_rows),
        "targeted_rows": sum(1 for row in reconstructed_rows if row["contest_name"]),
        "unmatched_rows": sum(1 for row in reconstructed_rows if not row["contest_name"]),
        "unique_pairs": len({(row["county"], row["imprinted_id"]) for row in reconstructed_rows}),
    }

    summary_path = analysis_dir / "reconstructed_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))

    print(f"Wrote reconstructed selections to {output_csv}")
    print(f"Summary written to {summary_path}")


if __name__ == "__main__":
    main()
