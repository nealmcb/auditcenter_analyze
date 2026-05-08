# Audit Center Analysis Tools

Independent verification and analysis tools for Colorado RLA audit center data.

## What This Does

1. **Import CSV Data** from auditcenter exports into normalized SQLite database
2. **Calculate Risk** for targeted and opportunistic contests using Kaplan-Markov risk-limiting audit statistics
3. **Verify Random Selection** using SHA-256 PRNG
4. **Explore Results** via Datasette web interface with all auditcenter tables
5. **Test-Driven Development** with comprehensive pytest test suite

Originally extracted from [ColoradoRLA](https://github.com/FreeAndFair/ColoradoRLA) rla_report / verify branch and modernized.

## Key Findings

Analysis of the archived auditcenter data (2019–2025) has revealed systematic
inconsistencies between what the RLA system drew for audit and what was actually
compared by audit boards.

- **[`docs/SELECTION_FLAWS.md`](docs/SELECTION_FLAWS.md)** — the original
  discovery: for Pueblo County Commissioner District 2 (2024 general), half the
  drawn ballots (189 of 378) have no comparison record, and 4 comparison records
  reference ballots that were never drawn. Documents the two underlying SQL bugs
  in `cdos-rla/colorado-rla`.

- **[`docs/SELECTION_FLAWS_SURVEY.md`](docs/SELECTION_FLAWS_SURVEY.md)** — a
  systematic scan across all 22 audited rounds (2019–2025): every round has at
  least one inconsistency; 869 contest-rounds have ballots that were drawn but
  apparently not audited (Bug 1); 9,148 contest-rounds have comparison records
  for ballots that were never drawn for that contest (Bug 2); Garfield County's
  contest name collision (Bug 3) confirmed in 2024. Notable cases include City
  of Aurora Mayor 2019 (1,030/1,787 draws unaudited) and Town of Castle Rock
  2021 (933/1,158).

- **[`docs/copilot-sun_apr_26_2026_auditcenter_inconsistency_in_colorado_rla.md`](docs/copilot-sun_apr_26_2026_auditcenter_inconsistency_in_colorado_rla.md)**
  — annotated Copilot conversation tracing the bugs to specific Java methods and
  SQL queries in the ColoradoRLA source, and assessing whether they affected
  actual audit calculations (the SQL bugs are export-only artifacts; whether
  round-2 draws were physically worked is an open question requiring `cvr_audit_info`
  table access).

## Quick Start

### Prerequisites
- Python 3.12+
- `uv` package manager

### Setup
```bash
# Install dependencies
make install-dev

# Run all checks
make check
```

### Import CSV Data
```bash
# Scan available CSV files (dry-run)
python3 src/auditcenter_analyze/import_csvs.py scan

# Import all data into SQLite database
python3 src/auditcenter_analyze/import_csvs.py import-all

# Import specific rounds
python3 src/auditcenter_analyze/import_csvs.py import-all --rounds 1,2,3
```

### Run Analysis
```bash
# Process all contests
./src/auditcenter_analyze/calculate_opportunistic_risk.py

# Process only opportunistic contests
./src/auditcenter_analyze/calculate_opportunistic_risk.py --opportunistic-only

# Show detailed work for one contest
./src/auditcenter_analyze/calculate_opportunistic_risk.py --contest "Amendment 80 (CONSTITUTIONAL)" --show-work
```

### Run Tests
```bash
# Run all tests
make test

# Run with verbose output
make test-v

# Run quietly
make test-quiet
```

### Explore with Datasette
```bash
# Launch datasette web interface
python3 src/auditcenter_analyze/view_database.py

# Or use the alias
./src/auditcenter_analyze/view_database.py
```

Open: http://localhost:8001

If port 8001 is already in use, the script will provide helpful instructions.

See `docs/DATASETTE_QUICKSTART.md` for more details.

## Data Access

The archived auditcenter exports live in a separate repository:
**[github.com/nealmcb/auditcenter](https://github.com/nealmcb/auditcenter)**

That repo contains all rounds of every Colorado RLA audit from 2017 through
2025, including `contestSelection.csv`, `contestComparison.csv`, ballot
manifests, seed files, and tabulation results organized by year and election
type.

To wire it up locally:

```bash
# Option A — clone alongside this repo and symlink
git clone https://github.com/nealmcb/auditcenter.git
ln -s /path/to/auditcenter/data data

# Option B — if you already have a local mirror
ln -s /path/to/your/mirror data
```

## Directory Structure

```
auditcenter_analyze/
├── src/
│   └── auditcenter_analyze/    Main analysis scripts
│       ├── import_csvs.py      CSV import to SQLite
│       ├── csv_loaders.py      CSV loading functions
│       ├── db_schema.py        Database schema definition
│       ├── normalize.py        Data normalization utilities
│       ├── calculate_opportunistic_risk.py  Risk calculations
│       └── view_database.py    Datasette launcher
├── tests/                       Test suite
├── docs/                        Analysis documentation
├── output/                      Generated databases
├── data/                        -> /srv/voting/audit/corla/scrapy/mirror/
├── datasette/                   Web exploration tools & metadata
├── Makefile                     Development commands
└── pyproject.toml               Project configuration
```

## Development

See `AGENTS.md` for development standards:
- Python 3.12 required
- `uv` for virtual environment management
- `black` for code formatting (line length 100)
- `ruff` for linting
- `mypy --strict` for type checking
- `pytest` for testing

### Available Commands

```bash
make help        # Show all available commands
make format      # Format code with black
make lint        # Run ruff linting
make typecheck   # Run mypy type checking
make test        # Run pytest tests (verbose)
make check       # Run all checks (format, lint, typecheck, test)
make install     # Install production dependencies
make install-dev # Install development dependencies
```

## Documentation

Key reference docs in `docs/`:

| File | What it covers |
|------|----------------|
| [`SELECTION_FLAWS.md`](docs/SELECTION_FLAWS.md) | Original inconsistency discovery (Pueblo 2024) |
| [`SELECTION_FLAWS_SURVEY.md`](docs/SELECTION_FLAWS_SURVEY.md) | Systemic scan across all 2019–2025 audits |
| [`ANALYSIS_FAQ.md`](docs/ANALYSIS_FAQ.md) | Practical caveats for interpreting exports and planning the next analysis pass |
| [`HANDOFF_DOCUMENT.md`](docs/HANDOFF_DOCUMENT.md) | Project history and current status |
| [`VERIFICATION_TOOLS_README.md`](docs/VERIFICATION_TOOLS_README.md) | SHA-256 random selection verification |
| [`DATASETTE_QUICKSTART.md`](docs/DATASETTE_QUICKSTART.md) | Exploring data via the web interface |
| [`AUDIT_TERMINOLOGY.md`](docs/AUDIT_TERMINOLOGY.md) | RLA terminology reference |
| [`COUNTY_KEY_EXPLANATION.md`](docs/COUNTY_KEY_EXPLANATION.md) | County name normalization |

Most other files in `docs/` are working notes from development sessions and
can be ignored by readers interested in the findings.

## Dependencies

- Python 3.12+
- `rlacalc` - Risk-Limiting Audit calculations (Kaplan-Markov)
- `datasette` - Web interface for exploring data
- Development tools: `pytest`, `black`, `ruff`, `mypy`

## History

Development history from ColoradoRLA verify branch commits:
- First commit: 5220e437 (2024-10-23) "First cut at python verification code and doc"
- Extracted: 2024-10-23

See `git log` for full development history.
