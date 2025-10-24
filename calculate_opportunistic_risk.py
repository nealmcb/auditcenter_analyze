#!/usr/bin/env python3
"""
Calculate Risk for Opportunistic Contests - CORRECTED

Sampling rate = (observed ballots with contest) / (manifest ballot_card_count)
"""

import csv
import sys
from pathlib import Path
from collections import defaultdict

script_dir = Path(__file__).parent / "server" / "eclipse-project" / "script" / "rla_export" / "rla_export"
sys.path.insert(0, str(script_dir))

import rlacalc

GAMMA = 1.03905
RISK_LIMIT = 0.03

def load_all_data(round_num=3):
    """Load all data efficiently in one pass."""
    data_dir = Path(__file__).parent / "neal_ignore" / "auditcenter-2024g"
    
    # 1. Load manifest counts per county
    print("Loading manifests...")
    manifest_counts = {}
    for manifest_file in (data_dir / "ballotManifests").glob("*BallotManifest.csv"):
        county = manifest_file.stem.replace("BallotManifest", "")
        total = 0
        with open(manifest_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                for col in ['# of Ballot Cards', '# of Ballots', '# of Ballot', '# Cards', '# Ballots']:
                    if col in row and row[col]:
                        total += int(row[col])
                        break
        manifest_counts[county] = total
    
    # 2. Load contest metadata
    print("Loading contest metadata...")
    contest_file = data_dir / f"round{round_num}" / "contest.csv"
    contest_metadata = {}
    with open(contest_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            contest_metadata[row['contest_name']] = row
    
    # 3. Load which counties have which contests
    print("Loading contest-county mappings...")
    counties_file = data_dir / "contestsByCounty.csv"
    counties_by_contest = defaultdict(set)
    with open(counties_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            counties_by_contest[row['contest_name']].add(row['county_name'])
    
    # 4. Load all examined ballots (one pass through contestComparison.csv)
    print("Loading examined ballots...")
    comparison_file = data_dir / f"round{round_num}" / "contestComparison.csv"
    
    # Track contest ballots per county with discrepancy info
    contest_ballots = defaultdict(lambda: defaultdict(list))
    
    with open(comparison_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            county = row['county_name']
            contest = row['contest_name']
            iid = row['imprinted_id']
            
            contest_ballots[contest][county].append({
                'iid': iid,
                'cvr': row.get('choice_per_voting_computer', ''),
                'audit': row.get('audit_board_selection', ''),
                'consensus': row.get('consensus', 'YES'),
            })
    
    return manifest_counts, contest_metadata, dict(counties_by_contest), dict(contest_ballots)

def has_discrepancy(ballot):
    """Check if a ballot has a discrepancy."""
    if ballot['consensus'] == 'NO':
        return True
    cvr = ballot['cvr'].strip()
    audit = ballot['audit'].strip()
    return cvr != audit and cvr != '' and audit != ''

def calculate_contest_risk(contest_name, contest_data, counties, contest_ballots_per_county, 
                            manifest_counts, show_work=False):
    """Calculate risk for one contest."""
    
    if show_work:
        print(f"\n{'='*80}")
        print(f"CONTEST: {contest_name}")
        print(f"{'='*80}\n")
    
    # Get contest metadata
    try:
        min_margin = int(contest_data['min_margin'])
        contest_ballot_card_count = int(contest_data['contest_ballot_card_count'])
    except (KeyError, ValueError):
        return {'error': 'Missing contest data'}
    
    # Step 1: Count observed ballots with contest per county
    county_data = {}
    total_observed = 0
    
    for county in counties:
        if county not in manifest_counts:
            continue
        
        manifest_count = manifest_counts[county]
        if manifest_count == 0:
            continue
        
        ballots = contest_ballots_per_county.get(county, [])
        observed_count = len(ballots)
        
        if observed_count > 0:
            county_data[county] = {
                'manifest_count': manifest_count,
                'observed_count': observed_count,
                'ballots': ballots,
            }
            total_observed += observed_count
    
    if not county_data:
        return {'error': 'No examined ballots'}
    
    if show_work:
        print("Step 1: Observed ballots with contest")
        print(f"  NOTE: 'ballot_card_count' from manifest")
        print(f"  NOTE: 'contest_ballot_card_count' from contest.csv = {contest_ballot_card_count:,}")
        for county, data in county_data.items():
            print(f"  {county}:")
            print(f"    ballot_card_count (manifest): {data['manifest_count']:,}")
            print(f"    Observed with contest: {data['observed_count']}")
        print(f"  Total observed: {total_observed}")
    
    # Step 2: Calculate sampling rates (observed with contest / manifest)
    for county, data in county_data.items():
        data['sampling_rate'] = data['observed_count'] / data['manifest_count']
    
    if show_work:
        print(f"\nStep 2: Sampling rates")
        print(f"  Formula: (observed with contest) / (ballot_card_count)")
        for county, data in county_data.items():
            print(f"  {county}: {data['observed_count']} / {data['manifest_count']:,} = {data['sampling_rate']:.8f} = {data['sampling_rate']*100:.6f}%")
    
    # Step 3: Find minimum rate
    min_rate = min(data['sampling_rate'] for data in county_data.values())
    min_county = min(county_data.items(), key=lambda x: x[1]['sampling_rate'])[0]
    
    if show_work:
        print(f"\nStep 3: Minimum sampling rate")
        print(f"  {min_rate:.8f} ({min_county})")
    
    # Step 4: Downsample to minimum rate
    valid_sample = []
    
    for county, data in county_data.items():
        if county == min_county:
            # Use ALL from minimum-rate county
            n_to_use = data['observed_count']
        else:
            # Downsample: manifest × min_rate
            n_to_use = int(data['manifest_count'] * min_rate)
        
        ballots_to_use = data['ballots'][:n_to_use]
        data['n_used'] = n_to_use
        data['ballot_ids'] = [b['iid'] for b in ballots_to_use]
        valid_sample.extend(ballots_to_use)
    
    if show_work:
        print(f"\nStep 4: Downsample to minimum rate")
        for county, data in county_data.items():
            marker = " (minimum - use ALL)" if county == min_county else f" (downsample: {data['manifest_count']:,} × {min_rate:.8f})"
            print(f"  {county}: {data['n_used']} ballots{marker}")
            if data['n_used'] <= 10:
                print(f"    IDs: {', '.join(data['ballot_ids'])}")
            else:
                print(f"    IDs: {', '.join(data['ballot_ids'][:5])} ... (+{data['n_used']-5} more)")
        print(f"  Total valid sample: {len(valid_sample)} ballots with contest")
    
    # Step 5: Count discrepancies
    discrepancies = sum(1 for b in valid_sample if has_discrepancy(b))
    
    if show_work:
        print(f"\nStep 5: Discrepancies")
        print(f"  Total: {discrepancies}")
    
    # Step 6: Calculate risk
    n = len(valid_sample)
    diluted_margin = min_margin / contest_ballot_card_count
    o1 = discrepancies
    o2 = u1 = u2 = 0
    
    risk = rlacalc.KM_P_value(n=n, gamma=GAMMA, margin=diluted_margin,
                               o1=o1, o2=o2, u1=u1, u2=u2)
    
    if show_work:
        print(f"\nStep 6: Risk calculation")
        print(f"  n (valid sample): {n}")
        print(f"  min_margin: {min_margin:,}")
        print(f"  contest_ballot_card_count: {contest_ballot_card_count:,}")
        print(f"  diluted_margin: {min_margin:,} / {contest_ballot_card_count:,} = {diluted_margin:.6f}")
        print(f"  discrepancies (o1): {discrepancies}")
        risk_str = f"{risk:.8e}" if risk < 0.0001 else f"{risk:.8f}"
        print(f"  Risk: {risk_str}")
        status = "✓ PASS" if risk <= RISK_LIMIT else "✗ FAIL"
        print(f"  {status} (risk limit = {RISK_LIMIT})")
    
    return {
        'n': n,
        'min_margin': min_margin,
        'contest_ballot_card_count': contest_ballot_card_count,
        'diluted_margin': diluted_margin,
        'discrepancies': discrepancies,
        'risk': risk,
        'counties': len(county_data),
        'min_rate': min_rate,
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Calculate opportunistic and targeted contest risks')
    parser.add_argument('--round', type=int, default=3)
    parser.add_argument('--contest', type=str, help='Specific contest (if omitted, does all)')
    parser.add_argument('--show-work', action='store_true', help='Show detailed calculation')
    parser.add_argument('--targeted-only', action='store_true', help='Only process targeted contests')
    parser.add_argument('--opportunistic-only', action='store_true', help='Only process opportunistic contests')
    args = parser.parse_args()
    
    # Load all data once
    manifest_counts, contest_metadata, counties_by_contest, contest_ballots = load_all_data(args.round)
    print(f"Loaded data for {len(contest_metadata)} contests")
    print()
    
    # Filter contests
    contests_to_process = []
    for name, data in contest_metadata.items():
        if args.contest and name != args.contest:
            continue
        
        audit_reason = data.get('audit_reason', '')
        
        if args.targeted_only and audit_reason not in ['county_wide_contest', 'state_wide_contest']:
            continue
        if args.opportunistic_only and audit_reason != 'opportunistic_benefits':
            continue
        
        # Skip if no examined ballots
        if name not in contest_ballots:
            continue
        
        contests_to_process.append((name, data, audit_reason))
    
    print(f"Processing {len(contests_to_process)} contests...")
    print()
    
    # Process each contest
    results = []
    for contest_name, contest_data, audit_reason in contests_to_process:
        counties = counties_by_contest.get(contest_name, set())
        contest_ballots_per_county = contest_ballots.get(contest_name, {})
        
        result = calculate_contest_risk(contest_name, contest_data, counties, 
                                         contest_ballots_per_county, manifest_counts,
                                         show_work=args.show_work)
        
        if 'error' in result:
            if args.show_work:
                print(f"ERROR: {result['error']}")
            continue
        
        result['audit_reason'] = audit_reason
        results.append((contest_name, result))
        
        if not args.show_work:
            status = "✓" if result['risk'] <= RISK_LIMIT else "✗"
            risk_str = f"{result['risk']:.6e}" if result['risk'] < 0.0001 else f"{result['risk']:.6f}"
            print(f"{status} {contest_name[:60]:60s} n={result['n']:4d} risk={risk_str}")
    
    # Summary
    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)
    
    targeted = [r for r in results if r[1]['audit_reason'] in ['county_wide_contest', 'state_wide_contest']]
    opportunistic = [r for r in results if r[1]['audit_reason'] == 'opportunistic_benefits']
    
    if targeted:
        targeted_pass = sum(1 for _, r in targeted if r['risk'] <= RISK_LIMIT)
        print(f"Targeted contests: {len(targeted)}")
        print(f"  Achieved risk limit: {targeted_pass}/{len(targeted)}")
        if targeted_pass < len(targeted):
            print(f"  FAILED:")
            for name, r in targeted:
                if r['risk'] > RISK_LIMIT:
                    print(f"    {name}: risk={r['risk']:.6f}")
    
    if opportunistic:
        opp_pass = sum(1 for _, r in opportunistic if r['risk'] <= RISK_LIMIT)
        print(f"Opportunistic contests: {len(opportunistic)}")
        print(f"  Below risk limit: {opp_pass}/{len(opportunistic)}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
