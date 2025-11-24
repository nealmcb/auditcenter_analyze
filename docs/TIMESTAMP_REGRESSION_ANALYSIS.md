# Timestamp Regression Analysis: Contest Count vs Delta Time

## Summary

Performed regression analysis to understand the relationship between the number of contests on a ballot and the time between consecutive ballot examinations.

## Methodology

1. **Filtered counties**: Only counties with mean delta times between 100-200 seconds (excluding multi-board counties)
2. **Removed outliers**: Used IQR method (1.5 × IQR) to remove outliers from delta times per county
3. **Regression**: Simple linear regression: `delta_time = intercept + slope × contest_count`

## Key Findings

### Overall Regression (All Counties Combined)
- **Equation**: `delta_time = 116.69 + 0.6164 × contest_count`
- **R² = 0.0053** (0.53% of variance explained - essentially no relationship)
- **Slope**: 0.62 seconds per additional contest
- **Interpretation**: Contest count explains almost nothing about examination time

### County-by-County Results

**Strongest relationships** (R² > 0.15):
- **Fremont**: R² = 0.2842, slope = 3.63 sec/contest
- **Weld**: R² = 0.2781, slope = 6.25 sec/contest

**Weakest relationships** (R² < 0.01):
- Most counties show essentially no relationship (R² ≈ 0)
- **El Paso**, **Yuma**: R² = 0.0000

## Important Observations

### 1. R² and Outliers

**Question**: Does R² incorporate outliers automatically?

**Answer**: Yes and No.
- R² is calculated from ALL data points in the regression
- **However**, in our analysis, we remove outliers using IQR method BEFORE calculating regression
- So R² reflects the relationship for "normal" data points only
- If outliers were included, they could:
  - Strongly influence the slope (if they have unusual contest counts)
  - Increase residual sum of squares (if they have unusual delta times)
  - Reduce R² if they don't fit the linear relationship

### 2. "Insufficient Data" Counties

**Result**: Several counties are marked as "insufficient data" in the plots.

The "insufficient data" condition occurs when:
- County has < 4 data points before outlier removal, OR
- County has < 2 data points after outlier removal, OR
- **County has < 2 distinct contest values after outlier removal** (most common issue)

**Counties with insufficient data** (only 1 distinct contest value):
- **Archuleta**: 29 points, all have 34 contests
- **Cheyenne**: 15 points, all have 33 contests  
- **Crowley**: 9 points, all have 31 contests
- **Otero**: 24 points, all have 33 contests
- **Prowers**: 10 points, all have 32 contests
- **Rio Grande**: 24 points, all have 34 contests
- **Sedgwick**: 59 points, all have 35 contests

**Why this is insufficient**:
- Regression requires variation in the independent variable (contest count)
- With only 1 distinct contest value, you cannot determine a slope
- The regression equation `delta_time = intercept + slope × contest_count` cannot be solved when all contest counts are identical
- This is different from having too few data points - you could have 100 points but if they all have the same contest count, regression is still impossible

### 3. Counties with Few Distinct Contest Values

**Issue**: Many counties show a "single hotspot" - most ballots have the same or very few contest counts.

**Examples**:
- **Archuleta, Cheyenne, Crowley, Otero, Prowers, Rio Grande, Sedgwick**: Only **1 distinct contest value** after outlier removal (all ballots have same number of contests)
- **Kiowa, Kit Carson, Logan, Ouray, Park, Pitkin, Saguache, Summit, Yuma**: Only **2 distinct contest values** after filtering

**Why this is a problem**:
- With only 1-2 distinct contest counts, there's almost no variation in the independent variable
- The slope cannot be meaningfully determined
- Any regression line is essentially fitting noise/variance in delta time, not a true relationship
- R² values are unreliable - they reflect variance in delta time, not a relationship with contest count

**What's happening with Baca and Fremont**:

**Baca County**:
- 83 data points before filtering, 70 after
- Contest counts range from 1 to 62 contests
- **But**: 35 ballots have 34 contests (50% of filtered data)
- Only 10 distinct contest values after filtering
- The regression is trying to fit a line through points clustered at just a few contest values
- Outliers at extreme contest counts (1, 62) may be driving the slope
- **Despite having multiple contest values, the data is heavily imbalanced** - most ballots have the same contest count

**Fremont County**:
- 20 data points before, 19 after (1 outlier removed)
- Contest counts: 2, 31, 33, 34 contests
- **Mostly clustered**: 7 ballots at 31 contests, 5 at 33, 7 at 34
- Only 4 distinct contest values, but they are relatively evenly distributed (not a single hotspot)
- The regression has some variation (2 to 34 contests), but most data is clustered around 31-34
- **The slope is strongly influenced by the single ballot at 2 contests** - this one point has high leverage
- **Balance ratio**: ~0.5 (7:7:5:1 distribution) - moderate balance, but small sample size makes it fragile

**Root Cause**:
- Many counties have homogeneous ballot styles
- Most ballots in a county have the same number of contests
- The few ballots with different contest counts are either:
  - Outliers that get removed
  - Special ballot styles (e.g., provisional, military)
  - Different precincts with different contests

**Implications**:
- The weak R² values (most < 0.05) are not surprising - there's simply not enough variation in contest counts to detect a relationship
- Counties with multiple distinct contest values (like Fremont with 2, 31, 33, 34) show stronger relationships
- The overall weak relationship suggests that **contest count is not a major factor** in examination time within counties
- Other factors (board pacing, breaks, ballot complexity, discrepancies) likely dominate

## R² and Outlier Contest Counts (Not Delta Time Outliers)

**Question**: When most ballots have 30 contests and one has 40, how does R² compare to balanced data (50 with 30, 50 with 40)?

**Answer**: R² is **highly sensitive to the balance** of contest count values:

**Simulation Results** (true relationship: delta = 100 + 5 × contests, same noise):
- **99:1 ratio** (99 at 30, 1 at 40): Mean R² = 0.07, highly variable (std dev = 0.05)
- **50:50 ratio** (balanced): Mean R² = 0.61, stable (std dev = 0.05)

**Why imbalanced data reduces R²**:
- With imbalanced data, the regression line is pulled toward the larger group (the 30-contest ballots)
- The single/few points in the minority group (40-contest ballots) have **high leverage**
- Small variations in those minority points cause large changes in the slope
- This increases residual variance and reduces R²
- R² becomes **unreliable** - it varies wildly from sample to sample

**Real-world example - Fremont County**:
- 1 ballot with 2 contests (5%)
- 7 ballots with 31 contests (37%)
- 5 ballots with 33 contests (26%)  
- 7 ballots with 34 contests (37%)
- The slope is strongly determined by the single ballot at 2 contests
- Even though R² = 0.2842, this is **not robust** - one point is driving the entire relationship

**Bottom line**: 
- Yes, R² **automatically** incorporates the effect of imbalanced contest counts
- Imbalanced data → Lower, more variable R²
- Balanced data → Higher, more stable R²
- When you see a "single hotspot" with a few outliers, R² is unreliable even if it looks reasonable

## Recommendations

1. **For counties with few distinct contest values**: The regression results should be interpreted with extreme caution:
   - Only 1 distinct value → Regression impossible (marked as "insufficient data")
   - Only 2 distinct values → R² depends heavily on balance ratio
   - Heavily imbalanced (e.g., 99:1) → R² is unreliable

2. **For overall analysis**: The weak relationship (R² = 0.0053) suggests contest count explains almost nothing about examination time. Focus on other factors:
   - Audit board pacing differences
   - Breaks and interruptions
   - Ballot complexity beyond contest count
   - Presence of discrepancies
   - County-level organizational differences

3. **Visual inspection**: The grid plots show most counties have data clustered at 1-2 contest values, making regression slopes unreliable even if R² seems reasonable.

