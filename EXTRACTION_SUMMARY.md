# Extraction Summary - Ready for Review

## What Will Happen

Running `./extract_to_auditcenter_analyze.sh` will:

1. **Create** `/srv/s/electionaudits/auditcenter_analyze/` with new git repo
2. **Extract** 39 files from verify branch (Python scripts + docs)
3. **Preserve** git history from commit 5220e437 onwards (13 commits)
4. **Reorganize** into clean structure (analysis/, datasette/, docs/)
5. **Update** paths to use symlinks for data and rlacalc
6. **NOT modify** colorado-rla-2018 repo at all

## Files Being Extracted (39 total)

**Python Scripts (8):**
- calculate_opportunistic_risk.py
- investigate_boulder_failures.py
- verify_*.py (6 scripts)

**Datasette (3):**
- datasette-metadata.json
- setup_datasette_env.sh  
- launch_datasette.sh

**Documentation (27):**
- All *VERIFICATION*.md, *ANALYSIS.md, *OPPORTUNISTIC*.md files
- DATASETTE_QUICKSTART.md, PACKAGE_STATUS.md
- Various analysis progress docs

**Config (1):**
- .gitignore (Python parts)

## New Repository Structure

```
/srv/s/electionaudits/auditcenter_analyze/
├── .git/                      (new repo with history)
├── README.md
├── .gitignore
│
├── analysis/
│   ├── calculate_opportunistic_risk.py
│   └── verify_*.py (7 files)
│
├── datasette/
│   ├── metadata.json
│   ├── setup_datasette_env.sh
│   └── launch_datasette.sh
│
├── docs/
│   └── *.md (27 documentation files)
│
├── output/
│   └── (generated .db files go here)
│
├── data -> /srv/voting/audit/corla/scrapy/mirror/
└── rlacalc -> ../colorado-rla-2018/server/.../rlacalc/
```

## Path Changes in Scripts

**Before:**
```python
data_dir = Path(__file__).parent / "neal_ignore" / "auditcenter-2024g"
script_dir = Path(__file__).parent / "server" / ... / "rlacalc"
```

**After:**
```python
data_dir = Path(__file__).parent.parent / "data" / "2024" / "general"
script_dir = Path(__file__).parent.parent / "rlacalc"
```

## Testing Plan

### Test 1: Output Comparison (Primary Test)
```bash
cd /srv/s/electionaudits/auditcenter_analyze
python3 analysis/calculate_opportunistic_risk.py --round 3 --no-db > /tmp/new_output.txt 2>&1

# Compare with baseline
diff /tmp/baseline_output.txt /tmp/new_output.txt
```

**Expected:** No differences (or only path differences in error messages)

### Test 2: Database Generation
```bash
python3 analysis/calculate_opportunistic_risk.py --db output/colorado_rla.db
sqlite3 output/colorado_rla.db "SELECT COUNT(*) FROM contest_risk_analysis"
```

**Expected:** 722 contests

### Test 3: Data Access
```bash
ls data/2024/general/*.csv | head -5
```

**Expected:** Shows BallotManifest.csv files, contest.csv, etc.

### Test 4: Verification Script
```bash
python3 analysis/verify_random_selection.py
```

**Expected:** All 32 ballots match for Bent County

### Test 5: Git History
```bash
git log --oneline
git log --oneline -- analysis/calculate_opportunistic_risk.py
```

**Expected:** See 13+ commits with proper history

## Baseline Output Captured

Already saved to: `/tmp/baseline_output.txt`

Key numbers to verify after extraction:
```
Targeted contests: 64
  Achieved risk limit: 61/64
  FAILED:
    Conejos County Commissioner District 3: risk=0.048408
    Routt County Commissioner - District 1: risk=0.041393
    Sedgwick County Commissioner - District 3: risk=0.030451
Opportunistic contests: 658
  Below risk limit: 223/658
```

## What Stays in colorado-rla-2018

Everything! The original repo is **not modified**:
- server/ (ColoradoRLA Java code)
- client/ (ColoradoRLA TypeScript code)
- All original documentation
- All other branches intact
- verify branch stays as-is

## Safety

- Script checks you're on verify branch
- Script checks target doesn't already exist
- Uses `git am` to preserve commit history
- All operations in new directory
- Colorado-rla-2018 untouched

## After Extraction

You'll have two repos:

**colorado-rla-2018/** - Original ColoradoRLA system
**auditcenter_analyze/** - Standalone audit analysis tools

Both can evolve independently. The analysis repo uses colorado-rla's rlacalc module via symlink.

## Ready to Run?

Review this plan, then:

```bash
cd /srv/s/electionaudits/colorado-rla-2018
git checkout verify  # if not already
./extract_to_auditcenter_analyze.sh
```

The script will show progress and final verification steps.

