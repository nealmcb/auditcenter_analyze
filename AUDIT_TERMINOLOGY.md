# Colorado RLA Audit Terminology Guide

## Important Distinctions

### What Does "Audited" Mean?

In the context of Colorado's Risk-Limiting Audit (RLA), it's important to distinguish between different types of "audit" activity:

## Three Levels of Audit Activity

### 1. **Has Audit Data**
**All contests** in the election have some audit data:
- Risk calculations
- Statistical parameters
- Margin information
- May even show a risk value below the risk limit

**This does NOT mean ballots were examined.**

### 2. **Targeted for RLA**
Some contests are **specifically selected** for risk-limiting audit:
- `audit_reason = county_wide_contest` (63 contests in 2024)
- `audit_reason = state_wide_contest` (2 contests: Presidential Electors, Regent)
- These contests will have physical ballots pulled and examined
- Total: **65 contests targeted for RLA in 2024 General Election**

### 3. **Had Ballots Examined**
Contests where physical ballots were actually examined:
- Includes all **targeted contests** (when they've started)
- Plus **opportunistic contests** (`audit_reason = opportunistic_benefits`)
  - These appear on ballots that were pulled for targeted contests
  - They get examined "for free" since the ballot is already in hand
  - No additional ballots are pulled specifically for these contests
- Total: **~727 contests** in 2024 had some level of examination

## Key Fields in `contest.csv`

### `audit_reason`
Indicates why/how a contest is included in the audit:

| Value | Meaning | Ballots Pulled? |
|-------|---------|-----------------|
| `county_wide_contest` | County selected this contest for RLA | **YES** - Targeted |
| `state_wide_contest` | State selected this contest for RLA | **YES** - Targeted |
| `opportunistic_benefits` | Contest examined when ballots pulled for other reasons | **NO** - Opportunistic |
| `not_auditable` | Uncontested race, cannot audit | **NO** |

### `audited_sample_count`
Number of physical ballots **actually examined** for this contest:
- `> 0` = Ballots were examined (either targeted or opportunistic)
- `= 0` = No ballots examined yet (contest may be targeted but not started)

### `random_audit_status`
Current status of the audit:
- `in_progress` = Audit ongoing, has not achieved risk limit
- `risk_limit_achieved` = Audit complete, passed statistical test
- `ended` = Audit ended (may have achieved risk limit in earlier round)
- `not_auditable` = Cannot be audited (uncontested)

## Understanding the 2024 Colorado General Election

### Statewide RLA Targets
2 contests were selected at the state level:
- Presidential Electors
- Regent of the University of Colorado - At Large

These were audited across **all 63 counties** (ballots pulled in each county).

### County-Level RLA Targets
63 contests were selected by individual counties:
- Usually County Commissioner races
- One contest per county
- Each county pulled ballots for its own targeted contest

### Opportunistic Examination
~662 other contests were examined opportunistically:
- Constitutional amendments (appeared on targeted ballots)
- Propositions (appeared on targeted ballots)
- Judicial retention (appeared on targeted ballots)
- Other races on the same ballots

**Key point:** No additional ballots were pulled for opportunistic contests. They were examined because they happened to appear on ballots that were already pulled for the 65 targeted contests.

## How to Find Targeted Contests

### Using the Verification Tools

#### Show all contests with examined ballots (including opportunistic):
```bash
python3 verify_any_contest.py --list-contests-for-county Bent
```

Output shows markers:
- `[TARGETED]` = County-wide RLA target
- `[STATE RLA]` = State-wide RLA target
- `[opportunistic]` = Examined opportunistically

#### Show ONLY contests targeted for RLA:
```bash
python3 verify_any_contest.py --list-contests-for-county Bent --targeted-only
```

#### Example output for Bent County:
```
Contests TARGETED for RLA in Bent County:
--------------------------------------------------------------------------------
  Bent County Commissioner-District 1                     [TARGETED]         ( 32 ballots)
  Presidential Electors                                   [STATE RLA]        ( 32 ballots)
  Regent of the University of Colorado - At Large         [STATE RLA]        ( 32 ballots)

Total: 3 contests with examined ballots
```

### Directly from CSV Data

Look at the `audit_reason` field in `contest.csv`:

```bash
# Count contests by audit reason
cut -d',' -f2 contest.csv | sort | uniq -c

# Output:
#   63 county_wide_contest  <- Targeted by counties
#    2 state_wide_contest   <- Targeted by state
#  660 opportunistic_benefits <- Examined opportunistically
```

## Verification Implications

### Can Verify Random Selection
For contests where:
- `audited_sample_count > 0` (ballots were examined)
- `ballot_card_count = contest_ballot_card_count` (county-wide contest)

You can verify that the correct ballots were randomly selected.

**Targeted contests are best candidates** because:
- They definitely have examined ballots
- They're usually county-wide
- The random selection was done specifically for them

### Cannot Verify (Currently)
- Contests with `audited_sample_count = 0`
- Multi-county contests (need CVR data)
- Opportunistic contests may be harder (selection was for a different contest)

## Examples

### Bent County - 2024 General Election

```bash
python3 verify_any_contest.py --list-contests-for-county Bent --targeted-only
```

**Targeted Contests:**
1. **Bent County Commissioner-District 1** (county_wide_contest)
   - 32 ballots examined
   - This is what drove the ballot selection
2. **Presidential Electors** (state_wide_contest)
   - 32 ballots examined (same 32 ballots)
3. **Regent of the University of Colorado** (state_wide_contest)
   - 32 ballots examined (same 32 ballots)

**Opportunistic:** 29 other contests examined on those same 32 ballots

**Total:** 32 contests had ballots examined, but only 3 were targeted for RLA.

### Boulder County - 2024 General Election

```bash
python3 verify_any_contest.py --list-contests-for-county Boulder --targeted-only
```

**Targeted Contests:**
1. **State Representative - District 10** (county_wide_contest)
   - 11 ballots examined
2. **Presidential Electors** (state_wide_contest)
   - 63 ballots examined
3. **Regent of the University of Colorado** (state_wide_contest)
   - 63 ballots examined

**Note:** Boulder pulled different numbers of ballots for different contests, showing they were independent selections.

## Summary

| Term | Meaning | Count (2024 GE) |
|------|---------|-----------------|
| **Contests with data** | All contests have risk calculations | ~727 |
| **Targeted for RLA** | Contests selected for ballot examination | **65** |
| **Had ballots examined** | Physical ballots were looked at | ~727 |
| **Opportunistic examination** | Examined as byproduct of targeted audits | ~662 |

## Why This Matters

### For Verification
When you verify random ballot selection, you're verifying the selection for the **targeted contest**. The opportunistic contests were examined as a side benefit, but their selection was driven by the targeted contest.

### For Understanding Audit Scope
The RLA in Colorado is targeted at 65 contests (2 statewide + 63 county-level), but provides examination of ~727 contests total through opportunistic benefits.

### For Reporting
When reporting audit results:
- "65 contests were targeted for RLA" ✓ Correct
- "727 contests were audited" ✗ Misleading (implies all were targeted)
- "727 contests had ballots examined, with 65 targeted for RLA" ✓ Correct

## Tool Commands Reference

```bash
# Show all examined contests in a county
python3 verify_any_contest.py --list-contests-for-county [COUNTY]

# Show ONLY targeted contests in a county
python3 verify_any_contest.py --list-contests-for-county [COUNTY] --targeted-only

# Verify a specific contest
python3 verify_any_contest.py --contest "Contest Name" --county "County"

# List all counties
python3 verify_any_contest.py --list-counties

# See which counties examined a contest
python3 verify_any_contest.py --list-counties-for-contest "Contest Name"
```

## References

- Colorado Secretary of State RLA procedures
- Risk-Limiting Audit standards (Lindeman & Stark)
- 2024 General Election audit data: `neal_ignore/auditcenter-2024g/`

---

**Last Updated:** October 23, 2025  
**Covers:** 2024 Colorado General Election RLA

