#!/usr/bin/env python3
"""
Verify all ballot selections for a county (not per-contest).

This verifies the UNION of all selections for targeted contests in a county.
"""

import hashlib
import csv
from pathlib import Path
from typing import List, Set, Dict

# County ID mapping (from county_ids.properties)
COUNTY_IDS = {
    1: 'Adams', 2: 'Alamosa', 3: 'Arapahoe', 4: 'Archuleta', 5: 'Baca',
    6: 'Bent', 7: 'Boulder', 8: 'Chaffee', 9: 'Cheyenne', 10: 'Clear Creek',
    11: 'Conejos', 12: 'Costilla', 13: 'Crowley', 14: 'Custer', 15: 'Delta',
    16: 'Denver', 17: 'Dolores', 18: 'Douglas', 19: 'Eagle', 20: 'Elbert',
    21: 'El Paso', 22: 'Fremont', 23: 'Garfield', 24: 'Gilpin', 25: 'Grand',
    26: 'Gunnison', 27: 'Hinsdale', 28: 'Huerfano', 29: 'Jackson', 30: 'Jefferson',
    31: 'Kiowa', 32: 'Kit Carson', 33: 'Lake', 34: 'La Plata', 35: 'Larimer',
    36: 'Las Animas', 37: 'Lincoln', 38: 'Logan', 39: 'Mesa', 40: 'Mineral',
    41: 'Moffat', 42: 'Montezuma', 43: 'Montrose', 44: 'Morgan', 45: 'Otero',
    46: 'Ouray', 47: 'Park', 48: 'Phillips', 49: 'Pitkin', 50: 'Prowers',
    51: 'Pueblo', 52: 'Rio Blanco', 53: 'Rio Grande', 54: 'Routt', 55: 'Saguache',
    56: 'San Juan', 57: 'San Miguel', 58: 'Sedgwick', 59: 'Summit', 60: 'Teller',
    61: 'Washington', 62: 'Weld', 63: 'Yuma', 64: 'Broomfield'
}

# Reverse mapping
COUNTY_NAME_TO_ID = {name: id for id, name in COUNTY_IDS.items()}

SEED = "53417960661093690826"
# Use data symlink relative to this file location
BASE_PATH = Path(__file__).parent.parent.parent / "data" / "2024" / "general"


def generate_random_numbers(seed: str, count: int, domain_size: int) -> List[int]:
    """Generate pseudo-random numbers using SHA-256."""
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


def load_ballot_manifest(manifest_file: str) -> List[str]:
    """Load ballot manifest and return list of imprinted_ids."""
    ballots = []
    with open(manifest_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        # Get column names from first row
        first_row = None
        for row in reader:
            first_row = row
            break
        
        if not first_row:
            return ballots
        
        # Find columns by looking for keywords
        columns = list(first_row.keys())
        
        # Find tabulator column
        tabulator_col = None
        for col in columns:
            if any(keyword in col.lower() for keyword in ['tabulator', 'scanner', 'device']):
                tabulator_col = col
                break
        
        # Find batch column  
        batch_col = None
        for col in columns:
            if 'batch' in col.lower():
                batch_col = col
                break
        
        # Find count column - look for specific patterns
        count_col = None
        for col in columns:
            col_lower = col.lower()
            # Look for columns that are clearly about ballot/card counts
            if (col_lower.startswith('#') or col_lower.startswith('.')) and \
               any(keyword in col_lower for keyword in ['ballot', 'card', 'in']):
                # Skip location/box columns
                if not any(skip in col_lower for skip in ['location', 'box']):
                    count_col = col
                    break
            elif col_lower in ['count', 'number of ballots', 'number of cards']:
                count_col = col
                break
        
        if not all([tabulator_col, batch_col, count_col]):
            raise ValueError(f"Cannot parse manifest. Columns: {columns}")
    
    # Reopen and process all rows
    with open(manifest_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tabulator = row[tabulator_col]
            batch = row[batch_col]
            num_cards = int(row[count_col])
            
            for position in range(1, num_cards + 1):
                ballots.append(f"{tabulator}-{batch}-{position}")
    return ballots


def get_targeted_contests_for_county(county: str, round_num: int = 3) -> List[Dict]:
    """Get all contests targeted for RLA in a specific county.
    
    Uses contestsByCounty.csv to determine which contests apply to this county.
    """
    targeted = []
    
    # First, get all contests that apply to this county
    county_id = COUNTY_NAME_TO_ID[county]
    contests_in_county = set()
    
    try:
        with open(BASE_PATH / "contestsByCounty.csv", 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if int(row['county_id']) == county_id:
                    contests_in_county.add(row['contest_name'])
    except FileNotFoundError:
        pass
    
    # Now check which of those are targeted for RLA
    contest_file = BASE_PATH / f"round{round_num}" / "contest.csv"
    try:
        with open(contest_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Check if targeted for RLA and in this county
                if (row['audit_reason'] in ['county_wide_contest', 'state_wide_contest'] and
                    row['contest_name'] in contests_in_county):
                    targeted.append({
                        'name': row['contest_name'],
                        'audit_reason': row['audit_reason'],
                        'audited_sample_count': int(row['audited_sample_count']),
                        'ballot_card_count': int(row['ballot_card_count']),
                        'contest_ballot_card_count': int(row['contest_ballot_card_count'])
                    })
    except FileNotFoundError:
        pass
    
    return targeted


def get_counties_for_contest(contest_name: str) -> List[int]:
    """Get all county IDs that have a contest, in alphabetical order.
    
    Uses contestsByCounty.csv to find ALL counties with the contest,
    not just counties with examined ballots.
    """
    counties_file = BASE_PATH / "contestsByCounty.csv"
    county_ids = []
    
    with open(counties_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['contest_name'] == contest_name:
                county_ids.append(int(row['county_id']))
    
    return sorted(county_ids)  # Should already be sorted, but make sure


def verify_county(county: str, round_num: int = 3):
    """Verify all ballot selections for a county."""
    
    print("=" * 80)
    print(f"COUNTY-LEVEL BALLOT SELECTION VERIFICATION")
    print(f"County: {county}")
    print("=" * 80)
    print()
    
    # Validate county name
    if county not in COUNTY_NAME_TO_ID:
        print(f"✗ ERROR: Invalid county name: '{county}'")
        print()
        print(f"To see all valid county names, run:")
        print(f"  python3 verify_county_selections.py --list-counties")
        print()
        return False
    
    county_id = COUNTY_NAME_TO_ID[county]
    print(f"County ID: {county_id}")
    print()
    
    # Get all ballots examined in this county
    comparison_file = BASE_PATH / f"round{round_num}" / "contestComparison.csv"
    examined_ballots = set()
    
    with open(comparison_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('county_name') == county:
                examined_ballots.add(row['imprinted_id'])
    
    print(f"Total ballots examined in {county} County: {len(examined_ballots)}")
    print()
    
    # Get targeted contests for this county
    targeted = get_targeted_contests_for_county(county, round_num)
    
    print(f"Contests targeted for RLA involving {county} County:")
    print("-" * 80)
    for contest in targeted:
        print(f"  {contest['name']:50s} [{contest['audit_reason']:20s}] ({contest['audited_sample_count']} selections)")
    print()
    
    # Load county manifest
    county_file_name = county.replace(' ', '')
    manifest_file = BASE_PATH / f"{county_file_name}BallotManifest.csv"
    manifest = load_ballot_manifest(manifest_file)
    print(f"Loaded {county} County manifest: {len(manifest):,} ballot cards")
    print()
    
    # Generate selections for each targeted contest
    all_selections = set()
    single_county_contests = []
    multi_county_contests = []
    
    for contest in targeted:
        # Check if single-county or multi-county
        counties_with_contest = get_counties_for_contest(contest['name'])
        
        if contest['audited_sample_count'] == 0:
            print(f"Skipping {contest['name'][:50]} (0 selections)")
            continue
        
        if len(counties_with_contest) == 1:
            # Single-county contest - use county manifest
            single_county_contests.append(contest)
            print(f"Generating {contest['audited_sample_count']} selections for: {contest['name'][:50]}...")
            print(f"  Single-county contest, using {county} manifest ({len(manifest):,} cards)")
            selections = generate_random_numbers(SEED, contest['audited_sample_count'], len(manifest))
            selected_ballots = {manifest[s-1] for s in selections}
            all_selections |= selected_ballots
            print(f"  ✓ Generated {len(selected_ballots)} selections")
        else:
            # Multi-county contest - build combined manifest
            multi_county_contests.append(contest)
            
            print(f"Generating {contest['audited_sample_count']} selections for: {contest['name'][:50]}...")
            print(f"  Multi-county contest spanning {len(counties_with_contest)} counties")
            
            # Build combined manifest in county ID order (alphabetically)
            # Track position ranges for each county
            combined_manifest = []
            county_ranges = {}
            current_pos = 0
            
            for cid in sorted(counties_with_contest):
                county_name = COUNTY_IDS[cid]
                # Remove spaces from county name for file path
                county_file_name = county_name.replace(' ', '')
                county_manifest_file = BASE_PATH / f"{county_file_name}BallotManifest.csv"
                try:
                    county_ballots = load_ballot_manifest(county_manifest_file)
                    start = current_pos + 1
                    end = current_pos + len(county_ballots)
                    county_ranges[cid] = (start, end)
                    combined_manifest.extend(county_ballots)
                    current_pos = end
                except FileNotFoundError:
                    # Missing manifest is OK if county has no examined ballots
                    print(f"  ⚠ Skipping {county_name} (no manifest file)")
                    continue
            
            print(f"  Combined manifest: {len(combined_manifest):,} cards from {len(counties_with_contest)} counties")
            
            # Find this county's range in the combined manifest
            this_county_id = COUNTY_NAME_TO_ID[county]
            if this_county_id in county_ranges:
                range_start, range_end = county_ranges[this_county_id]
                print(f"  {county} range: [{range_start:,} to {range_end:,}]")
            else:
                range_start, range_end = -1, -1
            
            # Domain is the full combined manifest
            domain_size = len(combined_manifest)
            
            # Generate selections from combined manifest
            selections = generate_random_numbers(SEED, contest['audited_sample_count'], domain_size)
            
            # Filter to just selections in THIS county's range
            selections_in_this_county = [s for s in selections if range_start <= s <= range_end]
            selected_ballots = {combined_manifest[s-1] for s in selections_in_this_county}
            
            all_selections |= selected_ballots
            print(f"  ✓ Generated {len(selections)} total selections, {len(selections_in_this_county)} in {county} County")
    
    print()
    
    # Verification
    print("=" * 80)
    print("VERIFICATION RESULTS")
    print("=" * 80)
    print()
    
    print(f"Generated selections (from {len(single_county_contests)} single-county + {len(multi_county_contests)} multi-county contests):")
    print(f"  Total selections: {len(all_selections)}")
    print(f"Total examined ballots in county: {len(examined_ballots)}")
    print()
    
    # Check: all generated selections should be examined
    not_examined = all_selections - examined_ballots
    if not_examined:
        print(f"✗ ERROR: {len(not_examined)} generated selections were NOT examined:")
        for ballot in sorted(not_examined)[:10]:
            print(f"  - {ballot}")
        if len(not_examined) > 10:
            print(f"  ... and {len(not_examined) - 10} more")
        print()
    else:
        print(f"✓ All {len(all_selections)} generated selections were examined")
        print()
    
    # Check: examined ballots should match generated selections
    extra_examined = examined_ballots - all_selections
    if extra_examined:
        print(f"⚠ WARNING: {len(extra_examined)} examined ballots are NOT in generated selections:")
        for ballot in sorted(extra_examined)[:10]:
            print(f"  + {ballot}")
        if len(extra_examined) > 10:
            print(f"  ... and {len(extra_examined) - 10} more")
        print()
        print(f"Possible causes:")
        print(f"  - Ballots selected for other targeted contests not analyzed here")
        print(f"  - Manifest ordering or data issues")
    else:
        print(f"✓ No extra ballots examined beyond generated selections")
        print()
    
    if not not_examined and not extra_examined:
        print(f"✓✓✓ PERFECT MATCH: All ballots match exactly!")
        print(f"  Generated: {len(all_selections)}")
        print(f"  Examined:  {len(examined_ballots)}")
        return True
    elif not not_examined:
        print(f"✓✓✓ VERIFICATION SUCCESSFUL")
        print(f"  All {len(all_selections)} generated selections were examined ✓")
        print()
        if extra_examined:
            print(f"  Note: {len(extra_examined)} additional ballots were examined")
            print(f"  These are likely from contests that require CVR data to verify:")
            for contest in multi_county_contests:
                print(f"    - {contest['name']}")
        return True
    else:
        print(f"✗ VERIFICATION FAILED")
        print(f"  {len(not_examined)} generated selections were not examined")
        return False


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify all ballot selections for a county")
    parser.add_argument("--county", default=None, help="County name (or use --all-counties)")
    parser.add_argument("--round", type=int, default=3, help="Round number (1, 2, or 3)")
    parser.add_argument("--list-counties", action="store_true", help="List all valid county names")
    parser.add_argument("--all-counties", action="store_true", help="Verify all counties")
    
    args = parser.parse_args()
    
    if args.list_counties:
        print("Valid county names:")
        print("-" * 80)
        for county_id in sorted(COUNTY_IDS.keys()):
            print(f"  {county_id:2d}. {COUNTY_IDS[county_id]}")
        print(f"\nTotal: {len(COUNTY_IDS)} counties")
        sys.exit(0)
    
    if args.all_counties:
        print("=" * 80)
        print("VERIFYING ALL COUNTIES")
        print("=" * 80)
        print()
        
        results = {}
        for county_id in sorted(COUNTY_IDS.keys()):
            county_name = COUNTY_IDS[county_id]
            print(f"\n{'='*80}")
            print(f"County {county_id}/64: {county_name}")
            print(f"{'='*80}\n")
            
            try:
                success = verify_county(county_name, args.round)
                results[county_name] = success
            except Exception as e:
                print(f"✗ ERROR verifying {county_name}: {e}")
                results[county_name] = False
            
            print()
        
        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY OF ALL COUNTIES")
        print("=" * 80)
        print()
        
        perfect = [c for c, s in results.items() if s and 'PERFECT' in str(s)]
        successful = [c for c, s in results.items() if s]
        failed = [c for c, s in results.items() if not s]
        
        print(f"Total counties verified: {len(results)}")
        print(f"  Successful: {len(successful)}")
        print(f"  Failed: {len(failed)}")
        print()
        
        if failed:
            print("Failed counties:")
            for c in failed:
                print(f"  - {c}")
        
        sys.exit(0 if len(failed) == 0 else 1)
    
    if not args.county:
        print("ERROR: Must specify --county or --all-counties")
        print()
        print("Usage:")
        print("  python3 verify_county_selections.py --county Boulder")
        print("  python3 verify_county_selections.py --all-counties")
        print("  python3 verify_county_selections.py --list-counties")
        sys.exit(1)
    
    success = verify_county(args.county, args.round)
    sys.exit(0 if success else 1)

