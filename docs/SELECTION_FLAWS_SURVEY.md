# Survey of Selection/Comparison Inconsistencies Across Colorado RLA Audits

Built from `analyze_selection_flaws.py`, informed by Copilot's analysis in
`copilot-sun_apr_26_2026_auditcenter_inconsistency_in_colorado_rla.md` and
`SELECTION_FLAWS.md`.

---

## Background: The Two Bugs

**Bug 1 — Cumulative `contest_cvr_ids`**  
`ComparisonAudit.addContestCVRIds()` always *appends*; the field grows across
rounds. `contest_selection.sql` reads the whole field with no round filter, so
every round's export reflects the final accumulated state. Symptom:
`contestSelection.csv` lists ballots from round N that were never worked by
the audit board.

**Bug 2 — SQL JOIN on `audit_reason`**  
`contest_comparison.sql` joins `comparison_audit` on `audit_reason` rather
than on contest identity. Any ballot pulled for *any* targeted contest of the
same type (county-wide, state-wide) is logged against every contest on that
ballot. Symptom: `contestComparison.csv` contains CVR IDs that never appeared
in `contestSelection.csv` for that contest.

**Bug 3 — `ContestCounter.groupingBy(name)` only**  
Contests are grouped by name string alone. Two counties using the same
un-prefixed contest name are silently merged into one cross-county draw.
Symptom: `contestsByCounty.csv` shows a county-level race without the county
name in the contest string.

---

## Method

For each audit directory containing both a `contestSelection.csv` (or
`contest_selection.csv`) and a `contestComparison.csv` (or
`contest_comparison.csv` / `CVRtoAuditBoardInterpretativeComparison.csv`
where it contains contest-level data):

- `sel_ids` = CVR IDs listed in `contest_cvr_ids` for that contest
- `cmp_ids` = CVR IDs appearing in `contestComparison.csv` for that contest
- `sel_only` = `sel_ids − cmp_ids` (drawn but no comparison record)
- `cmp_only` = `cmp_ids − sel_ids` (compared but never drawn for this contest)

---

## Summary Counts (all audits 2019–2025)

| Metric | Value |
|--------|-------|
| Rounds analysed | 22 |
| Rounds with at least one flaw | **22 / 22** |
| Contest-rounds with `sel_only > 0` | **869** |
| Contest-rounds with `cmp_only > 0` | **9,148** |

The near-universal `cmp_only > 0` across all rounds is consistent with Bug 2
— the `audit_reason`-based SQL join creates spurious comparison records for
every untargeted contest present on any audited ballot.

---

## Bug 1 Instances: Ballots Drawn But Not Audited

The strongest evidence is a `sel_only` count that is **identical across
multiple rounds**: the export captures the same cumulative end-state each
time, never showing a per-round delta.

### Top cases (sorted by sel_only)

| sel_only | sel | cmp | Election | Contest |
|----------|-----|-----|----------|---------|
| 1030 | 1787 | 764–799 | 2019/rounds 1-3 | City of Aurora Mayor - Arapahoe |
| 933 | 1158 | 225 | 2021/coordinated rounds 1-2 | Town of Castle Rock Ballot Issue 2B |
| 807 | 865 | 59 | 2020/statePrimary rounds 1-2 | State Representative - District 22 - REP |
| 569 | 634 | 65 | 2021/coordinated rounds 1-2 | City of Thornton Council Member - Ward 3 |
| 548 | 775 | 243 | 2020/general rounds 2-3 | City of Boulder Ballot Question 2C |
| 527 | 555 | 29 | 2022/primary rounds 1-2 | State Representative - District 21 - REP |
| 431 | 580 | 156 | 2021/coordinated rounds 1-2 | Arapahoe County School District #6 Littleton Director |
| 427 | 544 | 118 | 2020/statePrimary rounds 1-2 | State Senator - District 31 - DEM - Denver County |
| 386 | 420 | 34 | 2020/statePrimary rounds 1-2 | State Representative - District 20 - DEM |
| 369 | 551 | 186 | 2021/coordinated rounds 1-2 | Colorado Springs School District 11 Director - 2 Year Term |
| 365 | 1206 | 847 | 2022/primary round 2 | Douglas County Sheriff - REP |
| 332 | 567 | 235 | 2020/statePrimary rounds 1-2 | District Attorney - 11th Judicial District - REP - Chaffee |
| 309 | 318 | 9 | 2021/coordinated rounds 1-2 | West End School District RE-2 Ballot Issue 4A |
| 289 | 816 | 575 | 2020/general rounds 2-3 | City of Colorado Springs Ballot Question 2C |
| 288 | 321 | 33 | 2020/statePrimary rounds 1-2 | State Senator - District 8 - DEM - Rio Blanco County |
| 254 | 285 | 32 | 2020/statePrimary rounds 1-2 | Regent of U. of Colorado - CD 6 - REP - Adams County |
| 251 | 309 | 58 | 2019/rounds 1-3 | City Of Rocky Ford Referred Issue 2A |
| 246 | 298 | 57–65 | 2020/general rounds 1-3 | State Representative - District 30 |
| 244 | 372 | 131–146 | 2019/rounds 1-3 | Weld County School District 6 Ballot Issue 4C |
| 241 | 279 | 39 | 2020/statePrimary rounds 1-2 | State Senator - District 23 - DEM - Weld County |
| 223 | 276 | 53 | 2021/coordinated rounds 1-2 | Weld County School District RE-4 Ballot Issue 4A |
| 205 | 954 | 7499 | 2020/general rounds 2-3 | Proposition 114 (STATUTORY) |
| 190 | 213 | 24 | 2022/primary rounds 1-2 | State Representative - District 25 - REP |
| **189** | **378** | **193** | **2024/general rounds 1-3** | **Pueblo County Commissioner - District 2** |
| 186 | 264 | 172 | 2022/primary rounds 1-2 | Representative to 118th US Congress - CD 5 - DEM |
| 178 | 203 | 64 | 2022/primary rounds 1-2 | El Paso County Commissioner - District 5 - REP |
| 174 | 219 | 48 | 2022/primary rounds 1-2 | Mesa County - Representative 118th US Congress - CD 3 - DEM |
| 172 | 201 | 30 | 2020/statePrimary rounds 1-2 | State Representative - District 38 - DEM |
| 166 | 199 | 33–34 | 2019/rounds 1-3 | Cripple Creek-Victor School District RE-1 - District B |
| 166 | 240 | 115–153 | 2020/general rounds 1-3 | City and County of Denver Ballot Measure 2I |
| 164 | 240 | 76 | 2025-irv | City of Fort Collins Mayor |
| 105 | 156 | 59 | 2025/coordinated round 2 | Town of Telluride Ballot Question 300 |
| 385 | 424 | 39 | 2025/coordinated | Lewis-Palmer School District 38 Director - District 3 |
| 359 | 376 | 18 | 2025/coordinated | City of Arvada Council Member District 1 |
| 251 | 363 | 112 | 2025/coordinated | City of Thornton Ballot Question 2A |
| 233 | 263 | 30 | 2025/coordinated | Town of Crested Butte Mayor |

### Notable subtypes

**sel_only ≈ sel (near-total non-coverage):** Contests with nearly all drawn
ballots having no comparison record. These are the strongest evidence that the
audit board was never given those ballots to work. Examples: State
Representative - District 22 - REP (807/865, 93%); Town of Castle Rock Ballot
Issue 2B (933/1158, 81%); West End School District RE-2 4A (309/318, 97%).

**2025 coordinated — many contests, single-round analysis only:**
The 2025 audit has `round1/contestSelection.csv` and `round2/contestSelection.csv`
but no per-round `contestComparison.csv` — only `finalReports/contestComparison.csv`.
Comparing round-2 selection (cumulative) against the final comparison reveals
at least 25 contests with substantial `sel_only`. The signal is the same as
earlier years: ballots drawn but no audit board record.

For **Town of Telluride Ballot Question 300** specifically:
- Round 1 drew 81 CVR IDs; round 2 appended 75 more → 156 total.
- Final comparison: 59 CVR IDs.
- `sel_only = 105`: 55 from round-1 draws + 50 from round-2 draws, all unaudited.
This is a clearer demonstration of the mechanism than Pueblo, because both
rounds contributed unaudited ballots (not just the second round).

**sel grows between rounds, sel_only stays same or grows:** City of Boulder
2C shows sel_only=288 in round 1 then jumps to 548 in round 2 and remains 548
in round 3. This matches the mechanism: round 2 drew additional ballots
(sel went from 384→775), those new ballots were never audited, and round 3
added nothing new to the selection. City of Colorado Springs 2C follows the
same pattern.

**2022 general round 1 — 69 contests, sel > 0, cmp = 0 entirely:**  
The 2022 general audit's comparison data was only archived in Excel
(`AuditResultsReport.xlsx`, `StateAuditReport.xlsx`), not in CSV form. The
`CVRtoAuditBoardInterpretativeComparison.csv` present in that directory is
a *batch count* comparison (scanner/batch/count), not a contest-level one.
The 69 contests with CVR IDs in contestSelection have no CSV comparison
counterpart. Key examples:

| sel | Contest |
|-----|---------|
| 336 | Pueblo County Clerk and Recorder |
| 315 | Arapahoe County Commissioner - District 2 |
| 251 | Adams County Sheriff |
| 223 | Mesa County - Proposition FF (Statutory) |
| 214 | State Senator - District 30 |
| 200 | La Plata County Commissioner District 1 |
| 172 | Garfield County Clerk and Recorder |

---

## Bug 2 Instances: Comparison Records for Non-Selected Ballots

Every round in every year shows `cmp_only > 0` for many contests — consistent
with Bug 2 being structural across the system. The pattern is:

- Untargeted contest (sel=0): all cmp records are spurious
- Targeted contest (sel>0): a small number of additional cmp records come from
  ballots pulled for *other* targeted contests that happen to contain this
  contest

The 4-ballot `cmp_only` case for Pueblo County Commissioner - District 2 (2024)
documented in `SELECTION_FLAWS.md` appears unchanged across all three rounds:
CVR IDs 4447815, 4459345, 4466341, 4495312 — drawn for other Pueblo contests,
audited, and spuriously logged against PCCD2 via the `audit_reason` join.

---

## Bug 3 Instances: Contest Name Collisions

### 2024 general — Garfield County (confirmed)

Garfield County's CVR export omits the county name prefix for its two
commissioner contests:

```
Garfield: "County Commissioner - District 2"
Garfield: "County Commissioner - District 3"
```

All other counties that report county commissioners use the full county name
as a prefix (e.g., "Pueblo County Commissioner - District 2"). Under
`ContestCounter.countAllContests()`, which groups by `contest().name()` only,
Garfield's contests would be merged with any other county that uploads an
identically-named CVR string. No other county in the 2024 general uses that
exact string, so no cross-county merge occurred — but the code defect remains.

The same pattern was not found in 2019–2023 data (all Garfield entries in
earlier years also used the prefixed form or did not appear in the
contestsByCounty file used for this check).

### Statewide and multi-county races (by design)

Many contests appearing under multiple counties are intentional — statewide
ballot measures, judicial retention, congressional districts. The
`ContestCounter` grouping-by-name is *correct* for these. The Garfield issue
is specifically about county-local races that lack the county's name.

---

## How to Distinguish Bug 1 from "Ballots Not Containing That Contest"

Copilot raised the important alternative (Explanation A): ballots drawn via
the county-wide PRNG may not contain a specific district contest. Those would
correctly appear in `contestSelection.csv` (they were drawn) but not in
`contestComparison.csv` (no contest data to compare). The statistical
signature of this case is: `sel_only / sel` ≈ (1 − district fraction),
distributed randomly across the CVR ID space.

Bug 1 leaves a different signature:

1. The sel_only CVR IDs are concentrated in the *second half* of the sorted
   `contest_cvr_ids` list (later additions by `addContestCVRIds` in a second
   round).
2. The sel_only count is identical across all rounds (nothing changes per-round
   in the export).
3. Statistically: if the district contest appears on, say, 20% of county
   ballots, the probability that all 189 round-2 draws miss it is ~(0.8)^189
   ≈ 10^{-18} — essentially impossible.

The Pueblo case (189/189 second-half CVRs with no comparison, from a 90k-
ballot county) is overwhelmingly consistent with Bug 1, not Explanation A.

---

## 2025-IRV: City of Fort Collins Mayor (single round, sel_only=164)

The 2025-irv audit is Colorado's first IRV (Instant Runoff Voting) comparison
audit. The `contest_selection.csv` lists 240 CVR IDs for City of Fort Collins
Mayor (min_margin=5847). The `contest_comparison.csv` has only 76 matching
records. This is a single-round audit with no accumulation across rounds, so
the 164 `sel_only` ballots cannot be explained by the round-accumulation
mechanism.

Possible explanations:
1. The IRV audit uses a different comparison path (ranked ballot interpretation)
   and not all drawn ballots needed a regular comparison record.
2. Some drawn ballots genuinely don't contain the Fort Collins Mayor contest
   (if the domain was Larimer County-wide, many ballots outside Fort Collins
   would be selected).
3. Some ballots were drawn but not retrieved/worked.

The `ranked_ballot_interpretation.csv` file has 2,298 records for
Fort Collins Mayor, using a different identifier (`cvr_number` ≈ 190–190933)
than `contest_selection.csv` (`cvr_id` ≈ 2987–194123). These are different
ID namespaces and cannot be directly reconciled without a lookup table
mapping `cvr_id` → `cvr_number`. Until that mapping is established, it is
unknown whether the 164 unmatched drawn ballots were audited via the
IRV-specific path or genuinely not retrieved.

## Script

The full analysis is in `analyze_selection_flaws.py` at the project root.
Run with:

```
python3 analyze_selection_flaws.py 2>&1 | tee /tmp/selection_flaws_survey.txt
```
