# Opportunistic Contests Enhancement

## Issue
The tool reported "0 examined ballots" for opportunistic contests, even though physical ballot cards were actually examined for these contests. This was misleading.

## Root Cause
The `audited_sample_count` field in `contest.csv` only counts ballots specifically targeted for that contest. For opportunistic contests (`audit_reason = opportunistic_benefits`), this value is 0 even when ballots were examined.

## Solution
Enhanced the verification tool to:
1. Check `contestComparison.csv` for actual examined ballots
2. Report the actual count of examined ballot cards
3. Calculate what the sample size would have been if the contest had been targeted
4. Explain that the ballots were selected for a different (targeted) contest

## Examples

### Amendment 79 (CONSTITUTIONAL) - Bent County
```bash
python3 verify_any_contest.py --county Bent --contest "Amendment 79 (CONSTITUTIONAL)"
```

**Output:**
```
✓ Found contest data in round 3
  Status: in_progress
  County Ballot Card Count: 4,746,866
  Contest Ballot Card Count: 3,239,682
  Audited Sample Count: 0

ℹ NOTE: This contest was NOT targeted for RLA (audit_reason = opportunistic_benefits)
  BUT 32 ballot cards with this contest were examined opportunistically
  (appeared on ballots pulled for other targeted contests).

  The contest.csv shows audited_sample_count = 0 because the contest wasn't targeted,
  but we can see from contestComparison.csv that 32 ballots were examined.

  Random selection verification: The ballots were selected for a DIFFERENT contest.
  To verify selection, you would need to identify which targeted contest drove the selection.

  If this contest HAD been targeted for RLA, the estimated sample size would have been:
    ~665 ballots (based on margin of 741720)
```

**Interpretation:**
- 32 ballots examined (same ballots pulled for Bent County Commissioner-District 1)
- If Amendment 79 had been targeted in Bent County, would need ~665 ballots
- Since only 32 were examined, this wasn't enough for a full RLA of Amendment 79
- But the examination happened opportunistically at no additional cost

### Colorado Court of Appeals Judge - Schutz - Boulder County
```bash
python3 verify_any_contest.py --county Boulder --contest 'Colorado Court of Appeals Judge - Schutz'
```

**Output:**
```
ℹ NOTE: This contest was NOT targeted for RLA (audit_reason = opportunistic_benefits)
  BUT 63 ballot cards with this contest were examined opportunistically
  (appeared on ballots pulled for other targeted contests).

  If this contest HAD been targeted for RLA, the estimated sample size would have been:
    ~716 ballots (based on margin of 712233)
```

**Interpretation:**
- 63 ballots examined in Boulder
- Would need ~716 if targeted
- Boulder pulled ballots for State Representative - District 10 and the statewide contests
- This judicial retention appeared on those ballots

### Bent County Court - Clark - Bent County
```bash
python3 verify_any_contest.py --county Bent --contest "Bent County Court - Clark"
```

**Output:**
```
ℹ NOTE: This contest was NOT targeted for RLA (audit_reason = opportunistic_benefits)
  BUT 32 ballot cards with this contest were examined opportunistically

  If this contest HAD been targeted for RLA, the estimated sample size would have been:
    ~338 ballots (based on margin of 748)
```

**Interpretation:**
- Local county-level contest (retention)
- 32 ballots examined
- Would need ~338 if targeted
- Examined because it appeared on ballots for Bent County Commissioner-District 1

## Understanding the Numbers

### Why audited_sample_count = 0?
The `audited_sample_count` in `contest.csv` tracks ballots pulled **specifically for that contest**. For opportunistic contests, no ballots were pulled specifically for them, so this count is 0.

### Where do the examined ballots come from?
From `contestComparison.csv` - this shows every ballot card that was examined and what was recorded for each contest on that ballot.

### What does "would have been ~X ballots" mean?
This is calculated using the BRAVO optimistic sample size formula:
```python
diluted_margin = margin / (margin + 2 * ballot_card_count)
gamma = 1 / diluted_margin
estimated_sample = ceil(-2 * gamma * ln(0.03) / diluted_margin)
```

This shows what would have been needed for a full RLA if the contest had been targeted.

## Implications for Verification

### Can't Verify Random Selection Directly
For opportunistic contests, you cannot directly verify the random selection because:
- The ballots were selected for a **different** contest
- The random number domain and selection was driven by the targeted contest
- The opportunistic contest just happens to appear on those ballots

### What You CAN Verify
1. **Count of examined ballots** - Check `contestComparison.csv` matches expectations
2. **Which targeted contest drove selection** - Identify the contest that caused these ballots to be pulled
3. **Targeted contest selection** - Verify the random selection for the targeted contest

### Example Verification Path
To verify Amendment 79 examination in Bent County:
1. Verify random selection for **Bent County Commissioner-District 1** (the targeted contest)
2. Those same 32 ballots also had Amendment 79 on them
3. Therefore, Amendment 79 was examined on those 32 ballots opportunistically

## Key Distinctions

| Aspect | Targeted Contest | Opportunistic Contest |
|--------|------------------|----------------------|
| `audit_reason` | `county_wide_contest` or `state_wide_contest` | `opportunistic_benefits` |
| `audited_sample_count` | Count of ballots pulled for this contest | Usually 0 |
| Actual examined ballots | Check `contestComparison.csv` | Check `contestComparison.csv` |
| Random selection | Done specifically for this contest | Done for a different contest |
| Verification | Can verify the selection | Cannot verify directly; verify the targeted contest instead |

## Code Changes

Enhanced `verify_any_contest.py`:

```python
if audited_sample_count == 0:
    if audit_reason == 'opportunistic_benefits':
        # Check contestComparison.csv for actual examined ballots
        actual_examined = count_from_contestComparison(contest_name, county)
        
        if actual_examined > 0:
            print(f"ℹ NOTE: This contest was NOT targeted for RLA")
            print(f"  BUT {actual_examined} ballot cards were examined opportunistically")
            
            # Calculate hypothetical sample size
            estimated_sample = calculate_sample_size(margin, ballot_card_count)
            print(f"  If targeted, would have needed ~{estimated_sample} ballots")
```

## Benefits

1. **Accurate Reporting** - Users see the actual number of examined ballots
2. **Educational** - Explains the difference between targeted and opportunistic
3. **Context** - Shows what sample size would have been needed if targeted
4. **Transparency** - Makes clear that the contest wasn't targeted but was examined

## Files Modified

- `verify_any_contest.py` - Enhanced to check `contestComparison.csv` for opportunistic contests

## Testing

Tested with:
- ✓ Statewide constitutional amendment (Amendment 79)
- ✓ Statewide judicial retention (Court of Appeals Judge)
- ✓ County-level judicial retention (Bent County Court)

All correctly report actual examined ballot counts and calculated sample sizes.

---

**Date:** October 23, 2025  
**Issue:** Correctly report examined ballots for opportunistic contests  
**Status:** ✓ Complete

