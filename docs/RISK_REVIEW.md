# Risk Calculation Review: Python vs Kotlin Implementations

**Date:** 2026-05-12  
**Context:** Comparing John Caron's Kotlin risk results (`output/risks-via-kotlin.csv`) against
the Python implementation (`src/auditcenter_analyze/calculate_opportunistic_risk.py`), for the
2024 Colorado General RLA, round 3.  Both implementations assume **zero errors** for this
initial analysis.  Both use the Kaplan-Markov comparison audit framework with γ = 1.03905 and
a 3% risk limit.

---

## 1. What John's CSV Contains

**File:** `output/risks-via-kotlin.csv`  
**Rows:** 609 contests (65 targeted, 544 opportunistic), derived from the canonical contest list
(`2024GeneralCanonicalList.csv`) plus two added Douglas County contests and one removed
(La Plata County Surveyor).

Key fields:
| Field | Description |
|---|---|
| `npop` | Total ballot cards in the sampling jurisdiction (county total or statewide) — denominator for diluted margin |
| `nc` | Trusted upper bound on contest ballot cards (the contest-specific count) |
| `voteDiff` | Winner minus loser vote count (smallest assertion) |
| `reportedMargin` | `voteDiff / nc` |
| `dilutedMargin` | `voteDiff / npop` |
| `estMvrs` | CORLA's estimated sample size for this contest |
| `haveMvrs` | Actual MVR count from `round3/contestComparison.csv`: unique ballot IDs per county that never appear with `audit_reason = STATE_WIDE_CONTEST` |
| `estRisk` | KM p-value using `haveMvrs` as n and `dilutedMargin` |

John's notes:
- Point 3: statewide contests also use the "minimum county sampling rate" (same algorithm as
  multi-county), because that came out better than the statewide-only sampling rate.  "Not yet
  sure how to combine the two."
- Point 4: `haveMvrs` is generally a bit higher than `audited_sample_count` in `contest.csv`
  — CORLA appears to have added extra ballots to avoid an additional round.

---

## 2. What the Python Implementation Contains

**Script:** `src/auditcenter_analyze/calculate_opportunistic_risk.py`  
**Saved output:** `tests/baseline_output.txt`  
**Contests processed:** 725 total (2 state-wide targeted, 63 county-wide targeted, 660
opportunistic) — sourced from `round3/contest.csv` rather than the canonical list, so coverage
differs from John's.

The algorithm:
1. Load county ballot manifests → `ballot_card_count` per county.
2. For each contest, count observed ballots with the contest in `contestComparison.csv` per
   county.
3. Compute per-county sampling rate = `observed_with_contest / manifest_count`.
4. Find the minimum county sampling rate and downsample all other counties to that rate.
5. `n` = total contest-specific ballots in the downsampled uniform sample.
6. `diluted_margin = min_margin / contest_ballot_card_count` ← **bug, see §3**.
7. Risk = `rlacalc.KM_P_value(n, gamma, diluted_margin)`.

---

## 3. Algorithmic Differences

### 3.1 Diluted margin denominator — Python has a bug

The Python code computes:

```python
diluted_margin = min_margin / contest_ballot_card_count   # WRONG
```

but `contest_ballot_card_count` (column 6 of `contest.csv`, John's `nc`) is the
**contest-specific** ballot count, not the total jurisdiction population.  The correct
denominator for the diluted margin under uniform sampling is `ballot_card_count` (column 5 of
`contest.csv`, John's `npop`) — the total ballot cards in the jurisdiction from which the
uniform sample is drawn.

For a county-wide contest (nc = npop) the two are equal and the bug is invisible.  For a
sub-county district race, nc can be roughly half of npop, making Python's diluted margin ~2×
too large, which in turn makes the computed risk far too low.

**Fix (one line in `calculate_opportunistic_risk.py` around line 364):**
```python
ballot_card_count = int(contest_data["ballot_card_count"])   # npop — total jurisdiction
diluted_margin = min_margin / ballot_card_count
```

### 3.2 Definition of n — different but partially equivalent

| Implementation | n used in KM formula |
|---|---|
| **Python** | Contest-specific ballots in the downsampled uniform sample |
| **John's Kotlin** | `haveMvrs` = unique non-statewide county ballot IDs in `contestComparison.csv` (includes all ballots drawn for the county, not only those with this contest) |

In the KM test martingale, ballots that do **not** contain the contest contribute a factor of
exactly 1.0 — they carry no information about the contest and should not count toward n.
Therefore the Python definition (contest-specific ballots only) is mathematically correct for
`rlacalc.KM_P_value`.

John's `haveMvrs` counts total county non-statewide ballot cards, including those without the
contest.  Passing that larger n to the KM formula gives those non-contest ballots credit they
don't deserve, understating the risk somewhat.  (John may be using a different variant of the
KM formula that handles the full-population-draw setup explicitly — worth confirming.)

**Note on the 17 "mixed" Adams ballots:** `haveMvrs = 214` for Adams, not 231.  The 17
ballots excluded are those that appear in `contestComparison.csv` under **both**
`STATE_WIDE_CONTEST` and county-level reasons.  Python counts 231 unique ballot IDs for Adams
total, and 119 with District 1 specifically.

### 3.3 Contest coverage

| | Targeted | Opportunistic | Total |
|---|---|---|---|
| Python (`contest.csv`) | 65 | 660 | 725 (+ 3 skipped/Moffat) |
| John's Kotlin (canonical list) | 65 | 544 | 609 |

The ~116-contest gap is the difference between the canonical list and everything in
`contest.csv`.  The canonical list is the more authoritative source for contest identity;
`contest.csv` may include entries for contests that were never truly active.

---

## 4. Numerical Impact

The two bugs partially cancel — Python uses a larger (wrong) diluted margin but a smaller
(correct) n — but the diluted margin error dominates for district races.

### Example: Adams County Commissioner – District 1 (opportunistic)
- County total (`ballot_card_count` / npop) = 468,858
- Contest cards (`contest_ballot_card_count` / nc) = 236,872  ← district, ~half the county
- `min_margin` = 13,085

| Approach | n | diluted margin | computed risk |
|---|---|---|---|
| **John's Kotlin** | 214 (all county non-statewide) | 2.79% (npop) | **5.5%** |
| **Python (current — buggy)** | 119 (contest only) | 5.52% (nc) | **4.1%** |
| **Correct (Python n, fixed margin)** | 119 (contest only) | 2.79% (npop) | **~20%** |

### Example: Adams County Commissioner – District 5 (targeted, currently passing)
- `min_margin` = 17,761 | npop = 468,858 | nc = 236,872

| Approach | n | diluted margin | computed risk |
|---|---|---|---|
| **John's Kotlin** | 214 | 3.79% | **1.95%** ✓ |
| **Python (current — buggy)** | 119 | 7.50% | **0.08%** ✓ (false precision) |
| **Correct (Python n, fixed margin)** | 193 | 3.79% | **~2.87%** ✓ |

### Example: Arapahoe County Commissioner – District 1 (opportunistic)
- npop = 351,540 | nc = 80,484 (district, ~23% of county) | `min_margin` = 11,461

| Approach | n | diluted margin | computed risk |
|---|---|---|---|
| **John's Kotlin** | 52 (all county) | 3.26% | **43.9%** |
| **Python (current — buggy)** | ~11 (contest only) | 14.24% (nc) | **~46%** |
| **Correct (Python n, fixed margin)** | ~11 (contest only) | 3.26% (npop) | **~84%** |

### Statewide contests (npop ≠ nc)
For Amendment 80 (62 counties), npop = 4,763,790 and nc = 3,235,954.  John's
`dilutedMargin` = 0.88%, Python's = 1.30%.  At n = 372 (statewide minimum-rate sample), the
correct margin gives risk ≈ **5.0%** (just above limit); Python's inflated margin gives
**1.9%** (falsely under limit).

---

## 5. Python Baseline Output Summary

From `tests/baseline_output.txt` — run of `calculate_opportunistic_risk.py` with the current
(buggy) diluted margin, zero errors assumed:

```
Statewide ballot cards:  4,740,167
Total MVR ballots:       4,897 across 63 counties

Contests processed: 725
  State-wide targeted:   2
  County-wide targeted:  63
  Opportunistic:         660

TARGETED (64 total):
  Pass (≤3%):  61/64
  FAIL:
    Dove Creek Ambulance District Ballot Issue 6A    n=117  risk=4.71%
    Routt County Commissioner - District 1           n= 77  risk=4.14%
    Sedgwick County Commissioner - District 3        n= 84  risk=3.05%

OPPORTUNISTIC (658 total, 3 contests skipped/Moffat data missing):
  Pass (≤3%):  223/658  (34%)
  Fail (>3%):  435/658  (66%)
```

Selected opportunistic results to compare with John's CSV:

```
✓ 17th Judicial District Ballot Question 7B         n=123  risk=0.027%
✗ Adams 12 Five Star Schools Ballot Issue 5D        n= 51  risk=6.60%
✗ Adams 12 Five Star Schools Ballot Issue 5E        n= 51  risk=10.58%
✗ Adams County Commissioner - District 1            n=119  risk=4.05%
✓ Adams County Commissioner - District 2            n=119  risk=0.00%
✓ Amendment 79 (CONSTITUTIONAL)                     n=372  risk=0.00%
✗ Amendment 80 (CONSTITUTIONAL)                     n=372  risk=18.69%
✓ Arapahoe County Ballot Issue 1A                   n= 69  risk=0.00%
✗ Arapahoe County Commissioner - District 1         n= 19  risk=25.96%
✗ Arapahoe County Commissioner - District 3         n= 21  risk=77.88%
```

The full per-contest listing (867 lines) is in `tests/baseline_output.txt`.

---

## 6. Open Questions

1. **Which n is correct for KM?**  Python uses contest-specific ballot count (mathematically
   correct for `rlacalc.KM_P_value`).  John uses total county non-statewide ballots.  If
   John's Kotlin implements a different KM variant that explicitly handles a full-population
   draw (with non-contest ballots contributing factor 1 per draw), the results should converge
   once the diluted margin denominator is aligned.  Can John share the Kotlin KM
   implementation?

2. **Statewide contests: minimum-county-rate vs statewide rate.**  John uses the minimum county
   sampling rate for statewide contests because it "came out better."  The two rates should
   eventually be combined (e.g., take the minimum of the statewide rate and the minimum county
   rate) to be fully conservative.  This is open for both implementations.

3. **Contest list discrepancy (~116 contests).**  Python processes everything in
   `round3/contest.csv`; John uses the canonical list.  We should agree on the authoritative
   source and filter accordingly.

4. **Non-zero errors.**  Both implementations currently assume zero discrepancies.  The Python
   code already reads discrepancy counts from `contest.csv` for targeted contests; extending
   this to opportunistic contests requires determining winner/loser per choice for each contest.

5. **Statewide-selected ballot IDs in county samples.**  John excludes the 17 Adams ballots
   that appear under both `STATE_WIDE_CONTEST` and county reasons from `haveMvrs`.  Python
   counts all contest ballots regardless of selection reason.  We should decide the correct
   treatment: those 17 ballots were physically audited and their contest entries are valid
   comparisons.

---

## 7. Recommended Next Step

Fix the one-line diluted margin bug in Python, re-run, and compare the corrected output with
John's CSV side-by-side.  After that fix, the remaining gap will be purely in how n is defined
(§3.2 and open question 1 above).
