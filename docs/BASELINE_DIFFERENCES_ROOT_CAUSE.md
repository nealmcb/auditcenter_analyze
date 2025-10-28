# Root Cause Analysis: Baseline vs Current Risk Differences

## The Problem

**28 contests show differences** between baseline (commit f7079683) and current output.

**CRITICAL BUG IN CURRENT CODE:** The current code incorrectly reads discrepancy counts from `contest.csv` for opportunistic contests. 

**For opportunistic contests, `contest.csv` does NOT contain discrepancy information** because these contests were not targeted for audit - they are only counted when found on ballots sampled for other contests.

## The Correct Approach (What Baseline Did)

The baseline code correctly:
1. Loaded the opportunistic ballot sample
2. Checked each ballot for discrepancies using `has_discrepancy(b)`
3. Counted how many discrepancies existed in **that specific sample**

**Example: City of Pueblo Ballot Question 2A**
- Baseline found: 1 discrepancy (ballot iid=105-515-26: cvr="No", audit="Yes")
- Risk calculation used: o1=1
- Result: risk=0.49774

## The Wrong Approach (What Current Code Does)

The current code incorrectly:
1. Reads discrepancy counts from `contest.csv`
2. For opportunistic contests, `contest.csv` shows 0 discrepancies
3. Uses o1=0 in risk calculation

**Example: City of Pueblo Ballot Question 2A**
- Current reads from contest.csv: 0 discrepancies
- Risk calculation used: o1=0  
- Result: risk=0.25822

## Root Cause Summary

The current code has **TWO CRITICAL BUGS**:

### Bug #1: Counting Wrong Source for Opportunistic Contests
- **Current (WRONG):** Reads from contest.csv → Always shows 0 for opportunistic
- **Baseline (CORRECT):** Counts from actual sampled ballots in contestComparison.csv

### Bug #2: Not Classifying Discrepancy Types
- **Baseline:** Treats all as o1 (wrong classification but at least counts them)
- **Current:** Needs to classify o1/o2/u1/u2 based on winner/loser choices

## What Needs to Be Fixed

1. **For opportunistic contests:** Count discrepancies from the actual ballot samples, not contest.csv
2. **Classify discrepancies correctly:** Determine if each discrepancy is o1/o2/u1/u2 based on:
   - Whether CVR or audit choice was the winner
   - Whether it's a 1-vote or 2-vote error
3. **Apply the correct risk formula** with proper o1/o2/u1/u2 counts

The baseline got the counting right (for opportunistic contests) but used wrong classification.
The current code uses wrong counting (for opportunistic contests) but right classification approach.

Both are wrong, but in different ways.

