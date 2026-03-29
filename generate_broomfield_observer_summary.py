#!/usr/bin/env python3
"""
Generate observer summary for Broomfield County audit.

Sorts selections by location, scanner, batch, record ID,
then for each ballot shows contests and choices from CVR.
"""

import csv
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional


def parse_imprinted_id(imprinted_id: str) -> Tuple[str, str, str]:
    """Parse imprinted_id into tabulator, batch, record."""
    parts = imprinted_id.split("-")
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    raise ValueError(f"Invalid imprinted_id format: {imprinted_id}")


def natural_sort_key(text: str) -> List:
    """
    Generate a sort key for natural order sorting (like Java's NaturalOrderComparator).
    Splits text into alternating strings and numbers for proper numerical sorting.
    """
    def convert(text_part):
        return int(text_part) if text_part.isdigit() else text_part.lower()

    return [convert(c) for c in re.split(r'(\d+)', text)]


def load_manifest_locations(manifest_file: Path) -> Dict[Tuple[str, str], str]:
    """Load location for each (tabulator, batch) from manifest."""
    locations = {}
    with open(manifest_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tabulator = row.get("Tabulator ID", "").strip()
            # Try both "Batch ID" and "Batch" column names
            batch = row.get("Batch ID", row.get("Batch", "")).strip()
            location = row.get("Location", "").strip()
            if tabulator and batch:
                locations[(tabulator, batch)] = location
    return locations


def load_cvr_data(cvr_file: Path) -> Dict[str, Dict]:
    """Load CVR data indexed by imprinted_id."""
    cvr_data = {}

    with open(cvr_file, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()

        # Parse header rows to build column mapping
        # Row 1 (index 1, 2nd row): Contest names (with repeats)
        # Row 2 (index 2, 3rd row): Choices/candidates
        # Row 3 (index 3, 4th row): Party info (for primaries) - we ignore this
        # Use csv.reader to properly handle quoted fields
        row1_reader = csv.reader([lines[1]])
        row2_reader = csv.reader([lines[2]])
        row1 = next(row1_reader)
        row2 = next(row2_reader)
        # Strip whitespace and quotes
        row1 = [x.strip().strip('"') for x in row1]
        row2 = [x.strip().strip('"') for x in row2]

        # Build mapping: column_index -> (contest_name, candidate_name)
        # Contest names in row1 may repeat - each column has its own contest name
        # We use the exact contest name from each column
        column_map = {}  # col_idx -> (contest, candidate)

        # First 7 columns are metadata (CvrNumber, TabulatorNum, etc.)
        for i in range(7, max(len(row1), len(row2))):
            contest_name = row1[i] if i < len(row1) else ""
            candidate_name = row2[i] if i < len(row2) else ""

            # Only map if we have both a contest name and candidate name
            # Use the contest name from this specific column
            if contest_name and candidate_name:
                column_map[i] = (contest_name, candidate_name)

        # Group columns by contest for ordering
        contest_order = []
        seen_contests = set()
        for i in range(7, max(len(row1), len(row2))):
            if i in column_map:
                contest, _ = column_map[i]
                if contest not in seen_contests:
                    contest_order.append(contest)
                    seen_contests.add(contest)

        # Now read the actual CVR data (starting at row 4, index 3)
        # Use csv.reader to properly handle quoted fields
        for line in lines[4:]:
            row_reader = csv.reader([line])
            row_values = next(row_reader)
            row_values = [x.strip().strip('"') for x in row_values]

            if len(row_values) < 5:
                continue

            imprinted_id = row_values[4] if len(row_values) > 4 else ""
            if not imprinted_id:
                continue

            tabulator = row_values[1] if len(row_values) > 1 else ""
            batch = row_values[2] if len(row_values) > 2 else ""
            record = row_values[3] if len(row_values) > 3 else ""

            # Extract contest choices
            contest_choices = defaultdict(list)  # contest -> [choices]
            contest_on_ballot = set()  # contests that appear on this ballot

            for col_idx, (contest, candidate) in column_map.items():
                if col_idx < len(row_values):
                    value = row_values[col_idx]
                    if value == "1":
                        contest_choices[contest].append(candidate)
                        contest_on_ballot.add(contest)
                    elif value == "0":
                        # Contest appears on ballot but no mark for this candidate
                        contest_on_ballot.add(contest)

            # Build contests list in order, only including contests on the ballot
            contests = []
            for contest in contest_order:
                if contest in contest_on_ballot:
                    choices = contest_choices.get(contest, [])
                    contests.append((contest, choices))

            cvr_data[imprinted_id] = {
                "tabulator": tabulator,
                "batch": batch,
                "record": record,
                "contests": contests,
            }

    return cvr_data


def load_pull_list(pull_list_file: Path) -> List[str]:
    """Load imprinted IDs from the pull list text file."""
    selections = []
    with open(pull_list_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines, header lines, separator lines
            if not line or line.startswith("=") or line.startswith("-") or ":" in line:
                continue
            # Check if line starts with a digit (imprinted ID pattern)
            if re.match(r'^\d', line):
                # Split on whitespace and extract all imprinted IDs from the line
                ids = line.split()
                for id_str in ids:
                    # Validate format: XXX-XXX-XX
                    if re.match(r'^\d+-\d+-\d+$', id_str):
                        selections.append(id_str)
    return selections


def main():
    pull_list_file = Path("broomfield_pull_list.txt")
    manifest_file = Path("data/2025/files/BroomfieldManifest.csv")
    cvr_file = Path("/srv/voting/audit/corla/scrapy/mirror/2025/cvrs/broomfield-Redacted_CVR_Export_20251119093616.csv")
    output_file = Path("broomfield_observer_summary.txt")

    # Load selections from pull list
    print("Loading pull list...")
    selections = load_pull_list(pull_list_file)
    print(f"  Found {len(selections)} ballot selections")

    # Load manifest locations
    print("Loading manifest locations...")
    locations = load_manifest_locations(manifest_file)
    print(f"  Loaded {len(locations)} manifest entries")

    # Load CVR data
    print("Loading CVR data...")
    cvr_data = load_cvr_data(cvr_file)
    print(f"  Loaded {len(cvr_data)} CVR records")

    # Build sortable list with location info
    sortable = []
    for imprinted_id in selections:
        try:
            tabulator, batch, record = parse_imprinted_id(imprinted_id)
            location = locations.get((tabulator, batch), "")
            sortable.append({
                "imprinted_id": imprinted_id,
                "location": location,
                "tabulator": int(tabulator) if tabulator.isdigit() else 0,
                "batch": int(batch) if batch.isdigit() else 0,
                "record": int(record) if record.isdigit() else 0,
            })
        except ValueError as e:
            print(f"  Warning: Skipping {imprinted_id}: {e}")

    # Sort by location (natural order), tabulator, batch, record
    sortable.sort(key=lambda x: (
        natural_sort_key(x["location"]),
        x["tabulator"],
        x["batch"],
        x["record"]
    ))

    # Generate output
    print(f"Generating observer summary...")
    with open(output_file, "w", encoding="utf-8") as f:
        for item in sortable:
            imprinted_id = item["imprinted_id"]
            location = item.get("location", "")
            f.write(f"\n{'='*80}\n")
            f.write(f"Imprinted ID: {imprinted_id}")
            if location:
                f.write(f"  Location: {location}")
            f.write(f"\n{'='*80}\n\n")

            if imprinted_id not in cvr_data:
                f.write("  (CVR data not found)\n\n")
                continue

            data = cvr_data[imprinted_id]
            contests = data.get("contests", [])

            if not contests:
                f.write("  (No contests found in CVR)\n\n")
                continue

            for contest_name, choices in contests:
                # Extract Vote For number if present
                vote_for_match = re.search(r'\(Vote For=(\d+)\)', contest_name)
                if vote_for_match:
                    f.write(f"{contest_name}\n")
                else:
                    f.write(f"{contest_name} (Vote For=1)\n")

                if not choices:
                    f.write("  undervote\n")
                else:
                    for choice in choices:
                        f.write(f"  {choice}\n")

    print(f"✓ Generated observer summary: {output_file}")
    print(f"  Processed {len(sortable)} ballots")

    # Print first few imprinted IDs for verification
    print("\nFirst 10 ballots in order:")
    for i, item in enumerate(sortable[:10]):
        print(f"  {i+1}. {item['imprinted_id']} - {item['location']}")


if __name__ == "__main__":
    main()
