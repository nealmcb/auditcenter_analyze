# Cryptographic Verification Report
**Contest:** Crowley County Commissioner - District 3
**Contest ID:** 198

This report demonstrates the complete cryptographic chain from random seed
to selected ballots, allowing independent verification of the audit process.

---

## 1. Contest Overview

- **Contest Name:** Crowley County Commissioner - District 3
- **Audit Reason:** county_wide_contest
- **Number of Winners:** "Terry McMillian"

### Counties Involved
- **Crowley County:** 1,729 ballot cards

### Vote Totals

| Candidate | Votes |
|-----------|-------|
| Terry McMillian | 1,317 |
| Richard Medina | 350 |

**Winner(s):** "Terry McMillian"

---

## 2. RLA Input Parameters

- **Risk Limit:** 0.03 (3%)
- **Gamma:** 1.03905
- **Minimum Margin:** 967 votes
- **Contest Ballot Card Count:** 1,729
- **Diluted Margin:** 0.559283
  - Calculated as: min_margin / contest_ballot_card_count = 967 / 1729
- **Sample Size:** 15
- **Discrepancies Found:** 0
- **Risk Value:** 0.009070
- **Achieved Risk Limit:** ✓ Yes

---

## 3. Sample Size Calculation

The sample size is determined using the Kaplan-Markov risk calculation
method, which depends on:
1. The diluted margin (difference between winner and runner-up, divided by total ballots)
2. The risk limit (0.03 = 3%)
3. The gamma parameter (1.03905)

For this contest, the required sample size is **15 ballots**.

---

## 4. Ballot Manifest

- **County:** Crowley
- **Total Ballot Cards:** 1,729
- **Manifest File:** `CrowleyBallotManifest.csv`

The manifest file contains batch-level data with:
- Tabulator ID
- Batch number
- Number of ballot cards in each batch

From this, we create an ordered list of all ballot positions,
each identified by `tabulator-batch-position` (imprinted_id).

---

## 5. Random Seed

**Seed Value:** `53417960661093690826`

This seed was generated publicly and committed before the audit began.
It ensures that ballot selection cannot be manipulated, as the seed
must have been created after the ballot manifests were finalized.

---

## 6. Cryptographic Selection Process

Each ballot is selected using the following deterministic process:

### Algorithm
```
for i in 1 to sample_size:
    hash_input = seed + "," + i
    hash_output = SHA-256(hash_input)
    int_output = interpret_as_big_integer(hash_output)
    selection = (int_output mod domain_size) + 1
```

### Detailed Calculations

Showing detailed calculations for all 15 selections:

#### Selection #1

- **Hash Input:** `53417960661093690826,1`
- **SHA-256 Hash:** `72c8598cb8032587f3b69c896ff86b2697b9958347358981025b8e16da486c90`
- **As Integer:** `51917652200644199007266985192332680021051019672388504459370329584306271841424`
- **Modulo Operation:** `51917652200644199007266985192332680021051019672388504459370329584306271841424 mod 1729 = 842`
- **Add 1 (1-indexed):** `843`
- **Manifest Position:** Position 843 in ordered ballot list
- **Ballot Details:** Batch 34, Position 18 in batch
- **Imprinted ID:** `102-34-18`

#### Selection #2

- **Hash Input:** `53417960661093690826,2`
- **SHA-256 Hash:** `5e06d7556b5aa78b4d6e365036f27981aa71a97fff6c2c5e52ad1a2236cab04f`
- **As Integer:** `42529495027581445786233121179061764457657834714777780741929549479927398182991`
- **Modulo Operation:** `42529495027581445786233121179061764457657834714777780741929549479927398182991 mod 1729 = 1118`
- **Add 1 (1-indexed):** `1119`
- **Manifest Position:** Position 1119 in ordered ballot list
- **Ballot Details:** Batch 45, Position 19 in batch
- **Imprinted ID:** `102-45-19`

#### Selection #3

- **Hash Input:** `53417960661093690826,3`
- **SHA-256 Hash:** `34f8d4e7f2ba078e480942023cb70487649330ccaf7f1bf79a6c2c047971b273`
- **As Integer:** `23959915621930193907857595934714758452456058735389030016460250805330928317043`
- **Modulo Operation:** `23959915621930193907857595934714758452456058735389030016460250805330928317043 mod 1729 = 1155`
- **Add 1 (1-indexed):** `1156`
- **Manifest Position:** Position 1156 in ordered ballot list
- **Ballot Details:** Batch 47, Position 6 in batch
- **Imprinted ID:** `102-47-6`

#### Selection #4

- **Hash Input:** `53417960661093690826,4`
- **SHA-256 Hash:** `9bda2be9fb408ee09f07b0114e844658d91de6d669de60907006217cb5b4295a`
- **As Integer:** `70493967273748406298953807195118579249919819816035099514933319026183641508186`
- **Modulo Operation:** `70493967273748406298953807195118579249919819816035099514933319026183641508186 mod 1729 = 1157`
- **Add 1 (1-indexed):** `1158`
- **Manifest Position:** Position 1158 in ordered ballot list
- **Ballot Details:** Batch 47, Position 8 in batch
- **Imprinted ID:** `102-47-8`

#### Selection #5

- **Hash Input:** `53417960661093690826,5`
- **SHA-256 Hash:** `50a4b6ce6d75587f75b543404dd141f96667bfef8a7a1f18816b579cc6bf4009`
- **As Integer:** `36476052488396408426359091414331091242984692489503382443122146415746173845513`
- **Modulo Operation:** `36476052488396408426359091414331091242984692489503382443122146415746173845513 mod 1729 = 1366`
- **Add 1 (1-indexed):** `1367`
- **Manifest Position:** Position 1367 in ordered ballot list
- **Ballot Details:** Batch 55, Position 18 in batch
- **Imprinted ID:** `102-55-18`

#### Selection #6

- **Hash Input:** `53417960661093690826,6`
- **SHA-256 Hash:** `9e02e590af058142f98684852b8ca7ed05f279fcb2e6cf81d2203d4db483e003`
- **As Integer:** `71470548170863296878552766487804634634919390095485517571126824029703834427395`
- **Modulo Operation:** `71470548170863296878552766487804634634919390095485517571126824029703834427395 mod 1729 = 1200`
- **Add 1 (1-indexed):** `1201`
- **Manifest Position:** Position 1201 in ordered ballot list
- **Ballot Details:** Batch 49, Position 1 in batch
- **Imprinted ID:** `102-49-1`

#### Selection #7

- **Hash Input:** `53417960661093690826,7`
- **SHA-256 Hash:** `0ad8f5f7bea250d46dfb48f0a7e21d80478b14fa2990618afb80af0bcaf44cae`
- **As Integer:** `4906465058862693613342408135695853007079145991153039104856954828471959571630`
- **Modulo Operation:** `4906465058862693613342408135695853007079145991153039104856954828471959571630 mod 1729 = 97`
- **Add 1 (1-indexed):** `98`
- **Manifest Position:** Position 98 in ordered ballot list
- **Ballot Details:** Batch 4, Position 23 in batch
- **Imprinted ID:** `102-4-23`

#### Selection #8

- **Hash Input:** `53417960661093690826,8`
- **SHA-256 Hash:** `d1a71ff3def9e9f6dfbf7b45d945ad46518e12d0e94c9ed6237e30e58ecf5117`
- **As Integer:** `94828669342606593353478604893985346643910646089500209522570044018299862208791`
- **Modulo Operation:** `94828669342606593353478604893985346643910646089500209522570044018299862208791 mod 1729 = 847`
- **Add 1 (1-indexed):** `848`
- **Manifest Position:** Position 848 in ordered ballot list
- **Ballot Details:** Batch 34, Position 23 in batch
- **Imprinted ID:** `102-34-23`

#### Selection #9

- **Hash Input:** `53417960661093690826,9`
- **SHA-256 Hash:** `aa510ed43faba2be3cfe4f82346a9b13ee5ce88fecfd5b2e7b5ea6279f8eba29`
- **As Integer:** `77036401218065164871042652719692274569505532152051096383738961675795299220009`
- **Modulo Operation:** `77036401218065164871042652719692274569505532152051096383738961675795299220009 mod 1729 = 1116`
- **Add 1 (1-indexed):** `1117`
- **Manifest Position:** Position 1117 in ordered ballot list
- **Ballot Details:** Batch 45, Position 17 in batch
- **Imprinted ID:** `102-45-17`

#### Selection #10

- **Hash Input:** `53417960661093690826,10`
- **SHA-256 Hash:** `5850e39579e8f35412024f5684f9f0a7303ceccef1c5050ab57fb67198ae8edc`
- **As Integer:** `39946449166801105356527197201342496126933478385374143449034627203814277418716`
- **Modulo Operation:** `39946449166801105356527197201342496126933478385374143449034627203814277418716 mod 1729 = 936`
- **Add 1 (1-indexed):** `937`
- **Manifest Position:** Position 937 in ordered ballot list
- **Ballot Details:** Batch 38, Position 12 in batch
- **Imprinted ID:** `102-38-12`

#### Selection #11

- **Hash Input:** `53417960661093690826,11`
- **SHA-256 Hash:** `29ff36a2d7e230eb34365da6a0268e2fe5145ed7c2e8424f4a87e0c63a0cc696`
- **As Integer:** `18995749877981689021851918673602854860619857132466649055190424606852164404886`
- **Modulo Operation:** `18995749877981689021851918673602854860619857132466649055190424606852164404886 mod 1729 = 68`
- **Add 1 (1-indexed):** `69`
- **Manifest Position:** Position 69 in ordered ballot list
- **Ballot Details:** Batch 3, Position 19 in batch
- **Imprinted ID:** `102-3-19`

#### Selection #12

- **Hash Input:** `53417960661093690826,12`
- **SHA-256 Hash:** `bce5eafa914f6f4312e220133e631c0ea03d8293779dbf783598515c8d036009`
- **As Integer:** `85441045275423106603345357768439944680073106984913852269464983126831582633993`
- **Modulo Operation:** `85441045275423106603345357768439944680073106984913852269464983126831582633993 mod 1729 = 1587`
- **Add 1 (1-indexed):** `1588`
- **Manifest Position:** Position 1588 in ordered ballot list
- **Ballot Details:** Batch 64, Position 14 in batch
- **Imprinted ID:** `102-64-14`

#### Selection #13

- **Hash Input:** `53417960661093690826,13`
- **SHA-256 Hash:** `beb81036837bbb6eb6de8ec9fb717febcd26a8fcbec57b9d59c4ef606f265aba`
- **As Integer:** `86264652988365315848828094725660621777128116309468387787274881261258802617018`
- **Modulo Operation:** `86264652988365315848828094725660621777128116309468387787274881261258802617018 mod 1729 = 39`
- **Add 1 (1-indexed):** `40`
- **Manifest Position:** Position 40 in ordered ballot list
- **Ballot Details:** Batch 2, Position 15 in batch
- **Imprinted ID:** `102-2-15`

#### Selection #14

- **Hash Input:** `53417960661093690826,14`
- **SHA-256 Hash:** `8600713eb5b1c6de3cb710cf9c147cbf5a95abca973b480c28a733566e7dc248`
- **As Integer:** `60610703298146234676481477484571168528058311476352478882502737562899213828680`
- **Modulo Operation:** `60610703298146234676481477484571168528058311476352478882502737562899213828680 mod 1729 = 1441`
- **Add 1 (1-indexed):** `1442`
- **Manifest Position:** Position 1442 in ordered ballot list
- **Ballot Details:** Batch 58, Position 18 in batch
- **Imprinted ID:** `102-58-18`

#### Selection #15

- **Hash Input:** `53417960661093690826,15`
- **SHA-256 Hash:** `b30efbd18dfbdff3b5af30e28aee457ca9a52e1de3f504d6763efd7903eb2065`
- **As Integer:** `80990473743226127178646501551878500047250375443457310345053829663988552245349`
- **Modulo Operation:** `80990473743226127178646501551878500047250375443457310345053829663988552245349 mod 1729 = 282`
- **Add 1 (1-indexed):** `283`
- **Manifest Position:** Position 283 in ordered ballot list
- **Ballot Details:** Batch 12, Position 8 in batch
- **Imprinted ID:** `102-12-8`

---

## 7. Actual Audit Selections

The following ballots were actually examined during the audit:

| # | Imprinted ID |
|---|--------------|
| 1 | `102-12-8` |
| 2 | `102-2-15` |
| 3 | `102-3-19` |
| 4 | `102-34-18` |
| 5 | `102-34-23` |
| 6 | `102-38-12` |
| 7 | `102-4-23` |
| 8 | `102-45-17` |
| 9 | `102-45-19` |
| 10 | `102-47-6` |
| 11 | `102-47-8` |
| 12 | `102-49-1` |
| 13 | `102-55-18` |
| 14 | `102-58-18` |
| 15 | `102-64-14` |

---

## 8. Verification Results

✓✓✓ **VERIFICATION SUCCESSFUL** ✓✓✓

All ballot selections match the expected random selections!
Verified 15 ballots using seed `53417960661093690826`

This confirms:
- The random selection process was followed correctly
- The cryptographic chain is intact
- Anyone can reproduce these results independently

---

## 9. Reproducibility Instructions

To independently verify this audit:

1. **Retrieve the seed:**
   ```sql
   SELECT seed FROM audit_random_seed WHERE round = 3;
   ```

2. **Get contest parameters:**
   ```sql
   SELECT contest_ballot_card_count, min_margin
   FROM contests WHERE contest_id = ?;
   ```

3. **Load the ballot manifest:**
   - File: `CrowleyBallotManifest.csv`
   - Create ordered list of all ballot positions

4. **Generate random selections:**
   - For each i from 1 to sample_size:
   - Compute: `SHA-256(seed + "," + i)`
   - Convert to integer and take modulo contest_ballot_card_count
   - Add 1 for 1-indexing
   - Map to ballot position in manifest

5. **Compare with audit results:**
   ```sql
   SELECT DISTINCT imprinted_id
   FROM ballot_comparisons
   WHERE contest_id = 198
   ORDER BY imprinted_id;
   ```

All steps are deterministic and reproducible by anyone with access to:
- The ballot manifest (public record)
- The random seed (publicly committed)
- This verification algorithm (open source)
