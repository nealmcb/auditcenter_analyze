#!/usr/bin/env python3
"""
General-purpose random ballot selection verification for 2024 General Election.

Usage:
    python3 verify_any_contest.py --contest "Contest Name" --county "County Name"
    
Or use the default (Bent County Commissioner-District 1)
"""

import hashlib
import csv
import sys
import argparse
from typing import List, Tuple, Optional


def generate_random_numbers(seed: str, count: int, domain_size: int) -> List[int]:
    """
    Generate pseudo-random numbers using SHA-256.
    
    Based on: us.freeandfair.corla.crypto.PseudoRandomNumberGenerator
    """
    selections = []
    i = 0
    
    while len(selections) < count:
        i += 1
        hash_input = f"{seed},{i}"
        hash_output = hashlib.sha256(hash_input.encode('utf-8')).digest()
        int_output = int.from_bytes(hash_output, byteorder='big')
        pick = (int_output % domain_size) + 1
        selections.append(pick)
    
    return selections


def load_ballot_manifest(manifest_file: str) -> List[Tuple[str, str, str, int]]:
    """Load ballot manifest and create index mapping."""
    ballots = []
    
    with open(manifest_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            county = row['County']
            
            # Handle different column name variations
            if 'Tabulator ID' in row:
                tabulator = row['Tabulator ID']
            elif 'Tabulator' in row:
                tabulator = row['Tabulator']
            else:
                raise ValueError(f"Could not find tabulator column in manifest")
            
            # Handle batch column variations (with or without trailing space)
            if 'Batch' in row:
                batch = row['Batch']
            elif 'Batch ' in row:
                batch = row['Batch ']
            else:
                raise ValueError(f"Could not find batch column in manifest")
            
            # Handle ballot count column variations
            if '# of Ballot Cards' in row:
                num_cards = int(row['# of Ballot Cards'])
            elif '# of Ballot' in row:
                num_cards = int(row['# of Ballot'])
            else:
                raise ValueError(f"Could not find ballot count column in manifest")
            
            for position in range(1, num_cards + 1):
                ballots.append((county, tabulator, batch, position))
    
    return ballots


def ballot_to_imprinted_id(county: str, tabulator: str, batch: str, position: int) -> str:
    """Convert ballot tuple to imprinted_id format."""
    return f"{tabulator}-{batch}-{position}"


def find_contest(contest_name: str, contest_file: str) -> Optional[dict]:
    """Find contest in contest.csv file."""
    with open(contest_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['contest_name'] == contest_name:
                return row
    return None


def load_actual_selections(comparison_file: str, contest_name: str) -> List[str]:
    """Load actual ballot selections from contest comparison file."""
    selections = []
    
    with open(comparison_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['contest_name'] == contest_name:
                selections.append(row['imprinted_id'])
    
    return selections


def verify_contest(contest_name: str, county: Optional[str] = None, 
                  base_path: str = "/srv/s/electionaudits/colorado-rla-2018/neal_ignore/auditcenter-2024g") -> bool:
    """
    Verify random ballot selection for a given contest.
    
    Args:
        contest_name: Name of the contest to verify
        county: County name (for finding manifest), can be inferred from contest name
        base_path: Base path to audit data
        
    Returns:
        True if verification successful, False otherwise
    """
    
    SEED = "53417960661093690826"
    
    print("=" * 80)
    print("RANDOM BALLOT SELECTION VERIFICATION")
    print("=" * 80)
    print(f"Contest: {contest_name}")
    if county:
        print(f"County: {county}")
    print()
    
    # Find contest in round 3, 2, or 1 (use latest available)
    contest_data = None
    round_num = None
    
    for r in [3, 2, 1]:
        contest_file = f"{base_path}/round{r}/contest.csv"
        try:
            contest_data = find_contest(contest_name, contest_file)
            if contest_data:
                round_num = r
                print(f"✓ Found contest data in round {r}")
                break
        except FileNotFoundError:
            continue
    
    if not contest_data:
        print(f"✗ ERROR: Could not find contest '{contest_name}' in any round")
        return False
    
    # Extract parameters
    ballot_card_count = int(contest_data['ballot_card_count'])
    contest_ballot_card_count = int(contest_data['contest_ballot_card_count'])
    audited_sample_count = int(contest_data['audited_sample_count'])
    status = contest_data['random_audit_status']
    
    print(f"  Status: {status}")
    print(f"  County Ballot Card Count: {ballot_card_count:,}")
    print(f"  Contest Ballot Card Count: {contest_ballot_card_count:,}")
    print(f"  Audited Sample Count: {audited_sample_count}")
    print()
    
    # Use contest_ballot_card_count for random selection domain
    domain_size = contest_ballot_card_count
    
    # Infer county from contest name if not provided
    if not county:
        # Try to extract county from contest name
        if contest_name.startswith("Adams County") or "Adams" in contest_name:
            county = "Adams"
        elif contest_name.startswith("Bent County"):
            county = "Bent"
        elif contest_name.startswith("Arapahoe County"):
            county = "Arapahoe"
        # Add more counties as needed
        else:
            print("✗ ERROR: Please specify --county parameter")
            return False
    
    # Load ballot manifest
    manifest_file = f"{base_path}/{county}BallotManifest.csv"
    try:
        print(f"Loading manifest: {manifest_file}")
        ballot_manifest = load_ballot_manifest(manifest_file)
        print(f"✓ Loaded {len(ballot_manifest):,} ballot cards from manifest")
    except FileNotFoundError:
        print(f"✗ ERROR: Could not find manifest file: {manifest_file}")
        return False
    
    if len(ballot_manifest) != ballot_card_count:
        print(f"⚠ WARNING: Manifest has {len(ballot_manifest)} cards, county reports {ballot_card_count}")
    
    if len(ballot_manifest) < contest_ballot_card_count:
        print(f"✗ ERROR: Manifest has {len(ballot_manifest)} cards but contest expects {contest_ballot_card_count}")
        return False
    print()
    
    # Generate random selections using contest domain size
    print(f"Generating {audited_sample_count} random selections from domain [1, {domain_size}]...")
    random_selections = generate_random_numbers(SEED, audited_sample_count, domain_size)
    print(f"✓ Generated selections")
    print(f"  First 5: {random_selections[:5]}")
    if audited_sample_count > 5:
        print(f"  Last:    {random_selections[-1]}")
    print()
    
    # Map to imprinted IDs
    print("Mapping to ballot cards...")
    expected_imprinted_ids = []
    
    for selection in random_selections:
        if selection > len(ballot_manifest):
            print(f"✗ ERROR: Selection {selection} exceeds manifest size {len(ballot_manifest)}")
            return False
        
        county_name, tabulator, batch, position = ballot_manifest[selection - 1]
        imprinted_id = ballot_to_imprinted_id(county_name, tabulator, batch, position)
        expected_imprinted_ids.append(imprinted_id)
    
    print(f"✓ Mapped all selections")
    print()
    
    # Load actual selections
    comparison_file = f"{base_path}/round{round_num}/contestComparison.csv"
    print(f"Loading actual selections from round {round_num}...")
    try:
        actual_imprinted_ids = load_actual_selections(comparison_file, contest_name)
        print(f"✓ Loaded {len(actual_imprinted_ids)} actual selections")
    except Exception as e:
        print(f"✗ ERROR: Could not load actual selections: {e}")
        return False
    print()
    
    # Compare
    print("=" * 80)
    print("VERIFICATION RESULTS")
    print("=" * 80)
    
    expected_sorted = sorted(expected_imprinted_ids)
    actual_sorted = sorted(actual_imprinted_ids)
    
    if expected_sorted == actual_sorted:
        print("✓✓✓ VERIFICATION SUCCESSFUL ✓✓✓")
        print()
        print("All ballot selections match the expected random selections!")
        print(f"Verified {len(expected_sorted)} ballots using seed {SEED}")
        return True
    else:
        print("✗✗✗ VERIFICATION FAILED ✗✗✗")
        print()
        
        expected_set = set(expected_sorted)
        actual_set = set(actual_sorted)
        
        missing = expected_set - actual_set
        extra = actual_set - expected_set
        matching = len(expected_set & actual_set)
        
        print(f"Matching: {matching} / {len(expected_sorted)}")
        
        if missing:
            print(f"\nExpected but NOT in audit ({len(missing)}):")
            for ballot in sorted(missing)[:10]:
                print(f"  - {ballot}")
            if len(missing) > 10:
                print(f"  ... and {len(missing) - 10} more")
        
        if extra:
            print(f"\nIn audit but NOT expected ({len(extra)}):")
            for ballot in sorted(extra)[:10]:
                print(f"  + {ballot}")
            if len(extra) > 10:
                print(f"  ... and {len(extra) - 10} more")
        
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Verify random ballot selection for 2024 General Election contests"
    )
    parser.add_argument(
        "--contest",
        default="Bent County Commissioner-District 1",
        help="Contest name (must match exactly as in contest.csv)"
    )
    parser.add_argument(
        "--county",
        default=None,
        help="County name for manifest file (e.g., 'Bent', 'Adams')"
    )
    parser.add_argument(
        "--list-contests",
        action="store_true",
        help="List all available contests"
    )
    
    args = parser.parse_args()
    
    if args.list_contests:
        base_path = "/srv/s/electionaudits/colorado-rla-2018/neal_ignore/auditcenter-2024g"
        print("Available contests in round 1:")
        print("-" * 80)
        with open(f"{base_path}/round1/contest.csv", 'r') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 1):
                print(f"{i:3d}. {row['contest_name']}")
        return
    
    # Infer county from contest name if not provided
    county = args.county
    if not county:
        contest_lower = args.contest.lower()
        # Extract county name from contest
        if " county " in contest_lower:
            parts = args.contest.split(" County ")
            county = parts[0].split()[-1]
        elif contest_lower.startswith("bent "):
            county = "Bent"
        elif contest_lower.startswith("adams "):
            county = "Adams"
        # Add more as needed
    
    success = verify_contest(args.contest, county)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

