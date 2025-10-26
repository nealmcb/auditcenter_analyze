# Domain Size for Random Selection - CONFIRMED

## From the Code

`BallotSelection.java` line 265:
```java
final int domainSize = ballotsCast(contestResult.countyIDs()).intValue();
```

Where `ballotsCast()` returns:
```java
return BallotManifestInfoQueries.totalBallots(countyIds);
```

**This is the total ballots from the manifest(s) for the involved counties.**

## What This Means

### For Single-County Contests
**Domain = Full county manifest**

Example - Boulder State Rep District 10:
- Domain: 396,121 (all Boulder ballot cards)
- NOT 44,675 (cards with State Rep 10)

**User was right:** "If the district is entirely in the county, there is no problem since the random selection remains county-wide."

### For Multi-County Contests
**Domain = Combined manifests of all involved counties**

Example - Presidential Electors (63 counties):
- Domain: Sum of all 63 county manifests
- Manifests combined in county ID (alphabetical) order

## Understanding ballot_card_count vs contest_ballot_card_count

### In contest.csv

These fields describe the contest scope, but **neither directly determines the random selection domain**.

| Field | Meaning | Used For |
|-------|---------|----------|
| `ballot_card_count` | Total cards in involved counties | Roughly matches manifest total |
| `contest_ballot_card_count` | Cards that have this contest | Risk calculations, margin dilution |

### Random Selection Uses

**Domain = Manifest total** (from `BallotManifestInfo` records)

Not directly from either CSV field!

## Why contest_ballot_card_count Exists

Used for:
1. **Risk calculations** - Diluted margin formula
2. **Sample size estimation** - BRAVO algorithm  
3. **Reporting** - How many cards could have this contest
4. **NOT for random selection domain**

## Example: Boulder State Rep District 10

```
From contest.csv:
  ballot_card_count: 396,121
  contest_ballot_card_count: 44,675
  audited_sample_count: 106

From manifest:
  Boulder manifest: 396,121 cards

Random selection:
  Domain: 396,121 (from manifest)
  Selections: 106
  Expected with contest: 106 × (44,675/396,121) ≈ 11.9 ≈ 11 ✓
  Actual examined: 11 ✓
```

The math checks out!

## The Remaining Mystery

If domain = 396,121 and we generate 106 selections:
- ✓ All 106 selections use Boulder manifest positions
- ✓ About 11 will have State Rep 10 (11.3% hit rate)
- ✓ 11 ballots with State Rep 10 were examined

**But:** Of those 11 examined:
- 9 match our generated 106 ✓
- 2 don't match (101-362-181, 106-63-127) ✗

**Possible causes:**
1. **Manifest ordering mismatch** - Our manifest order doesn't match the system's
2. **Multiple tabulators** - Boulder has tabulators 101-110, maybe ordering issue
3. **Data inconsistency** - Maybe contest.csv values don't match actual
4. **Round progression** - Maybe selections carry over differently than expected

## The 14 "No Targeted Contest" Ballots

User clarified:
> "It is fine to end up with ballot cards that have no targeted contests in general. Remember these are just parts of ballots."

**Ah!** These are ballot CARDS, not full ballots. A ballot might have multiple cards:
- Card 1: Federal/State contests
- Card 2: Local contests, tax measures
- Card 3: Judicial retention

If the system selected ballot card #1 for Presidential Electors, the audit board might have examined ALL cards from that ballot packet, including cards with only local contests.

**So Problem 3 might not be a problem at all** - it's expected behavior!

## Revised Understanding

### Problem 1 (REAL): 2 State Rep 10 ballots not in our 106
- Needs debugging
- Manifest ordering or generation issue

### Problem 2 (EXPECTED): 13 from statewide contests
- Can't verify without CVR mapping
- Acknowledged limitation

### Problem 3 (MAYBE OK): 14 with no targeted contests
- Could be other cards from multi-card ballots
- Could be from Presidential Electors/Regent selections
- If Card 1 selected for PE, all cards in packet get examined

## Next Steps

1. **Debug the 2-ballot mismatch** for State Rep 10
   - Check manifest position-by-position
   - Verify tabulator ordering
   - Look for off-by-one errors

2. **Verify multi-card hypothesis** for the 14
   - Check if they're part of multi-card ballot packets
   - See if ballot packet #1 has Presidential Electors

3. **Consider CVR-based verification** for complete solution

---

**Date:** October 23, 2025  
**Key Finding:** Domain = Total manifest (not contest_ballot_card_count)  
**Status:** Approach confirmed correct, investigating 2-ballot mismatch

