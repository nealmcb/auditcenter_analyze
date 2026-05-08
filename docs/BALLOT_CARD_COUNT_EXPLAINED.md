# ballot_card_count vs contest_ballot_card_count Explained

> **Historical note:** This document contains an earlier interpretation that random
> selection used `contest_ballot_card_count`. That part was later superseded by
> `docs/DOMAIN_SIZE_CONFIRMED.md`, which ties the selection domain to manifest
> totals from the upstream source code. The field definitions and ballot-card
> caveats below are still useful, but treat `DOMAIN_SIZE_CONFIRMED.md` as the
> authoritative statement on domain size.

## The Two Fields

Every contest in `contest.csv` has two important fields:

### `ballot_card_count`
**Definition:** Total number of ballot CARDS across all counties where the contest could theoretically appear.

**For single-county contests:** The county's total ballot cards
**For multi-county contests:** Sum of all relevant counties' ballot cards

### `contest_ballot_card_count`  
**Definition:** Number of ballot cards that ACTUALLY have this specific contest on them.

**Always ≤ ballot_card_count**

## Examples

### Example 1: Bent County Commissioner-District 1
```
ballot_card_count:         2,221
contest_ballot_card_count: 2,221
```

**Interpretation:**
- All 2,221 ballot cards in Bent County have this contest
- Contest appears on every ballot card in the county
- No CVR mapping needed

### Example 2: Boulder State Representative - District 10
```
ballot_card_count:         396,121  (all Boulder cards)
contest_ballot_card_count:  44,675  (cards with State Rep 10)
```

**Interpretation:**
- Boulder County has 396,121 total ballot cards
- Only 44,675 of them have State Rep District 10
- The contest appears on 11.3% of Boulder's cards
- Ratio: 44,675 / 396,121 = 11.3%

**Why different?**
- State Rep District 10 only covers part of Boulder County
- Voters in other parts of Boulder don't get this contest
- They get a different State Rep district contest

### Example 3: Presidential Electors
```
ballot_card_count:         4,746,866  (all statewide cards)
contest_ballot_card_count: 3,239,722  (cards with PE)
```

**Interpretation:**
- Colorado has 4,746,866 total ballot cards
- Only 3,239,722 have Presidential Electors
- Ratio: 3,239,722 / 4,746,866 = 68.3%

**Why different?**
- Not all ballot cards have Presidential Electors
- Could be property-holder ballots (tax elections only)
- Could be special ballot types
- 31.7% of ballot cards don't have this contest

## What This Means for Random Selection

### The Critical Question

**Which field determines the random selection domain?**

Based on the code (`BallotSelection.java`):
- The random selection generates numbers in range [1, `contest_ballot_card_count`]
- NOT [1, `ballot_card_count`]

**This means:**
- For Bent Commissioner: domain [1, 2,221] ✓ matches manifest
- For Boulder State Rep 10: domain [1, 44,675] ✗ doesn't match manifest (396,121)
- For Presidential Electors: domain [1, 3,239,722] ✗ doesn't match any single manifest

## The CVR Mapping Problem

When `contest_ballot_card_count < ballot_card_count`:

### The Challenge
Random selection picks indices in [1, contest_ballot_card_count], but these are **contest-specific indices**, not manifest positions.

**Example for Boulder State Rep 10:**
- Random selection: #5,234 (out of 44,675)
- Question: Which of the 396,121 manifest positions is this?
- Answer: Unknown without CVR data!

### What CVR Provides
The CVR (Cast Vote Record) contains records for each ballot card scanned, and each record shows which contests appear on that card.

**CVR would tell us:**
```
Contest Index #1 = CVR record #42 = Manifest position #42
Contest Index #2 = CVR record #87 = Manifest position #87
Contest Index #3 = CVR record #103 = Manifest position #103
... etc for all 44,675 cards with State Rep 10
```

## Single-County vs Multi-County

### User's Correction
> "If the district is entirely in the county, there is no problem since the random selection remains county-wide."

**My original understanding:** Use full county manifest (396,121)
**Actual implementation:** Uses contest-specific domain (44,675)

**The problem remains:** Even for single-county districts, if `contest_ballot_card_count < ballot_card_count`, we need CVR to map contest indices to manifest positions.

### Multi-County is Different
For multi-county contests, we have TWO problems:
1. Contest-specific domain (need CVR mapping)
2. Multi-county ordering (need to combine manifests)

## Implications for Boulder State Rep 10

```
Contest: State Representative - District 10
Counties: 1 (Boulder only)
ballot_card_count: 396,121
contest_ballot_card_count: 44,675
```

**Current verification:**
- Domain used: 396,121 (full county)
- Matches: 9 of 11
- Doesn't match: 2 (101-362-181, 106-63-127)

**Should use:**
- Domain: 44,675 (contest-specific)
- But can't map to imprinted_ids without CVR

**Result:** Even single-county district contests need CVR data when they don't appear on all cards.

## When Verification Works Without CVR

**Only when:** `ballot_card_count = contest_ballot_card_count`

This means:
- Contest appears on ALL ballot cards in its scope
- Contest index = Manifest position (1:1 mapping)
- No CVR needed

**Examples:**
- ✓ Bent County Commissioner-District 1 (2,221 = 2,221)
- ✗ Boulder State Rep 10 (44,675 ≠ 396,121)
- ✗ Presidential Electors (3,239,722 ≠ 4,746,866)

## The Full Picture

### Ballot Cards vs Ballots

**Important:** A ballot card is a physical piece of paper, not a full ballot.
- Multi-card ballots have multiple ballot cards
- Each card can have different contests
- Some cards might have only tax measures (property-holder ballots)

### Why contest_ballot_card_count < ballot_card_count

1. **Geographic districts:** Contest covers only part of the jurisdiction
   - State Rep districts within a county
   - City contests within a county
   - School district contests

2. **Special ballots:** Some ballot cards don't have certain contests
   - Property-holder ballots (tax elections only)
   - Special district elections
   - Jurisdictional boundaries

3. **Ballot card variations:** Different cards for different voter types
   - In-person vs mail-in might differ
   - Different precincts might have different contests

## Summary

| Field | Meaning | Use Case |
|-------|---------|----------|
| `ballot_card_count` | Total cards in scope | Theoretical maximum |
| `contest_ballot_card_count` | Cards with this contest | **Random selection domain** |

**Key insight:** Random selection uses `contest_ballot_card_count`, which requires CVR mapping when it differs from `ballot_card_count`.

**User's point about balloon cards with no targeted contests:** Valid! Ballot cards can have only opportunistic contests. This is normal and expected.

**The remaining mystery:** Why 9/11 match instead of 0/11 or 11/11? This suggests our approach is partially correct but something is still wrong.

---

**Date:** October 23, 2025  
**Status:** Explained but verification approach needs revision
