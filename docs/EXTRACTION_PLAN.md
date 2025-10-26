# Extraction Plan: auditcenter_analyze (with Git History)

## Goal
Extract Python audit analysis work from `verify` branch into standalone repo, preserving commit history from 5220e437 onwards.

## Files to Extract (39 files from verify branch)

### Python Scripts (8 files)
```
calculate_opportunistic_risk.py
investigate_boulder_failures.py
verify_any_contest.py
verify_audit_comprehensive.py
verify_county_selections.py
verify_random_selection.py
verify_random_selection_verbose.py
verify_risk_calculations.py
```

### Datasette Setup (3 files)
```
datasette-metadata.json
setup_datasette_env.sh
launch_datasette.sh
```

### Documentation (27 files)
```
AUDIT_TERMINOLOGY.md
BALLOT_CARD_COUNT_EXPLAINED.md
BOULDER_FAILURE_ANALYSIS.md
BREAKTHROUGH_SUCCESS.md
BUGFIX_SUMMARY.md
COMPREHENSIVE_OUTPUT_SUMMARY.md
COMPREHENSIVE_VERIFICATION_STATUS.md
COUNTY_VERIFICATION_COMPLETE.md
DATASETTE_QUICKSTART.md
DISTRICT_VS_MULTICOUNTY.md
DOMAIN_SIZE_CONFIRMED.md
ENHANCED_ERROR_REPORTING.md
FINAL_VERIFICATION_STATUS.md
MULTICOUNTY_VERIFICATION_GUIDE.md
OPPORTUNISTIC_CONTESTS_UPDATE.md
OPPORTUNISTIC_RISK_FINAL.md
PACKAGE_STATUS.md
RANDOM_SELECTION_VERIFICATION_RESULTS.md
SAMPLE_SIZE_ENHANCEMENT.md
SESSION_SUMMARY.md
SINGLE_COUNTY_DISTRICT_PROGRESS.md
TERMINOLOGY_UPDATE_SUMMARY.md
UNION_OF_SELECTIONS.md
UPDATE_SUMMARY.md
VERIFICATION_EXAMPLES.md
VERIFICATION_INDEX.md
VERIFICATION_SUMMARY.md
VERIFICATION_TOOLS_README.md
```

### Git Config (1 file)
```
.gitignore (extract Python-related parts only)
```

## Commits to Preserve (13 commits)

```
5220e437 First cut at python verification code and doc
008a1dde Update .gitignore for Python
5002924d tracking improved verification
ad27a108 mostly working statewide
6fe85b26 verify_audit_comprehensive.py working statewide
63bdc504 more shots at opportunistic_risk
3da120cc bad opportunistic risk calculation
96c7a974 working risk calculation for Erie
32087321 nearly working for all contessts
d7399831 reported working, but some odd output
7c7a5265 looking good
f7079683 working?
d08cf534 Proposed datasette code
```

## Step-by-Step Execution

### Step 1: Create New Repo with Filtered History

```bash
cd /srv/s/electionaudits

# Create new repo from scratch
mkdir auditcenter_analyze
cd auditcenter_analyze
git init

# Add remote pointing to colorado-rla-2018
git remote add source ../colorado-rla-2018

# Fetch the verify branch
git fetch source verify

# Create orphan branch to start fresh
git checkout --orphan main

# Cherry-pick commits with only relevant files
# We'll use git filter-repo or manual cherry-pick
```

### Step 2: Extract Commits Using git filter-repo (Alternative A - Recommended)

```bash
cd /srv/s/electionaudits

# Clone the repo for filtering
git clone colorado-rla-2018 auditcenter_analyze
cd auditcenter_analyze

# Checkout verify branch
git checkout verify

# Install git filter-repo if not available
# pip install git-filter-repo

# Filter to keep only Python analysis files
git filter-repo \
  --path calculate_opportunistic_risk.py \
  --path investigate_boulder_failures.py \
  --path verify_any_contest.py \
  --path verify_audit_comprehensive.py \
  --path verify_county_selections.py \
  --path verify_random_selection.py \
  --path verify_random_selection_verbose.py \
  --path verify_risk_calculations.py \
  --path datasette-metadata.json \
  --path setup_datasette_env.sh \
  --path launch_datasette.sh \
  --path 'AUDIT_TERMINOLOGY.md' \
  --path 'BALLOT_CARD_COUNT_EXPLAINED.md' \
  --path 'BOULDER_FAILURE_ANALYSIS.md' \
  --path 'BREAKTHROUGH_SUCCESS.md' \
  --path 'BUGFIX_SUMMARY.md' \
  --path 'COMPREHENSIVE_OUTPUT_SUMMARY.md' \
  --path 'COMPREHENSIVE_VERIFICATION_STATUS.md' \
  --path 'COUNTY_VERIFICATION_COMPLETE.md' \
  --path 'DATASETTE_QUICKSTART.md' \
  --path 'DISTRICT_VS_MULTICOUNTY.md' \
  --path 'DOMAIN_SIZE_CONFIRMED.md' \
  --path 'ENHANCED_ERROR_REPORTING.md' \
  --path 'FINAL_VERIFICATION_STATUS.md' \
  --path 'MULTICOUNTY_VERIFICATION_GUIDE.md' \
  --path 'OPPORTUNISTIC_CONTESTS_UPDATE.md' \
  --path 'OPPORTUNISTIC_RISK_FINAL.md' \
  --path 'PACKAGE_STATUS.md' \
  --path 'RANDOM_SELECTION_VERIFICATION_RESULTS.md' \
  --path 'SAMPLE_SIZE_ENHANCEMENT.md' \
  --path 'SESSION_SUMMARY.md' \
  --path 'SINGLE_COUNTY_DISTRICT_PROGRESS.md' \
  --path 'TERMINOLOGY_UPDATE_SUMMARY.md' \
  --path 'UNION_OF_SELECTIONS.md' \
  --path 'UPDATE_SUMMARY.md' \
  --path 'VERIFICATION_EXAMPLES.md' \
  --path 'VERIFICATION_INDEX.md' \
  --path 'VERIFICATION_SUMMARY.md' \
  --path 'VERIFICATION_TOOLS_README.md' \
  --path '.gitignore' \
  --refs verify
```

### Step 3: Manual Method (Alternative B - If no git-filter-repo)

```bash
cd /srv/s/electionaudits/colorado-rla-2018

# Export patches for the commits we want
git format-patch -o /tmp/verify-patches 5220e437^..verify

# Create new repo
cd /srv/s/electionaudits
mkdir auditcenter_analyze
cd auditcenter_analyze
git init

# Apply patches one by one, keeping only relevant files
for patch in /tmp/verify-patches/*.patch; do
  git am --directory=. < "$patch" || {
    # If patch fails, skip files we don't want
    git am --abort
    # Manually apply...
  }
done
```

### Step 4: Reorganize Directory Structure

```bash
cd /srv/s/electionaudits/auditcenter_analyze

# Create subdirectories
mkdir -p analysis datasette docs output

# Move Python scripts
git mv *.py analysis/

# Move datasette files  
git mv datasette-metadata.json datasette/metadata.json
git mv setup_datasette_env.sh datasette/
git mv launch_datasette.sh datasette/

# Move documentation
git mv *.md docs/

# Create symlinks
ln -s /srv/voting/audit/corla/scrapy/mirror data
ln -s ../colorado-rla-2018/server/eclipse-project/script/rla_export/rla_export rlacalc

# Commit reorganization
git add data rlacalc
git commit -m "Reorganize: scripts to analysis/, docs to docs/, add data/rlacalc symlinks"
```

### Step 5: Update File Paths

Update imports in all Python scripts:

**analysis/calculate_opportunistic_risk.py:**
- Line 13-14: Change rlacalc path
- Line 23: Change data path

**analysis/verify_*.py:**
- Similar path updates

**datasette/launch_datasette.sh:**
- Update paths to ../output/ and metadata.json

```bash
# Commit path updates
git add -A
git commit -m "Update paths for new directory structure"
```

### Step 6: Create Additional Files

**README.md:**
```bash
cd /srv/s/electionaudits/auditcenter_analyze
cat > README.md << 'EOF'
[README content as specified earlier]
EOF
git add README.md
git commit -m "Add README"
```

**Update .gitignore:**
```bash
cat >> .gitignore << 'EOF'

# Virtual environments
datasette-env/

# Generated databases
output/*.db
*.db

# Python cache
__pycache__/
*.pyc
EOF
git add .gitignore
git commit -m "Update .gitignore for new structure"
```

### Step 7: Test Before Finalizing

**Test 1: Baseline comparison**
```bash
cd /srv/s/electionaudits/auditcenter_analyze
python3 analysis/calculate_opportunistic_risk.py --round 3 --no-db > /tmp/new_output.txt 2>&1

# Compare
diff /tmp/baseline_output.txt /tmp/new_output.txt
```

Expected: Only path differences in error messages, if any

**Test 2: Database generation**
```bash
python3 analysis/calculate_opportunistic_risk.py --db output/colorado_rla.db

sqlite3 output/colorado_rla.db "SELECT COUNT(*) FROM contest_risk_analysis"
# Expected: 722
```

**Test 3: Verification script**
```bash
python3 analysis/verify_random_selection.py
# Expected: All 32 ballots match
```

**Test 4: Data access**
```bash
ls -la data/2024/general/
# Expected: Shows audit data
```

### Step 8: Final Verification

```bash
# Check git history preserved
git log --oneline
# Should show all 13+ commits with proper messages

# Check all files present
find . -type f | grep -v '.git' | sort

# Verify original repo unchanged
cd /srv/s/electionaudits/colorado-rla-2018
git status
# Should be clean (only colorado_rla.db untracked)
```

## Baseline Output Captured

Baseline from current verify branch saved to: `/tmp/baseline_output.txt`

Summary numbers to match:
- Targeted contests: 64 (61 passed, 3 failed)
- Opportunistic contests: 658 (223 below limit)
- Skipped: 3 (Moffat County issues)

## Success Criteria

- ✓ All 13 commits from verify branch preserved
- ✓ File history maintained (git log -- filename shows evolution)
- ✓ Test output matches baseline exactly
- ✓ Database has 722 contests
- ✓ Original colorado-rla-2018 repo unchanged
- ✓ Data symlink works
- ✓ rlacalc symlink works

