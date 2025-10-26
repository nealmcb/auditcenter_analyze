# Package Installation Status

## Current Global Packages (in ~/.local/)

**Total packages:** 446

**Key packages causing conflicts:**
```
numpy:     2.2.6      (NumPy 2.x - breaking changes)
scipy:     1.11.1     (compiled for NumPy 1.x - INCOMPATIBLE)
pandas:    2.3.1
datasette: 0.64.6     (tries to load scipy via pint→dask→scipy)
```

**Other important packages using numpy:**
- Jupyter (ecosystem)
- matplotlib 3.7.1
- Various data science tools

## The Problem

**datasette** → **pint** → **dask** → **scipy 1.11.1** → expects **numpy 1.x**

But you have **numpy 2.2.6** installed globally.

## Why NOT to Downgrade Numpy Globally

Downgrading numpy in `~/.local/` would affect:
- ✗ All 446 packages in your user Python environment
- ✗ Jupyter notebooks you might be running
- ✗ Other data analysis scripts
- ✗ Any tools depending on NumPy 2.x features

**Risk:** Breaking other projects to fix datasette.

## Recommended Solution

**Virtual Environment Isolation**

Location: `./datasette-env/`
- Independent Python environment
- Own copy of packages (numpy 1.x, datasette, etc.)
- Does NOT affect global `~/.local/` packages
- Can be deleted without consequences

## Package Locations After Setup

**Global packages (unchanged):**
```
~/.local/lib/python3.10/site-packages/
  ├── numpy 2.2.6 ← stays at version 2.x
  ├── scipy 1.11.1
  ├── pandas 2.3.1
  ├── jupyter
  └── ... 442 other packages
```

**Datasette environment (isolated):**
```
./datasette-env/lib/python3.10/site-packages/
  ├── numpy 1.26.x ← downgraded ONLY here
  ├── datasette
  ├── datasette-vega
  └── ... datasette dependencies
```

## Commands

**Setup (one-time):**
```bash
bash setup_datasette_env.sh
```

**Use datasette:**
```bash
bash launch_datasette.sh
# or manually:
source datasette-env/bin/activate
datasette colorado_rla.db --metadata datasette-metadata.json
deactivate
```

**Your analysis script (uses global packages):**
```bash
python3 calculate_opportunistic_risk.py
# Uses numpy 2.2.6 from ~/.local/
```

## Cleanup

If you want to remove datasette setup:
```bash
\rm -rf datasette-env/
```

This won't affect your global packages.

