#!/usr/bin/env python3
"""
Generate per-county pull lists for targeted contests.

Given a county name, this script enumerates every ballot card (imprinted ID)
that will be drawn for targeted contests in that county, sorted in the order
an audit board will receive them (location, tabulator, batch, position).
The output is a plain-text file with multiple columns for easy printing.
"""

from __future__ import annotations

import csv
import hashlib
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import typer

DATA_ROOT = Path("data/2025")
CONTEST_FILE = DATA_ROOT / "round1" / "contest.csv"
SELECTION_FILE = DATA_ROOT / "round1" / "contestSelection.csv"
SEED = "54023377576816319259"  # 2025 audit seed
DEFAULT_COLUMNS = 3

app = typer.Typer(help=__doc__)


def natural_sort_key(text: str) -> List:
    """Create a key for natural (human-friendly) sorting."""

    def convert(part: str):
        return int(part) if part.isdigit() else part.lower()

    return [convert(chunk) for chunk in re.split(r"(\d+)", text)]


def normalize_county(name: str) -> str:
    """Normalize county names for comparison."""
    return re.sub(r"\s+", " ", name.strip()).lower()


def resolve_manifest_path(county: str) -> Path:
    """Find the manifest CSV for a county."""
    base = DATA_ROOT / "files"
    candidates = [
        f"{county}Manifest.csv",
        f"{county.replace(' ', '')}Manifest.csv",
        f"{county.replace(' ', '_')}Manifest.csv",
        f"{county.replace(' ', '-')}Manifest.csv",
    ]
    for candidate in candidates:
        path = base / candidate
        if path.exists():
            return path
    raise FileNotFoundError(f"Could not find manifest for county '{county}'")


def find_column(fieldnames: Sequence[str], candidates: Iterable[str]) -> Optional[str]:
    """Return first matching column name from candidates (case-insensitive)."""
    normalized = {name.lower(): name for name in fieldnames}
    for candidate in candidates:
        if candidate.lower() in normalized:
            return normalized[candidate.lower()]
    return None


def load_manifest_entries(manifest_path: Path) -> Dict[str, Dict[str, str]]:
    """
    Load manifest entries keyed by imprinted_id.

    Returns mapping of imprinted_id -> dict with location, tabulator, batch, position.
    """
    entries: Dict[str, Dict[str, str]] = {}

    with manifest_path.open("r", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []

        county_col = find_column(fieldnames, ["County"])
        tabulator_col = find_column(fieldnames, ["Tabulator ID", "Tabulator"])
        batch_col = find_column(fieldnames, ["Batch ID", "Batch", "Batch Number"])
        count_col = find_column(
            fieldnames,
            [
                "# of Ballot Cards",
                "# of ballot cards",
                "# of Ballots",
                "# ballots",
                "# cards",
                "Number of Ballots",
            ],
        )

        if not all([county_col, tabulator_col, batch_col, count_col]):
            raise ValueError(
                f"Manifest {manifest_path} missing required columns. Found: {fieldnames}"
            )

        for row in reader:
            tabulator = row.get(tabulator_col, "").strip()
            batch = row.get(batch_col, "").strip()
            try:
                card_count = int(row.get(count_col, "0"))
            except ValueError:
                continue

            location = row.get("Location", "").strip()

            for position in range(1, card_count + 1):
                imprinted_id = f"{tabulator}-{batch}-{position}"
                entries[imprinted_id] = {
                    "location": location,
                    "tabulator": tabulator,
                    "batch": batch,
                    "position": str(position),
                }

    return entries


def load_contest_types() -> Dict[str, str]:
    """Load contest names and their audit_reason types."""
    contest_types = {}
    if not CONTEST_FILE.exists():
        return contest_types
    
    with CONTEST_FILE.open("r", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            contest_name = row.get("contest_name", "").strip()
            audit_reason = row.get("audit_reason", "").strip()
            if contest_name and audit_reason:
                contest_types[contest_name] = audit_reason
    
    return contest_types


def generate_random_numbers(seed: str, count: int, domain_size: int) -> List[int]:
    """Generate pseudo-random numbers using SHA-256."""
    selections = []
    i = 0
    while len(selections) < count:
        i += 1
        hash_input = f"{seed},{i}"
        hash_output = hashlib.sha256(hash_input.encode("utf-8")).digest()
        int_output = int.from_bytes(hash_output, byteorder="big")
        pick = (int_output % domain_size) + 1
        selections.append(pick)
    return selections


def load_ballot_manifest_from_file(manifest_file: Path) -> List[Tuple[str, str, str, int]]:
    """Load ballot manifest and return list of (county, tabulator, batch, position)."""
    ballots: List[Tuple[str, str, str, int]] = []
    
    with manifest_file.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        
        def find_col(candidates: List[str]) -> Optional[str]:
            normalized_map = {col.lower().replace(" ", "").replace("#", ""): col 
                             for col in fieldnames if col}
            for candidate in candidates:
                key = candidate.lower().replace(" ", "").replace("#", "")
                if key in normalized_map:
                    return normalized_map[key]
            return None
        
        county_col = find_col(["County", "county"]) or fieldnames[0]
        tabulator_col = find_col(["Tabulator ID", "Tabulator", "Scanner ID", "Device ID"]) or fieldnames[1]
        batch_col = find_col(["Batch ID", "Batch", "Batch Number", "Batch #"]) or fieldnames[2]
        count_col = find_col(["# of Ballot Cards", "# of ballot cards", "# of Ballots", 
                             "Number of Ballots", "# Ballot Cards"]) or fieldnames[3]
        
        for row in reader:
            try:
                num_cards = int(row.get(count_col, "0") or "0")
            except (TypeError, ValueError):
                continue
            
            county = row.get(county_col, "").strip()
            tabulator = row.get(tabulator_col, "").strip()
            batch = row.get(batch_col, "").strip()
            
            for position in range(1, num_cards + 1):
                ballots.append((county, tabulator, batch, position))
    
    return ballots


def ballot_to_imprinted_id(tabulator: str, batch: str, position: int) -> str:
    """Convert to imprinted_id format."""
    return f"{tabulator}-{batch}-{position}"


def load_targeted_imprinted_ids(
    county: str, contest_types: Dict[str, str], manifest_path: Path
) -> Tuple[List[str], List[str]]:
    """
    Generate targeted imprinted IDs for a county from first principles.
    Returns: (county_wide_ids, statewide_ids)
    """
    normalized = normalize_county(county)
    county_wide_ids: List[str] = []
    statewide_ids: List[str] = []
    
    # Load manifest
    manifest = load_ballot_manifest_from_file(manifest_path)
    domain_size = len(manifest)
    
    # Load contests for this county from contestsByCounty.csv
    county_contests = []
    contests_by_county = DATA_ROOT / "contestsByCounty.csv"
    if contests_by_county.exists():
        with contests_by_county.open("r", encoding="utf-8-sig") as cf:
            cbc_reader = csv.DictReader(cf)
            for cbc_row in cbc_reader:
                cbc_county = cbc_row.get("county_name", "").strip()
                contest_name = cbc_row.get("contest_name", "").strip()
                
                if normalize_county(cbc_county) != normalized:
                    continue
                
                # Get contest details from contest.csv
                audit_reason = contest_types.get(contest_name, "")
                if audit_reason in ("county_wide_contest", "state_wide_contest"):
                    # Get sample count from contestSelection.csv (more reliable than contest.csv)
                    sample_count = 0
                    if SELECTION_FILE.exists():
                        with SELECTION_FILE.open("r", encoding="utf-8-sig") as handle:
                            sel_reader = csv.DictReader(handle)
                            for sel_row in sel_reader:
                                if sel_row.get("contest_name", "").strip() == contest_name:
                                    cvr_ids_str = sel_row.get("contest_cvr_ids", "").strip()
                                    if cvr_ids_str and cvr_ids_str != "[]":
                                        # Parse CVR IDs to get count
                                        cvr_ids = [x.strip() for x in cvr_ids_str.strip("[]").split(",") 
                                                  if x.strip()]
                                        sample_count = len(cvr_ids)
                                    break
                    
                    # Fall back to contest.csv if no selection data
                    if sample_count == 0:
                        with CONTEST_FILE.open("r", encoding="utf-8-sig") as handle:
                            contest_reader = csv.DictReader(handle)
                            for contest_row in contest_reader:
                                if contest_row.get("contest_name", "").strip() == contest_name:
                                    sample_count = int(contest_row.get("audited_sample_count", "0") or "0")
                                    break
                    
                    if sample_count > 0:
                        county_contests.append((contest_name, audit_reason, sample_count))
    
    # Generate selections for each county-wide contest
    # Note: For county-wide contests, selections are from this county's manifest only
    # Selections are sequential across contests (each contest continues the sequence)
    county_wide_set = set()
    running_index = 0  # Track cumulative selection index across all contests
    
    for contest_name, audit_reason, sample_count in county_contests:
        if audit_reason == "county_wide_contest":
            # Generate selections starting from the next index
            selections = []
            for i in range(sample_count):
                running_index += 1
                hash_input = f"{SEED},{running_index}"
                hash_output = hashlib.sha256(hash_input.encode("utf-8")).digest()
                int_output = int.from_bytes(hash_output, byteorder="big")
                pick = (int_output % domain_size) + 1
                selections.append(pick)
            
            for pick in selections:
                if 1 <= pick <= domain_size:
                    county_name, tabulator, batch, position = manifest[pick - 1]
                    imprinted_id = ballot_to_imprinted_id(tabulator, batch, position)
                    county_wide_set.add(imprinted_id)
    
    county_wide_ids = list(county_wide_set)
        # For statewide contests, we can't generate from single county manifest
        # They're drawn from all counties combined, so we'll estimate separately
    
    # For statewide contests, we need to estimate based on proportion
    # This is a rough estimate - actual selections come from combined statewide manifest
    statewide_contests = [(name, reason, count) for name, reason, count in county_contests 
                         if reason == "state_wide_contest"]
    statewide_set = set()
    if statewide_contests:
        # Estimate: assume selections are proportional to county size
        # This is just a guess - actual selections require combined manifest
        # Rough estimate: county gets samples proportional to its ballot card count
        # This is very approximate
        for contest_name, _, sample_count in statewide_contests:
            # Very rough estimate - would need full statewide manifest to be accurate
            # Using a rough estimate of 2M total ballot cards statewide
            estimated_for_county = max(1, int(sample_count * domain_size / 2000000))  # rough estimate
            selections = generate_random_numbers(SEED, estimated_for_county, domain_size)
            for pick in selections:
                if 1 <= pick <= domain_size:
                    county_name, tabulator, batch, position = manifest[pick - 1]
                    imprinted_id = ballot_to_imprinted_id(tabulator, batch, position)
                    statewide_set.add(imprinted_id)
    
    statewide_ids = list(statewide_set)
    
    return county_wide_ids, statewide_ids


def format_columns(values: Sequence[str], columns: int) -> List[str]:
    """Return rows of text with values arranged in multiple columns."""
    if columns <= 0:
        columns = 1

    total = len(values)
    rows = math.ceil(total / columns)
    padded = values + [""] * (rows * columns - total)

    lines: List[str] = []
    for row_idx in range(rows):
        parts = []
        for col in range(columns):
            idx = row_idx + col * rows
            value = padded[idx]
            parts.append(value.ljust(20))
        lines.append("  ".join(parts).rstrip())
    return lines


@app.command()
def main(
    county: str = typer.Argument(..., help="County name (e.g., 'Boulder')"),
    columns: int = typer.Option(
        DEFAULT_COLUMNS, "--columns", "-c", help="Number of columns in output"
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output text file (default: <county>_pull_list.txt)",
    ),
) -> None:
    """Generate the multi-column pull list for a county."""
    county_clean = county.strip()
    manifest_path = resolve_manifest_path(county_clean)
    manifest_entries = load_manifest_entries(manifest_path)
    contest_types = load_contest_types()
    county_wide_ids, statewide_ids = load_targeted_imprinted_ids(
        county_clean, contest_types, manifest_path
    )

    def process_ids(ids: List[str]) -> Tuple[List[str], List[str]]:
        """Process a list of IDs and return (sorted_ids, missing_ids)."""
        records = []
        missing = []
        for imprinted in ids:
            entry = manifest_entries.get(imprinted)
            if not entry:
                missing.append(imprinted)
                continue
            records.append(
                (
                    entry["location"],
                    entry["tabulator"],
                    entry["batch"],
                    int(entry["position"]),
                    imprinted,
                )
            )

        # Sort in the order audit boards will see them
        records.sort(
            key=lambda rec: (
                natural_sort_key(rec[0]),
                int(rec[1]) if rec[1].isdigit() else rec[1],
                int(rec[2]) if rec[2].isdigit() else rec[2],
                rec[3],
            )
        )

        return [rec[4] for rec in records], missing

    # Process county-wide targets
    county_wide_sorted, county_wide_missing = process_ids(county_wide_ids)
    
    # Process statewide targets (estimate)
    statewide_sorted, statewide_missing = process_ids(statewide_ids)

    all_missing = county_wide_missing + statewide_missing
    if all_missing:
        typer.echo(
            f"⚠️  Warning: {len(all_missing)} imprinted IDs were not found in the manifest "
            f"for {county_clean}. They will be omitted.",
            err=True,
        )

    if output is None:
        safe_name = county_clean.lower().replace(" ", "_")
        output = Path(f"{safe_name}_pull_list.txt")

    with output.open("w", encoding="utf-8") as handle:
        handle.write(f"{county_clean} County Targeted Pull List\n")
        handle.write("=" * 80 + "\n\n")
        
        # County-wide targets section
        handle.write("COUNTY-WIDE TARGETED CONTESTS\n")
        handle.write("-" * 80 + "\n")
        handle.write(f"Total ballot cards: {len(county_wide_sorted)}\n\n")
        if county_wide_sorted:
            lines = format_columns(county_wide_sorted, columns)
            for line in lines:
                handle.write(line + "\n")
        else:
            handle.write("(No county-wide targeted contests)\n")
        handle.write("\n\n")
        
        # Statewide targets section (estimate)
        handle.write("STATEWIDE TARGETED CONTESTS (Estimate)\n")
        handle.write("-" * 80 + "\n")
        handle.write(
            f"Estimated ballot cards from statewide draws: {len(statewide_sorted)}\n"
        )
        handle.write(
            "(Note: Statewide selections are drawn from all counties. "
            "This is an estimate for this county only.)\n\n"
        )
        if statewide_sorted:
            lines = format_columns(statewide_sorted, columns)
            for line in lines:
                handle.write(line + "\n")
        else:
            handle.write("(No statewide targeted contests found in this county)\n")

    total = len(county_wide_sorted) + len(statewide_sorted)
    typer.echo(
        f"✓ Generated pull list for {county_clean}: {output} "
        f"({len(county_wide_sorted)} county-wide, {len(statewide_sorted)} statewide, "
        f"{total} total ballot cards)"
    )


if __name__ == "__main__":
    app()

