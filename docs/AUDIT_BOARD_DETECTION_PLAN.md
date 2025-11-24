# Audit Board Detection and Statistics Plan

## Background

Visual analysis of sequence vs timestamp plots reveals that audit boards produce distinctive patterns:
- Each audit board appears as a set of points forming lines sloping up and to the right
- Multiple parallel lines indicate multiple audit boards working simultaneously
- Negative deltas (sequence going backwards in time) typically indicate:
  1. A new audit board starting (more common)
  2. Out-of-order data entry (less common)
  3. Multiple audit boards with overlapping sequence ranges

## Approach 1: Delta-Based Audit Board Detection

### Overview
Detect audit board transitions by identifying negative deltas in sequence vs timestamp progression. Each negative delta indicates a new audit board starting work.

### Algorithm

1. **Preprocessing**
   - Load sequence vs timestamp data for all counties
   - **Sort by sequence number** (not timestamp) to get audit board progression order
   - Calculate delta_time between consecutive timestamps
   - Calculate delta_sequence = current_sequence - previous_sequence

2. **Audit Board Segmentation**
   - Initialize: `current_board = 1`, `board_assignments = []`
   - For each ballot in sequence order:
     - If `delta_sequence < 0`:
       - **New audit board detected**: `current_board += 1`
       - Mark this as the start of a new board's work
     - Assign ballot to `current_board`
   - Note: Since sorted by sequence, delta_time can be negative when boards alternate in time (expected)

3. **Statistics Collection - "Normal" Case Only**
   - **Key insight**: Collect statistics only for consecutive sequence numbers
   - For statistics, filter to pairs where `delta_sequence == 1` (consecutive ballots)
   - This represents the "normal" audit board workflow, excluding:
     - Gaps in sequence (missing ballots)
     - Out-of-order entries
     - Transitions between boards
   
   For each county and each detected audit board, using only consecutive pairs:
   - **Count**: Number of consecutive pairs (delta_sequence == 1)
   - **Total ballots**: Number of ballots processed by this board
   - **Time span**: First timestamp to last timestamp
   - **Duration**: Total time (last - first timestamp)
   - **Mean delta_time**: Average time between consecutive ballots (delta_sequence == 1)
   - **StdDev delta_time**: Standard deviation of delta_time (for consecutive pairs)
   - **Median delta_time**: Median time between consecutive ballots
   - **Min/Max delta_time**: Fastest and slowest consecutive intervals
   - **Sequence range**: Min and max sequence numbers
   - **Sequence span**: Total sequence numbers covered
   - **Consecutive rate**: % of ballots that are consecutive (pairs / (total - 1))

4. **Outlier Handling**
   - For statistics on consecutive pairs, filter out extreme outliers
   - Use IQR method: remove deltas > Q3 + 1.5*IQR (only for delta_sequence == 1)
   - Note: Negative delta_time values are **expected** when sorted by sequence (boards alternate)

5. **Exclusions**
   - **Skip counties**: Dolores, Hinsdale, Otero (known complex cases)
   - **Skip Baca** (user noted it's "even more complicated")
   - Process all other counties

6. **Edge Cases**
   - **Single ballot boards**: If a board only processes 1 ballot, mark as suspect
   - **Overlapping sequences**: If sequences overlap between boards, keep separate
   - **Isolated out-of-order entries**: These will create very short "boards" - flag for review

### Advantages
- Simple to implement
- Directly uses the negative delta signal (sorted by sequence)
- Works well when audit boards have distinct sequence ranges
- Statistics focus on "normal" consecutive workflow (delta_sequence == 1)
- Handles parallel boards correctly (they alternate in time, but maintain sequence order)

### Disadvantages
- Fails when sequences overlap significantly between boards
- Sensitive to out-of-order data entry (but stats only use consecutive pairs)
- May over-segment if there are many isolated out-of-order entries
- Statistics exclude gaps and transitions (may under-represent total work time)

---

## Approach 2: Linear Segment Detection (Alternative)

### Overview
Group points into linear segments using clustering or line-fitting techniques. Audit boards produce roughly linear trajectories in sequence-time space.

### Algorithm

1. **Preprocessing**
   - Load sequence vs timestamp data
   - Convert timestamps to numeric (seconds since start)
   - Normalize both axes for clustering

2. **Segment Detection Methods**

   **Option A: Hough Transform / Line Detection**
   - Apply Hough line transform to detect dominant lines
   - Group points near each detected line
   - Requires tuning: max line gap, min line length, angle resolution

   **Option B: RANSAC Line Fitting**
   - Iteratively fit lines using RANSAC
   - For each iteration:
     - Randomly sample points
     - Fit line through sample
     - Count inliers (points near line within threshold)
     - Keep best fit
   - Remove inliers, repeat for next segment
   - Stop when too few points remain or max segments reached

   **Option C: DBSCAN Clustering with Linear Constraints**
   - Use modified DBSCAN that prefers linear clusters
   - Cluster based on:
     - Temporal proximity (timestamps)
     - Sequence proximity (weighted less)
     - Linear alignment (preference for points forming lines)

   **Option D: Piecewise Linear Regression**
   - Use segmentation algorithms (e.g., segmented least squares)
   - Find optimal breakpoints that minimize total error
   - Each segment represents an audit board's work

3. **Inlier/Outlier Classification**
   - For each detected segment:
     - Calculate distance from each point to the fitted line
     - Mark points with distance > threshold as outliers
     - Threshold could be: median distance + 2*MAD (Median Absolute Deviation)

4. **Segment Validation**
   - **Minimum length**: Segments must have at least N ballots (e.g., 5)
   - **Minimum duration**: Segments must span at least M minutes (e.g., 10)
   - **Temporal continuity**: Check for large gaps within segment (may indicate missed breakpoint)

5. **Statistics Collection**
   For each detected segment (audit board):
   - Same statistics as Approach 1
   - **Slope**: Sequence/time slope (ballots per minute)
   - **Line fit quality**: R² or residual sum of squares
   - **Outlier count**: How many points were excluded

6. **Special Handling**
   - **Isolated points**: Points not near any line → mark as "unassigned" or "out-of-order"
   - **Parallel segments**: Multiple segments with similar slopes → likely multiple boards
   - **Overlapping segments**: If segments overlap in time but not sequence, may be correct

### Advantages
- More robust to out-of-order entries
- Can handle overlapping sequence ranges better
- Provides visual validation (lines can be plotted)
- May work better for complex cases (Dolores, Hinsdale, Otero, Baca)

### Disadvantages
- More complex to implement
- Requires parameter tuning (thresholds, min segment size)
- May miss subtle board transitions
- Computational cost higher

---

## Recommended Hybrid Approach

### Phase 1: Apply Approach 1 to "clean" counties
- Process all counties except: Dolores, Hinsdale, Otero, Baca
- Use delta-based detection
- Generate per-board statistics

### Phase 2: Apply Approach 2 to complex counties
- Process excluded counties (Dolores, Hinsdale, Otero, Baca) using line detection
- Compare results with Approach 1 if re-processed

### Phase 3: Validation and Refinement
- Visual inspection: Plot detected board assignments with different colors
- Flag counties with:
  - Many single-ballot "boards"
  - Suspicious statistics (very short durations, extreme deltas)
  - Low board assignment rate (< 80% of ballots assigned)
- Manual review of flagged counties

### Phase 4: Statistics Output

**Per County Summary:**
- Total ballots processed
- Number of audit boards detected
- Mean ballots per board
- Mean duration per board
- Overall statistics (aggregated across all boards)

**Per Board CSV:**
- `county`, `board_number`, `total_ballots`, `consecutive_pairs`, `consecutive_rate`, `duration_seconds`, `mean_delta_seconds`, `stddev_delta_seconds`, `median_delta_seconds`, `min_delta_seconds`, `max_delta_seconds`, `sequence_min`, `sequence_max`, `timestamp_start`, `timestamp_end`, `slope_ballots_per_minute`

**Visualization:**
- Plot sequence vs timestamp with board assignments colored differently
- One plot per county (or grid)
- Highlight unassigned/outlier points in gray

---

## Implementation Details

### Data Structures

```python
BallotRecord = {
    county: str
    imprinted_id: str
    sequence: int  # Sorted by this
    timestamp: datetime
    board_number: int | None  # Assigned by detection
    delta_time: float | None  # Seconds since previous (can be negative when boards alternate)
    delta_sequence: int | None  # Current sequence - previous sequence
    is_consecutive: bool  # True if delta_sequence == 1
    is_outlier: bool  # For consecutive pairs only
}

BoardStatistics = {
    county: str
    board_number: int
    total_ballots: int  # All ballots assigned to this board
    consecutive_pairs: int  # Number of consecutive pairs (delta_sequence == 1)
    consecutive_rate: float  # consecutive_pairs / (total_ballots - 1)
    timestamp_start: datetime
    timestamp_end: datetime
    duration_seconds: float  # Total time span
    sequence_min: int
    sequence_max: int
    consecutive_deltas: List[float]  # Only for delta_sequence == 1 (after outlier removal)
    mean_delta: float  # Mean of consecutive_deltas
    stddev_delta: float  # StdDev of consecutive_deltas
    median_delta: float  # Median of consecutive_deltas
    min_delta: float  # Min of consecutive_deltas
    max_delta: float  # Max of consecutive_deltas
    slope: float  # Ballots per minute (estimated from consecutive pairs)
}
```

### Key Parameters

**Approach 1:**
- Sort by: **sequence** (not timestamp)
- Statistics filter: Only include pairs where `delta_sequence == 1` (consecutive)
- `max_negative_delta_sequence`: Threshold for new board detection (default: -1)
- `max_delta_time_outlier`: For consecutive pairs, drop deltas > this (default: 7200 seconds = 2 hours)
- `min_board_ballots`: Flag boards with fewer than this (default: 3)
- Note: Negative delta_time values are **expected** (boards work in parallel)

**Approach 2:**
- `line_distance_threshold`: Max distance from line to be inlier (default: adapt to data)
- `min_segment_length`: Minimum points per segment (default: 5)
- `min_segment_duration`: Minimum time span per segment (default: 600 seconds = 10 minutes)
- `max_segments`: Maximum number of segments to find (default: 10)

---

## Questions to Address

1. **How to handle single isolated ballots?**
   - Option: Assign to nearest board (temporal or sequence)
   - Option: Mark as "unassigned" for manual review
   - Option: Create a special "catch-all" board

2. **What if negative delta_sequence happens within what looks like a single board's work?**
   - Option: Allow small negative deltas (-1, -2) as noise
   - Option: Use sliding window to detect trends

3. **How to validate board assignments?**
   - Visual inspection of colored plots
   - Check for reasonable statistics (not too fast/slow)
   - Compare with known audit board assignments if available

4. **Should we handle re-entering boards?**
   - If same sequence range is processed twice (gap in time), one board or two?
   - Likely two separate sessions of same board

---

## Next Steps

1. Implement Approach 1 for clean counties
2. Generate visualizations with board assignments
3. Test on subset of counties
4. Implement Approach 2 for comparison
5. Decide on hybrid strategy
6. Generate final statistics output

---

## Approach Comparison Summary

### When to Use Approach 1 (Delta-Based)

**Best for:**
- Counties where audit boards work on distinct sequence ranges
- Counties with minimal out-of-order data entry
- Simple cases where negative deltas clearly indicate board transitions
- Faster processing needed

**Expected Success Rate:**
- Most counties (55-58 out of 63)
- Especially large counties with clear work division

**Limitations:**
- Fails with overlapping sequence ranges
- Breaks down with many isolated out-of-order entries
- May create spurious "boards" from data entry errors

### When to Use Approach 2 (Linear Segmentation)

**Best for:**
- Complex counties (Dolores, Hinsdale, Otero, Baca)
- Counties with overlapping sequence ranges
- Cases with many out-of-order entries
- When visual validation is important

**Expected Success Rate:**
- Can handle complex cases that Approach 1 fails on
- May produce more accurate board assignments overall
- Better at filtering noise

**Limitations:**
- More computationally expensive
- Requires parameter tuning
- May under-segment if boards have similar pacing
- More complex to implement and debug

### Hybrid Recommendation

**Phase 1: Quick Analysis**
- Use Approach 1 for all counties except exclusions
- Identify counties with suspicious results:
  - Many single-ballot boards
  - Very high board counts (> 10)
  - Very low assignment rate (< 80% of ballots)

**Phase 2: Refinement**
- Re-process excluded counties with Approach 2
- Re-process flagged counties with Approach 2
- Compare results where both approaches were used

**Phase 3: Manual Review**
- Visual inspection of colored plots
- Review counties with unusual statistics
- Validate against known audit structure (if available)

### Expected Outputs

1. **Per County Summary CSV**
   - County name
   - Total ballots
   - Number of boards detected
   - Assignment rate (% of ballots assigned)
   - Mean ballots per board
   - Mean duration per board

2. **Per Board Statistics CSV**
   - County, board number, statistics (see above)

3. **Visualizations**
   - Grid plot: Each county with board assignments color-coded
   - Combined plot: All counties with board colors (may be too cluttered)

4. **Flag Report**
   - Counties with suspicious results
   - Unassigned ballots
   - Outliers and anomalies

---

## Implementation Priority

1. **Start with Approach 1** (simpler, faster)
2. **Validate visually** on subset of counties
3. **Identify problem counties** from Approach 1 results
4. **Implement Approach 2** for problem counties
5. **Compare and refine** both approaches
6. **Generate final statistics** using best method per county

