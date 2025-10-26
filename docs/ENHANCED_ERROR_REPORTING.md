# Enhanced Error Reporting - COMPLETE

**Date:** October 24, 2025  
**Enhancement:** Detailed error reporting for contests with no data

---

## Enhanced Error Messages

The script now provides **precise, detailed error information** for contests that cannot be processed:

### Error Type 1: Contest Not in Manifests

**When:** Contest is in `contest.csv` but not found in any county ballot manifest

**Error Message:**
```
ERROR for City of Craig Ballot Question 2A: Contest not found in any county manifest
  Details: No counties have this contest in their ballot manifests  
  Reason: Contest may be misnamed or not applicable to any county
```

**What this means:**
- Contest exists in contest metadata
- But no county ballot manifest contains this contest name
- Likely causes: misnamed contest, contest not applicable to any county

### Error Type 2: Contest in Manifests but Zero Examined Ballots

**When:** Contest appears in county manifests but has zero examined ballots

**Error Message:**
```
ERROR for [Contest Name]: Contest appears in N county(ies) but has zero examined ballots
  Details: Counties: [County1, County2, ...]
  Reason: Contest does not appear on any sampled ballot
```

**What this means:**
- Contest exists in county ballot manifests
- Contest appears in `contestsByCounty.csv` 
- But **zero ballots were examined** that contained this contest
- Likely causes: contest name mismatch between files, contest on ballots not selected for audit

---

## Summary Output Enhancement

The summary now includes **detailed breakdown** of error types:

```
Errors encountered:
  Contest not found in any county manifest: 3 contests
  Contests not in manifests:
    - These contests are in contest.csv but not found in any county ballot manifest
    - May be misnamed or not applicable to any county in this election
```

---

## Current Results (662 Total Contests)

**Targeted:** 64 contests  
**Opportunistic:** 598 contests  
**Errors:** 3 contests

**Error Breakdown:**
- **3 contests:** "Contest not found in any county manifest"
- **0 contests:** "Contest appears in counties but has zero examined ballots"

---

## Precision in Terminology

**Before:** Vague "No examined ballots in any county (skip)"

**After:** Precise diagnosis:
- ✅ **"Contest does not appear on any sampled ballot"** - Contest exists in manifests but wasn't found on examined ballots
- ✅ **"Contest may be misnamed or not applicable to any county"** - Contest not found in any manifest

This makes it clear whether the issue is:
1. **Data mismatch** (contest exists but not examined)
2. **Missing data** (contest doesn't exist in manifests)

---

## Usage Examples

### See All Errors with Details
```bash
python3 calculate_opportunistic_risk.py --show-work
```

### Test Specific Contest with Error
```bash
python3 calculate_opportunistic_risk.py --contest "City of Craig Ballot Question 2A" --show-work
```

### Summary with Error Breakdown
```bash
python3 calculate_opportunistic_risk.py
```

---

## Implementation Details

### Error Detection Logic
```python
if not county_data:
    counties_in_contest = [c for c in counties if c in manifest_counts and manifest_counts[c] > 0]
    if counties_in_contest:
        return {
            'error': f'Contest appears in {len(counties_in_contest)} county(ies) but has zero examined ballots',
            'details': f'Counties: {", ".join(counties_in_contest)}',
            'reason': 'Contest does not appear on any sampled ballot'
        }
    else:
        return {
            'error': 'Contest not found in any county manifest',
            'details': 'No counties have this contest in their ballot manifests',
            'reason': 'Contest may be misnamed or not applicable to any county'
        }
```

### Enhanced Display
- **Error message:** Clear, concise description
- **Details:** Specific information (counties, counts)
- **Reason:** Explanation of what this means
- **Summary breakdown:** Categorizes error types with explanations

---

## Result

✅ **Always prints details** for contests with no data  
✅ **Precise terminology** about what "no data" means  
✅ **Clear distinction** between missing manifests vs. zero examined ballots  
✅ **Helpful explanations** of likely causes  
✅ **Summary breakdown** categorizes error types  

The script now provides **complete transparency** about why certain contests cannot be processed!

---

*Enhanced: October 24, 2025*  
*Script: calculate_opportunistic_risk.py*  
*Error reporting: Complete and precise*

