# Multi-County Contest Verification Guide

## The Discovery

County IDs are **alphabetical**! From `county_ids.properties`:

```
1 = Adams
2 = Alamosa  
3 = Arapahoe
4 = Archuleta
5 = Baca
6 = Bent
7 = Boulder
... etc (alphabetical order)
```

This means for multi-county contests, manifests are combined in **alphabetical order by county name**.

## How Multi-County Selection Works

### The Algorithm

1. Get all counties that have the contest
2. Sort by county ID (which is alphabetical by name)
3. Concatenate manifests in that order
4. Generate random selections from the combined manifest

### Example: Presidential Electors

**Counties:** All 63 (alphabetically: Adams, Alamosa, Arapahoe, ...)

**Combined Manifest:**
- Adams ballots: [1 to X]
- Alamosa ballots: [X+1 to Y]
- Arapahoe ballots: [Y+1 to Z]
- ... etc ...
- Yuma ballots: [... to 3,239,722]

**Random Selection:**
- Generate numbers in [1, 3,239,722]
- Each number maps to a specific county based on the ranges above

## Critical Insight: Counties vs Examined Ballots

**User's observation:**
> "We may need help for targeted audits of multi-county districts. Especially if e.g. one county has only a small number of ballots in the contest, is included in the random selection, but none of the ballots show up."

### The Problem

For multi-county districts:

#### Example Scenario
Imagine Congressional District 4 spans 21 counties:
- Kit Carson: 10,000 ballots with this contest
- Baca: 5,000 ballots with this contest
- ... 
- Adams: 100 ballots with this contest (very few!)

If we randomly select 100 ballots from the 100,000+ total:
- Most will come from counties with many ballots
- Adams might get 0 selected ballots (by chance)

#### The Issue for Verification

If we only look at `contestComparison.csv`:
- We see examined ballots from 20 counties
- We DON'T see Adams (0 examined)

But to verify the random selection, we need:
- **All 21 counties** in the manifest ordering
- Even though Adams had 0 examined ballots

### The Solution

Use **`contestsByCounty.csv`** not `contestComparison.csv` to determine which counties to include:

```python
# WRONG: Only gets counties with examined ballots
counties_examined = get_from_contestComparison(contest_name)

# RIGHT: Gets ALL counties where contest appears
counties_with_contest = get_from_contestsByCounty(contest_name)
```

## Data Sources

### `contestsByCounty.csv`
Shows **all counties where a contest appears** (regardless of examination):
```csv
county_id,county_name,contest_name,contest_id
1,Adams,Presidential Electors,5278
2,Alamosa,Presidential Electors,5279
... (all 63 counties)
```

### `contestComparison.csv`
Shows **only counties with examined ballots**:
```csv
county_name,contest_name,imprinted_id,...
Adams,Presidential Electors,101-1-1,...
... (only counties with examined ballots)
```

### Why This Matters

For proper verification of multi-county contests:

1. **Get counties from `contestsByCounty.csv`**
   - Gives complete list of counties with the contest
   - Includes counties with 0 examined ballots

2. **Combine manifests in alphabetical (county ID) order**
   - All counties in the list, even if 0 examined
   - This creates the correct domain for random selection

3. **Generate random selections**
   - Use the combined manifest as domain
   - Some counties may get 0 selections (that's fine!)

4. **Verify against `contestComparison.csv`**
   - Check that examined ballots match generated selections
   - Counties with 0 examined are expected if random didn't pick them

## Example: Congressional District 4

From `contestsByCounty.csv`: **21 counties** have this contest

Counties in alphabetical order (by ID):
1. Adams (ID 1)
2. Arapahoe (ID 3)
3. Baca (ID 5)
4. Bent (ID 6)
5. Cheyenne (ID 9)
... 
21. Yuma (ID 63)

From `contestComparison.csv`: **21 counties** had examined ballots
- All 21 counties had at least 1 examined ballot
- No counties with 0 examined in this case

But this doesn't always happen! A county could have:
- The contest available (in contestsByCounty.csv)
- 0 examined ballots (not in contestComparison.csv)
- Still must be included in manifest ordering for verification

## Implementation

### For Multi-County Verification

```python
# Get ALL counties with the contest (not just examined)
county_ids = get_counties_for_contest_from_contestsByCounty(contest_name)

# Load manifests in county ID order
combined_manifest = []
for county_id in sorted(county_ids):
    county_name = COUNTY_IDS[county_id]
    manifest = load_manifest(f"{county_name}BallotManifest.csv")
    combined_manifest.extend(manifest)

# Generate selections
domain_size = len(combined_manifest)
selections = generate_random_numbers(seed, sample_size, domain_size)

# Map to imprinted_ids
expected_ballots = {combined_manifest[s-1] for s in selections}

# Get examined ballots (may be from fewer counties)
examined_ballots = get_from_contestComparison(contest_name)

# Verify
assert examined_ballots ⊆ expected_ballots
```

## Key Distinction

| Data Source | Shows | Use For |
|-------------|-------|---------|
| `contestsByCounty.csv` | All counties where contest **appears** | Building combined manifest |
| `contestComparison.csv` | Counties with **examined ballots** | Verification target |

**Rule:** Always use `contestsByCounty.csv` to determine the manifest ordering, even if some counties had 0 examined ballots.

## Why This Could Matter

### Scenario 1: Small County with Contest
- County has 50 ballots with the contest
- Multi-county contest has 100,000 total ballots
- Random selection picks 100 ballots
- Probability this county gets selected: 50/100,000 × 100 = 0.05%
- **Likely outcome:** 0 examined ballots from this county

### Scenario 2: Verification Mistake
If we forgot to include that county in manifest ordering:
- Our combined manifest would be wrong
- Random number X might map to wrong county/ballot
- Verification would fail even though selection was correct

### Scenario 3: Correct Verification
If we include the county (using contestsByCounty.csv):
- Combined manifest is correct
- Random selections map correctly
- County with 0 examined is expected (none selected by chance)
- Verification succeeds ✓

## Implications

For robust multi-county verification:

1. ✓ **Use contestsByCounty.csv** for county list
2. ✓ **Sort by county ID** (alphabetical order)
3. ✓ **Include ALL counties** even if 0 examined ballots
4. ✓ **Verify examined ⊆ generated** (subset relationship)
5. ✓ **Don't expect all counties** to have examined ballots

## Current Status

The verification tool now:
- Knows counties are ordered alphabetically (by ID)
- Can check `contestsByCounty.csv` for complete county list
- Ready to implement multi-county verification correctly

Next step: Implement the combined manifest approach for multi-county contests.

---

**Date:** October 23, 2025  
**Discovery:** County IDs are alphabetical  
**Key Insight:** Use contestsByCounty.csv, not contestComparison.csv, for manifest ordering  
**Status:** Ready to implement multi-county verification

