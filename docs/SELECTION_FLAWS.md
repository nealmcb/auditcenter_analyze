# Internal Inconsistency in AuditCenter Data: contestSelection vs contestComparison

## Summary

`contestSelection.csv` lists the CVR IDs that were drawn for each contest.
`contestComparison.csv` records the actual ballot comparisons (with audit board votes).
These two files should agree: every CVR ID selected should have a comparison record,
and every comparison record should correspond to a selected CVR ID.

For **Pueblo County Commissioner - District 2** (2024 General, all three rounds
contain identical data), they do not agree:

| File | CVR IDs |
|------|---------|
| `contestSelection.csv` | 378 |
| `contestComparison.csv` | 193 |
| **In both** | **189** |
| Only in `contestSelection` (selected, no comparison) | **189** |
| Only in `contestComparison` (comparison, not selected) | **4** |

Half the drawn ballots have no comparison record. Four comparison records reference
ballots that were never drawn.

---

## Data: `data/2024/general/round1/` (identical in round2 and round3)

### Matching — CVR IDs present in both files

These 189 CVR IDs appear in both the selection list and the comparison records,
as expected:

| cvr_id | imprinted_id |
|--------|--------------|
| 4363908 | 105-5-82 |
| 4365137 | 105-18-37 |
| 4365359 | 105-20-17 |
| 4365649 | 105-23-90 |
| 4365766 | 105-24-75 |

*(5 of 189 shown)*

---

### In `contestSelection` only — selected but no comparison record

These 189 CVR IDs were drawn by the RNG and listed in `contestSelection.csv`,
but have no corresponding row in `contestComparison.csv`. The audit center
has no record that these ballots were ever examined:

| cvr_id | imprinted_id |
|--------|--------------|
| 4363533 | *(not in contestComparison — unknown)* |
| 4363664 | *(not in contestComparison — unknown)* |
| 4364261 | *(not in contestComparison — unknown)* |
| 4364626 | *(not in contestComparison — unknown)* |
| 4365292 | *(not in contestComparison — unknown)* |

*(5 of 189 shown)*

Note: `imprinted_id` is not available from `contestSelection.csv` directly;
it would need to be looked up via the CVR data or ballot manifest.

---

### In `contestComparison` only — comparison record but never selected

These 4 CVR IDs appear in `contestComparison.csv` for this contest but are
absent from `contestSelection.csv`. They were apparently compared against
audit board votes, but were never drawn for this contest:

| cvr_id | imprinted_id |
|--------|--------------|
| 4447815 | 111-195-51 |
| 4459345 | 105-367-81 |
| 4466341 | 102-466-31 |
| 4495312 | 105-479-49 |

*(all 4 shown — there are no others)*

---

## Interpretation

The CVR ID ↔ imprinted_id mapping is independent of contest name, so the
"mis-attribution" hypothesis (that selected ballots were logged under wrong
contest names) would not explain the `only_in_selection` side: those 189
CVR IDs would simply appear under a different contest in `contestComparison.csv`,
yet they are still drawn and still unaccounted for *for this contest*.

The `only_in_comparison` side (4 ballots) is more puzzling: ballots that
were compared but not drawn. These could be carryover from a prior round,
manually added, or a data entry error.

The cleanest statement of the inconsistency: **189 ballots were selected for
Pueblo County Commissioner District 2 but the audit center produced no
comparison record for them.**
