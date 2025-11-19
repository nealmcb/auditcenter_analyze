#!/usr/bin/env python3
"""
Generate observer summary for La Plata County audit.

Sorts first 60 selections by location, scanner, batch, record ID,
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
            batch = row.get("Batch ID", "").strip()
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


def main():
    selections_file = Path("la_plata_selections.csv")
    manifest_file = Path("data/2025/files/LaPlataManifest.csv")
    cvr_file = Path("/srv/voting/audit/corla/2025/laplata/cvr/laplata-Modified_CVR_Export_20251113162556.csv")
    output_file = Path("la_plata_observer_summary.txt")
    
    # Load first 60 selections
    selections = []
    with open(selections_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 60:
                break
            selections.append(row["imprinted_id"])
    
    # Load manifest locations
    locations = load_manifest_locations(manifest_file)
    
    # Load CVR data
    print("Loading CVR data...")
    cvr_data = load_cvr_data(cvr_file)
    
    # Build sortable list with location info
    sortable = []
    for imprinted_id in selections:
        tabulator, batch, record = parse_imprinted_id(imprinted_id)
        location = locations.get((tabulator, batch), "")
        sortable.append({
            "imprinted_id": imprinted_id,
            "location": location,
            "tabulator": int(tabulator) if tabulator.isdigit() else 0,
            "batch": int(batch) if batch.isdigit() else 0,
            "record": int(record) if record.isdigit() else 0,
        })
    
    # Sort by location (natural order), tabulator, batch, record
    sortable.sort(key=lambda x: (
        natural_sort_key(x["location"]),
        x["tabulator"],
        x["batch"],
        x["record"]
    ))
    
    # Generate output
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
                f.write(f"{contest_name}\n")
                if not choices:
                    f.write("  undervote\n")
                else:
                    for choice in choices:
                        f.write(f"  {choice}\n")
    
    print(f"✓ Generated observer summary: {output_file}")
    print(f"  Processed {len(sortable)} ballots")


if __name__ == "__main__":
    main()

