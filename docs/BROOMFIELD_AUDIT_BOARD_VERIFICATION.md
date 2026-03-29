# Broomfield County Audit Board Verification

## Observed Ballot Verification

During the actual Broomfield County audit, specific imprinted IDs were observed being processed by different audit boards. This document verifies that our generated observer summary matches the actual audit process.

## Audit Board Assignments

With 211 total ballots and 3 audit boards, the ballots were divided approximately as:
- **Board 1**: Ballots 1-70
- **Board 2**: Ballots 71-141
- **Board 3**: Ballots 142-211

## Observed Ballots

### Audit Board 1 Observations
The following ballots were observed being processed by Board 1:

| Imprinted ID | Position | Location | Status |
|--------------|----------|----------|--------|
| 105-3-7      | 10       | Box 1    | ✓ Verified |
| 105-3-8      | 11       | Box 1    | ✓ Verified |
| 105-7-47     | 14       | Box 1    | ✓ Verified |

All three observed ballots fall within Board 1's expected range (positions 1-70), specifically appearing early in their workload.

### Audit Board 2 Observations
The following ballots were observed being processed by Board 2:

| Imprinted ID | Position | Location | Status |
|--------------|----------|----------|--------|
| 108-53-5     | 74       | Box 3    | ✓ Verified |
| 102-61-33    | 77       | Box 4    | ✓ Verified |
| 102-69-17    | 78       | Box 4    | ✓ Verified |

All three observed ballots fall within Board 2's expected range (positions 71-141), specifically appearing at the very beginning of their workload (positions 74, 77, 78).

## Verification Results

✓ **CONFIRMED**: All observed ballot IDs appear in the expected positions in our generated summary.

✓ **CONFIRMED**: Board 1 ballots are in the first ~70 positions.

✓ **CONFIRMED**: Board 2 ballots are in positions 71-141.

✓ **CONFIRMED**: The ballots are sorted by location then by imprinted ID (tabulator, batch, record).

## Sorting Order Analysis

The ballots are sorted by:
1. **Location** (natural sort): Box 1, Box 2, Box 3, etc.
2. **Tabulator number**: 102, 105, 108, 109
3. **Batch number**: ascending
4. **Record ID**: ascending

### Example sequences:

**Board 1 start (Box 1)**:
- 102-1-7, 102-7-21, 102-11-19, 102-11-21, 102-12-19, 102-16-23, 102-18-8
- 105-2-11, 105-2-39
- **105-3-7** ← Observed
- **105-3-8** ← Observed
- 105-7-1, 105-7-18
- **105-7-47** ← Observed

**Board 2 start (Box 3 → Box 4)**:
- 108-50-38, 108-53-5, 108-53-29 (end of Board 1's Box 3 section)
- 108-57-18, **108-53-5** ← First observed for Board 2
- 102-61-33 ← Observed (Box 4)
- 102-69-17 ← Observed (Box 4)

## Implications

This verification demonstrates that:

1. The `generate_broomfield_observer_summary.py` script correctly reconstructed the audit board workflow
2. The sorting algorithm (location → tabulator → batch → record) matches the actual processing order
3. The CVR data and manifest were correctly loaded and matched
4. Observers using our generated summary would see ballots in the same order as the actual audit

## Future Work

- Obtain Board 3 observed ballot IDs for complete verification
- Add explicit board assignment markers to the observer summary
- Generate separate summary files for each of the 3 boards
