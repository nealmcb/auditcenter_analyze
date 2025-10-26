# Sample Size Display Enhancement

**Date:** October 24, 2025  
**Enhancement:** Display total examined ballots per county to show sample size context

---

## The Problem

**Before:** Output only showed total ballot cards in manifest vs. observed with contest

```
Kiowa:
  ballot_card_count (manifest): 1,060
  Observed with contest: 48
```

**Confusing:** 48 out of 1,060 looks like only 4.5% coverage for a statewide contest!

**Reality:** Kiowa only examined **57 ballots total**, and 48 of those had the contest.

---

## The Solution

**After:** Output now shows total examined ballots AND percentage

```
Kiowa:
  ballot_card_count (manifest): 1,060
  Total examined ballots: 57        ← Sample size!
  Observed with contest: 48
  Percentage: 84.2%                  ← Much better!
```

**Clear:** 48 out of 57 examined = 84.2%, which makes sense for a statewide contest.

---

## Complete Example: Amendment 79 (CONSTITUTIONAL)

### Before Enhancement
```
Kiowa:
  ballot_card_count (manifest): 1,060
  Observed with contest: 48
```
❌ Looks wrong - only 4.5%?

### After Enhancement  
```
Kiowa:
  ballot_card_count (manifest): 1,060
  Total examined ballots: 57
  Observed with contest: 48
  Percentage: 84.2%
```
✅ Makes sense - 84% of examined ballots had this statewide contest

---

## What This Shows

### Statewide Contests
- Should appear on ~100% of examined ballots
- Example: **Amendment 79**
  - Broomfield: 56/56 = 100.0%
  - Crowley: 15/15 = 100.0%
  - Kiowa: 48/57 = 84.2% (reasonable - some multi-card effects)

### County-Wide Contests
- Should appear on high % of examined ballots in that county
- Lower % may indicate district-level contest

### Opportunistic Contests
- May appear on small % of examined ballots
- Depends on geographic distribution

---

## Key Insights

1. **ballot_card_count (manifest)** = Total ballot cards in county
   - This is the universe for random selection
   - Example: Kiowa has 1,060 total ballot cards

2. **Total examined ballots** = How many were actually audited
   - This is the sample size for the county
   - Example: Kiowa examined only 57 ballots

3. **Observed with contest** = How many examined ballots had this contest
   - This is the relevant sample for risk calculation
   - Example: 48 of Kiowa's 57 examined ballots had Amendment 79

4. **Percentage** = (Observed with contest) / (Total examined) × 100
   - Shows coverage within the sample
   - Example: 48/57 = 84.2%

---

## Implementation

### Data Loading
```python
# Track total examined ballots per county (unique imprinted_id)
examined_per_county = defaultdict(set)

with open(comparison_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        county = row['county_name'].replace(' ', '')
        iid = row['imprinted_id']
        examined_per_county[county].add(iid)

# Convert sets to counts
examined_counts = {county: len(ballots) for county, ballots in examined_per_county.items()}
```

### Display
```python
for county, data in county_data.items():
    total_examined = examined_counts.get(county, 0)
    print(f"  {county}:")
    print(f"    ballot_card_count (manifest): {data['manifest_count']:,}")
    print(f"    Total examined ballots: {total_examined}")
    print(f"    Observed with contest: {data['observed_count']}")
    if total_examined > 0:
        pct = 100.0 * data['observed_count'] / total_examined
        print(f"    Percentage: {pct:.1f}%")
```

---

## Usage

### Statewide Contest
```bash
python3 calculate_opportunistic_risk.py \
  --contest "Amendment 79 (CONSTITUTIONAL)" \
  --show-work
```

Shows sample sizes for all 64 counties.

### County-Wide Contest
```bash
python3 calculate_opportunistic_risk.py \
  --contest "Boulder County Commissioner District 2" \
  --show-work
```

Shows sample size for Boulder County.

---

## Benefits

✅ **Clarity:** Immediately see the sample size context  
✅ **Validation:** Percentages help validate statewide vs. district contests  
✅ **Understanding:** Shows relationship between manifest, sample, and contest coverage  
✅ **Debugging:** Helps identify data issues (e.g., missing ballots)  

The enhancement makes the output **much more interpretable** without additional flags or configuration!

---

*Enhanced: October 24, 2025*  
*Script: calculate_opportunistic_risk.py*  
*Performance: Still 0.5 seconds for 662 contests*

