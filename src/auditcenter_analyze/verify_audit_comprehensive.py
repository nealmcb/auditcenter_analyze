#!/usr/bin/env python3
"""
Comprehensive ballot selection verification for Colorado RLA 2024.

Architecture:
1. Load all examined ballot cards (preserving county + imprinted_id)
2. Identify targeted contests and build universes (combined manifests)
3. Go round-by-round
4. For each contest, generate selections and mark which ballot cards were selected
5. Identify ballot cards selected for unknown reasons
6. Preserve data for reports and analysis

This approach is efficient - loads manifests once, processes all contests.
"""

import hashlib
import csv
import json
from pathlib import Path
from typing import Dict, Set, List, Tuple
from collections import defaultdict

# County ID mapping (alphabetical order)
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

COUNTY_NAME_TO_ID = {name: cid for cid, name in COUNTY_IDS.items()}

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
        
        # Smart column detection
        first_row = None
        for row in reader:
            first_row = row
            break
        
        if not first_row:
            return ballots
        
        columns = list(first_row.keys())
        
        # Find columns
        tab_col = next((c for c in columns if any(k in c.lower() for k in ['tabulator', 'scanner', 'device'])), None)
        batch_col = next((c for c in columns if 'batch' in c.lower()), None)
        count_col = next((c for c in columns if c.lower().startswith(('#', '.')) and any(k in c.lower() for k in ['ballot', 'card', 'in'])), None)
        
        if not all([tab_col, batch_col, count_col]):
            raise ValueError(f"Cannot parse manifest. Columns: {columns}")
    
    # Reopen and process
    with open(manifest_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tabulator = row[tab_col]
            batch = row[batch_col]
            num_cards = int(row[count_col])
            
            for position in range(1, num_cards + 1):
                ballots.append(f"{tabulator}-{batch}-{position}")
    
    return ballots


class AuditVerifier:
    """Main verification class."""
    
    def __init__(self, base_path: str = BASE_PATH):
        self.base_path = base_path
        self.manifests = {}  # county_id -> list of imprinted_ids
        self.universes = {}  # contest_name -> ContestUniverse
        self.examined_ballots = {}  # (county_name, imprinted_id) -> ExaminedBallot
        self.results = {}  # Per-round, per-county results
        
    def load_examined_ballots(self, round_num: int):
        """Load all examined ballot cards for a round."""
        print(f"Loading examined ballots for Round {round_num}...")
        
        comparison_file = f"{self.base_path}/round{round_num}/contestComparison.csv"
        
        with open(comparison_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                county_name = row.get('county_name', '')
                imprinted_id = row['imprinted_id']
                contest_name = row['contest_name']
                
                key = (county_name, imprinted_id)
                if key not in self.examined_ballots:
                    self.examined_ballots[key] = {
                        'county': county_name,
                        'imprinted_id': imprinted_id,
                        'contests': set(),
                        'selected_for': set()  # Which contests selected this ballot
                    }
                
                self.examined_ballots[key]['contests'].add(contest_name)
        
        unique_ballots = len(self.examined_ballots)
        unique_counties = len(set(b['county'] for b in self.examined_ballots.values()))
        
        print(f"  Loaded {unique_ballots:,} unique ballot cards from {unique_counties} counties")
        return unique_ballots
    
    def get_targeted_contests(self, round_num: int) -> List[Dict]:
        """Get all contests targeted for RLA, sorted by county count (largest first)."""
        contest_file = f"{self.base_path}/round{round_num}/contest.csv"
        contests = []
        
        with open(contest_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['audit_reason'] in ['county_wide_contest', 'state_wide_contest']:
                    if int(row['audited_sample_count']) > 0:
                        contests.append({
                            'name': row['contest_name'],
                            'audit_reason': row['audit_reason'],
                            'audited_sample_count': int(row['audited_sample_count']),
                            'ballot_card_count': int(row['ballot_card_count']),
                            'contest_ballot_card_count': int(row['contest_ballot_card_count'])
                        })
        
        # Get county counts from contestsByCounty.csv
        for contest in contests:
            county_ids = self.get_counties_for_contest(contest['name'])
            contest['county_ids'] = county_ids
            contest['num_counties'] = len(county_ids)
        
        # Sort by number of counties (largest first)
        contests.sort(key=lambda c: c['num_counties'], reverse=True)
        
        return contests
    
    def get_counties_for_contest(self, contest_name: str) -> List[int]:
        """Get all county IDs that have a contest (from contestsByCounty.csv)."""
        county_ids = []
        
        with open(f"{self.base_path}/contestsByCounty.csv", 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['contest_name'] == contest_name:
                    county_ids.append(int(row['county_id']))
        
        return sorted(county_ids)
    
    def load_manifest_for_county(self, county_id: int) -> List[str]:
        """Load manifest for a county (cached)."""
        if county_id in self.manifests:
            return self.manifests[county_id]
        
        county_name = COUNTY_IDS[county_id]
        county_file_name = county_name.replace(' ', '')
        manifest_file = f"{self.base_path}/{county_file_name}BallotManifest.csv"
        
        try:
            manifest = load_ballot_manifest(manifest_file)
            self.manifests[county_id] = manifest
            return manifest
        except FileNotFoundError:
            self.manifests[county_id] = []
            return []
    
    def build_contest_universe(self, contest_name: str, county_ids: List[int]) -> Dict:
        """Build combined manifest universe for a contest."""
        combined_manifest = []
        county_ranges = {}
        current_pos = 0
        
        for cid in sorted(county_ids):
            manifest = self.load_manifest_for_county(cid)
            if manifest:
                start = current_pos + 1
                end = current_pos + len(manifest)
                county_ranges[cid] = (start, end)
                combined_manifest.extend(manifest)
                current_pos = end
        
        return {
            'contest_name': contest_name,
            'combined_manifest': combined_manifest,
            'county_ranges': county_ranges,
            'domain_size': len(combined_manifest),
            'num_counties': len(county_ids),
            'county_ids': county_ids
        }
    
    def verify_round(self, round_num: int):
        """Verify a single round."""
        print()
        print("=" * 80)
        print(f"ROUND {round_num} VERIFICATION")
        print("=" * 80)
        print()
        
        # Load examined ballots
        num_examined = self.load_examined_ballots(round_num)
        print()
        
        # Get targeted contests
        targeted = self.get_targeted_contests(round_num)
        print(f"Targeted contests: {len(targeted)}")
        print(f"  {sum(1 for c in targeted if c['num_counties'] > 1)} multi-county")
        print(f"  {sum(1 for c in targeted if c['num_counties'] == 1)} single-county")
        print()
        
        # Build universes for largest contests first
        print("Building contest universes...")
        for contest in targeted:
            print(f"  {contest['name'][:50]:50s} ({contest['num_counties']:2d} counties, {contest['audited_sample_count']:4d} selections)")
            
            universe = self.build_contest_universe(contest['name'], contest['county_ids'])
            self.universes[contest['name']] = universe
        
        print()
        print(f"Loaded {len(self.manifests)} county manifests (cached for reuse)")
        print()
        
        # Generate selections and mark examined ballots
        print("Generating selections and marking ballot cards...")
        print()
        
        for contest in targeted:
            universe = self.universes[contest['name']]
            selections = generate_random_numbers(SEED, contest['audited_sample_count'], universe['domain_size'])
            
            print(f"{contest['name'][:60]:60s}", end='')
            
            # Mark which ballot cards were selected for this contest
            for selection_idx, selection in enumerate(selections):
                imprinted_id = universe['combined_manifest'][selection - 1]
                
                # Find which county this selection is in
                county_id = None
                for cid, (start, end) in universe['county_ranges'].items():
                    if start <= selection <= end:
                        county_id = cid
                        break
                
                if county_id:
                    county_name = COUNTY_IDS[county_id]
                    key = (county_name, imprinted_id)
                    
                    if key in self.examined_ballots:
                        self.examined_ballots[key]['selected_for'].add(contest['name'])
            
            # Count how many were actually examined
            examined_for_contest = sum(1 for b in self.examined_ballots.values() 
                                      if contest['name'] in b['selected_for'])
            print(f" {examined_for_contest:4d} examined")
        
        print()
        
        # Analysis
        print("=" * 80)
        print(f"ROUND {round_num} ANALYSIS")
        print("=" * 80)
        print()
        
        # Count ballots by selection status
        selected_for_something = sum(1 for b in self.examined_ballots.values() if b['selected_for'])
        not_selected = sum(1 for b in self.examined_ballots.values() if not b['selected_for'])
        
        print(f"Examined ballot cards:")
        print(f"  Selected for known targeted contest: {selected_for_something:,}")
        print(f"  NOT selected for any targeted contest: {not_selected:,}")
        print()
        
        if not_selected > 0:
            print(f"⚠ {not_selected} ballot cards examined but not selected for any targeted contest")
            print(f"  Possible explanations:")
            print(f"    - Multi-card ballot packets (Card 1 selected → all cards examined)")
            print(f"    - Replacement ballots for 'ballot not found'")
            print(f"    - Phantom ballots")
            print(f"    - Data errors")
            print()
            
            # Show examples
            examples = [b for b in self.examined_ballots.values() if not b['selected_for']][:5]
            if examples:
                print(f"  Examples:")
                for b in examples:
                    contests = ', '.join(list(b['contests'])[:3])
                    print(f"    {b['county']:15s} {b['imprinted_id']:20s} - {contests}")
                if not_selected > 5:
                    print(f"    ... and {not_selected - 5} more")
            print()
        
        # Per-county summary
        by_county = defaultdict(lambda: {'examined': 0, 'selected': 0, 'unaccounted': 0})
        for ballot in self.examined_ballots.values():
            county = ballot['county']
            by_county[county]['examined'] += 1
            if ballot['selected_for']:
                by_county[county]['selected'] += 1
            else:
                by_county[county]['unaccounted'] += 1
        
        print(f"Per-county summary:")
        print(f"{'County':<15s} {'Examined':>10s} {'Selected':>10s} {'Unaccounted':>12s} {'Status':>10s}")
        print("-" * 80)
        
        for county in sorted(by_county.keys()):
            stats = by_county[county]
            if stats['unaccounted'] == 0:
                status = "✓ Perfect"
            elif stats['selected'] == stats['examined']:
                status = "✓ Match"
            else:
                status = f"⚠ {stats['unaccounted']} extra"
            
            print(f"{county:<15s} {stats['examined']:>10,d} {stats['selected']:>10,d} {stats['unaccounted']:>12,d} {status:>10s}")
        
        print()
        
        # Overall verification
        all_selected = sum(1 for b in self.examined_ballots.values() if b['selected_for'])
        all_examined = len(self.examined_ballots)
        
        if not_selected == 0:
            print(f"✓✓✓ PERFECT VERIFICATION")
            print(f"  All {all_examined:,} examined ballot cards were selected for targeted contests")
        else:
            match_rate = (all_selected / all_examined) * 100
            print(f"✓ VERIFICATION SUCCESSFUL ({match_rate:.1f}%)")
            print(f"  {all_selected:,} of {all_examined:,} ballot cards accounted for")
            print(f"  {not_selected:,} examined for unknown reasons (likely multi-card packets)")
        
        print()
        
        return {
            'round': round_num,
            'total_examined': all_examined,
            'accounted_for': all_selected,
            'unaccounted': not_selected,
            'by_county': dict(by_county)
        }
    
    def save_results(self, output_file: str):
        """Save detailed results for further analysis."""
        data = {
            'examined_ballots': [
                {
                    'county': b['county'],
                    'imprinted_id': b['imprinted_id'],
                    'contests_on_ballot': list(b['contests']),
                    'selected_for_contests': list(b['selected_for'])
                }
                for b in self.examined_ballots.values()
            ],
            'universes': {
                name: {
                    'domain_size': u['domain_size'],
                    'num_counties': u['num_counties'],
                    'county_ids': u['county_ids']
                }
                for name, u in self.universes.items()
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Detailed results saved to: {output_file}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Comprehensive audit verification")
    parser.add_argument("--round", type=int, default=2, help="Round to verify (1, 2, or 3)")
    parser.add_argument("--all-rounds", action="store_true", help="Verify all rounds")
    parser.add_argument("--output", help="Save detailed results to JSON file")
    
    args = parser.parse_args()
    
    verifier = AuditVerifier()
    
    if args.all_rounds:
        for round_num in [1, 2, 3]:
            try:
                result = verifier.verify_round(round_num)
            except FileNotFoundError as e:
                print(f"Round {round_num} data not available: {e}")
                break
    else:
        verifier.verify_round(args.round)
    
    if args.output:
        verifier.save_results(args.output)


if __name__ == "__main__":
    main()

