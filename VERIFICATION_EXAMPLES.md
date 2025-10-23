# Verification Tool Examples

## Important Terminology

**Please read [AUDIT_TERMINOLOGY.md](AUDIT_TERMINOLOGY.md) for complete details.**

Quick distinctions:
- **Targeted for RLA** = Contest was specifically selected for risk-limiting audit (`audit_reason` = `county_wide_contest` or `state_wide_contest`)
- **Examined ballots** = Physical ballots were looked at (includes both targeted and opportunistic contests)
- **Opportunistic** = Contest examined because it appeared on ballots pulled for targeted contests (`audit_reason` = `opportunistic_benefits`)

The 2024 General Election had:
- **65 contests targeted for RLA** (2 statewide + 63 county-level)
- **~727 contests with examined ballots** (65 targeted + ~662 opportunistic)

## Quick Reference for All Features

### Basic Verification

**Verify Bent County Commissioner-District 1 (default):**
```bash
python3 verify_random_selection.py
```

**Output:**
```
✓✓✓ VERIFICATION SUCCESSFUL ✓✓✓
All 32 ballots were correctly selected based on seed 53417960661093690826
```

---

### See Cryptographic Details

**Show SHA-256 hashes for first 5 selections:**
```bash
python3 verify_random_selection_verbose.py
```

**Output includes:**
```
Selection #1:
  Input:      '53417960661093690826,1'
  SHA-256:    72c8598cb8032587f3b69c896ff86b2697b9958347358981025b8e16da486c90
  Result:     125
  Ballot:     102-5-25
```

---

### Discovery: List What's Available

#### 1. List All Counties (63 total)
```bash
python3 verify_any_contest.py --list-counties
```

**Output:**
```
Counties with audit data:
--------------------------------------------------------------------------------
  Adams
  Alamosa
  Arapahoe
  ...
  Weld
  Yuma

Total: 63 counties
```

#### 2. List All Contests (~727 total)
```bash
python3 verify_any_contest.py --list-contests
```

**Output:**
```
Available contests in round 1:
--------------------------------------------------------------------------------
  1. 17th Judicial District Ballot Question 7B               [in_progress]
  2. Adams 12 Five Star Schools Ballot Issue 5D              [in_progress]
  ...
```

#### 3. List Contests for a Specific County

**Show all contests with examined ballots:**
```bash
python3 verify_any_contest.py --list-contests-for-county Bent
```

**Output:**
```
Contests with examined ballots in Bent County:
--------------------------------------------------------------------------------
  Amendment 79 (CONSTITUTIONAL)                           [opportunistic]    ( 32 ballots)
  Bent County Commissioner-District 1                     [TARGETED]         ( 32 ballots)
  Presidential Electors                                   [STATE RLA]        ( 32 ballots)
  ...

Total: 32 contests with examined ballots
  3 were targeted for RLA (county_wide_contest or state_wide_contest)
  29 had opportunistic examination (ballots pulled for other contests)
```

**Show ONLY contests targeted for RLA:**
```bash
python3 verify_any_contest.py --list-contests-for-county Bent --targeted-only
```

**Output:**
```
Contests TARGETED for RLA in Bent County:
--------------------------------------------------------------------------------
  Bent County Commissioner-District 1                     [TARGETED]         ( 32 ballots)
  Presidential Electors                                   [STATE RLA]        ( 32 ballots)
  Regent of the University of Colorado - At Large         [STATE RLA]        ( 32 ballots)

Total: 3 contests with examined ballots
```

**Try other counties:**
```bash
python3 verify_any_contest.py --list-contests-for-county Adams --targeted-only
python3 verify_any_contest.py --list-contests-for-county Denver --targeted-only
python3 verify_any_contest.py --list-contests-for-county "El Paso" --targeted-only
```

#### 4. List Counties for a Specific Contest
```bash
python3 verify_any_contest.py --list-counties-for-contest "Amendment 79 (CONSTITUTIONAL)"
```

**Output:**
```
Counties with ballots audited for: Amendment 79 (CONSTITUTIONAL)
--------------------------------------------------------------------------------
  Pueblo                         (193 ballots)
  El Paso                        (160 ballots)
  Dolores                        (143 ballots)
  ...
  Bent                           ( 32 ballots)

Total: 63 counties
```

**Try other contests:**
```bash
# Statewide contests
python3 verify_any_contest.py --list-counties-for-contest "Presidential Electors"
python3 verify_any_contest.py --list-counties-for-contest "Amendment 80 (CONSTITUTIONAL)"

# County-specific contests
python3 verify_any_contest.py --list-counties-for-contest "Adams County Commissioner - District 5"
python3 verify_any_contest.py --list-counties-for-contest "Denver Mayor"
```

---

### Verify Specific Contests

#### County-Wide Contest (Works Best)
```bash
python3 verify_any_contest.py --contest "Bent County Commissioner-District 1"
```

**Output:**
```
✓ Found contest data in round 3
  Status: risk_limit_achieved
  Ballot Card Count: 2,221
  Audited Sample Count: 32

✓✓✓ VERIFICATION SUCCESSFUL ✓✓✓
All ballot selections match the expected random selections!
```

#### Specify County Explicitly
```bash
python3 verify_any_contest.py \
  --contest "Alamosa County Commissioner - District 1" \
  --county Alamosa
```

---

## Common Workflows

### Workflow 1: Explore a County's Audit

```bash
# Step 1: See what contests were audited
python3 verify_any_contest.py --list-contests-for-county Bent

# Step 2: Pick a contest and verify it
python3 verify_any_contest.py --contest "Bent County Commissioner-District 1"
```

### Workflow 2: Explore a Statewide Contest

```bash
# Step 1: See which counties audited it
python3 verify_any_contest.py --list-counties-for-contest "Amendment 79 (CONSTITUTIONAL)"

# Step 2: Note that statewide contests are more complex
#         (requires CVR data for proper verification)
```

### Workflow 3: Find All County Commissioner Races

```bash
# List all contests (pipe to grep)
python3 verify_any_contest.py --list-contests | grep "Commissioner"
```

### Workflow 4: Compare Audit Effort Across Counties

```bash
# See how many ballots each county audited for a statewide contest
python3 verify_any_contest.py --list-counties-for-contest "Presidential Electors"

# The output shows ballot counts per county
```

---

## Understanding the Output

### Listing Options Use `contestComparison.csv`

The listing features scan the actual audited ballots from `contestComparison.csv`, which means:

- **Counts show actual audited ballots**, not theoretical sample sizes
- **Only includes contests with audited ballots** (some contests may have had 0 ballots audited)
- **Reflects the most recent round** (Round 3 if available, else Round 2, else Round 1)

### Why Some Contests Can't Be Verified

The verification works best when:
- `ballot_card_count` = `contest_ballot_card_count`
- Contest appears on all ballot cards in the county
- Example: Bent County Commissioner-District 1 (all 2,221 cards)

More complex scenarios (district-level, multi-county) require:
- CVR (Cast Vote Record) data
- More sophisticated ballot mapping
- This is future work

---

## Tips

### Get Help
```bash
python3 verify_any_contest.py --help
```

### Pipe Output for Analysis
```bash
# Count contests per county
python3 verify_any_contest.py --list-contests-for-county Adams | grep "ballots)" | wc -l

# Find contests with many audited ballots
python3 verify_any_contest.py --list-counties-for-contest "Amendment 79 (CONSTITUTIONAL)" | \
  grep "ballots)" | sort -k2 -nr | head -10
```

### Check Exit Codes
```bash
python3 verify_random_selection.py
echo $?  # 0 = success, 1 = failure
```

---

## Summary of Tools

| Tool | Purpose | Key Options |
|------|---------|-------------|
| `verify_random_selection.py` | Verify Bent County | (no options, just run it) |
| `verify_random_selection_verbose.py` | Show SHA-256 details | (no options, just run it) |
| `verify_any_contest.py` | General verification + discovery | `--list-counties`<br>`--list-contests`<br>`--list-contests-for-county`<br>`--list-counties-for-contest` |

---

## Important Notes

### Manifest Timing Assumption

All verifications assume that:
1. **Ballot manifests were uploaded first** (and locked in)
2. **Random seed was generated after** manifests were committed
3. **Ballot selection used seed + manifests**

This sequence is critical for audit integrity. If the seed were generated first, someone could potentially manipulate the manifest to favor specific ballot selections.

### What Is Verified

✓ Mathematical correctness of random selection  
✓ Proper SHA-256 implementation  
✓ Correct manifest mapping  
✓ Sequential multi-round selection  

### What Is NOT Verified

✗ Physical ballot retrieval  
✗ Audit board interpretations  
✗ Original CVR accuracy  
✗ Manifest timing (assumed correct)  

---

## Further Reading

- `VERIFICATION_SUMMARY.md` - Overview of verification results
- `VERIFICATION_TOOLS_README.md` - Complete tool documentation
- `RANDOM_SELECTION_VERIFICATION_RESULTS.md` - Detailed results for Bent County
- `VERIFICATION_INDEX.md` - Quick start guide

