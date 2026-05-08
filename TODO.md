# TODO List

## Core Functionality

- [ ] **sampling factor implementation and testing**
  - Implement proper sampling factor calculations
  - Test with various contest types and scenarios

- [ ] **Pick some contests to confirm calculations on**
  - Choose simple contests
  - Choose multi-county contests
  - Choose existing targets
  - Choose contests with discrepancies of various types
  - Choose contests with selections in certain counties

- [ ] **Review has_discrepancy implementation**
  - Investigate issue: seems to ignore undervotes (bad news)
  - Check if consensus==NO is relevant
  - Determine frequency of consensus==NO occurrence

- [ ] **Investigate Routt and Sedgwick County failures**
  - Why sample count discrepancy? (175 vs 77 for Routt)
  - Are risk calculations correct? (barely failing vs ColoradoRLA pass)
  - Trace through ColoradoRLA calculations to understand differences

- [ ] **Investigate 722 vs 725 contest analysis discrepancy**
  - 725 contests imported into contests table
  - Only 722 contests have risk analysis results
  - Missing 3 Moffat County contests: "City of Craig Ballot Question 2A", "Moffat County Commissioner District 1", "Moffat County Commissioner District 2"
  - These contests appear in ballot_comparisons but not in contest_risk_analysis
  - Determine why calculate_opportunistic_risk.py skipped them

- [ ] **Compare with official tabulation results and call out pretend audits of irrelevant county results**
  - Document where county-specific “targets” are actually slices of wider contests, e.g. Proposition 130 - Kit Carson

- [ ] **address FIXME to determine winners, losers, and proper discrepancy type**
  - Reference rla_report and related documentation
  - Implement proper winner/loser determination logic

## Code Quality & Architecture

- [x] **Create a practical FAQ for interpreting archive caveats** ✅
  - Added `docs/ANALYSIS_FAQ.md`
  - Consolidates reliable findings from notes and code
  - Highlights ballot-card scope, export caveats, normalization, and next-pass guidance

- [x] **Set up git pre-commit hooks to run tests, formatting, and lint checks** ✅
  - Hook stored in `.hooks/pre-commit` (version controlled)
  - Symlinked via `make setup-hooks`
  - See: docs/PRE_COMMIT_HOOK_OPTIONS.md

- [ ] **write a clean spec based on rla_report and work to date**
  - Document current implementation
  - Reference rla_report specifications
  - Capture insights from work to date

- [ ] **modularize**
  - Break down monolithic functions
  - Improve code organization
  - Enhance reusability

- [ ] **craft good unit tests**
  - Create tests for core calculations
  - Test edge cases and error handling
  - Ensure good coverage


## External Integration

- [ ] **Import all auditcenter CSV files to datasette database**
  - Ballot manifests (63 county files) - handle 11 different column name variations
  - Contest metadata (from contest.csv in each round)
  - Ballot comparisons (from contestComparison.csv with timestamps)
  - Vote totals (from tabulate.csv and tabulateCounty.csv)
  - Contest selections (from contestSelection.csv)
  - Contest-to-county mapping (from contestsByCounty.csv)
  - Random seed (from seed.csv)
  - Handle county name normalization (Clear Creek vs ClearCreek, etc.)
  - Handle contest name variations (encoding, whitespace, prefixes/suffixes)
  - Link between analysis tables and source CSV data
  - See docs/HANDOFF_DOCUMENT.md section "Import All CSVs to Database"

- [x] **Add proper foreign key columns to analysis tables** ✅
  - Added INTEGER contest_id and county_id columns to both tables
  - Kept TEXT columns for human-readable display in Datasette
  - Added FOREIGN KEY constraints and lookups in save_to_database
  - Datasette now auto-detects and creates clickable links
  - Note: default DB path changed to output/colorado_rla.db

- [ ] **Use Arlo to reanalyze Colorado audit center results**
  - Investigate Arlo library availability
  - Assess relevance for our use case
  - Integrate if beneficial

## Feature Development

- [ ] **Develop predictive opportunistic audit command**
  - Predict risk levels based on election results
  - Consider which contests are selected for audit
  - Implement without actual audit data

- [ ] **Identify contests with risk levels above one**
  - Filter contests where sample discrepancies worsen initial risk
  - Report these exceptional cases clearly

- [ ] **Add command completion for options, counties, contests**
  - Focus on main commands, especially show_interpretations
  - Implement tab completion
  - Improve user experience

- [ ] **Build Streamlit dashboard**
  - Interactive exploration beyond datasette
  - Visual drill-down into contests
  - Charts and timelines
  - Hash verification interface
  - Ballot trace visualization
  - See docs/cursor_chat/cursor_web_app_design_for_risk_analysis.md

- [ ] **Expand ballot manifests to individual ballot records**
  - Currently manifests only have batch-level counts
  - Create per-ballot rows with tabulator, batch, position
  - Required for detailed ballot trace functionality

- [ ] **Produce some charts, averages**
  - Visualize results
  - Calculate and display averages
  - Note: consider colorblind accessibility (user has deuteranopia)

- [ ] **Provide overview starting from the beginning**
  - Guide novice users through election results
  - Show winners and basic contest information
  - Make data accessible and understandable

- [ ] **Create verification report for Crowley County Commissioner District 3**
  - Show complete cryptographic verification chain
  - Demonstrate seed → SHA-256 → ballot selection
  - Display contest info, margins, vote totals
  - Map random numbers to manifest positions
  - Verify all 15 selected ballots
  - See docs/VERIFICATION_REPORT_PLAN.md for spec
  - Needs testing: `src/auditcenter_analyze/generate_verification_report.py`

- [ ] **Verify discrepancy classifications in contest.csv**
  - Currently relying on ColoradoRLA's o1/o2/u1/u2 counts from contest.csv
  - Need to verify these classifications are correct by examining actual ballot comparisons
  - Check cvr_choice vs audit_choice against winner/loser to confirm overstatement vs understatement
  - Verify vote count differences (1-vote vs 2-vote errors)

## Additional Notes

### Data Structure Challenges (from docs)
- 11 different column name variations in ballot manifests (e.g., "# of Ballot Cards", "# of ballot cards", "# of Ballots", etc.)
- County name normalization needed (Clear Creek vs ClearCreek)
- Contest name variations (encoding issues, whitespace, prefixes/suffixes)
- Manifests have batch-level data only, need expansion to per-ballot records
- Missing CVR data - only comparisons available, not original CVR files
- Ballot reuse across rounds needs consideration

### Key CSV Files Available
Located in `data/2024/general/`:
- ballotManifests/ (63 county-specific files)
- contestsByCounty.csv
- seed.csv
- tabulate.csv, tabulateCounty.csv
- round1/, round2/, round3/ (each containing contest.csv, contestComparison.csv, contestSelection.csv)

### References
- Main CSV import plan: docs/HANDOFF_DOCUMENT.md "Import All CSVs to Database"
- Data structure details: docs/cursor_chat/cursor_web_app_design_for_risk_analysis.md
- Contest sampling factor: docs/HANDOFF_DOCUMENT.md "Contest Sampling Factor Discovery"
