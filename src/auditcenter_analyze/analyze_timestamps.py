#!/usr/bin/env python3
"""
Analyze timestamps in round 3 contestComparison.csv.

Extract timestamp data per imprinted_id to understand audit timing patterns.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import typer

DATA_ROOT = Path(__file__).parent.parent.parent / "data" / "2024" / "general"
COMPARISON_FILE = DATA_ROOT / "round3" / "contestComparison.csv"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "timestamp_analysis"

app = typer.Typer(help=__doc__)


def parse_timestamp(ts_str: str) -> Optional[datetime]:
    """Parse timestamp string to datetime object."""
    if not ts_str or not ts_str.strip():
        return None
    try:
        # Format: 2024-11-19 09:44:18.62646
        return datetime.strptime(ts_str.strip(), "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        try:
            # Try without microseconds
            return datetime.strptime(ts_str.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


def has_discrepancy(row: Dict[str, str]) -> bool:
    """Check if a row represents a discrepancy (consensus=NO or mismatch)."""
    consensus = row.get("consensus", "").strip().upper()
    if consensus == "NO":
        return True

    cvr_choice = row.get("choice_per_voting_computer", "").strip()
    audit_choice = row.get("audit_board_selection", "").strip()

    # Remove quotes for comparison
    cvr_choice = cvr_choice.strip('"')
    audit_choice = audit_choice.strip('"')

    # Both empty is fine (undervote)
    if not cvr_choice and not audit_choice:
        return False

    # Mismatch if one is empty and the other isn't, or if they differ
    if cvr_choice != audit_choice:
        return True

    return False


@app.command()
def main(
    output_csv: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output CSV file (default: output/timestamp_analysis/ballot_timestamps.csv)",
    ),
    multi_timestamp_csv: Optional[Path] = typer.Option(
        None,
        "--multi-output",
        "-m",
        help="Output CSV for multi-timestamp ballots (default: output/timestamp_analysis/multi_timestamp_ballots.csv)",
    ),
) -> None:
    """Extract timestamp data per imprinted_id from round 3 contestComparison.csv."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if output_csv is None:
        output_csv = OUTPUT_DIR / "ballot_timestamps.csv"
    if multi_timestamp_csv is None:
        multi_timestamp_csv = OUTPUT_DIR / "multi_timestamp_ballots.csv"

    # Group data by imprinted_id
    ballot_data: Dict[str, Dict] = defaultdict(
        lambda: {
            "county": "",
            "cvr_id": "",
            "timestamps": [],
            "contests": set(),
            "discrepancies": 0,
            "ballot_type": "",
        }
    )

    print(f"Loading {COMPARISON_FILE}...")
    with COMPARISON_FILE.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        row_count = 0
        for row in reader:
            row_count += 1
            imprinted_id = row.get("imprinted_id", "").strip()
            if not imprinted_id:
                continue

            # Store county and CVR ID (use first occurrence)
            if not ballot_data[imprinted_id]["county"]:
                ballot_data[imprinted_id]["county"] = row.get("county_name", "").strip()
                ballot_data[imprinted_id]["cvr_id"] = row.get("cvr_id", "").strip()
                ballot_data[imprinted_id]["ballot_type"] = row.get("ballot_type", "").strip()

            # Collect timestamp
            timestamp_str = row.get("timestamp", "").strip()
            if timestamp_str:
                ts = parse_timestamp(timestamp_str)
                if ts:
                    ballot_data[imprinted_id]["timestamps"].append(ts)

            # Track contests
            contest = row.get("contest_name", "").strip()
            if contest:
                ballot_data[imprinted_id]["contests"].add(contest)

            # Count discrepancies
            if has_discrepancy(row):
                ballot_data[imprinted_id]["discrepancies"] += 1

    print(f"Loaded {row_count:,} rows")
    print(f"Found {len(ballot_data):,} unique imprinted_ids")

    # Process ballots
    single_timestamp_rows: List[Dict] = []
    multi_timestamp_rows: List[Dict] = []

    for imprinted_id, data in ballot_data.items():
        timestamps = sorted(set(data["timestamps"]))  # Sort and deduplicate
        contest_count = len(data["contests"])

        if len(timestamps) == 0:
            # Skip ballots with no timestamps
            continue
        elif len(timestamps) == 1:
            # Single timestamp - use it
            single_timestamp_rows.append(
                {
                    "county": data["county"],
                    "imprinted_id": imprinted_id,
                    "cvr_id": data["cvr_id"],
                    "timestamp": timestamps[0],
                    "timestamp_str": timestamps[0].strftime("%Y-%m-%d %H:%M:%S.%f"),
                    "contest_count": contest_count,
                    "discrepancy_count": data["discrepancies"],
                    "ballot_type": data["ballot_type"],
                    "is_multi_timestamp": False,
                }
            )
        else:
            # Multi-timestamp - use last timestamp for main CSV, create separate entries for multi CSV
            last_ts = timestamps[-1]
            single_timestamp_rows.append(
                {
                    "county": data["county"],
                    "imprinted_id": imprinted_id,
                    "cvr_id": data["cvr_id"],
                    "timestamp": last_ts,
                    "timestamp_str": last_ts.strftime("%Y-%m-%d %H:%M:%S.%f"),
                    "contest_count": contest_count,
                    "discrepancy_count": data["discrepancies"],
                    "ballot_type": data["ballot_type"],
                    "is_multi_timestamp": True,
                }
            )

            # Create separate rows for each timestamp in multi-timestamp report
            for i, ts in enumerate(timestamps):
                prev_ts = timestamps[i - 1] if i > 0 else None
                duration_seconds = (ts - prev_ts).total_seconds() if prev_ts else None

                multi_timestamp_rows.append(
                    {
                        "county": data["county"],
                        "imprinted_id": imprinted_id,
                        "cvr_id": data["cvr_id"],
                        "timestamp": ts,
                        "timestamp_str": ts.strftime("%Y-%m-%d %H:%M:%S.%f"),
                        "timestamp_sequence": i + 1,
                        "total_timestamps": len(timestamps),
                        "duration_from_previous_seconds": duration_seconds,
                        "contest_count": contest_count,
                        "discrepancy_count": data["discrepancies"],
                        "ballot_type": data["ballot_type"],
                    }
                )

    print(
        f"\nSingle timestamp ballots: {len([r for r in single_timestamp_rows if not r['is_multi_timestamp']]):,}"
    )
    print(
        f"Multi-timestamp ballots: {len([r for r in single_timestamp_rows if r['is_multi_timestamp']]):,}"
    )
    print(f"Total entries in multi-timestamp report: {len(multi_timestamp_rows):,}")

    # Sort main CSV by county, then timestamp
    single_timestamp_rows.sort(key=lambda r: (r["county"], r["timestamp"]))

    # Calculate delta timestamps (time between consecutive ballots)
    print("\nCalculating time deltas between consecutive ballots...")
    for i in range(1, len(single_timestamp_rows)):
        prev = single_timestamp_rows[i - 1]
        curr = single_timestamp_rows[i]

        # Only calculate delta if same county
        if prev["county"] == curr["county"]:
            delta = (curr["timestamp"] - prev["timestamp"]).total_seconds()
            curr["delta_seconds"] = delta
            curr["delta_minutes"] = delta / 60.0
        else:
            curr["delta_seconds"] = None
            curr["delta_minutes"] = None

    # First row has no delta
    if single_timestamp_rows:
        single_timestamp_rows[0]["delta_seconds"] = None
        single_timestamp_rows[0]["delta_minutes"] = None

    # Write main CSV
    print(f"\nWriting {output_csv}...")
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "county",
                "imprinted_id",
                "cvr_id",
                "timestamp",
                "contest_count",
                "discrepancy_count",
                "delta_seconds",
                "delta_minutes",
                "ballot_type",
                "is_multi_timestamp",
            ],
        )
        writer.writeheader()
        for row in single_timestamp_rows:
            writer.writerow(
                {
                    "county": row["county"],
                    "imprinted_id": row["imprinted_id"],
                    "cvr_id": row["cvr_id"],
                    "timestamp": row["timestamp_str"],
                    "contest_count": row["contest_count"],
                    "discrepancy_count": row["discrepancy_count"],
                    "delta_seconds": row.get("delta_seconds"),
                    "delta_minutes": row.get("delta_minutes"),
                    "ballot_type": row["ballot_type"],
                    "is_multi_timestamp": row["is_multi_timestamp"],
                }
            )

    print(f"Wrote {len(single_timestamp_rows):,} rows")

    # Write multi-timestamp CSV if there are any
    if multi_timestamp_rows:
        multi_timestamp_rows.sort(key=lambda r: (r["county"], r["imprinted_id"], r["timestamp"]))

        print(f"\nWriting {multi_timestamp_csv}...")
        with multi_timestamp_csv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "county",
                    "imprinted_id",
                    "cvr_id",
                    "timestamp",
                    "timestamp_sequence",
                    "total_timestamps",
                    "duration_from_previous_seconds",
                    "contest_count",
                    "discrepancy_count",
                    "ballot_type",
                ],
            )
            writer.writeheader()
            for row in multi_timestamp_rows:
                writer.writerow(
                    {
                        "county": row["county"],
                        "imprinted_id": row["imprinted_id"],
                        "cvr_id": row["cvr_id"],
                        "timestamp": row["timestamp_str"],
                        "timestamp_sequence": row["timestamp_sequence"],
                        "total_timestamps": row["total_timestamps"],
                        "duration_from_previous_seconds": row["duration_from_previous_seconds"],
                        "contest_count": row["contest_count"],
                        "discrepancy_count": row["discrepancy_count"],
                        "ballot_type": row["ballot_type"],
                    }
                )

        print(f"Wrote {len(multi_timestamp_rows):,} rows")

    # Generate summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)

    # Contest count distribution
    contest_counts = [r["contest_count"] for r in single_timestamp_rows]
    if contest_counts:
        print("\nContest count per ballot:")
        print(f"  Min: {min(contest_counts)}")
        print(f"  Max: {max(contest_counts)}")
        print(f"  Mean: {sum(contest_counts) / len(contest_counts):.1f}")
        print(f"  Median: {sorted(contest_counts)[len(contest_counts) // 2]}")

    # Discrepancy count
    discrepancy_counts = [r["discrepancy_count"] for r in single_timestamp_rows]
    total_discrepancies = sum(discrepancy_counts)
    ballots_with_discrepancies = sum(1 for d in discrepancy_counts if d > 0)
    print("\nDiscrepancies:")
    print(f"  Total discrepancies: {total_discrepancies:,}")
    print(
        f"  Ballots with discrepancies: {ballots_with_discrepancies:,} ({100.0 * ballots_with_discrepancies / len(single_timestamp_rows):.1f}%)"
    )

    # Time deltas (excluding None values and outliers)
    deltas = [
        r.get("delta_seconds") for r in single_timestamp_rows if r.get("delta_seconds") is not None
    ]
    if deltas:
        # Filter out very large gaps (likely breaks or board changes)
        reasonable_deltas = [d for d in deltas if d < 3600]  # Less than 1 hour
        if reasonable_deltas:
            print("\nTime between consecutive ballots (same county, excluding >1hr gaps):")
            print(f"  Count: {len(reasonable_deltas):,}")
            print(
                f"  Min: {min(reasonable_deltas):.1f} seconds ({min(reasonable_deltas) / 60:.1f} minutes)"
            )
            print(
                f"  Max: {max(reasonable_deltas):.1f} seconds ({max(reasonable_deltas) / 60:.1f} minutes)"
            )
            print(
                f"  Mean: {sum(reasonable_deltas) / len(reasonable_deltas):.1f} seconds ({sum(reasonable_deltas) / len(reasonable_deltas) / 60:.1f} minutes)"
            )
            median_delta = sorted(reasonable_deltas)[len(reasonable_deltas) // 2]
            print(f"  Median: {median_delta:.1f} seconds ({median_delta / 60:.1f} minutes)")

    # Temporal patterns
    hours = [r["timestamp"].hour for r in single_timestamp_rows]
    hour_counts = defaultdict(int)
    for h in hours:
        hour_counts[h] += 1

    print("\nAudit activity by hour of day:")
    for hour in sorted(hour_counts.keys()):
        count = hour_counts[hour]
        pct = 100.0 * count / len(single_timestamp_rows)
        print(f"  {hour:2d}:00 - {count:4d} ballots ({pct:5.1f}%)")

    # County-level aggregates
    county_stats: Dict[str, Dict] = defaultdict(
        lambda: {
            "count": 0,
            "total_contests": 0,
            "total_discrepancies": 0,
            "deltas": [],
        }
    )

    for row in single_timestamp_rows:
        county = row["county"]
        county_stats[county]["count"] += 1
        county_stats[county]["total_contests"] += row["contest_count"]
        county_stats[county]["total_discrepancies"] += row["discrepancy_count"]
        if row.get("delta_seconds") is not None:
            county_stats[county]["deltas"].append(row["delta_seconds"])

    print("\nCounty-level aggregates (top 10 by ballot count):")
    sorted_counties = sorted(county_stats.items(), key=lambda x: x[1]["count"], reverse=True)
    for county, stats in sorted_counties[:10]:
        avg_contests = stats["total_contests"] / stats["count"] if stats["count"] > 0 else 0
        avg_delta = sum(stats["deltas"]) / len(stats["deltas"]) if stats["deltas"] else None
        print(
            f"  {county:20s}: {stats['count']:4d} ballots, "
            f"{avg_contests:.1f} avg contests, "
            f"{stats['total_discrepancies']:3d} discrepancies",
            end="",
        )
        if avg_delta:
            print(f", {avg_delta / 60:.1f} min avg between ballots")
        else:
            print()

    print("\n✓ Analysis complete!")
    print(f"  Main output: {output_csv}")
    if multi_timestamp_rows:
        print(f"  Multi-timestamp output: {multi_timestamp_csv}")


if __name__ == "__main__":
    app()
