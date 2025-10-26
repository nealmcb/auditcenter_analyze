#!/usr/bin/env python3
"""
Verify random ballot selection for 2024 General Election audit.

This script verifies that the imprinted_id values in the contest comparison
reflect the ballot cards that should have been selected based on the random seed.

Test case: Bent County Commissioner-District 1
"""

import hashlib
import csv
from typing import List, Tuple


def generate_random_numbers(seed: str, count: int, domain_size: int) -> List[int]:
    """
    Generate pseudo-random numbers using SHA-256.
    
    This implements the algorithm from:
    server/eclipse-project/src/main/java/us/freeandfair/corla/crypto/PseudoRandomNumberGenerator.java
    
    Args:
        seed: Random seed (minimum 20 digits)
        count: Number of random numbers to generate
        domain_size: Size of the domain (max value)
        
    Returns:
        List of random numbers in range [1, domain_size]
    """
    selections = []
    i = 0
    
    print(f"Generating {count} random selections from domain size {domain_size}")
    print(f"Using seed: {seed}")
    print()
    
    while len(selections) < count:
        i += 1
        # Hash input: seed + "," + count
        hash_input = f"{seed},{i}"
        hash_output = hashlib.sha256(hash_input.encode('utf-8')).digest()
        
        # Convert hash to integer
        int_output = int.from_bytes(hash_output, byteorder='big')
        
        # Map to range [1, domain_size] (1-indexed)
        pick = (int_output % domain_size) + 1
        
        # With replacement: always add (duplicates possible)
        selections.append(pick)
        
    return selections


def load_ballot_manifest(manifest_file: str) -> List[Tuple[str, str, str, int]]:
    """
    Load ballot manifest and create index mapping.
    
    Args:
        manifest_file: Path to ballot manifest CSV
        
    Returns:
        List of (county, tabulator, batch, position) tuples indexed from 1
    """
    ballots = []
    
    with open(manifest_file, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
        reader = csv.DictReader(f)
        for row in reader:
            county = row['County']
            tabulator = row['Tabulator ID']
            batch = row['Batch']
            num_cards = int(row['# of Ballot Cards'])
            
            # Each batch contributes num_cards ballot positions
            for position in range(1, num_cards + 1):
                ballots.append((county, tabulator, batch, position))
    
    return ballots


def ballot_to_imprinted_id(county: str, tabulator: str, batch: str, position: int) -> str:
    """
    Convert ballot tuple to imprinted_id format.
    
    Format: tabulator-batch-position
    """
    return f"{tabulator}-{batch}-{position}"


def load_actual_selections(comparison_file: str, contest_name: str) -> List[str]:
    """
    Load actual ballot selections from contest comparison file.
    
    Args:
        comparison_file: Path to contestComparison.csv
        contest_name: Name of contest to filter
        
    Returns:
        List of imprinted_id values
    """
    selections = []
    
    with open(comparison_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['contest_name'] == contest_name:
                selections.append(row['imprinted_id'])
    
    return selections


def main():
    # Configuration for Bent County Commissioner-District 1
    SEED = "53417960661093690826"
    CONTEST_NAME = "Bent County Commissioner-District 1"
    BALLOT_CARD_COUNT = 2221
    SAMPLE_SIZE = 32  # Changed to 32 to match actual audit (went to round 2)
    
    MANIFEST_FILE = "/srv/s/electionaudits/colorado-rla-2018/neal_ignore/auditcenter-2024g/BentBallotManifest.csv"
    COMPARISON_FILE = "/srv/s/electionaudits/colorado-rla-2018/neal_ignore/auditcenter-2024g/round2/contestComparison.csv"
    
    print("=" * 80)
    print("RANDOM BALLOT SELECTION VERIFICATION")
    print("2024 General Election Audit")
    print("=" * 80)
    print()
    print(f"Contest: {CONTEST_NAME}")
    print(f"Ballot Card Count: {BALLOT_CARD_COUNT}")
    print(f"Sample Size: {SAMPLE_SIZE}")
    print()
    
    # Step 1: Generate random selections
    print("STEP 1: Generating random selections")
    print("-" * 80)
    random_selections = generate_random_numbers(SEED, SAMPLE_SIZE, BALLOT_CARD_COUNT)
    print(f"Generated {len(random_selections)} selections")
    print(f"First 10 selections: {random_selections[:10]}")
    print()
    
    # Step 2: Load ballot manifest
    print("STEP 2: Loading ballot manifest")
    print("-" * 80)
    ballot_manifest = load_ballot_manifest(MANIFEST_FILE)
    print(f"Loaded {len(ballot_manifest)} ballot cards from manifest")
    
    if len(ballot_manifest) != BALLOT_CARD_COUNT:
        print(f"WARNING: Manifest has {len(ballot_manifest)} cards, expected {BALLOT_CARD_COUNT}")
    else:
        print("✓ Manifest size matches ballot_card_count")
    print()
    
    # Step 3: Map random numbers to imprinted IDs
    print("STEP 3: Mapping random selections to ballot cards")
    print("-" * 80)
    expected_imprinted_ids = []
    
    for i, selection in enumerate(random_selections, 1):
        # selection is 1-indexed, list is 0-indexed
        county, tabulator, batch, position = ballot_manifest[selection - 1]
        imprinted_id = ballot_to_imprinted_id(county, tabulator, batch, position)
        expected_imprinted_ids.append(imprinted_id)
        
        if i <= 10 or i == len(random_selections):  # Show first 10 and last one
            print(f"  Selection {i:2d}: Random #{selection:4d} -> {imprinted_id}")
        elif i == 11:
            print(f"  ... ({len(random_selections) - 11} more) ...")
    print()
    
    # Step 4: Load actual selections from audit
    print("STEP 4: Loading actual audit selections")
    print("-" * 80)
    actual_imprinted_ids = load_actual_selections(COMPARISON_FILE, CONTEST_NAME)
    print(f"Loaded {len(actual_imprinted_ids)} actual selections from audit")
    print(f"First 10 actual: {actual_imprinted_ids[:10]}")
    print()
    
    # Step 5: Compare expected vs actual
    print("STEP 5: Verification Results")
    print("=" * 80)
    
    # Sort both lists for comparison
    expected_sorted = sorted(expected_imprinted_ids)
    actual_sorted = sorted(actual_imprinted_ids)
    
    if expected_sorted == actual_sorted:
        print("✓✓✓ VERIFICATION SUCCESSFUL ✓✓✓")
        print()
        print("The random ballot selection matches perfectly!")
        print(f"All {len(expected_sorted)} ballots were correctly selected based on seed {SEED}")
        print()
        print("Note: This contest required 32 ballots across 2 rounds to achieve the risk limit.")
        print("      Initial estimate was 31, but one additional ballot was needed.")
        print()
        print("IMPORTANT ASSUMPTION:")
        print("      This verification assumes the ballot manifest was provided BEFORE the")
        print("      random seed was generated, which is critical for audit integrity.")
        return True
    else:
        print("✗✗✗ VERIFICATION FAILED ✗✗✗")
        print()
        print("Mismatch between expected and actual selections")
        
        # Find differences
        expected_set = set(expected_sorted)
        actual_set = set(actual_sorted)
        
        missing = expected_set - actual_set
        extra = actual_set - expected_set
        
        if missing:
            print(f"\nExpected but NOT in audit ({len(missing)}):")
            for ballot in sorted(missing):
                print(f"  - {ballot}")
        
        if extra:
            print(f"\nIn audit but NOT expected ({len(extra)}):")
            for ballot in sorted(extra):
                print(f"  + {ballot}")
        
        print("\nDetailed comparison:")
        print(f"Expected: {expected_sorted}")
        print(f"Actual:   {actual_sorted}")
        
        return False
    
    print()


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)

