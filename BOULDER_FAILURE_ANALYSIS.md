# Boulder County Verification Failures - Analysis

## Summary of Investigation

Boulder County Round 2 shows **29 examined ballots NOT in our generated selections**.

After detailed investigation, these 29 ballots fall into THREE categories:

## Problem 1: State Rep 10 Ballots Not Generated (2 ballots)

**Ballots:**
- `101-362-181`
- `106-63-127`

**Issue:** These ballots HAVE State Representative - District 10 on them and were examined, but they were NOT in our 106 generated selections.

**This is a REAL FAILURE** - Our random generation is wrong or the manifest ordering is incorrect.

**Next steps:**
- Verify these ballot positions in the manifest
- Check if there's a manifest ordering issue
- Debug the random number generation

## Problem 2: Statewide Contest Ballots (13 ballots)

**Examples:**
- `101-311-107`
- `101-314-127`
- `101-58-157`
- `102-131-133`
- `102-224-85`
... (8 more)

**Issue:** These ballots have Presidential Electors and/or Regent on them, but not State Rep 10.

**Expected:** These were selected for Presidential Electors or Regent (statewide contests).

**Why we can't verify:** Presidential Electors and Regent have `ballot_card_count ≠ contest_ballot_card_count`, meaning the random selection uses a contest-specific domain that requires CVR data to map.

**This is EXPECTED** - We acknowledged we can't verify statewide contests without CVR.

## Problem 3: Ballots With NO Targeted Contests (14 ballots!)

**Ballots:**
- `101-187-104` - has: City of Boulder 2C, 2D, 2E, Propositions, RTD 7A
- `102-122-200` - has: City of Boulder 2C, 2D, 2E, Propositions, RTD 7A
- `102-322-346` - has: City of Longmont 3A, Propositions, RTD 7A, St Vrain
- `103-147-152` - has: City of Longmont 3A, Propositions, RTD 7A, St Vrain
- `103-91-140` - has: City of Boulder 2C, 2D, 2E, Propositions
... (9 more)

**Issue:** These ballots have:
- ✗ NO State Representative - District 10
- ✗ NO Presidential Electors
- ✗ NO Regent
- ✓ ONLY opportunistic contests

**This is COMPLETELY UNEXPLAINED!**

These ballots should not have been selected based on any of the 3 targeted contests in Boulder.

**Possible explanations:**
1. There's a 4th targeted contest we're missing
2. Ballots were selected through a different mechanism
3. Data error in contest.csv or contestComparison.csv
4. Misunderstanding of how the audit system works

## Verification Numbers

### Round 2 Boulder
- **Targeted contests:** 3
  - Presidential Electors: 100 selections statewide
  - Regent: 302 selections statewide
  - State Representative - District 10: 106 selections county-wide

- **Examined ballots:** 135 total unique ballots
  - Presidential Electors: 63 examined
  - Regent: 63 examined
  - State Rep 10: 11 examined

### Our Generation
- **State Rep 10:** 106 selections from [1, 396,121]
- **Presidential Electors:** Skipped (needs CVR)
- **Regent:** Skipped (needs CVR)
- **Total generated:** 106 unique ballots

### The Gap
- Generated: 106
- Examined: 135
- Difference: 29 ballots
  - 2 have State Rep 10 (Problem 1)
  - 13 have PE/Regent (Problem 2)
  - 14 have none of the above (Problem 3)

## Investigation Needed

### For Problem 1 (2 ballots)
Check manifest positions:
```bash
# Where is 101-362-181 in the manifest?
# Where is 106-63-127 in the manifest?
# Were these positions in our 106 generated random numbers?
```

### For Problem 2 (13 ballots)
Verify statewide selections:
```bash
# Generate selections for Presidential Electors using combined statewide manifest
# Generate selections for Regent using combined statewide manifest  
# Check if these 13 ballots are in those selections
```

### For Problem 3 (14 ballots)
**This is the critical mystery:**
```bash
# What mechanism selected these ballots?
# Check for any other targeted contests
# Check system logs or documentation
# Verify data integrity
```

## Comparison to Bent County

Bent County shows **PERFECT MATCH** (32/32).

**Why?**
- Simple case: only 1 county-wide targeted contest
- All ballots selected for that contest
- Statewide contests (PE, Regent) appear on same ballots
- No complexity

**Boulder is more complex:**
- District-level contest (State Rep 10)
- Multiple tabulators (101-110)
- Different ballot styles in different parts of county
- May have additional selection mechanisms we don't understand

## Recommendations

1. **Fix Problem 1 first** - Debug why 2 ballots with State Rep 10 aren't in our 106
2. **Document Problem 2** - Known limitation (statewide CVR requirement)
3. **Solve Problem 3** - Critical to understand where those 14 ballots came from

**Problem 3 is the most concerning** because it suggests either:
- Our understanding of the system is incomplete
- The data has issues
- There's a selection mechanism we're not aware of

---

**Created:** October 23, 2025  
**Status:** Investigation complete, problems categorized  
**Next Step:** Debug Problem 1, investigate Problem 3

