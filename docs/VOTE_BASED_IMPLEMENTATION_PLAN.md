# Contest Sampling Factor: Implementation Plan

## Summary

Replace arbitrary "fake ballot" approach with **contest sampling factor** calculation using vote totals from `tabulateCounty.csv` combined with overall sampling rates. This accounts for BOTH contest prevalence AND sampling intensity.

**Key Formula:**
```
contest_sampling_factor = (votes / manifest_count) × (examined_total / manifest_count)
```

This improves accuracy from ~2000% error to ~5% error for contests with zero observed ballots, AND correctly handles different overall sampling rates across counties.

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

**Replace Step 1 (Count observed ballots) & Step 2 (Calculate sampling rates):**

**OLD:**
```python
# Step 1: Count observed ballots per county
for county in counties:
    ballots = contest_ballots_per_county.get(county, [])
    observed_count = len(ballots)
    
    if observed_count == 0:
        # Use 1 fake ballot
        county_data[county] = {
            'manifest_count': manifest_count,
            'observed_count': 1,  # FAKE
            'ballots': [{'iid': 'NONE', ...}],  # FAKE
            'is_fake': True,
        }

# Step 2: Calculate sampling rates
for county, data in county_data.items():
    data['sampling_rate'] = data['observed_count'] / data['manifest_count']
```

**NEW:**
```python
# Step 1: Calculate contest sampling factor per county
for county in counties:
    if county not in manifest_counts:
        continue
    
    manifest_count = manifest_counts[county]
    examined_total = examined_counts.get(county, 0)
    if manifest_count == 0 or examined_total == 0:
        continue
    
    ballots = contest_ballots_per_county.get(county, [])
    observed_count = len(ballots)
    
    # Get vote total for this contest in this county
    vote_total = 0
    if county in vote_totals and contest_name in vote_totals[county]:
        vote_total = vote_totals[county][contest_name]
    
    # Calculate contest_sampling_factor
    # = (contest_prevalence) × (overall_sampling_rate)
    # = (votes / manifest) × (examined_total / manifest)
    
    if observed_count > 0:
        # Normal case: use observed count for contest prevalence
        contest_prevalence = observed_count / manifest_count
        estimation_method = 'observed'
    elif vote_total > 0:
        # Zero observed: use votes as proxy for contest prevalence
        contest_prevalence = vote_total / manifest_count
        estimation_method = 'vote_based'
    else:
        # No observations AND no votes: minimal placeholder
        contest_prevalence = 0.1 / manifest_count
        estimation_method = 'placeholder'
    
    overall_sampling_rate = examined_total / manifest_count
    contest_sampling_factor = contest_prevalence × overall_sampling_rate
    
    county_data[county] = {
        'manifest_count': manifest_count,
        'examined_total': examined_total,
        'observed_count': observed_count,
        'vote_total': vote_total,
        'contest_prevalence': contest_prevalence,
        'overall_sampling_rate': overall_sampling_rate,
        'contest_sampling_factor': contest_sampling_factor,
        'ballots': ballots,
        'estimation_method': estimation_method,
    }

# Step 2: Find minimum contest_sampling_factor
min_factor = min(data['contest_sampling_factor'] for data in county_data.values())
min_county = min(county_data.items(), 
                 key=lambda x: x[1]['contest_sampling_factor'])[0]
```

**Update Step 3 & 4 (Downsampling):**

**Constraint:** Can't use more ballots than we observed!

```python
# Step 3: Display minimum contest_sampling_factor
if show_work:
    print(f"\nStep 3: Minimum contest_sampling_factor")
    print(f"  {min_factor:.10f} ({min_county})")

# Step 4: Downsample to minimum factor
for county, data in county_data.items():
    if county == min_county:
        # Use ALL observed ballots from minimum-factor county
        n_to_use = data['observed_count']
    else:
        # Downsample by factor ratio
        # ratio = min_factor / this_county_factor
        # n_to_use = observed_count × ratio
        ratio = min_factor / data['contest_sampling_factor']
        target = int(data['observed_count'] * ratio)
        n_to_use = min(target, data['observed_count'])
    
    ballots_to_use = data['ballots'][:n_to_use]
    data['n_used'] = n_to_use
    data['ballot_ids'] = [b['iid'] for b in ballots_to_use]
    valid_sample.extend(ballots_to_use)
```

**Update show_work output:**

```python
if show_work:
    print("Step 1: Calculate contest sampling factor per county")
    print(f"  Formula: (contest_prevalence) × (overall_sampling_rate)")
    print(f"         = (votes or observed / manifest) × (examined_total / manifest)")
    print()
    
    for county, data in county_data.items():
        method = data['estimation_method']
        print(f"  {county}:")
        print(f"    manifest_count: {data['manifest_count']:,}")
        print(f"    examined_total: {data['examined_total']}")
        print(f"    observed_with_contest: {data['observed_count']}")
        
        if method == 'vote_based':
            print(f"    vote_total: {data['vote_total']:,}")
            print(f"    Estimation: VOTE-BASED")
        
        print(f"    contest_prevalence: {data['contest_prevalence']:.8f}")
        print(f"    overall_sampling_rate: {data['overall_sampling_rate']:.8f}")
        print(f"    contest_sampling_factor: {data['contest_sampling_factor']:.10f}")
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
ALTER TABLE county_sampling_details ADD COLUMN contest_prevalence REAL;
ALTER TABLE county_sampling_details ADD COLUMN overall_sampling_rate REAL;
ALTER TABLE county_sampling_details ADD COLUMN contest_sampling_factor REAL;
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

## Detailed Worked Example

### BRUSH RURAL FIRE PROTECTION DISTRICT BALLOT ISSUE 7A

**Counties:** Morgan, Washington

#### Input Data

**Morgan County:**
- manifest_count: 13,669
- examined_total: 39 ballots
- observed_with_contest: 2 ballots
- vote_total: 452 + 555 = 1,007 votes

**Washington County:**
- manifest_count: 2,838
- examined_total: 31 ballots
- observed_with_contest: 0 ballots
- vote_total: 10 + 11 = 21 votes

#### Step 1: Calculate contest_sampling_factor

**Morgan (has observations):**
```
contest_prevalence = observed / manifest
                   = 2 / 13,669
                   = 0.00014632

overall_sampling_rate = examined_total / manifest
                      = 39 / 13,669
                      = 0.00285285

contest_sampling_factor = 0.00014632 × 0.00285285
                        = 0.0000004174
```

**Washington (zero observed - use votes):**
```
contest_prevalence = votes / manifest
                   = 21 / 2,838
                   = 0.00740028

overall_sampling_rate = examined_total / manifest
                      = 31 / 2,838
                      = 0.01092323

contest_sampling_factor = 0.00740028 × 0.01092323
                        = 0.0000808386
```

#### Step 2: Find Minimum

```
min_factor = 0.0000004174 (Morgan)  ← Morgan is minimum!
```

**Why Morgan?** Even though Morgan has higher contest prevalence (0.146% vs 0.74%), Morgan's lower overall sampling rate (0.285% vs 1.09%) makes the combined factor smaller.

#### Step 3: Downsample

**Morgan (minimum - use all):**
```
Use ALL 2 observed ballots
```

**Washington (downsample):**
```
ratio = min_factor / factor_Washington
      = 0.0000004174 / 0.0000808386
      = 0.00516

target = observed × ratio
       = 0 × 0.00516
       = 0 ballots (can't use what we didn't observe!)
```

#### Final Sample

```
Total uniform sample: 2 ballots (both from Morgan)
Washington contribution: 0 (correctly - examined none)
```

### Key Insight

**The contest_sampling_factor correctly identified Morgan as the constraint** because:
- Morgan's overall sampling was less intensive (39/13,669 vs 31/2,838)
- Even though the contest was MORE common in Morgan (2/13,669 vs 0/2,838 observed)
- The **product** of both factors determines the effective sampling

This is much more accurate than the fake ballot method which would have incorrectly identified Washington as minimum!

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

