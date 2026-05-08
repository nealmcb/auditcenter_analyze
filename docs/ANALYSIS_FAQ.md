# Analysis FAQ for Audit Center Data

This FAQ is a practical guide for reading the archived Colorado auditcenter data without repeating earlier misunderstandings. It consolidates the more reliable findings from the notes in this repository and points out where older notes conflict with later code-backed conclusions.

## 1) What is the most important thing to know before analyzing anything?

The public CSV exports are useful, but they are not a perfect representation of what the live audit system did.

Two upstream export problems recur throughout the notes:

- `contestSelection.csv` is cumulative across rounds, so later exports can include ballots drawn in earlier and later rounds together.
- `contestComparison.csv` can include comparison rows for contests that were never directly drawn, because opportunistic examination and SQL joins blur the boundary between “drawn for this contest” and “compared while this ballot card was already in hand.”

See `docs/SELECTION_FLAWS.md`, `docs/SELECTION_FLAWS_SURVEY.md`, and `docs/copilot-sun_apr_26_2026_auditcenter_inconsistency_in_colorado_rla.md`.

## 2) Are “ballot” and “ballot card” the same thing?

No.

A ballot packet can contain multiple ballot cards, and different cards can contain different contests. Many apparent mismatches stop being mysterious once you remember that the data is mostly about ballot cards, not full ballot packets.

That means:

- a selected card may not contain the contest you expected,
- another card from the same packet may be the one that contains the targeted contest,
- cards with “no targeted contest” are often normal rather than evidence of a bad draw.

See `docs/BALLOT_CARD_COUNT_EXPLAINED.md` and `docs/DOMAIN_SIZE_CONFIRMED.md`.

## 3) Why do some ballots seem to be “missing” contests?

Usually because you are looking at only one card from a multi-card ballot packet, or because the contest appears only in part of a county or jurisdiction.

Common benign explanations:

- district contests only appear on some county ballot cards,
- statewide or opportunistic contests may be observed on cards drawn for another targeted contest,
- the retrieved ballot packet may include extra cards that do not carry the targeted contest.

Do not assume “missing contest” means “missing data” until you rule out ballot-card scope.

## 4) What is the difference between `ballot_card_count` and `contest_ballot_card_count`?

- `ballot_card_count`: total ballot cards in the contest’s county scope
- `contest_ballot_card_count`: ballot cards that actually contain that contest

They are both meaningful, but they answer different questions.

The later, code-backed conclusion in this repo is:

- random selection domain is driven by the manifest total for the participating counties,
- `contest_ballot_card_count` is primarily for risk/sample calculations and contest prevalence.

When older notes disagree, trust `docs/DOMAIN_SIZE_CONFIRMED.md` over the earlier interpretation in `docs/BALLOT_CARD_COUNT_EXPLAINED.md`. That older note is still useful for field definitions and ballot-card framing, but not for the final statement about random-selection domain.

## 5) Should `contestSelection.csv` and `contestComparison.csv` match 1:1?

No. Treat that as a false assumption.

This repository documents repeated structural mismatches across many rounds and years. Some are explained by cumulative selection exports, and some by opportunistic or over-broad comparison exports. A simple set difference between those files is not enough to prove that ballots were skipped.

Use those files as related but not interchangeable evidence sets.

## 6) Does `sel_only` prove ballots were not actually audited?

Not by itself.

At least two explanations are possible:

1. the ballot card was legitimately selected, but that card did not contain the contest, so there is no comparison row for that contest;
2. the ballot was selected in a later round but never physically worked before the audit concluded.

The public CSV exports do not fully distinguish these cases. Several notes conclude that live-table evidence such as `cvr_audit_info` would be needed to prove which explanation applies in a given case.

## 7) What does `audited_sample_count` mean, and when is it misleading?

It is most reliable for targeted contests.

For opportunistic contests, `audited_sample_count = 0` is often expected even when ballots were in fact examined. The actual examined count for those contests is better inferred from `contestComparison.csv`.

See `docs/OPPORTUNISTIC_CONTESTS_UPDATE.md` and `docs/AUDIT_TERMINOLOGY.md`.

## 8) What does “opportunistic” mean here?

It means the contest was examined because it appeared on ballot cards that were already pulled for a different targeted contest.

So:

- opportunistic contests can have comparison rows,
- they can affect downstream analysis,
- but they were not the direct driver of the random draw.

This matters because you should not describe all such contests as having had a full targeted RLA.

## 9) Why are county joins fragile?

Because county names are not uniform across files.

Examples already documented here include:

- `ClearCreekBallotManifest.csv`
- `Clear Creek` in CSV content
- mixed spacing/casing in user-facing inputs

The repository’s normalization helpers intentionally separate:

- canonical display form (`normalize_county_name`)
- lookup/join key (`normalized_county_key`)

See `src/auditcenter_analyze/normalize.py` and `docs/COUNTY_KEY_EXPLANATION.md`.

## 10) Why are manifest imports fragile?

Because the manifest ballot-count column name is not standardized.

The code already handles a long list of variants, including `# of Ballot Cards`, `# Ballots`, `# in Batch`, and others. Any second-pass import pipeline that assumes a single column name will silently miscount counties.

See `src/auditcenter_analyze/csv_loaders.py` and `docs/HANDOFF_DOCUMENT.md`.

## 11) Are contest names stable enough to use as unique keys?

Not always.

Known hazards include:

- trailing whitespace,
- punctuation changes,
- Unicode quote variants,
- missing county prefixes,
- same visible contest text used in multiple places.

The Garfield discussion in the notes shows why grouping only by contest name can be dangerous for county-local contests. Use normalized keys plus county/round context whenever possible.

## 12) Can I infer audit-board identity from `audit_board_selection`?

No.

Despite the field name, `audit_board_selection` is the board’s interpretation of the vote, not the board number. Timestamp clustering may help infer workflow patterns, but direct board identity is not present in that field.

See `docs/TIMESTAMP_ANALYSIS_PLAN.md`.

## 13) What do timestamps reliably tell us?

Mostly when interpretations were entered, not when ballots were physically retrieved.

Useful cautions:

- one ballot card can appear in many comparison rows because it has many contests,
- most cards share one timestamp across contests,
- some cards have multiple timestamps because they were revisited or completed later,
- timestamps are informative for process analysis, but weak evidence for board identity or throughput by themselves.

See `docs/TIMESTAMP_ANALYSIS_PLAN.md` and `docs/TIMESTAMP_REGRESSION_ANALYSIS.md`.

## 14) Are empty strings a simple way to count undervotes?

No.

An empty string can mean different things depending on context, including:

- true undervote,
- contest not present on that card,
- one side recorded nothing while the other side recorded selections.

This is one reason the current notes emphasize better normalization of selections and caution around discrepancy counting. See `docs/UNDERVOTE_QUERYING_CHALLENGES.md`.

## 15) Are all discrepancies interchangeable?

No. The repo repeatedly distinguishes:

- `o2` two-vote overstatement
- `o1` one-vote overstatement
- `u1` one-vote understatement
- `u2` two-vote understatement

They do not affect risk the same way. Older or partial logic that treated every discrepancy as the same kind can materially distort risk values.

See `docs/DISCREPANCY_CLASSIFICATION_BUG_FIX.md`, `docs/BASELINE_DIFFERENCES_ROOT_CAUSE.md`, and `docs/HANDOFF_DOCUMENT.md`.

## 16) Which notes should I trust most?

Prefer the documents that either:

- cite upstream Java/SQL behavior directly, or
- line up with the current Python code in `src/auditcenter_analyze/`.

Good starting points:

- `docs/SELECTION_FLAWS.md`
- `docs/SELECTION_FLAWS_SURVEY.md`
- `docs/DOMAIN_SIZE_CONFIRMED.md`
- `docs/COUNTY_KEY_EXPLANATION.md`
- `docs/AUDIT_TERMINOLOGY.md`
- `docs/UNDERVOTE_QUERYING_CHALLENGES.md`
- `src/auditcenter_analyze/normalize.py` for the current normalization rules the docs refer to
- `src/auditcenter_analyze/csv_loaders.py` for the manifest/header handling the docs refer to
- `src/auditcenter_analyze/import_csvs.py` for the current Typer-based import workflow
- `src/auditcenter_analyze/db_schema.py` for the current normalized SQLite structure

Be especially careful with older exploratory notes when a later file explicitly says the earlier interpretation was wrong.

## 17) What is already in place for a better second pass?

The repo already has the beginnings of a normalized SQLite pipeline:

- `src/auditcenter_analyze/import_csvs.py` provides a Typer CLI,
- `src/auditcenter_analyze/db_schema.py` defines normalized tables,
- `src/auditcenter_analyze/csv_loaders.py` handles manifests, counties, contests, vote totals, seeds, and round data,
- `src/auditcenter_analyze/normalize.py` centralizes key name-cleaning rules.

That means the next pass should build on the existing import/schema work rather than starting from scratch.

## 18) If I normalize everything into SQLite, what should I preserve?

Preserve both normalized and raw forms.

In practice, that means:

- keep raw CSV rows for traceability,
- keep normalized county and contest keys for joins,
- separate ballot-card facts from ballot-packet assumptions,
- keep round context explicit,
- preserve provenance about which CSV and round a record came from.

The current schema already follows this pattern in several tables by keeping `raw_row` columns and normalized lookup fields.

## 19) What should a future MCP/tooling pass focus on?

Focus on reducing repeated ambiguity rather than only adding more reports.

Highest-value targets:

1. a dependable SQLite import/rebuild workflow for all rounds;
2. reusable query helpers for contest scope, county normalization, and round-aware selection/comparison joins;
3. explicit views for targeted vs opportunistic examination;
4. helper functions or skills that explain ballot-card vs ballot-packet behavior before doing “missing ballot” analysis;
5. audit workflows that flag when a conclusion depends on unavailable live data rather than exported CSVs.

## 20) What are the safest rules of thumb for future analysis?

- Think in ballot cards first, ballot packets second.
- Do not assume selection and comparison exports are round-pure or 1:1.
- Treat opportunistic contests as “examined on already-pulled cards,” not “independently selected.”
- Normalize county and contest keys before joining anything.
- Keep raw values for auditability.
- Treat empty selections and discrepancy types carefully.
- Prefer later code-backed notes over earlier speculative notes when they conflict.

## Recommended next reading order

1. `README.md`
2. `docs/AUDIT_TERMINOLOGY.md`
3. `docs/DOMAIN_SIZE_CONFIRMED.md`
4. `docs/COUNTY_KEY_EXPLANATION.md`
5. `docs/SELECTION_FLAWS.md`
6. `docs/SELECTION_FLAWS_SURVEY.md`
7. `docs/UNDERVOTE_QUERYING_CHALLENGES.md`
8. `src/auditcenter_analyze/import_csvs.py`
9. `src/auditcenter_analyze/db_schema.py`
10. `src/auditcenter_analyze/csv_loaders.py`
