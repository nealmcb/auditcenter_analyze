# Audit Terminology Clarification - Summary

## Issue Raised

User correctly noted that the terminology was confusing:
- **All contests** have audit data and risk calculations
- **Not all contests** were targeted for full RLA with ballot examination
- Need to distinguish "targeted for RLA" from "had ballots examined" from "has audit data"

## Changes Made

### 1. Enhanced `--list-contests-for-county`

**Before:** Just listed contests with ballot counts
**After:** Shows audit reason markers and summary statistics

```bash
python3 verify_any_contest.py --list-contests-for-county Bent
```

**New Output:**
```
Contests with examined ballots in Bent County:
--------------------------------------------------------------------------------
  Amendment 79 (CONSTITUTIONAL)                           [opportunistic]    ( 32 ballots)
  Bent County Commissioner-District 1                     [TARGETED]         ( 32 ballots)
  Presidential Electors                                   [STATE RLA]        ( 32 ballots)
  ...

Total: 32 contests with examined ballots
  3 were targeted for RLA (county_wide_contest or state_wide_contest)
  29 had opportunistic examination (ballots pulled for other contests)
```

**Markers:**
- `[TARGETED]` = `audit_reason` = `county_wide_contest`
- `[STATE RLA]` = `audit_reason` = `state_wide_contest`
- `[opportunistic]` = `audit_reason` = `opportunistic_benefits`

### 2. New `--targeted-only` Flag

**Purpose:** Show ONLY contests that were targeted for RLA

```bash
python3 verify_any_contest.py --list-contests-for-county Bent --targeted-only
```

**Output:**
```
Contests TARGETED for RLA in Bent County:
--------------------------------------------------------------------------------
  Bent County Commissioner-District 1                     [TARGETED]         ( 32 ballots)
  Presidential Electors                                   [STATE RLA]        ( 32 ballots)
  Regent of the University of Colorado - At Large         [STATE RLA]        ( 32 ballots)

Total: 3 contests with examined ballots
```

### 3. Updated Error Messages

**Changed from:**
> "This contest has 0 audited ballots."

**Changed to:**
> "This contest has 0 examined ballots (audited_sample_count = 0)."
> 
> "Nothing to verify - no physical ballots were selected for examination."
> 
> "Note: The contest may have audit data and risk calculations, but was either:
>   - Not targeted for RLA (audit_reason != county_wide_contest/state_wide_contest)
>   - Targeted but not yet started
>   - Ended in an earlier round"

### 4. Created Comprehensive Documentation

**New file:** `AUDIT_TERMINOLOGY.md`

Explains:
- Three levels of audit activity (data / targeted / examined)
- How to identify targeted contests
- Understanding the 2024 audit scope
- Examples and implications for verification

### 5. Updated Examples

**Updated file:** `VERIFICATION_EXAMPLES.md`

Added terminology section at the top and updated all examples to use correct terminology.

## Key Terminology

### Three Levels of Audit Activity

1. **Has Audit Data** (All ~727 contests)
   - Risk calculations
   - Statistical parameters
   - May show risk below limit
   - Does NOT mean ballots were examined

2. **Targeted for RLA** (**65 contests**)
   - `audit_reason = county_wide_contest` (63)
   - `audit_reason = state_wide_contest` (2)
   - Ballots pulled specifically for these contests
   - Random selection driven by these contests

3. **Had Ballots Examined** (~727 contests)
   - Includes all targeted contests (when started)
   - Plus ~662 opportunistic contests
   - Opportunistic = examined as byproduct of targeted contests

### Audit Reasons

| `audit_reason` | Count | Ballots Pulled? | Meaning |
|----------------|-------|-----------------|---------|
| `county_wide_contest` | 63 | **YES** | County selected for RLA |
| `state_wide_contest` | 2 | **YES** | State selected for RLA |
| `opportunistic_benefits` | ~662 | **NO** | Examined when ballots pulled for others |
| `not_auditable` | Some | **NO** | Uncontested, cannot audit |

## How to Find Targeted Contests

### Quick Method
```bash
# Show only targeted contests
python3 verify_any_contest.py --list-contests-for-county [COUNTY] --targeted-only
```

### From CSV
```bash
# Count by audit_reason
cut -d',' -f2 round3/contest.csv | sort | uniq -c
```

Output:
```
  63 county_wide_contest   <- Targeted by counties
   2 state_wide_contest    <- Targeted by state  
 660 opportunistic_benefits <- Examined opportunistically
```

## Understanding 2024 Colorado General Election

### Statewide Targets (2)
1. **Presidential Electors** - Audited in all 63 counties
2. **Regent of the University of Colorado - At Large** - Audited in all 63 counties

### County-Level Targets (63)
- One contest per county (usually County Commissioner)
- Each county selected its own target
- Examples:
  - Bent County: Commissioner - District 1
  - Adams County: Commissioner - District 5
  - Boulder County: State Representative - District 10

### Opportunistic Examination (~662)
- Constitutional amendments (7)
- Propositions (5)
- Judicial retention questions (~15)
- Other contests appearing on targeted ballots

**Key Point:** No additional ballots were pulled for opportunistic contests. They were examined because they appeared on ballots already pulled for the 65 targeted contests.

## Verification Implications

### Can Verify
Best candidates for random selection verification:
- **Targeted contests** with `audited_sample_count > 0`
- County-wide contests (`ballot_card_count = contest_ballot_card_count`)
- Example: Bent County Commissioner-District 1 ✓

### Challenging to Verify
- Opportunistic contests (selection driven by different contest)
- Multi-county contests (need CVR data)
- Contests with `audited_sample_count = 0`

## Example: Bent County

```bash
python3 verify_any_contest.py --list-contests-for-county Bent --targeted-only
```

**Result:**
- 3 contests targeted for RLA
  - 1 county-level (Commissioner District 1)
  - 2 statewide (Presidential Electors, Regent)
- 29 contests examined opportunistically
- Total: 32 contests with examined ballots

**Ballot Count:** All 32 contests examined on the same 32 physical ballots
- Ballots were selected for Commissioner District 1 (the county target)
- Presidential Electors and Regent also targeted, so appeared on those ballots
- 29 other contests happened to appear on those same ballots

## Files Modified

1. `verify_any_contest.py`
   - Enhanced `list_contests_for_county()` to show audit reasons
   - Added `--targeted-only` flag
   - Updated error messages for clarity

2. `VERIFICATION_EXAMPLES.md`
   - Added terminology section
   - Updated examples with new markers

3. `AUDIT_TERMINOLOGY.md` (NEW)
   - Comprehensive guide to audit terminology
   - Examples and implications
   - How-to guide for finding targeted contests

4. `TERMINOLOGY_UPDATE_SUMMARY.md` (NEW)
   - This file - summary of changes

## Testing

### Bent County
```bash
# All examined contests
python3 verify_any_contest.py --list-contests-for-county Bent
# Shows: 32 contests (3 targeted, 29 opportunistic)

# Only targeted
python3 verify_any_contest.py --list-contests-for-county Bent --targeted-only
# Shows: 3 contests (1 county + 2 state)
```

### Adams County
```bash
python3 verify_any_contest.py --list-contests-for-county Adams --targeted-only
# Shows: 3 contests (Commissioner District 5 + 2 statewide)
```

### Boulder County
```bash
python3 verify_any_contest.py --list-contests-for-county Boulder --targeted-only
# Shows: 3 contests (State Rep District 10 + 2 statewide)
```

All working correctly ✓

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| Terminology | "audited" (ambiguous) | "examined" / "targeted for RLA" (clear) |
| Contest listing | Just counts | Shows audit reasons with markers |
| Filtering | Not available | `--targeted-only` flag |
| Error messages | Generic | Explains the distinction |
| Documentation | Scattered | Comprehensive `AUDIT_TERMINOLOGY.md` |

## For Users

**To find contests targeted for RLA in your county:**
```bash
python3 verify_any_contest.py --list-contests-for-county [COUNTY] --targeted-only
```

**To understand what each marker means:**
Read `AUDIT_TERMINOLOGY.md`

**To verify a targeted contest:**
```bash
python3 verify_any_contest.py --contest "Contest Name" --county "County"
```

---

**Last Updated:** October 23, 2025  
**Context:** 2024 Colorado General Election RLA  
**Issue:** Terminology clarification (targeted vs examined vs data)  
**Status:** ✓ Complete

