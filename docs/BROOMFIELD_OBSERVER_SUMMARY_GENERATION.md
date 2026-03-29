# Broomfield County Observer Summary Generation

## Overview

This document describes the process of generating an observer summary for the Broomfield County 2025 audit. The observer summary is a text file that lists each ballot to be audited in the order that audit boards should process them, showing the expected vote choices for each contest on each ballot.

## Background

The observer summary was originally created for La Plata County (see `la_plata_observer_summary.txt`) using `generate_observer_summary.py`. For Broomfield County, we needed to adapt this approach because:

1. Broomfield had 210 county-wide targeted ballot selections (plus 1 statewide estimate)
2. There were 3 audit boards instead of 1
3. The pull list format was different (text file vs CSV)
4. The manifest column names were slightly different

## Files Involved

### Input Files
- **Pull List**: `broomfield_pull_list.txt` - Contains 211 imprinted IDs (210 county-wide + 1 statewide)
- **Manifest**: `data/2025/files/BroomfieldManifest.csv` - Maps (tabulator, batch) pairs to physical locations (boxes)
- **CVR**: `/srv/voting/audit/corla/scrapy/mirror/2025/cvrs/broomfield-Redacted_CVR_Export_20251119093616.csv` - Contains vote choices for each ballot

### Output Files
- **Observer Summary**: `broomfield_observer_summary.txt` - Generated summary for audit observers
- **Script**: `generate_broomfield_observer_summary.py` - Script to generate the summary

## Script Functionality

The `generate_broomfield_observer_summary.py` script:

1. **Loads the pull list** - Parses `broomfield_pull_list.txt` to extract all imprinted IDs
2. **Loads manifest locations** - Reads the manifest to map each ballot to its physical location
3. **Loads CVR data** - Parses the CVR file to extract vote choices for each contest on each ballot
4. **Sorts ballots** - Orders ballots by:
   - Location (natural sort order for "Box 1", "Box 2", etc.)
   - Tabulator number
   - Batch number
   - Record ID
5. **Generates output** - Creates a formatted text file showing each ballot's contests and choices

## Key Differences from La Plata Script

1. **Pull list parsing**: Broomfield's pull list is a text file with whitespace-separated IDs, not a CSV
2. **Manifest columns**: Broomfield uses "Batch" column name instead of "Batch ID"
3. **Number of selections**: Processes all 211 ballots instead of just the first 60
4. **Vote For notation**: Added logic to preserve or add "(Vote For=N)" notation in contest names

## Running the Script

```bash
cd /home/srv/s/electionaudits/auditcenter_analyze
python3 generate_broomfield_observer_summary.py
```

Expected output:
```
Loading pull list...
  Found 211 ballot selections
Loading manifest locations...
  Loaded 604 manifest entries
Loading CVR data...
  Loaded 29678 CVR records
Generating observer summary...
✓ Generated observer summary: broomfield_observer_summary.txt
  Processed 211 ballots
```

## Output Format

Each ballot entry in the summary follows this format:

```
================================================================================
Imprinted ID: 102-1-7  Location: Box 1
================================================================================

City and County of Broomfield - Mayor (2 Years) (Vote For=1)
  Kimberly Groom
City and County of Broomfield Councilmember Ward 4 (4 Years) (Vote For=1)
  Larry Hardouin
...
```

- **Imprinted ID**: The unique ballot identifier (tabulator-batch-record)
- **Location**: Physical storage location from the manifest
- **Contests**: Listed in order they appear in the CVR
- **Choices**: Indented under each contest, or "undervote" if no selection made

## Audit Board Organization

With 3 audit boards and 211 ballots, each board would process approximately 70 ballots. The ballots are already sorted by location to make physical retrieval efficient.

## Verification

The user mentioned that some imprinted IDs were observed during the actual audit. These can be used to verify that:
1. The ballots appear in the correct order
2. The vote choices match what was observed
3. The location information is accurate

(To be updated once the observed ballot IDs are provided)

## Future Improvements

1. Add explicit audit board assignments (divide the 211 ballots into 3 groups)
2. Include page breaks or section markers for each audit board
3. Add summary statistics (total ballots, ballots per location, etc.)
4. Cross-reference with observed ballot IDs for validation
