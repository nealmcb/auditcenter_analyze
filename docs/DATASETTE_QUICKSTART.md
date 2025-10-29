# Datasette Quick Start

## Step 1: Run the analysis and create database

```bash
./src/auditcenter_analyze/calculate_opportunistic_risk.py
```

This will:
- Analyze all 662 contests
- Save results to `output/colorado_rla.db` (SQLite)
- Print summary to console

Options:
- `--db custom.db` - use different database file
- `--no-db` - skip database save (console only)
- `--round 2` - analyze different round

## Step 2: Launch Datasette

All dependencies are managed by `uv`. Just run:

```bash
./src/auditcenter_analyze/view_database.py
```

This will:
- Launch datasette on http://localhost:8001
- Load the database with pre-configured metadata
- Provide a web interface to explore the audit results

**Options:**
- `--db custom.db` - specify different database file
- `--metadata metadata.json` - specify different metadata file
- `--port 8001` - change port (default: 8001)
- `--host 0.0.0.0` - make accessible from other machines

**To stop:** Press Ctrl+C

## What You Can Do

### Browse Tables
- **contest_risk_analysis**: All contests with risk calculations
- **county_sampling_details**: Per-county breakdown for each contest
- **audit_metadata**: Configuration (risk limit, gamma, etc.)

### Filter & Sort
- Click column headers to sort
- Use facets (right sidebar) to filter by:
  - Audit reason (targeted vs opportunistic)
  - Pass/fail status
  - County
- Click "..." menu to add custom filters

### Run SQL Queries

Example: Find failed targeted contests
```sql
SELECT 
    contest_name,
    risk_value,
    sample_size,
    discrepancies
FROM contest_risk_analysis
WHERE audit_reason IN ('state_wide_contest', 'county_wide_contest')
  AND achieved_risk_limit = 0
ORDER BY risk_value DESC
```

Example: Show counties with high sampling rates
```sql
SELECT 
    county_name,
    COUNT(*) as contests,
    AVG(sampling_rate) as avg_rate,
    MAX(sampling_rate) as max_rate
FROM county_sampling_details
GROUP BY county_name
ORDER BY avg_rate DESC
LIMIT 20
```

### Export Data
- Click "CSV" or "JSON" link on any table/query
- Download full dataset or filtered results

## Daily Workflow

When new audit data arrives:

```bash
# Re-run analysis
./src/auditcenter_analyze/calculate_opportunistic_risk.py --round 3

# Restart datasette (auto-reloads database)
./src/auditcenter_analyze/view_database.py
```

The database is completely replaced each run, so you always see latest data.

