# Random Ballot Selection Verification Tools

## Overview

This directory contains Python tools to independently verify the random ballot selection process used in the 2024 Colorado General Election Risk-Limiting Audit (RLA).

## What Was Verified

✓ **Cryptographic random number generation** using SHA-256  
✓ **Ballot manifest mapping** from random numbers to physical ballots  
✓ **Multi-round audit progression** where additional ballots are selected sequentially  
✓ **Complete transparency** with all SHA-256 hashes verifiable  

## Verification Results

**Status: ✓ SUCCESSFUL**

The random ballot selection for **Bent County Commissioner-District 1** was independently verified:
- All 32 ballots match the expected random selections
- Seed: 53417960661093690826
- Algorithm: SHA-256 based PRNG (per Philip Stark's specification)

See [RANDOM_SELECTION_VERIFICATION_RESULTS.md](RANDOM_SELECTION_VERIFICATION_RESULTS.md) for detailed results.

## Available Tools

### 1. `verify_random_selection.py`
**Purpose:** Verify a specific contest (Bent County Commissioner-District 1)  
**Usage:**
```bash
python3 verify_random_selection.py
```

**Output:** Complete verification report with all 32 ballot selections

### 2. `verify_random_selection_verbose.py`
**Purpose:** Show cryptographic details (SHA-256 hashes) for transparency  
**Usage:**
```bash
python3 verify_random_selection_verbose.py
```

**Output:** First 5 selections with complete SHA-256 hash values shown:
```
Selection #1:
  Input:      '53417960661093690826,1'
  SHA-256:    72c8598cb8032587f3b69c896ff86b2697b9958347358981025b8e16da486c90
  As Integer: 51917652200644199007266985192332680021051019672388504459370329584306271841424
  Modulo:     51917652200644199007266985192332680021051019672388504459370329584306271841424 mod 2221 = 124
  Result:     125 (add 1 for 1-indexing)
```

### 3. `verify_any_contest.py`
**Purpose:** General-purpose verification tool for any contest  
**Usage:**
```bash
# Default (Bent County)
python3 verify_any_contest.py

# Specific contest
python3 verify_any_contest.py --contest "Contest Name" --county "County"

# List all contests
python3 verify_any_contest.py --list-contests

# List all counties with audit data
python3 verify_any_contest.py --list-counties

# List contests audited in a specific county
python3 verify_any_contest.py --list-contests-for-county Bent

# List counties that audited a specific contest
python3 verify_any_contest.py --list-counties-for-contest "Amendment 79 (CONSTITUTIONAL)"
```

**Note:** Currently works best for contests where `ballot_card_count` = `contest_ballot_card_count` (i.e., the contest appears on all ballot cards in the county).

## Algorithm

The verification implements the SHA-256 based pseudo-random number generator from:
```
server/eclipse-project/src/main/java/us/freeandfair/corla/crypto/PseudoRandomNumberGenerator.java
```

### Pseudo-code:
```python
for i in 1 to sample_size:
    hash_input = seed + "," + i
    hash_output = SHA-256(hash_input)
    int_output = interpret_as_big_integer(hash_output)
    selection = (int_output mod domain_size) + 1
```

### Key Properties:
1. **Deterministic:** Same seed always produces same sequence
2. **Unpredictable:** Cannot predict without computing SHA-256
3. **Unbiased:** Uniform distribution over domain (with negligible bias)
4. **Verifiable:** Anyone can recompute and verify

### Critical Assumption:
**The ballot manifest must be provided BEFORE the random seed is generated.**

This is essential for audit integrity. If the seed were generated first, someone could potentially manipulate the manifest to favor specific ballot selections. The proper sequence is:

1. Counties upload ballot manifests (locked in)
2. Random seed is generated publicly
3. Ballots are selected using seed + manifests
4. Audit proceeds

This verification assumes this proper sequence was followed.

## Data Sources

All data from the 2024 General Election audit center:
```
neal_ignore/auditcenter-2024g/
├── seed.csv                           # Random seed: 53417960661093690826
├── BentBallotManifest.csv            # Ballot manifest for Bent County
├── round1/contest.csv                # Contest parameters (round 1)
├── round1/contestComparison.csv      # Actual ballot selections (round 1)
├── round2/contest.csv                # Contest parameters (round 2)
├── round2/contestComparison.csv      # Actual ballot selections (round 2)
└── round3/...                        # Final round data
```

## Example: Bent County Verification

### Contest Details
- **Contest:** Bent County Commissioner-District 1
- **Winner:** Jennifer Scofield (537-vote margin)
- **Ballot Cards:** 2,221 total
- **Sample Size:** 32 ballots (across 2 rounds)
  - Round 1: 31 ballots (initial estimate)
  - Round 2: 1 additional ballot (to achieve risk limit)

### Verification Process

1. **Generate 32 random numbers** from seed using SHA-256
2. **Map to ballot manifest:** Each number [1-2221] maps to specific batch/position
3. **Compare to audit:** Verify all imprinted_ids match

### Results

All 32 ballots matched perfectly:
```
102-11-7, 102-12-24, 102-13-1, 102-15-19, 102-23-25, 102-24-24, 102-27-20,
102-3-15, 102-3-25, 102-3-4, 102-33-10, 102-33-13, 102-34-2, 102-35-13,
102-36-1, 102-44-13, 102-46-5, 102-49-12, 102-5-25, 102-55-21, 102-66-10,
102-68-13, 102-68-22, 102-68-24, 102-69-10, 102-70-12, 102-70-4, 102-72-5,
102-73-1, 102-80-6, 102-83-3, 102-84-14
```

Note: Ballot `102-44-13` was the 32nd selection (Random #1088), drawn in Round 2 when the initial 31 ballots weren't sufficient to achieve the risk limit.

## Technical Notes

### Ballot Manifest Format

Different counties use slightly different CSV formats:

**Bent County:**
```csv
County,Tabulator ID,Batch,# of Ballot Cards,Location
Bent,102,1,25,Box 1
```

**Adams County:**
```csv
County,Tabulator,Batch ,# of Ballot,Box # Location
Adams,101,1,100,101-BOX1
```

The tools handle both formats automatically.

### Imprinted ID Format

Ballots are identified by: `tabulator-batch-position`

Example: `102-11-7` means:
- Tabulator: 102
- Batch: 11
- Position: 7 (7th card in that batch)

### Domain Size

For contests that appear on all ballot cards in a county:
- Domain size = `contest_ballot_card_count`

For contests that appear only on some ballot cards:
- Domain size = number of CVR records for that contest
- Mapping is more complex (requires CVR data, not just manifest)

## Limitations

### What This Verifies
✓ Mathematical correctness of random selection  
✓ Proper implementation of SHA-256 PRNG  
✓ Correct mapping from random numbers to ballots  
✓ Sequential selection across multiple rounds  

### What This Cannot Verify
✗ Physical retrieval of correct ballots  
✗ Accuracy of audit board interpretations  
✗ Correctness of original CVR data  
✗ Completeness of exported audit data  

### Current Scope
- Works perfectly for county-wide contests where contest appears on all ballot cards
- May not work for district-level contests that cover only subset of county
- Adams County Commissioner contests require more complex CVR-based mapping

## Extending the Verification

To verify additional contests:

1. **Identify contest** in `round*/contest.csv`
2. **Check if** `ballot_card_count` = `contest_ballot_card_count`
3. **If equal:** Use `verify_any_contest.py`
4. **If not equal:** Need to implement CVR-based ballot selection mapping

## Dependencies

- Python 3.x (standard library only)
- `hashlib` (SHA-256)
- `csv` (CSV parsing)

No external packages required!

## Reproducibility

All verification can be reproduced by anyone with:
1. The audit center data (publicly available)
2. Python 3
3. These scripts

The cryptographic verification provides extremely high confidence (< 1 in 10^50 chance of accidental match).

## References

### Source Code
- `server/eclipse-project/src/main/java/us/freeandfair/corla/crypto/PseudoRandomNumberGenerator.java`
- Based on Philip B. Stark's `sha256Rand` implementation

### Documentation
- `neal_ignore/VERIFICATION_CODE_GUIDE.md` - Complete code guide
- `RANDOM_SELECTION_VERIFICATION_RESULTS.md` - Detailed results

### Academic References
- Stark, P. B. (2008). "Conservative statistical post-election audits"
- Lindeman, M., & Stark, P. B. (2012). "A gentle introduction to risk-limiting audits"

## Contact

For questions about these verification tools, please refer to:
- The Colorado RLA codebase documentation
- The 2024 audit center data
- Philip Stark's publications on risk-limiting audits

---

**Last Updated:** October 23, 2025  
**Verification Status:** ✓ SUCCESSFUL for Bent County Commissioner-District 1  
**Tools Version:** 1.0

