#!/usr/bin/env python3
"""
Calculate Risk for Opportunistic Contests - CORRECTED v4

Key fix: Use CONTEST-BALLOT sampling rates, not overall sampling rates.
"""

import csv
import sys
from pathlib import Path
from collections import defaultdict

script_dir = Path(__file__).parent.parent / "server" / "eclipse-project" / "script" / "rla_export" / "rla_export"
sys.path.insert(0, str(script_dir))

import rlacalc

GAMMA = 1.03905
RISK_LIMIT = 0.03

def load_manifest_count(county_name):
    """Get total ballot cards from a county's manifest."""
    try:
        manifest_file = Path(__file__).parent / "neal_ignore" / "auditcenter-2024g" / "ballotManifests" / f"{county_name}BallotManifest.csv"
        total = 0
        
        with open(manifest_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                for col in ['# of Ballot Cards', '# of Ballots', '# of Ballot', '# Cards', '# Ballots']:
                    if col in row and row[col]:
                        total += int(row[col])
                        break
        
        return total
    except FileNotFoundError:
        return None

def load_comparison_data(round_num=3):
    """Load examined ballots with discrepancy info."""
    data_dir = Path(__file__).parent / "neal_ignore" / "auditcenter-2024g"
    file_path = data_dir / f"round{round_num}" / "contestComparison.csv"
    
    # Track contest-specific ballots per county
    contest_ballots_per_county = defaultdict(lambda: defaultdict(list))
    
    # Track all examined ballots per county (unique)
    all_examined_per_county = defaultdict(set)
    
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            county = row['county_name']
            iid = row['imprinted_id']
            contest = row['contest_name']
            
            # Track all examined ballots per county
            all_examined_per_county[county].add(iid)
            
            # Track ballots with this specific contest
            contest_ballots_per_county[contest][county].append({
                'iid': iid,
                'cvr': row.get('choice_per_voting_computer', ''),
                'audit': row.get('audit_board_selection', ''),
                'consensus': row.get('consensus', 'YES'),
            })
    
    return dict(contest_ballots_per_county), dict(all_examined_per_county)

def load_contest_data(round_num=3):
    """Load contest metadata."""
    data_dir = Path(__file__).parent / "neal_ignore" / "auditcenter-2024g"
    file_path = data_dir / f"round{round_num}" / "contest.csv"
    
    contests = {}
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            contests[row['contest_name']] = row
    
    return contests

def load_counties_by_contest(round_num=3):
    """Load which counties each contest appears in."""
    data_dir = Path(__file__).parent / "neal_ignore" / "auditcenter-2024g"
    file_path = data_dir / "contestsByCounty.csv"
    
    counties_by_contest = defaultdict(set)
    
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            counties_by_contest[row['contest_name']].add(row['county_name'])
    
    return dict(counties_by_contest)

def has_discrepancy(ballot_data):
    """Check if a ballot has a discrepancy."""
    if ballot_data['consensus'] == 'NO':
        return True
    cvr = ballot_data['cvr'].strip()
    audit = ballot_data['audit'].strip()
    return cvr != audit and cvr != '' and audit != ''

def calculate_multicounty_risk(contest_name, contest_data, counties, 
                                 contest_ballots_per_county, all_examined_per_county, show_work=False):
    """Calculate risk using CONTEST-BALLOT sampling rates."""
    
    if show_work:
        print(f"\n{'='*80}")
        print(f"DETAILED CALCULATION: {contest_name}")
        print(f"{'='*80}\n")
    
    # Get total contest universe from contest.csv
    try:
        total_contest_universe = int(contest_data['contest_ballot_card_count'])
        min_margin = int(contest_data['min_margin'])
    except:
        return {'error': 'Missing contest data'}
    
    # Step 1: Get manifest counts and total examined per county
    county_info = {}
    
    for county in counties:
        manifest_count = load_manifest_count(county)
        if manifest_count is None:
            continue
        
        # Total examined (all contests)
        total_examined = len(all_examined_per_county.get(county, []))
        
        # Contest ballots examined
        contest_ballots = contest_ballots_per_county.get(county, [])
        examined_contest_count = len(contest_ballots)
        
        if examined_contest_count > 0:
            county_info[county] = {
                'manifest_count': manifest_count,
                'total_examined': total_examined,
                'examined_contest_ballots': contest_ballots,
                'examined_count': examined_contest_count,
            }
    
    if len(county_info) == 0:
        return {'error': 'No counties with examined ballots'}
    
    total_examined_with_contest = sum(info['examined_count'] for info in county_info.values())
    
    if show_work:
        print("Step 1: Manifest counts and total examined")
        for county, info in county_info.items():
            print(f"  {county}:")
            print(f"    Manifest: {info['manifest_count']:,} ballot cards")
            print(f"    Total examined (all contests): {info['total_examined']} ballots")
            print(f"    With this contest: {info['examined_count']} ballots")
        print(f"  Total with contest: {total_examined_with_contest}")
    
    # Step 2: Estimate contest ballots per county (based on proportion)
    for county, info in county_info.items():
        fraction = info['examined_count'] / total_examined_with_contest
        estimated_contest_ballots = int(total_contest_universe * fraction)
        info['fraction'] = fraction
        info['estimated_contest_ballots'] = estimated_contest_ballots
    
    if show_work:
        print(f"\nStep 2: Estimate contest ballots per county")
        print(f"  Total contest universe: {total_contest_universe:,}")
        for county, info in county_info.items():
            print(f"  {county}: {total_contest_universe:,} × {info['fraction']:.4f} = {info['estimated_contest_ballots']:,} estimated")
    
    # Step 3: Calculate CONTEST-BALLOT sampling rates
    for county, info in county_info.items():
        info['contest_sampling_rate'] = info['examined_count'] / info['estimated_contest_ballots']
    
    if show_work:
        print(f"\nStep 3: CONTEST-BALLOT sampling rates")
        for county, info in county_info.items():
            print(f"  {county}: {info['examined_count']}/{info['estimated_contest_ballots']:,} = {info['contest_sampling_rate']:.6f} = {info['contest_sampling_rate']*100:.4f}%")
    
    # Step 4: Find minimum contest-ballot rate
    min_rate = min(info['contest_sampling_rate'] for info in county_info.values())
    min_county = min(county_info.items(), key=lambda x: x[1]['contest_sampling_rate'])[0]
    
    if show_work:
        print(f"\nStep 4: Minimum contest-ballot rate: {min_rate:.6f} ({min_county})")
    
    # Step 5: Downsample to minimum rate
    valid_sample_ballots = []
    
    for county, info in county_info.items():
        if county == min_county:
            # Use ALL contest ballots from minimum-rate county
            n_to_use = info['examined_count']
        else:
            # Downsample to minimum rate
            n_to_use = int(info['estimated_contest_ballots'] * min_rate)
        
        info['n_to_use'] = n_to_use
        ballots_to_use = info['examined_contest_ballots'][:n_to_use]
        info['ballot_ids_used'] = [b['iid'] for b in ballots_to_use]
        valid_sample_ballots.extend([(county, b) for b in ballots_to_use])
    
    if show_work:
        print(f"\nStep 5: Downsample to minimum contest-ballot rate")
        for county, info in county_info.items():
            marker = " (minimum - use ALL)" if county == min_county else ""
            print(f"  {county}: {info['n_to_use']} contest ballots{marker}")
            print(f"    Ballot IDs: {', '.join(info['ballot_ids_used'])}")
        print(f"  Total valid sample: {len(valid_sample_ballots)} contest ballots")
    
    # Step 6: Count discrepancies
    discrepancy_count = 0
    for county, ballot in valid_sample_ballots:
        if has_discrepancy(ballot):
            discrepancy_count += 1
    
    if show_work:
        print(f"\nStep 6: Discrepancies in valid sample")
        print(f"  Total: {discrepancy_count}")
    
    # Step 7: Risk calculation
    try:
        min_margin = int(contest_data['min_margin'])
        contest_universe = int(contest_data['contest_ballot_card_count'])
        diluted_margin = min_margin / contest_universe
    except:
        return {'error': 'Missing margin data'}
    
    n = len(valid_sample_ballots)
    o1 = discrepancy_count  # Conservative
    o2 = u1 = u2 = 0
    
    risk = rlacalc.KM_P_value(n=n, gamma=GAMMA, margin=diluted_margin,
                               o1=o1, o2=o2, u1=u1, u2=u2)
    
    if show_work:
        print(f"\nStep 7: Risk calculation")
        print(f"  n (valid contest-ballot sample): {n}")
        print(f"  min_margin: {min_margin:,}")
        print(f"  contest_ballot_card_count: {contest_universe:,}")
        print(f"  diluted_margin: {min_margin}/{contest_universe} = {diluted_margin:.6f}")
        print(f"  discrepancies (as o1): {o1}")
        risk_str = f"{risk:.8e}" if risk < 0.0001 else f"{risk:.8f}"
        print(f"  Risk: {risk_str}")
        result_str = '✓ Below' if risk <= RISK_LIMIT else '✗ Above'
        print(f"  {result_str} risk limit ({RISK_LIMIT})")
    
    return {
        'n': n,
        'min_margin': min_margin,
        'contest_universe': contest_universe,
        'diluted_margin': diluted_margin,
        'discrepancies': discrepancy_count,
        'o1': o1, 'o2': o2, 'u1': u1, 'u2': u2,
        'risk': risk,
        'counties': len(county_info),
        'min_rate': min_rate,
        'min_county': min_county,
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Calculate opportunistic risks - v4 CORRECTED')
    parser.add_argument('--round', type=int, default=3)
    parser.add_argument('--contest', type=str, required=True, help='Contest name')
    parser.add_argument('--show-work', action='store_true', help='Show detailed calculation')
    args = parser.parse_args()
    
    print(f"Loading data for round {args.round}...")
    contest_ballots_data, all_examined_per_county = load_comparison_data(args.round)
    contest_metadata = load_contest_data(args.round)
    counties_by_contest = load_counties_by_contest(args.round)
    
    if args.contest not in contest_metadata:
        print(f"Contest '{args.contest}' not found")
        return 1
    
    contest_data = contest_metadata[args.contest]
    counties = counties_by_contest.get(args.contest, set())
    contest_ballots_per_county = contest_ballots_data.get(args.contest, {})
    
    if not args.show_work:
        print(f"\nContest: {args.contest}")
        print(f"Counties: {len(counties)}")
    
    result = calculate_multicounty_risk(args.contest, contest_data, counties,
                                         contest_ballots_per_county, all_examined_per_county,
                                         show_work=args.show_work)
    
    if 'error' in result:
        print(f"ERROR: {result['error']}")
        return 1
    
    if not args.show_work:
        print(f"Valid sample: {result['n']} contest ballots")
        print(f"Diluted margin: {result['diluted_margin']:.6f}")
        risk_str = f"{result['risk']:.8e}" if result['risk'] < 0.0001 else f"{result['risk']:.8f}"
        print(f"Risk: {risk_str}")
        result_str = '✓ Below' if result['risk'] <= RISK_LIMIT else '✗ Above'
        print(f"{result_str} risk limit")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
