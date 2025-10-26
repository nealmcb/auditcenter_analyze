#!/usr/bin/env python3
"""
Calculate Risk for Opportunistic Contests - CORRECTED

Sampling rate = (observed ballots with contest) / (manifest ballot_card_count)
"""

import csv
import sys
import sqlite3
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

script_dir = Path(__file__).parent / "server" / "eclipse-project" / "script" / "rla_export" / "rla_export"
sys.path.insert(0, str(script_dir))

import rlacalc

GAMMA = 1.03905
RISK_LIMIT = 0.03

def load_all_data(round_num=3):
    """Load all data efficiently in one pass."""
    data_dir = Path(__file__).parent / "neal_ignore" / "auditcenter-2024g"
    
    # 1. Load manifest counts per county
    print("Step 1: Loading manifests...")
    manifest_counts = {}
    for manifest_file in (data_dir / "ballotManifests").glob("*BallotManifest.csv"):
        county_no_space = manifest_file.stem.replace("BallotManifest", "")
        total = 0
        with open(manifest_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # All known column name variations for ballot count
                for col in ['# of Ballot Cards', '# of ballot cards', '#of Ballot Cards', 
                            '# Ballot Cards', '# of Ballots Cards', '# of Ballots', 
                            '# of Ballot', '# Cards', '# Ballots', '# of cards', '. of Ballots']:
                    if col in row and row[col]:
                        total += int(row[col])
                        break
        
        manifest_counts[county_no_space] = total
    
    total_cards = sum(manifest_counts.values())
    print(f"  Loaded {len(manifest_counts)} county manifests")
    print(f"  Total ballot cards statewide: {total_cards:,}")
    print()
    
    # 2. Load contest metadata
    print("Step 2: Loading contest metadata...")
    contest_file = data_dir / f"round{round_num}" / "contest.csv"
    contest_metadata = {}
    contest_by_type = defaultdict(int)
    with open(contest_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            contest_metadata[row['contest_name']] = row
            audit_reason = row.get('audit_reason', 'unknown')
            contest_by_type[audit_reason] += 1
    
    # 3. Load which counties have which contests
    print("Step 3: Loading contest-county mappings...")
    counties_file = data_dir / "contestsByCounty.csv"
    counties_by_contest = defaultdict(set)
    with open(counties_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            county = row['county_name'].replace(' ', '')  # Normalize
            counties_by_contest[row['contest_name']].add(county)
    
    # 4. Load all examined ballots (one pass through contestComparison.csv)
    print("Step 4: Loading examined ballots...")
    comparison_file = data_dir / f"round{round_num}" / "contestComparison.csv"
    
    # Track contest ballots per county with discrepancy info
    contest_ballots = defaultdict(lambda: defaultdict(list))
    # Track total examined ballots per county (unique imprinted_id)
    examined_per_county = defaultdict(set)
    
    with open(comparison_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            county = row['county_name'].replace(' ', '')  # Normalize: remove spaces
            contest = row['contest_name']
            iid = row['imprinted_id']
            
            contest_ballots[contest][county].append({
                'iid': iid,
                'cvr': row.get('choice_per_voting_computer', ''),
                'audit': row.get('audit_board_selection', ''),
                'consensus': row.get('consensus', 'YES'),
            })
            
            # Track unique ballots per county
            examined_per_county[county].add(iid)
    
    # Convert sets to counts
    examined_counts = {county: len(ballots) for county, ballots in examined_per_county.items()}
    
    print(f"  Loaded {sum(examined_counts.values()):,} total examined ballots across {len(examined_counts)} counties")
    print()
    print("Sample sizes by county:")
    for county in sorted(examined_counts.keys()):
        manifest_count = manifest_counts.get(county, 0)
        examined_count = examined_counts[county]
        pct = 100.0 * examined_count / manifest_count if manifest_count > 0 else 0
        print(f"  {county:15s}: {examined_count:4d} examined / {manifest_count:7,d} ballot cards ({pct:5.2f}%)")
    print()
    
    print("Contest metadata summary:")
    print(f"  Total contests in contest.csv: {len(contest_metadata)}")
    print(f"  By audit_reason:")
    for reason in sorted(contest_by_type.keys()):
        print(f"    {reason}: {contest_by_type[reason]}")
    print()
    
    return manifest_counts, contest_metadata, dict(counties_by_contest), dict(contest_ballots), examined_counts, dict(contest_by_type)

def has_discrepancy(ballot):
    """Check if a ballot has a discrepancy."""
    if ballot['consensus'] == 'NO':
        return True
    cvr = ballot['cvr'].strip()
    audit = ballot['audit'].strip()
    return cvr != audit and cvr != '' and audit != ''

def calculate_contest_risk(contest_name, contest_data, counties, contest_ballots_per_county, 
                            manifest_counts, examined_counts, show_work=False):
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
    counties_with_zero_observed = []
    
    for county in counties:
        if county not in manifest_counts:
            continue
        
        manifest_count = manifest_counts[county]
        if manifest_count == 0:
            continue
        
        ballots = contest_ballots_per_county.get(county, [])
        observed_count = len(ballots)
        
        # Track counties with zero observed (contest appears but no ballots examined)
        if observed_count == 0:
            counties_with_zero_observed.append(county)
            # Pretend we have 1 ballot to allow calculation (will have higher risk)
            county_data[county] = {
                'manifest_count': manifest_count,
                'observed_count': 1,  # Pretend 1 ballot
                'ballots': [{'iid': 'NONE', 'cvr': '', 'audit': '', 'consensus': 'YES'}],  # Fake ballot
                'is_fake': True,
            }
            total_observed += 1
        elif observed_count > 0:
            county_data[county] = {
                'manifest_count': manifest_count,
                'observed_count': observed_count,
                'ballots': ballots,
                'is_fake': False,
            }
            total_observed += observed_count
    
    if not county_data:
        # Check if contest appears in contestsByCounty but has no examined ballots
        counties_in_contest = [c for c in counties if c in manifest_counts and manifest_counts[c] > 0]
        if counties_in_contest:
            return {
                'error': f'Contest appears in {len(counties_in_contest)} county(ies) but has zero examined ballots',
                'details': f'Counties: {", ".join(counties_in_contest)}',
                'reason': 'Contest does not appear on any sampled ballot'
            }
        else:
            return {
                'error': 'Contest not found in any county manifest',
                'details': 'No counties have this contest in their ballot manifests',
                'reason': 'Contest may be misnamed or not applicable to any county'
            }
    
    if show_work:
        print("Step 1: Observed ballots with contest")
        print(f"  NOTE: 'ballot_card_count' from manifest")
        print(f"  NOTE: 'contest_ballot_card_count' from contest.csv = {contest_ballot_card_count:,}")
        if counties_with_zero_observed:
            print(f"  ⚠ WARNING: {len(counties_with_zero_observed)} county(ies) had zero observed ballots")
            print(f"    Using 1 fake ballot for: {', '.join(counties_with_zero_observed)}")
            print(f"    ESTIMATION: Allows calculation but increases uncertainty")
        for county, data in county_data.items():
            fake_marker = " (FAKE - using 1)" if data.get('is_fake', False) else ""
            total_examined = examined_counts.get(county, 0)
            print(f"  {county}:")
            print(f"    ballot_card_count (manifest): {data['manifest_count']:,}")
            print(f"    Total examined ballots: {total_examined}")
            print(f"    Observed with contest: {data['observed_count']}{fake_marker}")
            if total_examined > 0:
                pct = 100.0 * data['observed_count'] / total_examined
                print(f"    Percentage: {pct:.1f}%")
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
        print(f"  Total uniformly random sample: {len(valid_sample)} ballots with contest")
    
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
        print(f"  contest_ballot_card_count: {contest_ballot_card_count:,}")
        print(f"  min_margin: {min_margin:,}")
        print(f"  diluted_margin: {min_margin:,} / {contest_ballot_card_count:,} = {diluted_margin:.6f}")
        print(f"  n (uniformly random sample): {n}")
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
        'min_rate_county': min_county,
        'county_data': county_data,
    }

def create_database(db_path):
    """Create SQLite database with schema for audit analysis."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Contest risk analysis results
    c.execute('''
        CREATE TABLE IF NOT EXISTS contest_risk_analysis (
            contest_name TEXT PRIMARY KEY,
            audit_reason TEXT,
            min_margin INTEGER,
            contest_ballot_card_count INTEGER,
            diluted_margin REAL,
            sample_size INTEGER,
            discrepancies INTEGER,
            risk_value REAL,
            min_sampling_rate REAL,
            min_rate_county TEXT,
            counties_involved INTEGER,
            achieved_risk_limit BOOLEAN,
            analysis_timestamp TEXT,
            round INTEGER
        )
    ''')
    
    # County sampling details
    c.execute('''
        CREATE TABLE IF NOT EXISTS county_sampling_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contest_name TEXT,
            county_name TEXT,
            manifest_count INTEGER,
            observed_count INTEGER,
            examined_total INTEGER,
            sampling_rate REAL,
            ballots_used INTEGER,
            had_fake_ballot BOOLEAN,
            ballot_ids TEXT,
            UNIQUE(contest_name, county_name)
        )
    ''')
    
    # Audit metadata
    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    conn.commit()
    return conn

def save_to_database(conn, results, errors, manifest_counts, examined_counts, round_num):
    """Save analysis results to SQLite database."""
    c = conn.cursor()
    timestamp = datetime.utcnow().isoformat()
    
    # Save audit metadata
    c.execute('INSERT OR REPLACE INTO audit_metadata VALUES (?, ?)', 
              ('last_analysis_timestamp', timestamp))
    c.execute('INSERT OR REPLACE INTO audit_metadata VALUES (?, ?)', 
              ('risk_limit', str(RISK_LIMIT)))
    c.execute('INSERT OR REPLACE INTO audit_metadata VALUES (?, ?)', 
              ('gamma', str(GAMMA)))
    c.execute('INSERT OR REPLACE INTO audit_metadata VALUES (?, ?)', 
              ('round', str(round_num)))
    
    # Clear old data for this round
    c.execute('DELETE FROM contest_risk_analysis WHERE round = ?', (round_num,))
    c.execute('DELETE FROM county_sampling_details')
    
    # Save contest results and county details
    county_detail_count = 0
    for contest_name, result in results:
        c.execute('''
            INSERT INTO contest_risk_analysis VALUES 
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            contest_name,
            result['audit_reason'],
            result['min_margin'],
            result['contest_ballot_card_count'],
            result['diluted_margin'],
            result['n'],
            result['discrepancies'],
            result['risk'],
            result['min_rate'],
            result.get('min_rate_county', ''),
            result['counties'],
            result['risk'] <= RISK_LIMIT,
            timestamp,
            round_num
        ))
        
        # Save county details for this contest
        if 'county_data' in result:
            for county, data in result['county_data'].items():
                ballot_ids_json = json.dumps(data.get('ballot_ids', []))
                c.execute('''
                    INSERT INTO county_sampling_details 
                    (contest_name, county_name, manifest_count, observed_count, 
                     examined_total, sampling_rate, ballots_used, had_fake_ballot, ballot_ids)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    contest_name,
                    county,
                    data['manifest_count'],
                    data['observed_count'],
                    examined_counts.get(county, 0),
                    data['sampling_rate'],
                    data.get('n_used', 0),
                    data.get('is_fake', False),
                    ballot_ids_json
                ))
                county_detail_count += 1
    
    conn.commit()
    print(f"\n✓ Saved {len(results)} contests to database")
    print(f"✓ Saved {county_detail_count} county-contest details to database")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Calculate opportunistic and targeted contest risks')
    parser.add_argument('--round', type=int, default=3)
    parser.add_argument('--contest', type=str, help='Specific contest (if omitted, does all)')
    parser.add_argument('--show-work', action='store_true', help='Show detailed calculation')
    parser.add_argument('--targeted-only', action='store_true', help='Only process targeted contests')
    parser.add_argument('--opportunistic-only', action='store_true', help='Only process opportunistic contests')
    parser.add_argument('--db', type=str, default='colorado_rla.db', help='SQLite database path')
    parser.add_argument('--no-db', action='store_true', help='Skip database save')
    args = parser.parse_args()
    
    # Initialize database if needed
    db_conn = None
    if not args.no_db:
        print(f"Initializing database: {args.db}")
        db_conn = create_database(args.db)
        print()
    
    # Load all data once
    manifest_counts, contest_metadata, counties_by_contest, contest_ballots, examined_counts, contest_by_type = load_all_data(args.round)
    
    # Filter contests and organize by type
    contests_by_reason = {
        'state_wide_contest': [],
        'county_wide_contest': [],
        'opportunistic_benefits': [],
    }
    skipped_filter = 0
    
    for name, data in contest_metadata.items():
        if args.contest and name != args.contest:
            skipped_filter += 1
            continue
        
        audit_reason = data.get('audit_reason', '')
        
        if args.targeted_only and audit_reason not in ['county_wide_contest', 'state_wide_contest']:
            skipped_filter += 1
            continue
        if args.opportunistic_only and audit_reason != 'opportunistic_benefits':
            skipped_filter += 1
            continue
        
        # Add to appropriate category (even if no examined ballots)
        if audit_reason in contests_by_reason:
            contests_by_reason[audit_reason].append((name, data, audit_reason))
    
    # Build ordered list: state, county, opportunistic
    contests_to_process = (
        contests_by_reason['state_wide_contest'] +
        contests_by_reason['county_wide_contest'] +
        contests_by_reason['opportunistic_benefits']
    )
    
    total_contests = len(contests_to_process)
    print(f"Processing {total_contests} contests by type:")
    print(f"  State-wide targeted: {len(contests_by_reason['state_wide_contest'])}")
    print(f"  County-wide targeted: {len(contests_by_reason['county_wide_contest'])}")
    print(f"  Opportunistic: {len(contests_by_reason['opportunistic_benefits'])}")
    if skipped_filter > 0:
        print(f"  (Filtered out: {skipped_filter})")
    if not args.show_work:
        print()
    
    # Process each contest with section headers
    results = []
    errors = []
    current_section = None
    
    for contest_name, contest_data, audit_reason in contests_to_process:
        # Print section header when type changes
        if current_section != audit_reason and not args.show_work:
            if current_section is not None:
                print()  # Blank line between sections
            
            if audit_reason == 'state_wide_contest':
                print("=" * 80)
                print(f"STATE-WIDE TARGETED CONTESTS ({len(contests_by_reason['state_wide_contest'])})")
                print("=" * 80)
            elif audit_reason == 'county_wide_contest':
                print("=" * 80)
                print(f"COUNTY-WIDE TARGETED CONTESTS ({len(contests_by_reason['county_wide_contest'])})")
                print("=" * 80)
            elif audit_reason == 'opportunistic_benefits':
                print("=" * 80)
                print(f"OPPORTUNISTIC CONTESTS ({len(contests_by_reason['opportunistic_benefits'])})")
                print("=" * 80)
            current_section = audit_reason
        
        counties = counties_by_contest.get(contest_name, set())
        contest_ballots_per_county = contest_ballots.get(contest_name, {})
        
        result = calculate_contest_risk(contest_name, contest_data, counties, 
                                         contest_ballots_per_county, manifest_counts,
                                         examined_counts, show_work=args.show_work)
        
        if 'error' in result:
            error_info = {
                'name': contest_name,
                'audit_reason': audit_reason,
                'error': result['error'],
                'details': result.get('details', ''),
                'reason': result.get('reason', ''),
                'contest_data': contest_data,
                'counties': list(counties),
            }
            errors.append(error_info)
            
            if args.show_work:
                print(f"ERROR for {contest_name}: {result['error']}")
                if 'details' in result:
                    print(f"  Details: {result['details']}")
                if 'reason' in result:
                    print(f"  Reason: {result['reason']}")
            else:
                # Show error in compact form
                print(f"⊗ {contest_name[:60]:60s} ERROR: {result['error'][:30]}")
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
    
    if errors:
        print()
        print("=" * 80)
        print(f"SKIPPED CONTESTS ({len(errors)})")
        print("=" * 80)
        
        # Group errors by type
        errors_by_type = defaultdict(list)
        for error_info in errors:
            errors_by_type[error_info['error']].append(error_info)
        
        for error_type, error_list in errors_by_type.items():
            print(f"\n{error_type}: {len(error_list)} contests")
            print()
            
            for err in error_list:
                print(f"  {err['name']}")
                print(f"    Audit reason: {err['audit_reason']}")
                
                # Show available data
                contest_data = err['contest_data']
                if contest_data.get('min_margin'):
                    print(f"    min_margin: {contest_data['min_margin']}")
                if contest_data.get('contest_ballot_card_count'):
                    print(f"    contest_ballot_card_count: {contest_data['contest_ballot_card_count']}")
                
                counties_list = err['counties']
                if counties_list:
                    print(f"    Counties: {', '.join(counties_list[:5])}", end="")
                    if len(counties_list) > 5:
                        print(f" ... (+{len(counties_list)-5} more)", end="")
                    print()
                
                if err.get('details'):
                    print(f"    {err['details']}")
                if err.get('reason'):
                    print(f"    → {err['reason']}")
                print()
    
    # Save results to database
    if db_conn:
        save_to_database(db_conn, results, errors, manifest_counts, examined_counts, args.round)
        db_conn.close()
        print(f"✓ Database saved: {args.db}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
