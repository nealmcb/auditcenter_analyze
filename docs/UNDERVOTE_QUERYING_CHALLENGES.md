# Undervote Querying Challenges

## Summary

Empty string `""` is the canonical representation for "contest skipped entirely" in the auditcenter dataset. Querying for these undervotes presents several challenges.

## Data Distribution (round3/contestComparison.csv)

Total comparisons: **149,272**

```
Both empty (CVR="" and Audit=""):        20,638 (13.8%)
CVR empty, Audit has selections:           145 (0.1%)  ⚠️ DISCREPANCY
CVR has selections, Audit empty:            13 (0.0%)  ⚠️ DISCREPANCY  
Both have selections (matching):        115,311 (77.2%)
Both have selections (different):         165 (0.1%)  ⚠️ DISCREPANCY
```

**Note:** The remaining ~13,000 rows likely represent vote-for-n contests with multiple selections per ballot.

## Query Scenarios

### 1. Find Undervotes by Contest

**Question:** "How many undervotes were there for Presidential Electors?"

**SQL:**
```sql
SELECT 
    contest_name,
    COUNT(*) as undervote_count
FROM ballot_comparisons
WHERE cvr_choice = ""
  AND audit_choice = ""
GROUP BY contest_name
ORDER BY undervote_count DESC;
```

**Challenge:** CSV stores multiple selections as `"""Selection 1"",""Selection 2"""`. Need to handle multiple patterns:
- Single undervote: `""` 
- Multiple selections: `"""Choice A"",""Choice B"""`
- Need regex or proper parsing for multi-value fields

### 2. Find Discrepancies Where CVR Says Undervote

**Question:** "Where did CVR record an undervote but audit board found selections?"

**SQL:**
```sql
SELECT 
    contest_name,
    county_name,
    imprinted_id,
    cvr_choice,
    audit_choice
FROM ballot_comparisons
WHERE cvr_choice = ""
  AND audit_choice != ""
ORDER BY contest_name, county_name;
```

**Challenge:** This reveals **145 discrepancies** where CVR recorded empty (`""`) but audit board found selections. 

**Example:** 
- CVR: `""` 
- Audit: `"""Yadira Caraveo"",""Susan Patricia Hall"""`
- This is a **vote-for-2 contest** where CVR missed both selections

These are real errors that should count in risk calculations, but current `has_discrepancy()` ignores them because of the `cvr != "" and audit != ""` check.

### 3. Find Discrepancies Where Audit Board Says Undervote

**Question:** "Where did CVR have selections but audit board found undervote?"

**SQL:**
```sql
SELECT 
    contest_name,
    county_name,  
    imprinted_id,
    cvr_choice,
    audit_choice
FROM ballot_comparisons
WHERE cvr_choice != ""
  AND audit_choice = "";
```

**Challenge:** This reveals **13 discrepancies**. 

**Example:**
- CVR: `"""Julie Duran Mullica"""`
- Audit: `""`
- CVR recorded a selection but audit board found none

These are also real errors. This is an **understatement** error (CVR credits votes that weren't actually cast), which affects risk differently than **overstatement** (CVR favors the wrong winner).

### 4. Count Undervotes Across Counties

**Question:** "Which counties have the highest undervote rates?"

**SQL:**
```sql
SELECT 
    county_name,
    COUNT(CASE WHEN cvr_choice = "" THEN 1 END) as undervote_count,
    COUNT(*) as total_examined,
    ROUND(100.0 * COUNT(CASE WHEN cvr_choice = "" THEN 1 END) / COUNT(*), 2) as pct_undervote
FROM ballot_comparisons
GROUP BY county_name
ORDER BY pct_undervote DESC;
```

**Challenge:** Need to ensure we're counting within a specific contest, not across all contests on a ballot.

### 5. Compare Undervote Rates: CVR vs Audit Board

**Question:** "Are there systematic differences in how undervotes are recorded?"

**SQL:**
```sql
SELECT
    contest_name,
    COUNT(CASE WHEN cvr_choice = "" THEN 1 END) as cvr_undervotes,
    COUNT(CASE WHEN audit_choice = "" THEN 1 END) as audit_undervotes,
    COUNT(CASE WHEN cvr_choice = "" AND audit_choice != "" THEN 1 END) as discrepancy_cvr_empty,
    COUNT(CASE WHEN cvr_choice != "" AND audit_choice = "" THEN 1 END) as discrepancy_audit_empty
FROM ballot_comparisons
GROUP BY contest_name
HAVING cvr_undervotes != audit_undervotes OR discrepancy_cvr_empty > 0 OR discrepancy_audit_empty > 0
ORDER BY contest_name;
```

**Challenge:** Need to distinguish between:
- Legitimate undervote differences (CVR vs Audit both agree)
- Discrepancies where one side missed something

## Why These Queries Are Hard

### 1. Multi-Value Fields

The CSV format `"""Choice A"",""Choice B"""` is not properly normalized for SQL queries:

```python
# Raw CSV:
"`"""John Doe"",""Jane Smith""`"

# Parsed as single string with nested quotes
# Hard to query: WHERE cvr_choice LIKE '%John Doe%'
# Complicated joins to candidate lookup tables
```

### 2. Empty String Ambiguity

Empty string `""` could represent:
- Contest not on ballot (correct)
- Contest skipped by voter (undervote)
- Error in recording (discrepancy)

Need metadata to distinguish these cases.

### 3. Performance

Counting undervotes on large datasets:
```sql
-- Slow: table scan
WHERE cvr_choice = ""

-- Needs index
CREATE INDEX idx_ballot_cvr_empty ON ballot_comparisons(contest_id) WHERE cvr_choice = "";
```

### 4. Normalization Issues

Current `normalize_choice()` just strips quotes:
```python
normalize_choice('"""Yes/For"""')  # Returns: "Yes/For"
normalize_choice('"""Yes/For"",""No/Against"""')  # Returns: "Yes/For","No/Against"
normalize_choice('""')  # Returns: "" (empty string)
```

But need to handle:
- Nested quoted strings with commas
- Multi-selection contests
- Encoding issues (smart quotes, Unicode)

### 5. vote-for-n Contests

Contests like "Vote for 3" are not undervotes:
- `"""Candidate A"",""Candidate B"""` is a **partial vote** (2 selections)
- NOT an undervote

But our CSV doesn't indicate contest type, so hard to distinguish partial votes from multi-vote contests.

## Current Implementation Issues

### has_discrepancy() Bug

```python
def has_discrepancy(ballot):
    if ballot["consensus"] == "NO":
        return True
    cvr = ballot["cvr"].strip()
    audit = ballot["audit"].strip()
    return cvr != audit and cvr != "" and audit != ""  # ⚠️ IGNORES 158 UNDERVOTE DISCREPANCIES!
```

This ignores:
- **145 cases** where CVR="" but Audit has selections
- **13 cases** where CVR has selections but Audit=""

These are real discrepancies that should affect risk calculations!

### Proposed Fix

```python
def has_discrepancy(ballot):
    """Check if a ballot has a discrepancy."""
    if ballot["consensus"] == "NO":
        return True
    cvr = ballot["cvr"].strip()
    audit = ballot["audit"].strip()
    
    # Both empty: no discrepancy
    if cvr == "" and audit == "":
        return False
    
    # Any difference is a discrepancy (including when one is empty)
    return cvr != audit
```

This would correctly count all **323 discrepancies** (145 + 13 + 165) instead of just 165.

## Recommendations

1. **Store raw CSV values** in database (don't normalize)
2. **Parse multi-value selections** into separate rows in a `ballot_selections` table
3. **Add metadata** about contest types (vote-for-1 vs vote-for-n)
4. **Fix has_discrepancy()** to count all discrepancies, not just non-empty mismatches
5. **Use NULL** instead of empty string in database for "no selection"
6. **Index empty strings** for performance: `CREATE INDEX ... WHERE cvr_choice = ''`
7. **Document** the distinction between:
   - Contest not on ballot
   - Contest present but skipped
   - Contest error/overvote

## References

- Empty string count analysis: ~20,638 both-empty matches in round3
- Discrepancy analysis: 145 + 13 + 165 = 323 total discrepancies
- Current code: `calculate_opportunistic_risk.py` has_discrepancy()
- Normalization: `normalize.py` normalize_choice()

