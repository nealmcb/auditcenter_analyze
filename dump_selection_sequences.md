Selection Mapping Snapshot
Saved tooling: new helper src/auditcenter_analyze/dump_selection_sequences.py parses every contestSelection.csv, maps CVR IDs to (county, imprinted_id) via the database, and emits repeatable artifacts. Run it any time with
uv run python -m src.auditcenter_analyze.dump_selection_sequences.
Artifacts written (all under output/):
targeted_selection_sequences.csv — ordered draws for every targeted contest (sequence, county, imprinted ID, CVR ID, round metadata). 454 101 rows capture duplicates and multi-county draws.
contest_comparison_all_pairs.csv — the 4 897 distinct (county_id, county_name, imprinted_id) combinations present anywhere in contestComparison.csv.
contest_comparison_residual_pairs.csv — now empty because every pair is accounted for by the targeted draws once we look up CVRs globally.
targeted_selection_summary.json — quick counts (all_pairs = 4 897, targeted_pairs = 4 897, residual_pairs = 0) plus placeholders for any missing data (none remain).
Why earlier numbers bounced (916 → 891 → 683): each attempt subtracted county draws using different filters. Once we stopped insisting the match live under the same contest label (and instead trusted the CVR-to-imprinted mapping), every ballot card in contestComparison tied back to an official targeted draw, so the residual set collapsed to zero.
Exact lists per method:
“All pairs” → contest_comparison_all_pairs.csv (4 897 rows).
“Targeted sequences” → targeted_selection_sequences.csv (per-contest sequence ordering).
“Residual” → contest_comparison_residual_pairs.csv (currently only the header).
This gives you a precise, reproducible index of every sampled ballot card along with its draw position for each targeted contest; opportunistic contests never factor into the tagging, per your request. If you want additional slices (e.g., statewide-only sequences), we can filter targeted_selection_sequences.csv directly.
