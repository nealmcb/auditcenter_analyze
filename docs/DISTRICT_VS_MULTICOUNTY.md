# District-Level vs Multi-County Contest Verification

## The Two Different Problems

### Problem 1: District-Level Contest (Within One County)

**Example:** State Representative - District 10 in Boulder County

**Numbers:**
- Contest Ballot Card Count: 44,675
- County Ballot Card Count: 396,121
- Counties with contest: 1 (Boulder only)

**The Issue:**
The contest appears on only some ballot cards within Boulder County. Random selection uses contest-specific indices [1-44,675], but we don't know which of the 396,121 manifest positions those map to.

**What's Needed:**
- CVR data showing which manifest positions contain this contest
- Mapping: contest index → manifest position
  - Example: Contest index #1 = Manifest position #42
  - Example: Contest index #2 = Manifest position #87

**User's Point:**
"If the district is entirely in the county, there is no problem since the random selection remains county-wide."

The random selection still uses the county's manifest, just limited to positions with this contest. We need CVR data to identify those positions, but it's a **single-county** problem.

---

### Problem 2: Multi-County Contest

**Example:** Presidential Electors (appears in all 63 counties)

**Numbers:**
- Contest Ballot Card Count: 3,239,722 (across all counties)
- County Ballot Card Count: 4,746,866 (statewide total)
- Counties with contest: 63 (all counties)

**The Issue:**
The contest spans multiple counties. Random selection uses indices [1-3,239,722] across ALL counties. We need to know how the county manifests are ordered/combined.

**What's Needed:**
1. List of counties with this contest (we have this: 63 counties)
2. **ORDER** in which their manifests are combined for random selection
   - Example: Adams [1-100,000], Alamosa [100,001-110,000], Arapahoe [110,001-250,000], etc.
3. Each county's manifest file

**User's Point:**
"The problem is when it appears in some but not all counties. I think we don't need CVR data necessarily, we just need to know the set of counties that have the contest, and the order in which their manifests are combined."

This is a **manifest ordering** problem, not a CVR problem. Once we know the order, we can map:
- Random index #50,000 → Adams County, position #50,000 in Adams
- Random index #105,000 → Alamosa County, position #5,000 in Alamosa

---

## Comparison

| Aspect | District-Level (Single County) | Multi-County |
|--------|-------------------------------|--------------|
| **Example** | State Rep District 10 (Boulder) | Presidential Electors (all counties) |
| **Counties** | 1 | Multiple (2-63) |
| **Domain** | Contest indices within county | Contest indices across all counties |
| **Manifest** | Single county manifest | Multiple county manifests |
| **What's needed** | CVR data (which positions have contest) | Manifest ordering (how counties combined) |
| **Complexity** | Single-county CVR mapping | Multi-county manifest sequencing |

---

## Updated Error Messages

### For District-Level Contest (Boulder State Rep 10)
```
✗ ERROR: Contest verification requires additional data for this contest type.

  Contest Ballot Card Count: 44,675
  County Ballot Card Count:  396,121

  This is a DISTRICT-LEVEL contest (within Boulder County).
  The contest appears on only 44,675 of 396,121
  ballot cards in the county.

  The problem:
    - Random selection uses domain [1, 44,675]
      (contest-specific ballot card indices within the county)
    - Manifest has 396,121 cards indexed sequentially
      (all county ballot cards)
    - We don't know WHICH manifest positions contain this contest

  To verify, you would need:
    - CVR (Cast Vote Record) data showing which of the 396,121
      manifest positions contain this contest
    - Mapping from contest index [1-44,675] to manifest positions
```

### For Multi-County Contest (Presidential Electors)
```
✗ ERROR: Contest verification requires additional data for this contest type.

  Contest Ballot Card Count: 3,239,722
  County Ballot Card Count:  4,746,866

  This is a MULTI-COUNTY contest.
  The contest appears in 63 counties: Adams, Alamosa, Arapahoe, Archuleta, Baca
  ... and 58 more counties

  The problem:
    - Random selection uses domain [1, 3,239,722]
      (contest-specific indices across ALL counties)
    - Each county has its own manifest
    - We need to know the ORDER in which county manifests are combined

  To verify, you would need:
    1. List of counties with this contest (we have: 63 counties)
    2. ORDER in which their manifests are combined for random selection
       Example: Adams [1-X], Alamosa [X+1-Y], Arapahoe [Y+1-Z], etc.
    3. Each county's manifest file
```

---

## What Works Now

The verification tool correctly identifies and explains both types of unsupported contests:

✓ **Detects single-county districts** - Checks if contest appears in only 1 county
✓ **Detects multi-county contests** - Checks contestComparison.csv for county list
✓ **Explains the specific problem** for each type
✓ **Suggests the correct solution** (CVR data vs manifest ordering)

---

## Examples

### Works ✓
- **Bent County Commissioner-District 1**
  - Contest: 2,221 cards
  - County: 2,221 cards
  - Appears on ALL county cards
  - No CVR or ordering needed

### Doesn't Work (District-Level) ✗
- **Boulder State Representative - District 10**
  - Contest: 44,675 cards
  - County: 396,121 cards
  - Single county, but only some cards
  - Needs: CVR data for Boulder

### Doesn't Work (Multi-County) ✗
- **Presidential Electors**
  - Contest: 3,239,722 cards
  - Counties: 63
  - Multi-county spanning all of Colorado
  - Needs: Manifest ordering across counties

---

## Future Enhancement Possibilities

### For District-Level Contests
If CVR data becomes available, could add:
```python
def load_cvr_for_contest(cvr_file, contest_name):
    """Map contest indices to manifest positions using CVR"""
    # Read CVR, filter for contest, build mapping
    # Return: {contest_index: manifest_position}
```

### For Multi-County Contests
If manifest ordering is documented, could add:
```python
def load_multicounty_manifests(counties_list, ordering_spec):
    """Combine county manifests in specified order"""
    # Load each county's manifest
    # Concatenate in correct order
    # Return combined manifest with proper indexing
```

---

## Key Insight

The user's clarification was important:

> "If the district is entirely in the county, there is no problem since the random selection remains county-wide. The problem is when it appears in some but not all counties."

This correctly identifies that:
1. **Single-county districts**: CVR problem (which cards have it?)
2. **Multi-county contests**: Ordering problem (how are counties combined?)

These are fundamentally different issues requiring different solutions.

---

**Last Updated:** October 23, 2025  
**Issue:** Distinguish district-level from multi-county verification challenges  
**Status:** ✓ Error messages updated to correctly identify each case

