#!/usr/bin/env python3
"""
Generate the first 80 ballot card selections for La Plata County 2025 audit.

Uses the provided seed to generate selections from first principles.
"""

import csv
import hashlib
from pathlib import Path
from typing import Optional


def generate_random_numbers(seed: str, count: int, domain_size: int) -> list[int]:
    """
    Generate pseudo-random numbers using SHA-256.

    Based on: us.freeandfair.corla.crypto.PseudoRandomNumberGenerator
    """
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


def load_ballot_manifest(manifest_file: Path) -> list[tuple[str, str, str, int]]:
    """Load ballot manifest and create index mapping."""
    ballots: list[tuple[str, str, str, int]] = []

    with open(manifest_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        
        # Find columns with flexible matching
        def find_col(candidates: list[str]) -> Optional[str]:
            normalized_map = {col.lower().replace(" ", "").replace("#", ""): col for col in fieldnames if col}
            for candidate in candidates:
                key = candidate.lower().replace(" ", "").replace("#", "")
                if key in normalized_map:
                    return normalized_map[key]
            return None

        count_col = find_col(["# of Ballot Cards", "# of ballot cards", "Number of Ballots", "Ballot Cards"])
        if not count_col:
            raise ValueError(f"Could not find ballot count column. Columns: {fieldnames}")

        county_col = find_col(["County", "county"])
        tabulator_col = find_col(["Tabulator ID", "Tabulator", "Scanner ID", "Device ID"])
        batch_col = find_col(["Batch ID", "Batch", "Batch Number", "Batch #"])

        if not county_col or not tabulator_col or not batch_col:
            raise ValueError(f"Missing required columns. Found: {fieldnames}")

        for row in reader:
            try:
                num_cards = int(row[count_col])
            except (TypeError, ValueError):
                continue

            county = row.get(county_col, "").strip()
            tabulator = row.get(tabulator_col, "").strip()
            batch = row.get(batch_col, "").strip()

            for position in range(1, num_cards + 1):
                ballots.append((county, tabulator, batch, position))

    return ballots


def ballot_to_imprinted_id(tabulator: str, batch: str, position: int) -> str:
    """Convert ballot tuple to imprinted_id format."""
    return f"{tabulator}-{batch}-{position}"


def main():
    SEED = "54023377576816319259"
    COUNTY_NAME = "La Plata"
    SAMPLE_SIZE = 80

    # Paths
    data_dir = Path(__file__).parent / "data" / "2025" / "files"
    manifest_file = data_dir / "LaPlataManifest.csv"
    output_file = Path(__file__).parent / "la_plata_selections.csv"

    print(f"Loading manifest: {manifest_file}")
    ballot_manifest = load_ballot_manifest(manifest_file)
    domain_size = len(ballot_manifest)
    print(f"✓ Loaded {domain_size:,} ballot cards from manifest")

    print(f"\nGenerating {SAMPLE_SIZE} random selections using seed: {SEED}")
    random_selections = generate_random_numbers(SEED, SAMPLE_SIZE, domain_size)
    print("✓ Generated selections")

    print(f"\nWriting results to: {output_file}")
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["sequence", "county_name", "imprinted_id"])

        for i, selection in enumerate(random_selections, 1):
            if selection > len(ballot_manifest):
                raise ValueError(f"Selection {selection} exceeds manifest size {len(ballot_manifest)}")

            county_name, tabulator, batch, position = ballot_manifest[selection - 1]
            imprinted_id = ballot_to_imprinted_id(tabulator, batch, position)
            writer.writerow([i, COUNTY_NAME, imprinted_id])

    print(f"✓ Wrote {SAMPLE_SIZE} selections to {output_file}")


if __name__ == "__main__":
    main()

