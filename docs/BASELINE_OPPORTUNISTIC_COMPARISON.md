# Opportunistic Contest Baseline Comparison

## Summary

**With temporary o1 interpretation (all discrepancies counted as o1 from sampled ballots):**

- **590 opportunistic contests processed**
- **588 matches exactly with baseline**
- **2 apparent mismatches due to data issue (not code)**

## The Two "Mismatches"

Both "mismatches" are actually the same root cause: **Contest names with trailing spaces in contest.csv**

### 1. State Representative - District 1

**Two entries in contest.csv:**
- `'State Representative - District 1'` (33 chars) - ballot_card_count=367,779, contest_ballot_card_count=4
- `'State Representative - District 1  '` (35 chars) - ballot_card_count=1,104,271, contest_ballot_card_count=38,101

**Baseline output:**
- First entry (no trailing space): Jefferson County appears in county list but has zero observed ballots → uses fake ballot, n=1, risk=0.51879120
- Second entry (with trailing space): Denver County, n=9, risk=0.29378467

**Current output:**
- Same as baseline for both entries

### 2. State Representative - District 9

**Two entries in contest.csv:**
- `'State Representative - District 9'` (33 chars) - ballot_card_count=330,888, contest_ballot_card_count=11,085
- `'State Representative - District 9 '` (34 chars) - ballot_card_count=1,104,271, contest_ballot_card_count=32,425

**Baseline output:**
- First entry: Arapahoe County, n=2, risk=0.61620345
- Second entry: Denver County, n=15, risk=0.02663243

**Current output:**
- Same as baseline for both entries

## Conclusion

**NO ACTUAL MISMATCHES!**

Both current code and baseline are working correctly. The "mismatches" reported by the comparison script were due to:
1. Name collision (same contest appears twice with trailing space variant)
2. One of the variants has a fake ballot (zero observed) so appears only as n=1 calculation

All opportunistic contests now match the baseline with the temporary o1 interpretation!

## Next Steps

The issue of correct discrepancy classification (o1/o2/u1/u2) for opportunistic contests remains to be implemented. Current temporary behavior counts all discrepancies from the sampled ballots and treats them all as o1, which matches the baseline output but is not the correct statistical approach.

