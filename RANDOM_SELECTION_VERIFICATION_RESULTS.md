# Random Ballot Selection Verification - 2024 General Election

## Summary

**Status: ✓ VERIFICATION SUCCESSFUL**

This document verifies that the random ballot selection in the 2024 Colorado General Election audit was correctly implemented according to the cryptographic specifications.

## Test Case

**Contest:** Bent County Commissioner-District 1  
**County:** Bent  
**Audit Type:** County-wide contest  
**Winner:** Jennifer Scofield (537-vote margin)

## Verification Parameters

- **Random Seed:** 53417960661093690826
- **Ballot Card Count:** 2,221
- **Sample Size:** 32 ballots (across 2 rounds)
- **Algorithm:** SHA-256 based pseudo-random number generator

## Results

All 32 ballots selected in the actual audit **exactly match** the ballots that should have been selected based on the random seed and the SHA-256 algorithm.

### Random Number Generation

The verification used the implementation from the Colorado RLA system:

```python
hash_input = f"{seed},{i}"
hash_output = SHA-256(hash_input)
int_output = int.from_bytes(hash_output, byteorder='big')
pick = (int_output % domain_size) + 1
```

### Sample Selections (First 10 + Last)

| Selection # | Random # | Imprinted ID | Notes |
|------------|----------|--------------|-------|
| 1 | 125 | 102-5-25 | Round 1 |
| 2 | 2053 | 102-83-3 | Round 1 |
| 3 | 369 | 102-15-19 | Round 1 |
| 4 | 810 | 102-33-10 | Round 1 |
| 5 | 299 | 102-12-24 | Round 1 |
| 6 | 1212 | 102-49-12 | Round 1 |
| 7 | 1737 | 102-70-12 | Round 1 |
| 8 | 575 | 102-23-25 | Round 1 |
| 9 | 75 | 102-3-25 | Round 1 |
| 10 | 1688 | 102-68-13 | Round 1 |
| ... | ... | ... | ... |
| **32** | **1088** | **102-44-13** | **Round 2** |

## Multi-Round Audit

This contest demonstrates how the risk-limiting audit adapts to actual findings:

1. **Initial Estimate:** 31 ballots needed (optimistic calculation)
2. **Round 1:** Audited 31 ballots, risk limit not achieved
3. **Round 2:** Audited 1 additional ballot (the 32nd random selection)
4. **Result:** Risk limit achieved with 32 ballots

The 32nd ballot (102-44-13) was correctly selected as the next sequential random number from the pseudo-random sequence, demonstrating that the system properly continues the random selection when additional ballots are needed.

## Verification Methodology

### Files Analyzed

1. **Seed:** `seed.csv` - Contains the random seed 53417960661093690826
2. **Manifest:** `BentBallotManifest.csv` - 2,221 ballot cards across 89 batches
3. **Contest Data:** `round2/contest.csv` - Final audit parameters
4. **Selections:** `round2/contestComparison.csv` - Actual audited ballots

### Algorithm

The verification script (`verify_random_selection.py`) performs the following steps:

1. **Generate Random Numbers:** Use SHA-256 PRNG with the seed to generate 32 random numbers in range [1, 2221]
2. **Map to Ballots:** Convert each random number to a ballot card using the manifest
3. **Compare:** Verify that the imprinted IDs match the actual audit selections

### Code Reference

The Python implementation follows the Java specification in:
- `server/eclipse-project/src/main/java/us/freeandfair/corla/crypto/PseudoRandomNumberGenerator.java`
- Based on Philip Stark's `sha256Rand` implementation

## All 32 Verified Ballots

Complete list of verified selections (sorted by imprinted ID):

```
102-11-7, 102-12-24, 102-13-1, 102-15-19, 102-23-25, 102-24-24, 102-27-20,
102-3-15, 102-3-25, 102-3-4, 102-33-10, 102-33-13, 102-34-2, 102-35-13,
102-36-1, 102-44-13, 102-46-5, 102-49-12, 102-5-25, 102-55-21, 102-66-10,
102-68-13, 102-68-22, 102-68-24, 102-69-10, 102-70-12, 102-70-4, 102-72-5,
102-73-1, 102-80-6, 102-83-3, 102-84-14
```

## Implications

This verification confirms that:

1. ✓ The random seed was correctly applied
2. ✓ The SHA-256 pseudo-random number generator worked as specified
3. ✓ The ballot manifest mapping was accurate
4. ✓ The sequential selection process across multiple rounds was correct
5. ✓ No ballots were added, removed, or substituted

## Reproducibility

Anyone can reproduce this verification by running:

```bash
python3 verify_random_selection.py
```

The script is self-contained and requires only:
- Python 3 with standard library (hashlib, csv)
- Access to the audit center data files

## Statistical Significance

The fact that all 32 randomly selected ballots match exactly provides strong cryptographic evidence that the selection process was:
- Deterministic (based on the seed)
- Unbiased (using SHA-256)
- Correctly implemented
- Not manipulated

The probability of this occurring by chance if the selection was incorrect would be astronomically small (< 1 in 10^50).

## Conclusion

The random ballot selection for the Bent County Commissioner-District 1 contest in the 2024 Colorado General Election audit was **correctly and properly implemented**. The audit system functioned exactly as designed, selecting ballots using cryptographic randomness based on the published seed.

This provides strong evidence of the integrity of the ballot selection process and demonstrates that the audit was conducted according to rigorous statistical standards.

---

**Verification Date:** October 23, 2025  
**Verified By:** Independent Python implementation  
**Verification Tool:** `verify_random_selection.py`

