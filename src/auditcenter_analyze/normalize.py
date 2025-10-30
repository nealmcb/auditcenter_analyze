"""Normalization utilities for auditcenter CSV imports.

These helpers standardize county names, contest names, and choice strings, and
handle common quoting/casing/spacing issues found in the CSV exports.
"""

from __future__ import annotations

import re
from typing import Dict


def strip_quotes_whitespace(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
        v = v[1:-1]
    return v.strip()


def normalize_choice(value: str) -> str:
    """Normalize choice strings by stripping quotes and whitespace."""
    v = strip_quotes_whitespace(value)
    v = re.sub(r"\s+", " ", v).strip()
    return v


def normalize_county_name(value: str) -> str:
    """Normalize county name to canonical form for display.

    Returns Title Case with spaces preserved (e.g., "Clear Creek").
    Used for human-readable displays and reports.

    Special handling for "Clear Creek" which appears as both "Clear Creek"
    (with spaces) and "ClearCreek" (without spaces) in the data.
    """
    v = strip_quotes_whitespace(value)
    v = re.sub(r"\s+", " ", v).strip()
    # Canonical form: Title Case with spaces preserved
    canonical = v
    # Normalized key: remove spaces, lowercase
    key = canonical.replace(" ", "").lower()
    # Special known mapping: Clear Creek vs ClearCreek
    if key == "clearcreek":
        canonical = "Clear Creek"
    return canonical


def normalized_county_key(value: str) -> str:
    """Return normalized county key for consistent dictionary lookups.

    Returns Title Case with spaces removed (e.g., "ClearCreek").
    Used as dictionary keys to join data across multiple sources:

    1. Ballot manifest files: filenames like "ClearCreekBallotManifest.csv"
    2. contestsByCounty.csv: contains "Clear Creek" (with spaces)
    3. contestComparison.csv: contains "Clear Creek" (with spaces)

    Without this normalization, lookups would fail because:
    - manifest_counts["ClearCreek"] = 6180
    - counties_from_csv = ["Clear Creek"]
    - manifest_counts[counties_from_csv[0]] → KeyError!
    """
    # Special handling for Clear Creek -> ClearCreek
    canonical = normalize_county_name(value)
    return canonical.replace(" ", "")


def normalize_contest_name(value: str) -> str:
    v = strip_quotes_whitespace(value)
    v = re.sub(r"\s+", " ", v)
    v = v.replace("’", "'")
    return v.strip()


def normalized_contest_key(value: str) -> str:
    return normalize_contest_name(value).lower()


def track_mapping(mapping_table: Dict[str, str], original: str, normalized: str) -> None:
    if original not in mapping_table:
        mapping_table[original] = normalized
