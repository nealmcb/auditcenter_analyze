# Handoff Document for auditcenter_analyze Project

**Date:** 2024-10-27  
**From:** ColoradoRLA workspace conversation  
**To:** auditcenter_analyze workspace  
**Repository:** `/srv/s/electionaudits/auditcenter_analyze/`  

---

## Project Overview

**Purpose:** Independent verification and analysis tools for Colorado RLA audit center data  
**Origin:** Extracted from `colorado-rla-2018` verify branch (19 commits from 5220e437 onwards)  
**Primary User:** Election auditing researchers and officials  
**Focus:** Evidence-based elections with cryptographic verification  

**Data Source:**  
- Primary: `/srv/voting/audit/corla/scrapy/mirror/2024/general/` (via `data/` symlink)
- Dependency: `../colorado-rla-2018/server/.../rlacalc/` (via `rlacalc/` symlink)

---

## Development Practices (User Preferences)

### Git Safety
- ✗ NEVER skip hooks (`--no-verify`)
- ✗ NEVER force push
- ✗ NEVER auto-update git config
- ✓ Only commit when explicitly asked
- User has `alias rm='rm -i'` - use `\rm` or `/bin/rm` to bypass

### Package Management
- User has 446 packages in `~/.local/` (numpy 2.2.6, Jupyter, pandas, etc.)
- ✗ NEVER modify global packages
- ✓ Always use virtual environments (datasette-env/ already created)
- Reason: Avoid breaking Jupyter and other data science tools

### Communication Style
- Ask clarifying questions when formulas unclear
- Provide concrete examples with numbers
- Show calculations step-by-step
- Offer alternatives with tradeoffs
- Verify understanding - don't assume

### Naming Conventions
- Avoid terms implying fraud or malfeasance
- Be precise and factual in technical language
- Example: `had_fake_ballot` → `estimation_method`

### Testing Methodology
- Capture baseline outputs before changes
- Use diff to verify only expected changes
- Compare with ColoradoRLA's official results
- Document any discrepancies thoroughly

### Evidence-Based Elections Philosophy
- Everything must be cryptographically verifiable
- Link to original cast vote records (CVRs)
- Support independent verification by anyone
- Will integrate hashes, tweets, blockchain commitments
- Transparency and traceability are paramount

---

## Major Accomplishments

### ✅ Repository Setup (Completed)
**Extraction from colorado-rla-2018:**
- 8 Python verification scripts
- 3 datasette setup files
- 27 documentation files
- 1 .gitignore
- 19 commits of history preserved
- Clean directory structure created

**Files:**
```
analysis/       - Python scripts
datasette/      - Web tools
docs/           - Documentation
output/         - Generated databases
data/           → /srv/voting/audit/corla/scrapy/mirror/
rlacalc/        → ../colorado-rla-2018/.../rlacalc/
```

### ✅ Risk Calculation Tool (Working)
**Script:** `analysis/calculate_opportunistic_risk.py`
- Analyzes 722 contests in ~0.5 seconds
- 64 targeted + 658 opportunistic contests
- Proper downsampling to minimum sampling rate
- Saves to SQLite database

**Current results:**
- Targeted: 61/64 pass (after bug fix)
- Opportunistic: 223/658 below risk limit
- Skipped: 3 (Moffat County data issues)

### ✅ Random Selection Verification (Working)
**Scripts:** `verify_random_selection.py`, `verify_any_contest.py`
- SHA-256 PRNG verification
- Verified all 32 Bent County ballots match
- Cryptographic confidence: < 1 in 10^50 false match

### ✅ SQLite Database (Generated)
**File:** `output/colorado_rla.db` (1.2 MB)
- `contest_risk_analysis`: 722 rows
- `county_sampling_details`: 2,613 rows
- `audit_metadata`: 4 configuration values

### ✅ Datasette Environment (Ready)
**Setup:** `datasette-env/` virtual environment
- Isolated from global packages (numpy 1.x compatible)
- datasette 0.65.1 + datasette-vega installed
- Launch: `cd datasette && bash launch_datasette.sh`
- Access: http://localhost:8001

### ✅ CRITICAL BUG FIX (Oct 27, 2024)
**Issue:** Treating all discrepancies as overstatements

**Impact:**
- Conejos County Commissioner District 3: NOW PASSES ✓
  - Before: risk = 0.0484 (incorrectly used o1=1 for u2=1)
  - After: risk = 0.0128 (correctly uses u2=1)
- Agreement with ColoradoRLA: 96.9% (62/64 targeted contests)

**Commit:** `8ce1802` "Fix critical bug: Correctly classify discrepancies..."

---

## Current Status

### Just Completed
1. Fixed discrepancy classification bug (o1/o2/u1/u2)
2. Verified Conejos now matches ColoradoRLA
3. Committed fix with documentation
4. Updated implementation plan with correct contest_sampling_factor formula

### Active Work
**Understanding contest_sampling_factor formula** - User clarified:

```
contest_sampling_factor = (contest_prevalence) × (overall_sampling_rate)
                        = (votes / manifest) × (examined_total / manifest)
```

**Why this matters:**
- Accounts for BOTH contest rarity AND sampling intensity
- Counties with low overall sampling get lower factors (correct!)
- Enables proper downsampling across counties with different sampling rates
- Fixes 95 cases currently using arbitrary "fake ballot"

### Open Questions/Issues

**1. Routt & Sedgwick Investigation (Medium Priority)**
- Routt: We calculate risk=0.0414, ColoradoRLA says "risk_limit_achieved"
  - Sample count discrepancy: metadata shows 175, we found 77
  - Need to investigate why
- Sedgwick: risk=0.0305 vs limit=0.0300 (barely failing)
  - Could be rounding or calculation difference

**2. Vote-Based Estimation Ready to Implement (High Priority)**
- Formula confirmed with user
- Implementation plan written and updated
- Ready to code
- Expected improvement: 95 cases from ~2000% error to ~5% error

---

## TODO List

### Immediate (Next Session)
- [ ] Implement contest_sampling_factor formula
- [ ] Load tabulateCounty.csv at startup
- [ ] Update county_data calculation
- [ ] Update downsampling algorithm (use factor ratio)
- [ ] Test on BRUSH RURAL FIRE contest specifically
- [ ] Test on full dataset (compare to baseline)
- [ ] Update database schema (add new columns)
- [ ] Regenerate colorado_rla.db

### Investigation Required
- [ ] Routt County: Why 175 vs 77 ballots?
- [ ] Sedgwick County: Risk 0.0305 vs 0.0300 - rounding?
- [ ] Compare our KM_P_value calls with ColoradoRLA source
- [ ] Verify diluted_margin calculation is correct

### Short Term (1-2 weeks)
- [ ] Launch datasette for user (already set up!)
- [ ] Add canned SQL queries for common exploration
- [ ] Import all CSV files into database
- [ ] Normalize ballot manifest column names (11 variations)
- [ ] Normalize county names across files
- [ ] Add ballot_comparisons table (with timestamps)
- [ ] Add cryptographic commitments table

### Medium Term (3-4 weeks)
- [ ] Build Streamlit dashboard
- [ ] Contest detail pages with charts
- [ ] Risk distribution visualization
- [ ] Ballot trace (random selection → CVR → audit → risk)
- [ ] Hash verification status display
- [ ] Multi-round comparison tools

### Long Term
- [ ] CVR file integration (if available)
- [ ] Cryptographic commitment browser (tweets, blockchain)
- [ ] Verification certificate generation
- [ ] Photo evidence linking
- [ ] Public verification workflow

---

## Critical Technical Details

### Discrepancy Types (Very Different Impacts!)

```
o2 = two-vote overstatement   CVR favors winner by 2 votes  WORST impact on risk
o1 = one-vote overstatement   CVR favors winner by 1 vote   BAD impact on risk
u1 = one-vote understatement  CVR under-reports winner by 1 LESS impact on risk  
u2 = two-vote understatement  CVR under-reports winner by 2 LEAST impact on risk
```

**Recent bug:** Was using o1 for everything. Conejos had u2=1, which we treated as o1=1, causing 3.78× higher risk!

### Contest Sampling Factor Formula

**For each county:**
```python
contest_prevalence = votes_for_contest / manifest_count
                     # OR observed_with_contest / manifest_count if observed > 0

overall_sampling_rate = examined_total / manifest_count

contest_sampling_factor = contest_prevalence × overall_sampling_rate
```

**Find minimum factor across counties, then downsample others:**
```python
ratio = min_factor / county_factor
ballots_to_use = min(observed_count × ratio, observed_count)
```

This creates uniform sampling relative to BOTH contest prevalence AND sampling intensity.

### Data Files Structure

**Key CSV files in `data/2024/general/`:**
```
ballotManifests/               - 63 county files (11 different column name variations!)
contestsByCounty.csv           - Contest-county mapping
seed.csv                       - Random seed: 53417960661093690826
tabulateCounty.csv             - Vote totals by county (KEY for new formula)
round3/contest.csv             - Contest metadata + discrepancy counts (o1/o2/u1/u2)
round3/contestComparison.csv   - CVR vs audit interpretations + timestamps
round3/contestSelection.csv    - Selected CVR IDs
```

**Manifest column variations for ballot count:**
```
'# of Ballot Cards', '# of ballot cards', '#of Ballot Cards',
'# Ballot Cards', '# of Ballots Cards', '# of Ballots',
'# of Ballot', '# Cards', '# Ballots', '# of cards', '. of Ballots'
```

**County name normalization needed:**
- Files use both "Clear Creek" and "ClearCreek"
- Remove spaces for consistency

**Contest name variations:**
- Example: "Calhan School District No. RJ1 Question 5B" vs "Calhan School District RJ1 Question 5B"
- Need normalization or canonical list matching

### Baseline Results (For Comparison)

**After bug fix:**
```
Targeted contests: 64
  Achieved risk limit: 61/64 (95.3%)
  FAILED (3):
    - Dove Creek Ambulance District: risk=0.0471 (legitimate - has o2=2)
    - Routt County Commissioner District 1: risk=0.0414 (investigate)
    - Sedgwick County Commissioner District 3: risk=0.0305 (investigate)

Opportunistic contests: 658
  Below risk limit: 223/658 (37.3%)
```

### Ballot Reuse Across Rounds

**Finding:** Ballots are reused across rounds!
- Round 1: 4,523 unique ballots
- Round 3: 4,612 unique ballots
- Only 89 new ballots added in rounds 2-3

**Each ballot has multiple contest comparisons:**
- Example: Ballot 101-2-51 has 39 contest interpretations
- When any targeted contest samples it, ALL contests get interpreted
- No re-examination needed - existing interpretations reused

**Implications:**
- We already use ballots from all targeted samples (correct!)
- contestComparison.csv is cumulative by round
- Timestamps show when first examined

---

## Files Modified Recently

**Committed (in git):**
- `analysis/calculate_opportunistic_risk.py` - Fixed o1/o2/u1/u2 bug
- `docs/DISCREPANCY_CLASSIFICATION_BUG_FIX.md` - Bug technical details
- `docs/BUGFIX_RESULTS_SUMMARY.md` - Results analysis
- `docs/VOTE_BASED_ESTIMATION_CASE_STUDY.md` - OLD (needs update)
- `docs/VOTE_BASED_IMPLEMENTATION_PLAN.md` - UPDATED with correct formula

**Not yet committed:**
- Documentation updates just made

---

## Database Schema (Current)

```sql
contest_risk_analysis (
    contest_name TEXT PRIMARY KEY,
    audit_reason TEXT,                -- state_wide | county_wide | opportunistic_benefits
    min_margin INTEGER,
    contest_ballot_card_count INTEGER,
    diluted_margin REAL,
    sample_size INTEGER,
    discrepancies INTEGER,            -- Total (o1+o2+u1+u2)
    risk_value REAL,
    min_sampling_rate REAL,           -- WILL BECOME: min_contest_sampling_factor
    min_rate_county TEXT,             -- County with minimum factor
    counties_involved INTEGER,
    achieved_risk_limit BOOLEAN,
    analysis_timestamp TEXT,
    round INTEGER
)

county_sampling_details (
    id INTEGER PRIMARY KEY,
    contest_name TEXT,
    county_name TEXT,
    manifest_count INTEGER,
    observed_count INTEGER,
    examined_total INTEGER,
    sampling_rate REAL,               -- WILL BECOME: contest_sampling_factor
    ballots_used INTEGER,
    had_fake_ballot BOOLEAN,          -- WILL BECOME: estimation_method TEXT
    ballot_ids TEXT                   -- JSON array
)

audit_metadata (
    key TEXT PRIMARY KEY,
    value TEXT
)
```

**Schema changes needed for contest_sampling_factor:**
- Add: `vote_total`, `contest_prevalence`, `overall_sampling_rate`, `contest_sampling_factor`
- Rename: `had_fake_ballot` → `estimation_method`
- Update: `sampling_rate` → `contest_sampling_factor` (or keep both)

---

## Next Steps (Priority Order)

### 1. Implement Contest Sampling Factor (IMMEDIATE)
**Status:** Formula confirmed, implementation plan ready

**Tasks:**
1. Load `tabulateCounty.csv`
2. Calculate `contest_sampling_factor` for each county
3. Use votes when observed=0 (vote-based estimation)
4. Update downsampling to use factor ratio
5. Test on BRUSH RURAL FIRE
6. Test on full dataset
7. Compare to baseline

**Expected impact:**
- Fixes 95 "fake ballot" cases
- Improves accuracy for ALL contests
- More defensible methodology

### 2. Launch Datasette (User is waiting!)
**Status:** Environment ready, just needs to be launched

```bash
cd /srv/s/electionaudits/auditcenter_analyze/datasette
bash launch_datasette.sh
# Opens at http://localhost:8001
```

User wants to explore the data NOW (before further improvements).

### 3. Investigate Routt & Sedgwick
**Questions:**
- Why sample count discrepancy? (175 vs 77 for Routt)
- Are we calculating risk correctly? (barely failing vs ColoradoRLA pass)
- Need to trace through their calculations

### 4. Import All CSVs to Database
**Files to import:**
- Ballot manifests (normalized)
- Contest metadata (from contest.csv) 
- Ballot comparisons (with timestamps)
- Vote totals
- Cryptographic commitments

**Challenges:**
- 11 column name variations in manifests
- Contest name variations across files
- County name normalization

### 5. Build Streamlit Dashboard
**Purpose:** Interactive exploration beyond datasette
- Visual drill-down into contests
- Charts and timelines
- Hash verification interface
- Ballot trace visualization

---

## Key Insights from Session

### 1. Contest Sampling Factor Discovery

**Old approach (WRONG):**
```
sampling_rate = observed_count / manifest_count
```
Only accounted for contest prevalence, ignored overall sampling intensity.

**New approach (CORRECT):**
```
contest_sampling_factor = (votes / manifest) × (examined_total / manifest)
```
Accounts for BOTH contest prevalence AND overall sampling rate.

**Why it matters:**
- County with low overall sampling has low factor (correct constraint)
- County with rare contest has low factor (correct constraint)
- Product captures combined effect
- Enables proper downsampling across counties with different sampling rates

### 2. Multi-Contest Ballot Usage

**Discovery:** Same ballot examined for ALL contests on it
- Ballot 101-2-51 has 39 contest comparisons
- When Presidential Electors samples it, all 39 contests get interpreted
- We already use this correctly in current code

**Implication:** Ballots from state-wide + county-wide targeted samples are ALL available for opportunistic contests.

### 3. Discrepancy Types Matter Hugely

**o2 vs u2:** Very different risk impacts!
- Conejos had u2=1, we treated as o1=1
- Result: 3.78× higher calculated risk
- After fix: matches ColoradoRLA

**Learning:** Always use ColoradoRLA's classifications when available (they've already done the work correctly).

---

## Code Quality Standards

**This is election integrity work - accuracy is critical:**
- Test changes against baselines
- Document methodology clearly
- Compare with ColoradoRLA when possible
- Explain discrepancies thoroughly
- Use real data when available (not arbitrary placeholders)
- Make calculations independently verifiable

---

## Technical Reference

### Baseline Output Location
`/tmp/baseline_output.txt` - Captured before bug fix

### Key Algorithms

**Downsampling:**
```
1. Calculate contest_sampling_factor for each county
2. Find minimum factor
3. Minimum-factor county: use ALL observed ballots
4. Other counties: downsample by ratio (limited by observations)
5. Creates uniform random sample
```

**Kaplan-Markov Risk:**
```python
risk = rlacalc.KM_P_value(
    n=sample_size,
    gamma=1.03905,
    margin=diluted_margin,
    o1=one_vote_over,
    o2=two_vote_over,
    u1=one_vote_under,
    u2=two_vote_under
)
```

### Important Constants
- `RISK_LIMIT = 0.03`
- `GAMMA = 1.03905`
- Random seed: `53417960661093690826`

---

## Known Issues & Investigations

### 1. Sample Count Discrepancy (Routt)
- ColoradoRLA metadata: `audited_sample_count=175`
- contestComparison.csv: 77 ballots found
- Gap: 98 ballots
- Need to understand where the discrepancy is

### 2. Risk Calculation Differences (Routt & Sedgwick)
- Both: ColoradoRLA says "risk_limit_achieved"
- Both: We calculate just above 0.03
- Both: Zero discrepancies (purely sample-size driven)
- May be formula difference or missing ballots

### 3. Contest Name Variations
- Same contest, different names in different files
- Example: Calhan School District (with/without "No.")
- Need normalization strategy

---

## Database Exploration

### Useful Queries (Once Datasette Running)

**Failed targeted contests:**
```sql
SELECT contest_name, sample_size, risk_value 
FROM contest_risk_analysis 
WHERE audit_reason IN ('state_wide_contest', 'county_wide_contest')
  AND achieved_risk_limit = 0
```

**Opportunistic contests that passed:**
```sql
SELECT contest_name, sample_size, risk_value
FROM contest_risk_analysis
WHERE audit_reason = 'opportunistic_benefits'
  AND achieved_risk_limit = 1
ORDER BY risk_value
LIMIT 50
```

**County sampling coverage:**
```sql
SELECT county_name, manifest_count, examined_total,
       ROUND(100.0 * examined_total / manifest_count, 2) as pct_sampled
FROM county_sampling_details
GROUP BY county_name, manifest_count, examined_total
ORDER BY pct_sampled DESC
```

---

## Parting Wisdom

### For the Next Agent

**You're working with Neal McBurnett:**
- Deep election auditing expertise
- Values evidence-based verification
- Careful about git/package management
- Prefers understanding over quick fixes
- Will catch subtle errors - explain clearly

**Communication tips:**
- Provide concrete examples (not just formulas)
- Show your work with actual calculations
- Offer alternatives when uncertain
- Ask for clarification on requirements
- Don't implement until understanding is confirmed

**Code principles:**
- Accuracy over speed
- Transparency over convenience
- Verification over trust
- Documentation over comments
- Evidence over assumptions

### The Big Picture

This project enables **independent verification of election audits**. Every calculation should be:
- Reproducible by anyone with public data
- Traceable to cryptographic commitments
- Explainable to technical and non-technical audiences
- Verifiably correct (matches ColoradoRLA or documented differences)

**You're building infrastructure for democracy.** Take the time to get it right.

### Current Momentum

- Just fixed a critical bug (good progress!)
- Contest sampling factor formula confirmed (ready to implement)
- Datasette ready to launch (user eager to explore)
- Strong foundation in place

**Next agent: Pick up with implementing contest_sampling_factor. The plan is solid. Execute carefully and test thoroughly.**

---

**Good luck! 🗳️**

