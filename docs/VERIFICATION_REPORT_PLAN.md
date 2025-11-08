# Verification Report Plan

## Objective
Create a comprehensive report showing how to verify a targeted RLA contest from start to finish, demonstrating the complete cryptographic chain from seed to selected ballots.

## Target Contest
**Crowley County Commissioner - District 3** (contest_id=198)
- Simple single-county contest suitable for verification
- Targeted (`county_wide_contest`)
- Sample size: 15 ballots
- Risk achieved: Yes (0.009 < 0.03)

## Report Structure

### Section 1: Contest Overview
- Contest name, ID, and audit reason
- County(s) involved (just Crowley County)
- Winner(s) and vote totals
- Margin calculation
- Contest metadata from database

### Section 3: Sample Size Calculation
Show how sample size was determined:
- Reference Kaplan-Markov calculation
- Expected sample size for given margin and risk limit
- Link to calculation or display n=15
- Note: This is deterministic based on inputs

### Section 4: Ballot Manifest
- County: Crowley
- Total ballot cards: 1729
- Tabulator: 102
- Number of batches and structure
- Link to manifest file/data
- Show how manifest creates ordered list of ballots

### Section 5: Random Seed
- Seed value: 53417960661093690826
- Source: seed.csv
- Public commitment: [if available]
- Hash verification: [if available]

### Section 6: Cryptographic Selection Process
For each of the 15 ballots, show:

#### Ballot 1:
1. **Hash Input**: `seed,1` → `"53417960661093690826,1"`
2. **SHA-256 Hash**: Show full hex hash
3. **Convert to Integer**: Show large integer
4. **Modulo Operation**: `hash_int % 1729`
5. **Add 1**: 1-indexed result (final random number)
6. **Map to Manifest**: Look up position N in ordered ballot list
7. **Imprinted ID**: Show tabulator-batch-position
8. **Verification**: Confirm this matches actual selection

Repeat for ballots 2-15 (can collapse/truncate after first few)

### Section 7: Actual Audit Selections
- List all 15 imprinted_ids from database
- Sort for comparison
- Match against calculated selections

### Section ?: RLA Input Parameters
Display the inputs needed for risk calculation:
- Risk limit: 0.03 (3%)
- Gamma: 1.03905
- Diluted margin: min_margin / contest_ballot_card_count
- Min margin: 967 votes
- Contest ballot card count: 1729
- Calculated diluted margin

### Section 8: Verification Results
- ✓ All 15 ballots match
- ✓ Cryptographic integrity confirmed
- ✓ Deterministic reproducibility demonstrated

### Section 9: Reproducibility Instructions
Provide a complete recipe:
1. Retrieve seed from audit_random_seed table
2. Get contest_ballot_card_count from contests table
3. Calculate sample size needed
4. Generate random numbers using SHA-256
5. Load manifest and map to ballot positions
6. Compare against ballot_comparisons

## Implementation Plan

### Phase 1: Data Gathering Script
Create `generate_verification_report.py`:
- Takes contest_name as argument
- Loads all data from database
- Cross-references CSV manifests
- Generates the report structure above

### Phase 2: Report Generation
Output format: Markdown
- Human-readable narrative
- Code snippets showing calculations
- Tables showing data
- Links to source files
- Verification commands

### Phase 3: Interactive Display
Consider Datasette integration:
- Custom query that shows the report
- Or embed as documentation page
- Or standalone HTML report

## Technical Requirements

### Dependencies
- Database connection (already have)
- CSV manifest loading (already have)
- SHA-256 hashing (already have)
- Ballot mapping logic (already have)

### Code Reuse
Leverage existing scripts:
- `verify_random_selection.py` - random number generation
- `verify_any_contest.py` - contest lookup
- `csv_loaders.py` - manifest loading

### Output Examples
Need to show actual output:
- First ballot calculation with full SHA-256
- Manifest mapping demonstration
- Comparison table

## Notes
- This is for ONE specific contest initially
- Could be generalized later
- Focus on clarity and transparency
- Every step should be reproducible by independent verifiers


