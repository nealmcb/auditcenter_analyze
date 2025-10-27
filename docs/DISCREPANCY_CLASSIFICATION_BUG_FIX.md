# Discrepancy Classification Bug Fix

**Date:** 2024-10-27  
**Issue:** Miscalculation of risk due to treating all discrepancies as overstatements  
**Status:** ✅ FIXED  

---

## The Bug

**Original code (WRONG):**
```python
o1 = discrepancies  # Treated ALL discrepancies as one-vote overstatements
o2 = u1 = u2 = 0    # Never used understatements
```

**Problem:** Overstatements and understatements have different impacts on risk:
- **Overstatement:** CVR favors winner more than reality → INCREASES risk
- **Understatement:** CVR favors winner less than reality → DECREASES risk (less conservative)

By treating understatements as overstatements, we were calculating artificially HIGH risk values.

---

## The Fix

**New code (CORRECT):**
```python
# Get ColoradoRLA's correct classifications from contest.csv
o2 = contest_data['two_vote_over_count']
o1 = contest_data['one_vote_over_count'] 
u1 = contest_data['one_vote_under_count']
u2 = contest_data['two_vote_under_count']
```

ColoradoRLA already classified discrepancies correctly. We just need to use their classifications!

---

## Impact on Failed Targeted Contests

### Before Fix: 3 Failures

1. **Conejos County Commissioner District 3:** risk = 0.0484 ✗
2. **Routt County Commissioner - District 1:** risk = 0.0414 ✗
3. **Sedgwick County Commissioner - District 3:** risk = 0.0305 ✗

### After Fix: 2 Failures

1. **Conejos County Commissioner District 3:** risk = 0.0128 ✓ **FIXED!**
2. **Routt County Commissioner - District 1:** risk = 0.0414 ✗ (legitimate)
3. **Sedgwick County Commissioner - District 3:** risk = 0.0305 ✗ (legitimate)

---

## Analysis of Remaining Failures

### Conejos (Now PASSES)

**Discrepancy breakdown:**
- Two-vote understatements: 1
- All others: 0

**What was wrong:**
- Old calculation: Treated as `o1=1` (one-vote overstatement)
- Correct calculation: Should be `u2=1` (two-vote understatement)

**Impact:**
- Old risk: 0.0484 (61% over limit)
- New risk: 0.0128 (57% under limit)
- **Difference: 3.78×** - huge impact!

**Verification:**
- ColoradoRLA status in contest.csv: "risk_limit_achieved" ✓
- Our new calculation: risk = 0.0128 ✓
- **Match!** ColoradoRLA was correct all along.

### Routt (Legitimate Failure)

**Discrepancy breakdown:**
- All zero (no discrepancies)

**Why it fails:**
- Contest size: 16,628 ballot cards
- Margin: 1,400 votes (8.4%)
- Sample: 77 ballots examined
- Risk: 0.0414

**Analysis:**
- With zero discrepancies, this is purely a sample-size issue
- Margin is relatively close (8.4%)
- 77 ballots isn't enough for this margin at 3% risk limit
- Would need ~95-100 ballots to achieve risk limit

**ColoradoRLA status:** "risk_limit_achieved" - **DISCREPANCY!**

This suggests either:
1. ColoradoRLA uses a different risk calculation method, OR
2. There's additional data/logic we're not seeing, OR
3. ColoradoRLA has a bug

### Sedgwick (Legitimate Failure - Barely)

**Discrepancy breakdown:**
- All zero (no discrepancies)

**Why it fails:**
- Contest size: 1,371 ballot cards
- Margin: 116 votes (8.5%)
- Sample: 84 ballots examined
- Risk: 0.0305 (barely over 0.03!)

**Analysis:**
- Very close to passing (0.0305 vs 0.0300)
- Just 1-2 more ballots might have pushed it under
- With zero discrepancies, purely sample-size driven

**ColoradoRLA status:** "risk_limit_achieved" - **DISCREPANCY!**

Same issue as Routt - ColoradoRLA says it passed, we say it barely failed.

---

## Why ColoradoRLA Might Disagree

### Hypothesis 1: Different Risk Calculation

ColoradoRLA might use a different formula or parameters:
- Different gamma value?
- Different diluted margin calculation?
- Sequential testing (SPRT) vs batch Kaplan-Markov?

### Hypothesis 2: Additional Ballots

The `audited_sample_count` column shows:
- Routt: 175 ballots (we found 77)
- Sedgwick: 88 ballots (we found 84)

Maybe there are ballots we're not counting?

**Need to investigate:**
- Are there ballots in other rounds?
- Are we missing some contest comparisons?
- Is there ballot reuse across contests we're not capturing?

### Hypothesis 3: Rounding/Precision

Sedgwick is SO close (0.0305 vs 0.0300) that rounding could explain it.

---

## Summary

**Bug fix impact:**
- ✅ Fixed: Conejos County (was false positive failure)
- ⚠️ Routt County: Legitimate failure OR calculation discrepancy with ColoradoRLA
- ⚠️ Sedgwick County: Barely failing OR rounding/calculation difference

**Confidence level:**
- High confidence the bug fix is correct (Conejos now matches ColoradoRLA)
- Medium confidence on Routt/Sedgwick failures (need deeper investigation)

**Recommendation:**
1. Accept the bug fix (definite improvement)
2. Investigate Routt/Sedgwick discrepancy with ColoradoRLA team
3. Compare our risk calculations against ColoradoRLA's source code
4. Check if there are additional ballots we're missing

---

## Code Changes

### Files Modified
- `analysis/calculate_opportunistic_risk.py`

### Key Changes
1. Load discrepancy counts from contest.csv metadata
2. Use ColoradoRLA's classifications (o1, o2, u1, u2)
3. Remove manual discrepancy counting
4. Pass correct parameters to KM_P_value()

### Testing
```bash
# Test fixed calculation on Conejos
python3 analysis/calculate_opportunistic_risk.py \
  --contest "Conejos County Commissioner District 3" \
  --show-work

# Expected: risk = 0.0128 (PASS)
# Before: risk = 0.0484 (FAIL)
```

---

## Next Steps

1. **Commit this fix** - Critical bug affecting risk calculations
2. **Regenerate database** - All risk values will be more accurate
3. **Investigate Routt/Sedgwick** - Why does ColoradoRLA say they passed?
4. **Document in metadata** - Explain o1/o2/u1/u2 in database schema
5. **Add validation** - Cross-check our risk values against ColoradoRLA's

---

**Conclusion:** This was a critical bug that inflated risk values when understatements were present. The fix brings our calculations into alignment with ColoradoRLA for most contests, with 2 remaining discrepancies that need investigation.

