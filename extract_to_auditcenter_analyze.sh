#!/bin/bash
# Extract audit analysis tools to new repo with git history
set -e

echo "=========================================="
echo "Extracting audit analysis to new repo"
echo "=========================================="
echo

# Verify we're in the right place
if [ ! -f "calculate_opportunistic_risk.py" ]; then
    echo "ERROR: Run this from colorado-rla-2018 directory"
    exit 1
fi

# Verify we're on verify branch
BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "verify" ]; then
    echo "ERROR: Must be on verify branch (currently on: $BRANCH)"
    echo "Run: git checkout verify"
    exit 1
fi

TARGET="../auditcenter_analyze"

if [ -d "$TARGET" ]; then
    echo "ERROR: $TARGET already exists"
    echo "Remove it first or choose different location"
    exit 1
fi

echo "Step 1: Creating new repository..."
mkdir -p "$TARGET"
cd "$TARGET"
git init
echo "✓ New repo created"
echo

echo "Step 2: Copying files from verify branch..."
cd - > /dev/null

# List of files to copy (with history)
FILES=(
    calculate_opportunistic_risk.py
    investigate_boulder_failures.py
    verify_any_contest.py
    verify_audit_comprehensive.py
    verify_county_selections.py
    verify_random_selection.py
    verify_random_selection_verbose.py
    verify_risk_calculations.py
    datasette-metadata.json
    setup_datasette_env.sh
    launch_datasette.sh
    .gitignore
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
)

# Export commits as patches
PATCH_DIR="/tmp/verify-patches-$$"
mkdir -p "$PATCH_DIR"
echo "Exporting commits from 5220e437..verify..."
git format-patch -o "$PATCH_DIR" 5220e437^..verify
echo "✓ Exported $(ls $PATCH_DIR/*.patch | wc -l) commits"
echo

# Apply patches to new repo
cd "$TARGET"
echo "Applying patches to new repository..."
for patch in "$PATCH_DIR"/*.patch; do
    # Try to apply patch
    if git am --reject < "$patch" 2>/dev/null; then
        echo "  ✓ Applied: $(basename $patch)"
    else
        # If it fails, it might be because it touches files we don't want
        # Just skip for now - we'll get the final state in next step
        git am --abort 2>/dev/null || true
        echo "  ⊙ Skipped: $(basename $patch) (may touch non-extracted files)"
    fi
done
echo

# Clean up patches
\rm -rf "$PATCH_DIR"

# Make sure we have current versions of all files
echo "Step 3: Ensuring all files are current..."
cd - > /dev/null
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" "$TARGET/"
        echo "  ✓ $file"
    fi
done
echo

cd "$TARGET"

# Stage any new/updated files
git add -A
if git diff --staged --quiet; then
    echo "No changes to commit (patches applied cleanly)"
else
    git commit -m "Sync final state of files from verify branch"
fi
echo

echo "Step 4: Reorganizing directory structure..."

# Create directory structure
mkdir -p analysis datasette docs output

# Move Python scripts
for file in *.py; do
    [ -f "$file" ] && git mv "$file" analysis/
done

# Move datasette files
git mv datasette-metadata.json datasette/metadata.json
git mv setup_datasette_env.sh datasette/
git mv launch_datasette.sh datasette/

# Move docs
for file in *.md; do
    [ -f "$file" ] && git mv "$file" docs/
done

# Commit reorganization
git commit -m "Reorganize: create analysis/, datasette/, docs/, output/ structure"
echo "✓ Directory structure created"
echo

echo "Step 5: Creating symlinks..."
ln -s /srv/voting/audit/corla/scrapy/mirror data
ln -s ../colorado-rla-2018/server/eclipse-project/script/rla_export/rla_export rlacalc

git add data rlacalc
git commit -m "Add symlinks: data -> audit mirror, rlacalc -> colorado-rla module"
echo "✓ Symlinks created"
echo

echo "Step 6: Updating paths in scripts..."

# Update calculate_opportunistic_risk.py
sed -i 's|Path(__file__).parent / "server" / "eclipse-project" / "script" / "rla_export" / "rla_export"|Path(__file__).parent.parent / "rlacalc"|' analysis/calculate_opportunistic_risk.py
sed -i 's|Path(__file__).parent / "neal_ignore" / "auditcenter-2024g"|Path(__file__).parent.parent / "data" / "2024" / "general"|' analysis/calculate_opportunistic_risk.py

# Update other verify scripts with same data path change
for script in analysis/verify_*.py analysis/investigate_boulder_failures.py; do
    if grep -q 'neal_ignore.*auditcenter-2024g' "$script" 2>/dev/null; then
        sed -i 's|"neal_ignore" / "auditcenter-2024g"|"data" / "2024" / "general"|' "$script"
        sed -i 's|Path(__file__).parent / "server"|Path(__file__).parent.parent / "rlacalc"|' "$script" 2>/dev/null || true
    fi
done

# Update datasette launch script
sed -i 's|datasette colorado_rla.db|datasette ../output/colorado_rla.db|' datasette/launch_datasette.sh
sed -i 's|--metadata datasette-metadata.json|--metadata metadata.json|' datasette/launch_datasette.sh

git add -A
git commit -m "Update paths: use symlinked data/ and rlacalc/ directories"
echo "✓ Paths updated"
echo

echo "Step 7: Creating README..."
cat > README.md << 'EOFREADME'
# Audit Center Analysis Tools

Independent verification and analysis tools for Colorado RLA audit center data.

Extracted from [ColoradoRLA](https://github.com/FreeAndFair/ColoradoRLA) verify branch.

## What This Does

1. **Calculate Risk** for targeted and opportunistic contests
2. **Verify Random Selection** using SHA-256 PRNG
3. **Explore Results** via Datasette web interface

## Quick Start

### Run Analysis
```bash
python3 analysis/calculate_opportunistic_risk.py
```

Analyzes 700+ contests and generates `output/colorado_rla.db`

### Explore with Datasette
```bash
cd datasette
bash setup_datasette_env.sh  # one-time
bash launch_datasette.sh
```

Open: http://localhost:8001

### Verify Random Selection
```bash
python3 analysis/verify_random_selection.py
```

## Data Access

Analysis tools read from `data/` which is symlinked to:
```
/srv/voting/audit/corla/scrapy/mirror/
```

Current example dataset: `data/2024/general/`

## Directory Structure

```
auditcenter_analyze/
├── analysis/          Python analysis scripts
├── datasette/         Web exploration tools
├── docs/              Analysis documentation
├── output/            Generated databases
├── data/              -> /srv/voting/audit/corla/scrapy/mirror/
└── rlacalc/           -> ../colorado-rla-2018/.../rlacalc/
```

## Documentation

See `docs/` for detailed documentation:
- `DATASETTE_QUICKSTART.md` - How to explore data
- `VERIFICATION_TOOLS_README.md` - Random selection verification
- `OPPORTUNISTIC_RISK_FINAL.md` - Risk calculation methodology

## Dependencies

- Python 3.10+
- rlacalc module (from colorado-rla-2018, accessed via symlink)
- Standard library only (no pip packages needed for analysis)
- Datasette (optional, for exploration - uses isolated venv)

## History

Development history from ColoradoRLA verify branch commits:
- First commit: 5220e437 (2024-10-23) "First cut at python verification code and doc"
- Extracted: $(date +%Y-%m-%d)

See `git log` for full development history.
EOFREADME

git add README.md
git commit -m "Add README with usage instructions"
echo "✓ README created"
echo

echo "Step 8: Updating .gitignore..."
cat >> .gitignore << 'EOFIGNORE'

# Audit analysis specific
datasette-env/
output/*.db
*.db
__pycache__/
*.pyc
*.pyo
EOFIGNORE

git add .gitignore
git commit -m "Update .gitignore for audit analysis repo"
echo "✓ .gitignore updated"
echo

echo "=========================================="
echo "✓ Extraction complete!"
echo "=========================================="
echo
echo "New repository: $TARGET"
echo "Commits: $(git log --oneline | wc -l)"
echo
echo "Next steps:"
echo "  cd $TARGET"
echo "  git log --oneline  # Review history"
echo "  python3 analysis/calculate_opportunistic_risk.py --round 3 --no-db > /tmp/new_output.txt 2>&1"
echo "  diff /tmp/baseline_output.txt /tmp/new_output.txt  # Verify output matches"
echo

