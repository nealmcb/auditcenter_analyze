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
