# Vote-Based Estimation: Implementation Plan

## Summary

Replace arbitrary "fake ballot" approach with vote-based estimation using `tabulateCounty.csv` data. This improves accuracy from ~2000% error to ~5% error for contests with zero observed ballots.

---

## Changes Required

### 1. Data Loading (New Function)

```python
def load_vote_totals(data_dir, round_num):
    """
    Load vote totals from tabulateCounty.csv.
    
    Returns:
        dict: {county_name: {contest_name: total_votes}}
    """
    vote_file = data_dir / "tabulateCounty.csv"
    vote_totals = defaultdict(lambda: defaultdict(int))
    
    with open(vote_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            county = row['county_name'].replace(' ', '')  # Normalize
            contest = row['contest_name']
            votes = int(row['votes'])
            vote_totals[county][contest] += votes  # Sum across all choices
    
    return dict(vote_totals)
```

### 2. Update `load_all_data()` Function

**Add to return values:**
```python
def load_all_data(round_num=3):
    # ... existing code ...
    
    # NEW: Load vote totals
    print("Step 5: Loading vote totals...")
    vote_totals = load_vote_totals(data_dir, round_num)
    print(f"  Loaded vote totals for {len(vote_totals)} counties")
    print()
    
    return (manifest_counts, contest_metadata, counties_by_contest, 
            contest_ballots, examined_counts, contest_by_type,
            vote_totals)  # NEW
```

### 3. Update `calculate_contest_risk()` Function

**Add parameter:**
```python
def calculate_contest_risk(contest_name, contest_data, counties, 
                          contest_ballots_per_county, manifest_counts, 
                          examined_counts, vote_totals,  # NEW
                          show_work=False):
```

**Replace Step 1 (Count observed ballots):**

**OLD:**
```python
# Step 1: Count observed ballots per county
for county in counties:
    if county not in manifest_counts:
        continue
    
    ballots = contest_ballots_per_county.get(county, [])
    observed_count = len(ballots)
    
    if observed_count == 0:
        counties_with_zero_observed.append(county)
        # Use 1 fake ballot
        county_data[county] = {
            'manifest_count': manifest_count,
            'observed_count': 1,  # FAKE
            'ballots': [{'iid': 'NONE', ...}],  # FAKE
            'is_fake': True,
        }
```

**NEW:**
```python
# Step 1: Estimate contest ballot cards per county
for county in counties:
    if county not in manifest_counts:
        continue
    
    manifest_count = manifest_counts[county]
    if manifest_count == 0:
        continue
    
    ballots = contest_ballots_per_county.get(county, [])
    observed_count = len(ballots)
    
    # Get vote-based estimate
    vote_total = 0
    if county in vote_totals and contest_name in vote_totals[county]:
        vote_total = vote_totals[county][contest_name]
    
    # Determine estimation method
    if observed_count > 0:
        # Normal case: use observed
        estimated_contest_cards = observed_count
        estimation_method = 'observed'
    elif vote_total > 0:
        # Zero observed, but have votes: use vote-based estimate
        estimated_contest_cards = vote_total
        estimation_method = 'vote_based'
        counties_with_vote_estimation.append(county)
    else:
        # No observations AND no votes: minimal placeholder
        estimated_contest_cards = 0.1
        estimation_method = 'placeholder'
        counties_with_placeholder.append(county)
    
    county_data[county] = {
        'manifest_count': manifest_count,
        'observed_count': observed_count,
        'estimated_contest_cards': estimated_contest_cards,
        'vote_total': vote_total,
        'ballots': ballots,
        'estimation_method': estimation_method,
    }
```

**Replace Step 2 (Calculate sampling rates):**

**OLD:**
```python
# Step 2: Calculate sampling rates
for county, data in county_data.items():
    data['sampling_rate'] = data['observed_count'] / data['manifest_count']
```

**NEW:**
```python
# Step 2: Calculate sampling rates (using estimates)
for county, data in county_data.items():
    data['sampling_rate'] = data['estimated_contest_cards'] / data['manifest_count']
```

**Update Step 4 (Downsampling):**

**Constraint:** Can't use more ballots than we observed!

```python
# Step 4: Downsample to minimum rate
for county, data in county_data.items():
    if county == min_county:
        # Use ALL observed ballots from minimum-rate county
        n_to_use = data['observed_count']
    else:
        # Downsample: manifest × min_rate, but limited by observations
        target = int(data['manifest_count'] * min_rate)
        n_to_use = min(target, data['observed_count'])
    
    ballots_to_use = data['ballots'][:n_to_use]
    data['n_used'] = n_to_use
    data['ballot_ids'] = [b['iid'] for b in ballots_to_use]
    valid_sample.extend(ballots_to_use)
```

**Update show_work output:**

```python
if show_work:
    print("Step 1: Estimate contest ballot cards per county")
    print(f"  Using vote totals from tabulateCounty.csv where available")
    
    for county, data in county_data.items():
        method = data['estimation_method']
        print(f"  {county}:")
        print(f"    ballot_card_count (manifest): {data['manifest_count']:,}")
        print(f"    Total examined ballots: {examined_counts.get(county, 0)}")
        
        if method == 'observed':
            print(f"    Observed with contest: {data['observed_count']}")
            print(f"    Estimation: OBSERVED (actual count)")
        elif method == 'vote_based':
            print(f"    Observed with contest: 0")
            print(f"    Vote total: {data['vote_total']:,}")
            print(f"    Estimation: VOTE-BASED (from tabulateCounty.csv)")
        else:  # placeholder
            print(f"    Observed with contest: 0")
            print(f"    Vote total: 0")
            print(f"    Estimation: PLACEHOLDER (no data available)")
        
        print(f"    Estimated contest cards: {data['estimated_contest_cards']:.1f}")
```

### 4. Update Database Schema

**Rename column:**
```sql
-- OLD:
had_fake_ballot BOOLEAN

-- NEW:
estimation_method TEXT  -- 'observed', 'vote_based', 'placeholder'
```

**Add columns:**
```sql
ALTER TABLE county_sampling_details ADD COLUMN vote_total INTEGER;
ALTER TABLE county_sampling_details ADD COLUMN estimated_contest_cards REAL;
```

**Updated schema:**
```python
c.execute('''
    CREATE TABLE IF NOT EXISTS county_sampling_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contest_name TEXT,
        county_name TEXT,
        manifest_count INTEGER,
        observed_count INTEGER,
        examined_total INTEGER,
        vote_total INTEGER,              -- NEW
        estimated_contest_cards REAL,    -- NEW
        sampling_rate REAL,
        ballots_used INTEGER,
        estimation_method TEXT,           -- NEW (replaces had_fake_ballot)
        ballot_ids TEXT,
        UNIQUE(contest_name, county_name)
    )
''')
```

### 5. Update `save_to_database()` Function

**Add new columns to insert:**
```python
c.execute('''
    INSERT INTO county_sampling_details 
    (contest_name, county_name, manifest_count, observed_count, 
     examined_total, sampling_rate, ballots_used, 
     vote_total, estimated_contest_cards, estimation_method,  -- NEW
     ballot_ids)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (
    contest_name,
    county,
    data['manifest_count'],
    data['observed_count'],
    examined_counts.get(county, 0),
    data['sampling_rate'],
    data.get('n_used', 0),
    data.get('vote_total', 0),                    -- NEW
    data.get('estimated_contest_cards', 0),       -- NEW
    data.get('estimation_method', 'observed'),    -- NEW
    ballot_ids_json
))
```

### 6. Update `main()` Function

**Pass vote_totals through:**
```python
# Load all data once
(manifest_counts, contest_metadata, counties_by_contest, contest_ballots, 
 examined_counts, contest_by_type, vote_totals) = load_all_data(args.round)

# ... later ...

result = calculate_contest_risk(
    contest_name, contest_data, counties, 
    contest_ballots_per_county, manifest_counts,
    examined_counts, vote_totals,  # NEW
    show_work=args.show_work
)
```

---

## Expected Changes in Results

### Contests with Zero Observations (95 cases)

**Example: BRUSH RURAL FIRE in Washington County**

| Metric | Old (Fake) | New (Vote-Based) | Improvement |
|--------|-----------|------------------|-------------|
| Rate | 0.035% | 0.740% | 21× more accurate |
| Estimated cards | 1 (fake) | 21 (from votes) | Realistic |
| Method | Arbitrary | Data-driven | Transparent |

**Overall impact:**
- 94-95 cases now use vote-based estimation (much better)
- 0-1 cases might still need placeholder (100% undervote - extremely rare)

### All Other Contests (2,518 cases)

**Minor changes:**
- Sampling rate calculation unchanged (still uses observed count)
- BUT now have vote_total available for validation/cross-checking
- Can detect anomalies (e.g., observed >> votes → possible data issue)

### Final Risk Values

**Expected:** Very similar, differences in <1% of cases
- Same ballots examined
- Same downsampling logic (limited by observations)
- Only rate calculation is more accurate

**Validation test:**
```bash
# Before:
python3 calculate_opportunistic_risk.py --round 3 > old_results.txt

# After implementing changes:
python3 calculate_opportunistic_risk.py --round 3 > new_results.txt

# Compare final risks:
diff old_results.txt new_results.txt

# Should show:
# - Identical contest lists
# - Identical sample sizes (n)
# - Identical or very similar risk values
# - Different intermediate calculations for ~95 contests
```

---

## Testing Plan

### Unit Tests

1. **Test vote loading:**
```python
def test_load_vote_totals():
    votes = load_vote_totals(test_data_dir, round_num=3)
    assert 'Washington' in votes
    assert 'BRUSH RURAL FIRE' in votes['Washington']
    assert votes['Washington']['BRUSH RURAL FIRE'] == 21
```

2. **Test estimation methods:**
```python
def test_estimation_methods():
    # Case 1: Normal (has observations)
    rate, meta = calculate_rate(observed=2, votes=1007, manifest=13669)
    assert meta['estimation_method'] == 'observed'
    
    # Case 2: Vote-based (zero observed)
    rate, meta = calculate_rate(observed=0, votes=21, manifest=2838)
    assert meta['estimation_method'] == 'vote_based'
    assert abs(rate - 0.00740) < 0.00001
    
    # Case 3: Placeholder (no data)
    rate, meta = calculate_rate(observed=0, votes=0, manifest=1000)
    assert meta['estimation_method'] == 'placeholder'
```

### Integration Tests

1. **Compare to baseline:**
```bash
# Save current results
python3 calculate_opportunistic_risk.py --no-db > baseline.txt

# Implement changes

# Compare new results  
python3 calculate_opportunistic_risk.py --no-db > new.txt
diff baseline.txt new.txt
```

2. **Specific contest verification:**
```bash
# Check BRUSH RURAL FIRE calculation
python3 calculate_opportunistic_risk.py \
  --contest "BRUSH RURAL FIRE PROTECTION DISTRICT BALLOT ISSUE 7A" \
  --show-work
```

### Expected Output Changes

**Before:**
```
Step 1: Observed ballots with contest
  Washington:
    ballot_card_count (manifest): 2,838
    Total examined ballots: 31
    Observed with contest: 1 (FAKE - using 1)
    ESTIMATION: Allows calculation but increases uncertainty
```

**After:**
```
Step 1: Estimate contest ballot cards per county
  Washington:
    ballot_card_count (manifest): 2,838
    Total examined ballots: 31
    Observed with contest: 0
    Vote total: 21
    Estimation: VOTE-BASED (from tabulateCounty.csv)
    Estimated contest cards: 21.0
```

---

## Rollout Plan

1. **Implement changes** in `calculate_opportunistic_risk.py`
2. **Test** on 2024 dataset
3. **Compare** results to baseline
4. **Document** differences (expect ~95 improved estimates)
5. **Update** database schema
6. **Regenerate** `colorado_rla.db`
7. **Update** Datasette metadata to explain new columns
8. **Commit** to git with clear commit message

---

## Documentation Updates Needed

1. **OPPORTUNISTIC_RISK_FINAL.md** - Update methodology section
2. **Datasette metadata.json** - Describe new columns
3. **README.md** - Note improved estimation method
4. **This document** - Mark as implemented

---

## Success Criteria

✓ All 722 contests still analyzed  
✓ Final risk values within 1% of baseline  
✓ 95 "fake ballot" cases replaced with vote-based estimates  
✓ Database has new columns (vote_total, estimated_contest_cards, estimation_method)  
✓ Documentation updated  
✓ Code is clearer and more maintainable  

---

**Ready to implement?**

