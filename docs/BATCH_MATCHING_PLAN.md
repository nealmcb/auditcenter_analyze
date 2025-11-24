# Batch Matching Implementation Plan

## Overview

Implement a robust check to determine if any two batches of ballots for a given county came from the same physical batch, based on cast vote records (CVR) from `ballot_comparisons`.

## Goal

Given two batches (identified by `(county_id, tabulator_id, batch_number)`), determine if they contain the same physical ballots with high confidence, accounting for minor scanner variation.

## Summary

This implementation will:

1. **Extract ballot data** from `ballot_comparisons` for each batch, aggregating all contest choices per ballot
2. **Compute per-ballot fingerprints** using:
   - Strict hash (SHA-256) for exact matching
   - SimHash (fuzzy hash) for near-duplicate detection
3. **Build batch signatures** including:
   - Cardinality (ballot count)
   - Style histogram
   - Strict hash multiset
   - SimHash cluster histogram
   - Contest schema (set of contests present)
4. **Compare batches** using a multi-stage approach:
   - Quick elimination (different cardinality, styles, or contests)
   - Strict hash multiset match
   - Fuzzy matching with Hamming distance
   - Sketch consistency check (SimHash clusters)
   - Longest Common Subsequence (LCS) analysis
5. **Provide CLI interface** for batch comparison and batch pair analysis

## Data Sources

1. **ballot_manifests**: Batch-level metadata (county_id, tabulator_id, batch_number, ballot_count)
2. **ballot_comparisons**: Per-ballot CVR data with:
   - `imprinted_id`: Format `tabulator-batch-position` (e.g., "102-11-7")
   - `cvr_choice`: CVR interpretation of votes (TEXT, may contain multiple selections)
   - `audit_choice`: Human interpretation of votes (TEXT, may contain multiple selections)
   - `contest_id`: Contest being compared (INTEGER)
   - `county_id`: County identifier (INTEGER)
   - `ballot_type`: Style identifier (TEXT, from ballot_type field)
   - `round`: Round number (INTEGER)
   - `timestamp`: When ballot was examined (TEXT)

**Note**: Each ballot appears multiple times in `ballot_comparisons` (once per contest). We need to aggregate by `imprinted_id` to build complete ballot signatures.

## Key Design Decisions

1. **Bitstring Representation**: 
   - Sort contests by `contest_id` for deterministic ordering
   - Serialize each contest's `cvr_choice` as UTF-8 bytes
   - Separate contests with a delimiter (e.g., `\x00`)
   - Handle empty strings (undervotes) consistently

2. **Using CVR vs Audit Choice**:
   - Use `cvr_choice` (CVR interpretation) for bitstring, as it's more consistent
   - CVR represents the machine-readable interpretation of the ballot
   - This allows matching even when human interpretation differs slightly

3. **Ballot Style Handling**:
   - Different styles may have different contest sets
   - Batch comparison should only compare ballots with same style (or normalize contest sets)

4. **Multiple Rounds**:
   - A ballot may appear in multiple rounds
   - Use latest round data (round 3 is cumulative)
   - Or aggregate across all rounds if needed

## Implementation Phases

### Phase 1: Data Extraction and Ballot Fingerprinting

#### 1.1 Extract ballot data for a batch
- Function: `extract_batch_ballots(conn, county_id, tabulator_id, batch_number) -> List[BallotRecord]`
- Query `ballot_comparisons` for all rows where `imprinted_id` matches pattern `{tabulator_id}-{batch_number}-*`
- Group by `imprinted_id` to aggregate all contests per ballot
- Store: `imprinted_id`, `ballot_type` (style_id), all contest choices

#### 1.2 Build ballot bitstring
- Function: `build_ballot_bitstring(ballot_records: List[Dict]) -> bytes`
- Collect all contests on the ballot from `ballot_comparisons`
- For each contest, serialize CVR choice(s) into canonical format
- Create deterministic bitstring:
  - Sort contests by contest_id
  - For each contest: serialize choice(s) as UTF-8, concatenate
  - Handle multi-value choices (vote-for-n contests)
  - Handle undervotes (empty string)
  - Result: deterministic byte sequence representing all votes

#### 1.3 Compute per-ballot fingerprints
- Function: `compute_ballot_fingerprints(bitstring: bytes) -> Tuple[str, int]`
- **Strict hash (H0)**: `sha256(bitstring).hexdigest()` or faster hash
- **Fuzzy hash (SimHash)**: Use SimHash algorithm (64-bit or 128-bit)
  - Convert bitstring to features (e.g., 8-byte chunks)
  - Compute SimHash signature
  - Alternative: Use MinHash if SimHash library unavailable

### Phase 2: Batch Signature Computation

#### 2.1 Create BatchSignature dataclass
```python
@dataclass
class BatchSignature:
    county_id: int
    tabulator_id: str
    batch_number: str
    cardinality: int  # Number of ballots
    style_histogram: Dict[str, int]  # Count per ballot_type
    strict_hash_multiset: Counter[str]  # H0 values
    cluster_histogram: Dict[int, int]  # SimHash bucket -> count
    contest_schema: Set[int]  # Set of contest_ids present
    ballots: List[BallotFingerprint]  # Per-ballot data for matching
```

#### 2.2 Compute batch signature
- Function: `compute_batch_signature(conn, county_id, tabulator_id, batch_number) -> BatchSignature`
- Extract all ballots in batch
- For each ballot:
  - Build bitstring
  - Compute H0 and SimHash
  - Store: `BallotFingerprint(imprinted_id, style_id, h0, simhash, bitstring)`
- Aggregate statistics:
  - Count ballots
  - Count per style_id
  - Collect all H0 values (multiset)
  - Bucket SimHash values (use high k bits for clustering)
  - Collect all contest_ids

### Phase 3: Comparison Logic

#### 3.1 Quick elimination checks
- Function: `quick_eliminate(sig_a: BatchSignature, sig_b: BatchSignature) -> Optional[str]`
- Check cardinality: if `|A| != |B|` → return "different_cardinality"
- Check style histogram: if `style_histogram_A != style_histogram_B` → return "different_styles"
- Check contest schema: if `contest_schema_A != contest_schema_B` → return "different_contests"
- Return `None` if cannot eliminate

#### 3.2 Strict set match
- Function: `strict_match(sig_a: BatchSignature, sig_b: BatchSignature) -> bool`
- Compare multiset(H0_A) == multiset(H0_B)
- If match → return `True` (virtually certain same physical batch)
- If no match → return `False` (continue to fuzzy matching)

#### 3.3 Fuzzy set match
- Function: `fuzzy_match(sig_a: BatchSignature, sig_b: BatchSignature) -> Tuple[bool, float, float]`
- Greedy bipartite matching:
  - For each ballot in A, find closest match in B by SimHash distance
  - Then verify with Hamming distance on bitstrings
  - Compute metrics:
    - Match rate: `matched_count / |A|`
    - Mean Hamming distance: average over all matches
- Heuristic threshold:
  - `match_rate >= 0.98 AND mean_hamming <= 0.3` → return `(True, match_rate, mean_hamming)`
  - Otherwise → return `(False, match_rate, mean_hamming)`

#### 3.4 Sketch consistency check
- Function: `sketch_consistency(sig_a: BatchSignature, sig_b: BatchSignature) -> float`
- Compare cluster histograms (SimHash buckets)
- Compute χ² distance or Jensen-Shannon divergence
- Return distance metric (lower = more similar)

#### 3.5 Longest Common Subsequence (LCS)
- Function: `compute_lcs(sig_a: BatchSignature, sig_b: BatchSignature) -> int`
- After fuzzy matching, extract matched ballot sequences
- Compute LCS length between sequences
- Higher LCS relative to batch size supports same-batch hypothesis

### Phase 4: Main Comparison Function

#### 4.1 Compare two batches
- Function: `compare_batches(conn, county_id, tabulator_a, batch_a, tabulator_b, batch_b) -> BatchComparisonResult`

```python
@dataclass
class BatchComparisonResult:
    county_id: int
    batch_a: Tuple[str, str]  # (tabulator, batch)
    batch_b: Tuple[str, str]
    is_same_batch: bool
    confidence: float  # 0.0 to 1.0
    match_type: str  # "strict", "fuzzy", "none"
    elimination_reason: Optional[str]
    cardinality_match: bool
    style_histogram_match: bool
    contest_schema_match: bool
    strict_hash_match: bool
    fuzzy_match_rate: Optional[float]
    mean_hamming_distance: Optional[float]
    sketch_distance: Optional[float]
    lcs_length: Optional[int]
    lcs_ratio: Optional[float]  # lcs_length / min(|A|, |B|)
```

### Phase 5: SimHash Implementation

#### 5.1 SimHash algorithm
- Function: `simhash(bitstring: bytes, hash_bits: int = 64) -> int`
- Algorithm (implement from scratch):
  1. Split bitstring into features:
     - Use sliding windows (e.g., 8-byte windows with 4-byte stride)
     - Or split by natural boundaries (e.g., per-contest segments)
  2. For each feature, compute hash using SHA-256 truncated to hash_bits
  3. Create vector of hash_bits length, initialized to zeros
  4. For each hash:
     - For each bit position i:
       - If hash bit i is 1: increment vector[i]
       - If hash bit i is 0: decrement vector[i]
  5. Convert final vector to integer:
     - For each position i: if vector[i] > 0, set bit i to 1, else 0
- Return: 64-bit integer (or larger if hash_bits > 64)

#### 5.2 Hamming distance
- Function: `hamming_distance(bitstring_a: bytes, bitstring_b: bytes) -> int`
- Count differing bits between two bitstrings
- Ensure bitstrings are same length (pad with zeros if needed)
- Use XOR and count set bits: `bin(a ^ b).count('1')` for integers

### Phase 6: Utility Functions

#### 6.1 Batch discovery
- Function: `find_batches_for_county(conn, county_id) -> List[Tuple[str, str]]`
- Query `ballot_manifests` for all batches in county
- Return list of `(tabulator_id, batch_number)` pairs

#### 6.2 Batch comparison CLI
- Command: `compare-batches` (using Typer)
- Options:
  - `--county NAME`: County name
  - `--batch-a T:B`: First batch (tabulator:batch)
  - `--batch-b T:B`: Second batch (tabulator:batch)
  - `--all-pairs`: Compare all pairs in county
- Output: JSON or formatted text

## Data Structures

### BallotFingerprint
```python
@dataclass
class BallotFingerprint:
    imprinted_id: str
    style_id: str  # ballot_type
    h0: str  # Strict hash (hex)
    simhash: int  # Fuzzy hash
    bitstring: bytes  # Original bitstring for Hamming distance
    sequence_index: Optional[int]  # Position within batch (from imprinted_id)
```

### BatchSignature
```python
@dataclass
class BatchSignature:
    county_id: int
    tabulator_id: str
    batch_number: str
    cardinality: int
    style_histogram: Dict[str, int]
    strict_hash_multiset: Counter[str]
    cluster_histogram: Dict[int, int]  # SimHash bucket (high bits) -> count
    contest_schema: Set[int]
    ballots: List[BallotFingerprint]
```

## Testing Strategy

1. **Unit tests**:
   - Bitstring generation (deterministic across runs)
   - SimHash computation
   - Hamming distance calculation
   - Quick elimination logic

2. **Integration tests**:
   - Extract batch signatures from database
   - Compare known matching batches
   - Compare known non-matching batches

3. **Edge cases**:
   - Empty batches
   - Single ballot batches
   - Batches with all undervotes
   - Batches with different contest sets

## Dependencies

- Standard library: 
  - `hashlib` (SHA-256 for hashing)
  - `collections.Counter` (for multisets)
  - `itertools` (for combinations, permutations)
  - `dataclasses` (for data structures)
  - `typing` (for type hints)
- Existing: `sqlite3`, database schema
- **No external dependencies required** - SimHash will be implemented from scratch

## File Structure

```
src/auditcenter_analyze/
  ├── batch_matching.py          # Main module
  ├── simhash.py                 # SimHash implementation
  └── fingerprint_utils.py       # Bitstring and hash utilities
```

## CLI Command

```bash
uv run auditcenter-analyze compare-batches \
  --county "Bent" \
  --batch-a "102:11" \
  --batch-b "102:12"
```

## Output Format

```json
{
  "batch_a": {"tabulator": "102", "batch": "11"},
  "batch_b": {"tabulator": "102", "batch": "12"},
  "is_same_batch": false,
  "confidence": 0.0,
  "elimination_reason": "different_cardinality",
  "metrics": {
    "cardinality_a": 50,
    "cardinality_b": 47,
    "style_histogram_match": true,
    "contest_schema_match": true
  }
}
```

## Performance Considerations

- Batch signatures can be cached/computed once per batch
- SimHash computation is O(n) where n = ballot count
- Fuzzy matching is O(n²) but can be optimized with approximate nearest neighbor
- For large batches, consider sampling approach
- Index `ballot_comparisons` on `imprinted_id` for faster lookups

## Potential Challenges

1. **Missing ballot data**: Not all ballots in a batch may appear in `ballot_comparisons` (only audited ballots)
   - Solution: Only compare ballots present in both batches

2. **Different contest sets**: Batches may have been audited for different contests
   - Solution: Compare only common contests, or use contest schema check

3. **Ballot ordering**: Physical order may differ between batches
   - Solution: Use LCS and fuzzy matching rather than strict sequence matching

4. **Scanner variation**: Minor mark detection differences
   - Solution: Fuzzy matching with Hamming distance threshold

5. **Undervotes**: Empty choices need consistent serialization
   - Solution: Use canonical empty string representation

6. **Multi-value choices**: Vote-for-n contests have multiple selections
   - Solution: Sort selections before serialization for consistency

## Implementation Order

Recommended order of implementation:

1. **Phase 1**: Core utilities
   - Bitstring building from ballot comparisons
   - Strict hash computation (SHA-256)
   - Hamming distance calculation

2. **Phase 2**: SimHash implementation
   - Implement SimHash algorithm from scratch
   - Test with known similar/different ballots

3. **Phase 3**: Batch signature computation
   - Extract batch ballots from database
   - Build batch signatures
   - Test with known batches

4. **Phase 4**: Comparison logic
   - Quick elimination checks
   - Strict hash matching
   - Fuzzy matching
   - Sketch consistency

5. **Phase 5**: LCS and main comparison function
   - Implement LCS algorithm
   - Combine all checks into main comparison function
   - Test with real batch pairs

6. **Phase 6**: CLI interface
   - Create Typer command
   - Add output formatting
   - Documentation

## Future Enhancements

1. Cache batch signatures in database table
2. Build index of batch signatures for fast lookup
3. Support for comparing batches across counties (less common)
4. Visualization of batch similarity matrix
5. Automated duplicate batch detection across entire dataset

