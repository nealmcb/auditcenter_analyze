# County Key Normalization Concept

## Problem

County names appear in multiple forms across different CSV files:
- Filenames: `ClearCreekBallotManifest.csv` (no spaces)
- CSV data: `Clear Creek` (with spaces)
- User input: Mixed case, possible typos

We need a **consistent key** to look up counties across dictionaries and databases.

## Solution: Two-Level Normalization

### Level 1: Canonical Form (display/human-readable)

**Function:** `normalize_county_name(value: str) -> str`

- **Input:** `"ClearCreek"` or `"Clear Creek"` or `"clear creek"`
- **Output:** `"Clear Creek"` (Title Case, spaces preserved)
- **Usage:** For display, reports, user-facing interfaces
- **Special handling:** Maps `ClearCreek` → `Clear Creek`

### Level 2: Dictionary Key (for lookups)

**Function:** `normalized_county_key(value: str) -> str`

- **Input:** `"ClearCreek"` or `"Clear Creek"` or `"clear creek"`
- **Output:** `"ClearCreek"` (Title Case, **spaces removed**)
- **Usage:** Dictionary keys, database lookups, data joins
- **Special handling:** Maps `Clear Creek` → `ClearCreek`

## Why Two Levels?

### Canonical Form Benefits
- Human-readable: `"Clear Creek"` looks better than `"ClearCreek"`
- Storage: One consistent name in database
- Display: Can show users proper county names

### Key Form Benefits
- Compatibility: Matches existing codebase (case-sensitive dictionaries)
- Performance: Shorter keys, faster lookups
- Consistency: Removes spacing variations

## Example

```python
from auditcenter_analyze.normalize import normalize_county_name, normalized_county_key

# All these normalize to same canonical form
normalize_county_name("ClearCreek")      # → "Clear Creek"
normalize_county_name("Clear Creek")     # → "Clear Creek"
normalize_county_name("clear creek")     # → "Clear Creek" (Title Case!)

# But keys preserve case (for compatibility)
normalized_county_key("ClearCreek")      # → "ClearCreek"
normalized_county_key("Clear Creek")     # → "ClearCreek"
normalized_county_key("clear creek")     # → "ClearCreek" (Title Case!)
```

## Usage in Code

### Dictionary Keys (county lookups)

```python
# Load manifests
manifest_counts = {}
for manifest_file in glob("*BallotManifest.csv"):
    county_stem = manifest_file.stem.replace("BallotManifest", "")  # "ClearCreek"
    county_key = normalized_county_key(county_stem)  # "ClearCreek"
    manifest_counts[county_key] = total_ballots

# Load contest data
for row in contestsByCounty.csv:
    county_name = row["county_name"]  # "Clear Creek"
    county_key = normalized_county_key(county_name)  # "ClearCreek"
    # Now can look up in manifest_counts!
    ballots = manifest_counts[county_key]
```

### Display

```python
# When showing results to user
for county_key, count in results.items():
    county_display = normalize_county_name(county_key)  # "Clear Creek"
    print(f"{county_display}: {count} ballots")
```

## Why Preserve Case?

The baseline output shows:
```
Adams          :  231 examined
Alamosa        :   66 examined
Arapahoe       :   69 examined
```

These are all **Title Case** with spaces removed. Existing code uses this convention:

```python
# Old code (before normalization)
county.replace(" ", "")  # "Clear Creek" → "ClearCreek"
```

The `normalized_county_key()` function **preserves this behavior** for compatibility.

## Current Implementation

```python
def normalize_county_name(value: str) -> str:
    """Canonical form: Title Case, spaces preserved."""
    v = strip_quotes_whitespace(value)
    v = re.sub(r"\s+", " ", v).strip()
    canonical = v
    key = canonical.replace(" ", "").lower()
    
    # Special known mapping
    if key == "clearcreek":
        canonical = "Clear Creek"
    return canonical

def normalized_county_key(value: str) -> str:
    """Dictionary key: Title Case, spaces removed."""
    canonical = normalize_county_name(value)
    return canonical.replace(" ", "")
```

## Migration Path

If we wanted to use lowercase keys in the future:

```python
# New approach (not current)
def normalized_county_key(value: str) -> str:
    """Dictionary key: lowercase, spaces removed."""
    canonical = normalize_county_name(value)
    return canonical.replace(" ", "").lower()
    
# Would produce:
normalized_county_key("Clear Creek")  # → "clearcreek"
```

But this would break existing code that expects Title Case keys!

## Why Lookup Keys Are Essential

### The Problem: Multiple Data Sources

County data comes from **three different sources** with different formats:

1. **Ballot Manifest Files:** `ClearCreekBallotManifest.csv` (no spaces)
2. **contestsByCounty.csv:** `"Clear Creek"` (with spaces)  
3. **contestComparison.csv:** `"Clear Creek"` (with spaces)

We need to **join data across these sources** to calculate risk.

### The Data Flow

```python
# Step 1: Load manifests (file names have no spaces)
for manifest_file in glob("*BallotManifest.csv"):
    county_stem = manifest_file.stem.replace("BallotManifest", "")  # "ClearCreek"
    county_key = normalized_county_key(county_stem)  # "ClearCreek"
    manifest_counts[county_key] = total_ballots
    
# manifest_counts = {"ClearCreek": 6180, "Adams": 468858, ...}

# Step 2: Load contest mappings (CSV has spaces)
for row in contestsByCounty.csv:
    county_name = row["county_name"]  # "Clear Creek"
    county_key = normalized_county_key(county_name)  # "ClearCreek"
    counties_by_contest[contest].add(county_key)

# counties_by_contest["Presidential Electors"] = {"ClearCreek", "Adams", ...}

# Step 3: Load ballot data (CSV has spaces)
for row in contestComparison.csv:
    county_name = row["county_name"]  # "Clear Creek"
    county_key = normalized_county_key(county_name)  # "ClearCreek"
    contest_ballots[contest][county_key].append(ballot)

# contest_ballots["Presidential Electors"]["ClearCreek"] = [ballot1, ballot2, ...]

# Step 4: CALCULATE RISK (THE KEY USAGE!)
for county in counties_by_contest["Presidential Electors"]:  # county = "ClearCreek"
    manifest_count = manifest_counts[county]  # Lookup: 6180 ✓
    ballots = contest_ballots_per_county[county]  # Lookup: [ballot1, ...] ✓
    # Both lookups work because we used same key everywhere!
```

### The Failure Without Keys

Without normalization, lookups fail:

```python
# manifest_counts uses filename key
manifest_counts = {"ClearCreek": 6180}

# But CSV data has spaces
counties_from_csv = ["Clear Creek"]

# Lookup FAILS!
manifest_count = manifest_counts["Clear Creek"]  # KeyError!
```

### Real Usage in Code

From `calculate_opportunistic_risk.py`:

```python
def calculate_contest_risk(contest_name, counties, contest_ballots_per_county, 
                           manifest_counts, examined_counts):
    # counties = ["ClearCreek", "Adams", "Boulder"] (from contestsByCounty.csv)
    # contest_ballots_per_county = {"ClearCreek": [...], ...} (from contestComparison.csv)
    # manifest_counts = {"ClearCreek": 6180, ...} (from manifest files)
    
    for county in counties:  # county = "ClearCreek"
        # These lookups ONLY work because all use same key!
        manifest_count = manifest_counts[county]  # Line 204
        ballots = contest_ballots_per_county.get(county, [])  # Line 208
```

**Line 204:** `manifest_count = manifest_counts[county]`  
**Line 208:** `ballots = contest_ballots_per_county.get(county, [])`

Both lookups depend on **consistent county keys** across all data structures!

## Summary

- **Canonical form** = human-readable, display
- **Key form** = dictionary lookups, database joins
- **Preserve case** for compatibility with existing code
- **Remove spaces** for consistent lookups across filenames and CSV data
- **Special handling** for "Clear Creek" vs "ClearCreek"
- **Critical usage:** Joining manifest counts, contest mappings, and ballot data
- **Without keys:** Data from different sources can't be joined (KeyError!)

