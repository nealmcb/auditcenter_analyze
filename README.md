# Audit Center Analysis Tools

Independent verification and analysis tools for Colorado RLA audit center data.

Extracted from [ColoradoRLA](https://github.com/FreeAndFair/ColoradoRLA) verify branch and modernized.

## What This Does

1. **Import CSV Data** from auditcenter exports into normalized SQLite database
2. **Calculate Risk** for targeted and opportunistic contests using Kaplan-Markov risk-limiting audit statistics
3. **Verify Random Selection** using SHA-256 PRNG
4. **Explore Results** via Datasette web interface with all auditcenter tables
5. **Test-Driven Development** with comprehensive pytest test suite

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

Analysis tools read from `data/` which is symlinked to:
```
/srv/voting/audit/corla/scrapy/mirror/
```

Current example dataset: `data/2024/general/`

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

See `docs/` for detailed documentation:
- `AGENTS.md` - Development standards and project approach
- `HANDOFF_DOCUMENT.md` - Project history and status
- `BASELINE_OPPORTUNISTIC_COMPARISON.md` - Comparison with historical baseline
- `DATASETTE_QUICKSTART.md` - How to explore data
- `VERIFICATION_TOOLS_README.md` - Random selection verification
- `COUNTY_KEY_EXPLANATION.md` - Data normalization and county key concepts
- `UNDERVOTE_QUERYING_CHALLENGES.md` - Undervote discrepancy analysis

## Dependencies

- Python 3.12+
- `rlacalc` - Risk-Limiting Audit calculations (Kaplan-Markov)
- `datasette` - Web interface for exploring data
- Development tools: `pytest`, `black`, `ruff`, `mypy`

## History

Development history from ColoradoRLA verify branch commits:
- First commit: 5220e437 (2024-10-23) "First cut at python verification code and doc"
- Extracted: $(date +%Y-%m-%d)

See `git log` for full development history.
