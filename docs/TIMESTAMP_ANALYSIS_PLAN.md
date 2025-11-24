# Timestamp Analysis Plan for 2024 Audit

## Objective
Analyze timestamps in round 3 `contestComparison.csv` to understand audit timing patterns across the election.

## Key Findings from Initial Exploration

1. **Timestamp Consistency**: 
   - 4,356 out of 4,612 imprinted_ids (94.4%) have a **single timestamp** - all contests on that ballot were interpreted at the same time
   - 256 imprinted_ids (5.6%) have **multiple timestamps** - these ballots were re-examined or had additional contests added later

2. **Data Structure**:
   - Each row in `contestComparison.csv` represents one contest interpretation on one ballot
   - Same `imprinted_id` appears multiple times (once per contest on that ballot)
   - `timestamp` field records when that interpretation was entered
   - `audit_board_selection` contains the selection value, NOT the board number

## Proposed Analysis Plan

### Phase 1: Extract Timestamp Data per Imprinted ID

**For all ballot cards:**
- Extract one timestamp per `imprinted_id` - the last one.
- Count number of contests on that CVR
- Count discrepancies
- Include: county, CVR ID, timestamp, contest count, discrepancy count

**For multi-timestamp ballots:**
- Produce a separate report with each timestamp)
- Calculate time differences
- Count contests per timestamp group

### Phase 2: Core Data Extraction

Create a CSV with the following columns:

0. County name
1. **imprinted_id** - Unique ballot identifier
3. **cvr_id** - CVR identifier (for linking to other data)
4. **timestamp** - Primary timestamp (first timestamp for multi-timestamp cases)
7. **contest_count** - Number of contests on this CVR
8. discrepancy count

### Phase 3: Additional Valuable Information

Consider extracting/calculating:

   - Session duration (time between consecutive ballots)
   - Regression of time between ballots and number of contests per ballot
   - Warn that with multiple audit boards we may need to guess audit board based on imprinted_id position within pull list (sorted by location, imprinted_id)

1. **Discrepancy Analysis**:
  - Whether discrepancies correlate with longer examination times

3. **Temporal Patterns**:
   - Time of day (hour, day of week)
   - Audit throughput (ballots per hour by county/board)

4. **Audit Board Identification** (if available):
   - infer from timestamp patterns or other sources
   - Could group by time windows to identify potential board assignments

6. **County-Level Aggregates**:
   - Average time per ballot
   - Total audit duration
   - Peak activity times

## Implementation Steps

1. **Load and Parse** `round3/contestComparison.csv`
2. **Group by imprinted_id** to collect all contest interpretations
3. **Extract timestamps** and verify consistency
4. **Calculate metrics** (contest count, etc.)
5. **Output CSV** with one row per imprinted_id, and potentially separate rows for multi-timestamp ballots
5b. sort csv by county, by timestamp, and generate delta timestamps (durations)
6. **Generate summary statistics**:
   - Distribution of contest counts
   - Distribution of examination durations
   - Temporal patterns (by hour, day)
   - County-level comparisons

## Questions to Answer

2. What causes multi-timestamp ballots? (change during confirmation pass?)
3. How long does it take to examine a ballot? (Time between consecutive ballots)
4. Are there patterns by time of day? (Peak hours, breaks)
5. Do discrepancies correlate with longer examination times?
6. How does ballot complexity (contest count) affect examination time?
7. Are there county-level differences in audit pace?

## Potential Issues

2. **county_name** - County where ballot was examined
1. **Audit Board Number**: Not directly available in `contestComparison.csv`
   - May need to infer from pull list sequence, estimating how many audit boards there were from timestamp density
   - Could check ActivityReport.xlsx (but structure unclear)
   - May need to group by time windows within counties

3. **Missing Data**:
   - Some timestamps may be missing or malformed
   - Need to handle edge cases gracefully

## Next Steps

1. Implement Phase 1 extraction script
2. Generate initial dataset
3. Review sample output for accuracy
4. Proceed with Phase 2 analysis
5. Generate visualizations and summary reports



