#!/usr/bin/env python3
"""
Investigate the 29 "extra" ballots in Boulder County Round 2.
Find out why they were examined but not in our generated selections.
"""

import hashlib
import csv

SEED = "53417960661093690826"
BASE_PATH = "/srv/s/electionaudits/colorado-rla-2018/neal_ignore/auditcenter-2024g"

# Generate selections
def generate_random_numbers(seed, count, domain_size):
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

# Load Boulder manifest
manifest = []
with open(f"{BASE_PATH}/BoulderBallotManifest.csv", 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        tabulator = row['Tabulator']
        batch = row['Batch']
        num_cards = int(row['# of Ballots'])
        for position in range(1, num_cards + 1):
            manifest.append(f"{tabulator}-{batch}-{position}")

print(f"Boulder manifest: {len(manifest)} cards")

# Generate 106 selections for State Rep 10
selections = generate_random_numbers(SEED, 106, len(manifest))
selected_ballots = {manifest[s-1] for s in selections}

print(f"Generated 106 selections for State Rep 10")
print()

# Load examined ballots
examined = {}
with open(f"{BASE_PATH}/round2/contestComparison.csv", 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get('county_name') == 'Boulder':
            ballot = row['imprinted_id']
            if ballot not in examined:
                examined[ballot] = set()
            examined[ballot].add(row['contest_name'])

print(f"Total examined ballots in Boulder Round 2: {len(examined)}")
print()

# Analyze the 29 "extra" ballots
extra = set(examined.keys()) - selected_ballots

print(f"Ballots examined but NOT in State Rep 10 selections: {len(extra)}")
print()

# Categorize them
has_state_rep = []
has_pe_or_regent = []
has_neither = []

for ballot in extra:
    contests = examined[ballot]
    has_sr = 'State Representative - District 10' in contests
    has_pe = 'Presidential Electors' in contests
    has_regent = 'Regent of the University of Colorado - At Large' in contests
    
    if has_sr:
        has_state_rep.append(ballot)
    elif has_pe or has_regent:
        has_pe_or_regent.append(ballot)
    else:
        has_neither.append(ballot)

print(f"CATEGORIZATION:")
print(f"  {len(has_state_rep)} have State Rep 10 (should have been selected!):")
for b in sorted(has_state_rep)[:5]:
    print(f"    {b}")

print(f"\n  {len(has_pe_or_regent)} have Presidential Electors or Regent (selected for statewide):")
for b in sorted(has_pe_or_regent)[:5]:
    print(f"    {b}")

print(f"\n  {len(has_neither)} have NEITHER State Rep 10, PE, nor Regent:")
for b in sorted(has_neither):
    print(f"    {b} - contests: {', '.join(list(examined[b])[:3])}")

print()
print("=" * 80)
print("CONCLUSION:")
print(f"  Problem 1: {len(has_state_rep)} ballots WITH State Rep 10 not in our 106 selections")
print(f"  Problem 2: {len(has_pe_or_regent)} ballots from statewide (can't verify without CVR)")
print(f"  Problem 3: {len(has_neither)} ballots with no targeted contests at all!")

