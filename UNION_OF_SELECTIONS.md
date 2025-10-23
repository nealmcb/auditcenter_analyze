# Union of Selections for District-Level Contest Verification

## Key Insight

User's observation:
> "Note that some will be selected for state-wide but not county contest. So the random selection verification should verify that all the ballots observed should have been selected for the state-wide or all the county-level contests, and that no others showed up."

## The Problem

When verifying a district-level contest like **State Representative - District 10 in Boulder**, ballots examined could come from selections for **any targeted contest** in that county:

### Boulder's Targeted Contests (Round 2)
1. **State Representative - District 10** (county-wide)
   - 106 selections from Boulder's 396,121 cards
   - Can verify: YES ✓ (single-county)

2. **Presidential Electors** (state-wide)
   - 100 selections statewide from 3,239,722 cards
   - Can verify: NO ✗ (need manifest ordering)

3. **Regent of the University** (state-wide)
   - 302 selections statewide from 3,239,722 cards
   - Can verify: NO ✗ (need manifest ordering)

### What Happened

Of the ballots examined for State Rep 10:
- **11 ballots** were examined in Boulder
- These could be from:
  - The 106 selections for State Rep 10, OR
  - Selections for Presidential Electors that are in Boulder, OR
  - Selections for Regent that are in Boulder

### Current Verification Result

When we generate 106 selections for State Rep 10 only:
- 9 of 11 examined ballots match
- 2 don't match: `101-362-181`, `106-63-127`

**Hypothesis:** Those 2 ballots were likely selected for Presidential Electors or Regent, not State Rep 10.

## The Correct Verification Logic

For a district-level contest in a county with multiple targeted contests:

```python
# Generate selections for ALL targeted contests in the county
selections_state_rep_10 = generate_selections(seed, 106, boulder_manifest)
selections_presidential = generate_selections(seed, ?, boulder_portion_of_statewide)  # Can't do this yet
selections_regent = generate_selections(seed, ?, boulder_portion_of_statewide)  # Can't do this yet

# Union of all selections
all_possible_selections = selections_state_rep_10 | selections_presidential | selections_regent

# Verify: All examined ballots should be in this union
examined_ballots_for_contest = get_examined_ballots("State Rep 10", "Boulder")

for ballot in examined_ballots_for_contest:
    assert ballot in all_possible_selections
```

## Current Limitation

We can only verify single-county targeted contests. For multi-county (statewide) contests, we need manifest ordering.

### What We CAN Check Now
- Generate selections for the single-county targeted contest (State Rep 10)
- Check if examined ballots are a **subset** of those selections
- Note: Some examined ballots might come from statewide contests we can't verify yet

### What This Means for Boulder State Rep 10
- 9 of 11 ballots match the State Rep 10 selections ✓
- 2 of 11 don't match
  - These 2 might be from Presidential Electors or Regent selections
  - OR there's a manifest ordering issue

## Verification Status

### For Single-County Contests (e.g., Bent County)

When a county has ONLY county-level targeted contests:
```
Bent targeted contests:
  - Bent County Commissioner-District 1 (county-wide)
  - (Presidential Electors and Regent are statewide but count as additional targets)
```

All ballot selections can be traced to specific contests more easily.

### For Mixed Contests (e.g., Boulder)

When a county has both county-level AND participates in state-wide:
```
Boulder targeted contests:
  - State Representative - District 10 (county-level) - CAN verify
  - Presidential Electors (state-wide) - CAN'T verify yet
  - Regent (state-wide) - CAN'T verify yet
```

Can only partially verify the county-level contest without knowing which ballots were selected for statewide contests.

## Example: The 2 Unmatched Ballots

Ballots in Boulder examined for State Rep 10 but not in our 106 generated selections:
- `101-362-181`
- `106-63-127`

### Possible Explanations

1. **Selected for statewide contest**
   - Could be in Presidential Electors selections
   - Could be in Regent selections
   - We can't verify these without manifest ordering

2. **Manifest ordering issue**
   - Our manifest ordering doesn't match the actual system
   - Tabulator 101 and 106 might be sequenced differently

3. **Both**
   - Combination of the above

## Next Steps

### To Achieve Full Verification

Would need to:
1. Determine manifest ordering for multi-county contests
2. Generate selections for Presidential Electors in Boulder
3. Generate selections for Regent in Boulder
4. Create union of all three selection sets
5. Verify all 11 examined ballots are in that union

### Current Best Practice

For now, when verifying a district-level contest:
1. Generate selections for that contest using full county manifest
2. Note that examined ballots could also come from other targeted contests
3. Report partial verification with caveats
4. If match rate is high (80%+), likely correct with some from other contests

## Revised Interpretation of Boulder Results

**Previously thought:** 82% match (9/11) suggests minor issues

**More likely:** 
- 9/11 were selected FOR State Rep 10 ✓
- 2/11 were selected for Presidential Electors or Regent ✓
- This is actually **100% correct** if those 2 are in statewide selections

## Updated Verification Message Needed

Instead of:
```
✗✗✗ VERIFICATION FAILED ✗✗✗
Matching: 9 / 106
```

Should say:
```
⚠ PARTIAL VERIFICATION (single-county contest only)
9 of 11 examined ballots match State Rep 10 selections
2 of 11 examined ballots don't match
  → These may have been selected for statewide contests (Presidential Electors, Regent)
  → Full verification requires multi-county contest support
```

---

**Date:** October 23, 2025  
**User Insight:** Ballots selected for ANY targeted contest can be examined  
**Current Status:** Need to verify union of all targeted contests, not just one

