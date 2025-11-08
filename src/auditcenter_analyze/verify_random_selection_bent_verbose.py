#!/usr/bin/env python3
"""
Verbose verification of random ballot selection with cryptographic details.

This script shows the complete SHA-256 hashing process for transparency.
"""

import hashlib
import csv
from pathlib import Path
from typing import List, Tuple


def generate_random_numbers_verbose(
    seed: str, count: int, domain_size: int, show_details: int = 5
) -> List[int]:
    """
    Generate pseudo-random numbers with verbose output showing hash details.

    Args:
        seed: Random seed (minimum 20 digits)
        count: Number of random numbers to generate
        domain_size: Size of the domain (max value)
        show_details: Number of selections to show detailed hash information for

    Returns:
        List of random numbers in range [1, domain_size]
    """
    selections = []
    i = 0

    print(f"Generating {count} random selections from domain size {domain_size}")
    print(f"Using seed: {seed}")
    print()
    print("Cryptographic Details for First {} Selections:".format(show_details))
    print("=" * 100)

    while len(selections) < count:
        i += 1
        # Hash input: seed + "," + count
        hash_input = f"{seed},{i}"
        hash_output = hashlib.sha256(hash_input.encode("utf-8")).digest()

        # Convert hash to integer
        int_output = int.from_bytes(hash_output, byteorder="big")

        # Map to range [1, domain_size] (1-indexed)
        pick = (int_output % domain_size) + 1

        # Show details for first few
        if i <= show_details:
            hash_hex = hash_output.hex()
            print(f"\nSelection #{i}:")
            print(f"  Input:      '{hash_input}'")
            print(f"  SHA-256:    {hash_hex}")
            print(f"  As Integer: {int_output}")
            print(f"  Modulo:     {int_output} mod {domain_size} = {int_output % domain_size}")
            print(f"  Result:     {pick} (add 1 for 1-indexing)")

        # With replacement: always add (duplicates possible)
        selections.append(pick)

    if show_details < count:
        print(f"\n... (remaining {count - show_details} selections calculated)")

    print("\n" + "=" * 100)
    print()

    return selections


def load_ballot_manifest(manifest_file: str) -> List[Tuple[str, str, str, int]]:
    """Load ballot manifest and create index mapping."""
    ballots = []

    with open(manifest_file, "r", encoding="utf-8-sig") as f:  # utf-8-sig handles BOM
        reader = csv.DictReader(f)
        for row in reader:
            county = row["County"]
            tabulator = row["Tabulator ID"]
            batch = row["Batch"]
            num_cards = int(row["# of Ballot Cards"])

            # Each batch contributes num_cards ballot positions
            for position in range(1, num_cards + 1):
                ballots.append((county, tabulator, batch, position))

    return ballots


def ballot_to_imprinted_id(county: str, tabulator: str, batch: str, position: int) -> str:
    """Convert ballot tuple to imprinted_id format."""
    return f"{tabulator}-{batch}-{position}"


def main():
    # Configuration
    SEED = "53417960661093690826"
    BALLOT_CARD_COUNT = 2221
    SAMPLE_SIZE = 5  # Just show first 5 for verbose output

    # Use data symlink relative to this file location
    data_dir = Path(__file__).parent.parent.parent / "data" / "2024" / "general"
    MANIFEST_FILE = data_dir / "BentBallotManifest.csv"

    print("=" * 100)
    print("CRYPTOGRAPHIC VERIFICATION OF RANDOM BALLOT SELECTION")
    print("2024 General Election Audit - Bent County Commissioner-District 1")
    print("=" * 100)
    print()

    # Generate random selections with full cryptographic details
    random_selections = generate_random_numbers_verbose(
        SEED, SAMPLE_SIZE, BALLOT_CARD_COUNT, show_details=5
    )

    # Load ballot manifest
    print("Loading ballot manifest...")
    ballot_manifest = load_ballot_manifest(MANIFEST_FILE)
    print(f"✓ Loaded {len(ballot_manifest)} ballot cards")
    print()

    # Map to actual ballots
    print("Mapping random numbers to physical ballots:")
    print("=" * 100)
    for i, selection in enumerate(random_selections, 1):
        county, tabulator, batch, position = ballot_manifest[selection - 1]
        imprinted_id = ballot_to_imprinted_id(county, tabulator, batch, position)
        print(f"  Selection {i}: Random #{selection:4d} -> Ballot {imprinted_id}")
        print(f"              (Batch {batch}, Position {position} in batch)")

    print("\n" + "=" * 100)
    print()
    print("This demonstrates transparency of the random selection process:")
    print("  1. Anyone can verify the SHA-256 hashes")
    print("  2. The seed (53417960661093690826) was publicly committed before the audit")
    print("  3. The process is deterministic - same seed always produces same results")
    print("  4. The process is cryptographically secure - cannot be manipulated")
    print()
    print("IMPORTANT ASSUMPTION:")
    print("  This verification assumes the ballot manifest was provided BEFORE the random")
    print("  seed was generated. This is critical for audit integrity - the seed must be")
    print("  generated after manifests are locked in, to prevent manipulation of the")
    print("  manifest to favor specific ballot selections.")
    print()


if __name__ == "__main__":
    main()
