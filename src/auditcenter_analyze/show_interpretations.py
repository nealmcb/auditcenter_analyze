#!/usr/bin/env python3
"""Show interesting columns from contestComparison.csv for a given contest/county/iid."""

import csv
import sys
from pathlib import Path

def has_discrepancy(row):
    """Check if a ballot has a discrepancy."""
    if row['consensus'] == 'NO':
        return True
    cvr = row['choice_per_voting_computer'].strip()
    audit = row['audit_board_selection'].strip()
    return cvr != audit and cvr != '' and audit != ''

def show_contest(contest_name=None, county=None, iid=None, data_file=None, discrepancies_only=True):
    if data_file is None:
        # Default to auditcenter_analyze data directory
        repo_root = Path(__file__).parent.parent.parent
        data_file = repo_root / 'data' / '2024' / 'general' / 'round3' / 'contestComparison.csv'
    
    with open(data_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        # Print header
        print(f"{'County':15s} {'Contest':40s} {'IID':15s} {'CVR':30s} {'Audit':30s} {'Consensus':10s}")
        print('-' * 160)
        
        row_count = 0
        for row in reader:
            match = True
            if contest_name and contest_name.lower() not in row['contest_name'].lower():
                match = False
            if county and county.lower() not in row['county_name'].lower():
                match = False
            if iid and iid not in row['imprinted_id']:
                match = False
            
            if match:
                # Check if we should skip non-discrepancies
                if discrepancies_only and not has_discrepancy(row):
                    continue
                
                cvr = row['choice_per_voting_computer'].strip().strip('"')[:29]
                audit = row['audit_board_selection'].strip().strip('"')[:29]
                iid_short = row['imprinted_id'][:14]
                contest_short = row['contest_name'][:39]
                county_short = row['county_name'][:14]
                
                print(f"{county_short:15s} {contest_short:40s} {iid_short:15s} {cvr:30s} {audit:30s} {row['consensus']:10s}")
                row_count += 1
        
        if row_count == 0:
            print("  No matching rows found.")

if __name__ == '__main__':
    data_file = None
    all_rows = False
    
    # Parse arguments
    args = sys.argv[1:]
    if not args:
        print("Usage: python3 show_contest.py ['contest name' | 'county' | 'imprinted_id'] [--all]")
        print("  or: python3 show_contest.py [-f|--file path/to/file.csv] ['contest name' | ...] [--all]")
        print("  --all: show all rows, not just discrepancies")
        sys.exit(1)
    
    # Check for --all flag
    if '--all' in args:
        all_rows = True
        args = [a for a in args if a != '--all']
    
    # Check for file override
    if '-f' in args or '--file' in args:
        try:
            idx = args.index('-f') if '-f' in args else args.index('--file')
            data_file = args[idx + 1]
            args = args[:idx] + args[idx + 2:]
        except IndexError:
            print("Error: -f/--file requires a file path")
            sys.exit(1)
    
    query = args[0] if args else None
    
    if not query:
        print("Error: please provide a search term")
        sys.exit(1)
    
    # Determine search type
    if query.startswith('102-') or query.startswith('101-') or any(query.startswith(p) for p in ['201-', '202-', '203-', '204-', '105-', '106-', '107-', '108-', '109-', '110-']):
        show_contest(iid=query, data_file=data_file, discrepancies_only=not all_rows)
    elif any(query.lower() in county.lower() for county in ['Adams', 'Alamosa', 'Arapahoe', 'Archuleta', 'Baca', 'Bent', 'Boulder', 'Broomfield', 'Chaffee', 'Cheyenne', 'Clear Creek', 'Conejos', 'Costilla', 'Crowley', 'Custer', 'Delta', 'Denver', 'Dolores', 'Douglas', 'Eagle', 'El Paso', 'Elbert', 'Fremont', 'Garfield', 'Gilpin', 'Grand', 'Gunnison', 'Hinsdale', 'Huerfano', 'Jackson', 'Jefferson', 'Kiowa', 'Kit Carson', 'La Plata', 'Lake', 'Larimer', 'Las Animas', 'Lincoln', 'Logan', 'Mesa', 'Mineral', 'Moffat', 'Montezuma', 'Montrose', 'Morgan', 'Otero', 'Ouray', 'Park', 'Phillips', 'Pitkin', 'Prowers', 'Pueblo', 'Rio Blanco', 'Rio Grande', 'Routt', 'Saguache', 'San Miguel', 'Sedgwick', 'Summit', 'Teller', 'Washington', 'Weld', 'Yuma']):
        show_contest(county=query, data_file=data_file, discrepancies_only=not all_rows)
    else:
        show_contest(contest_name=query, data_file=data_file, discrepancies_only=not all_rows)

