#!/usr/bin/env python3
"""
Detect audit boards and generate statistics using delta-based detection.

Sorts by sequence, detects board transitions on negative deltas,
and collects statistics only for consecutive pairs (delta_sequence == 1).
"""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import typer

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "audit_boards"
BALLOTS_CSV = (
    Path(__file__).parent.parent.parent / "output" / "timestamp_analysis" / "ballot_timestamps.csv"
)

app = typer.Typer(help=__doc__)

# Excluded counties (complex cases)
EXCLUDED_COUNTIES = {"Dolores", "Hinsdale", "Otero", "Baca"}


def parse_timestamp(ts_str: str) -> Optional[datetime]:
    """Parse timestamp string to datetime object."""
    if not ts_str or not ts_str.strip():
        return None
    try:
        return datetime.strptime(ts_str.strip(), "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        try:
            return datetime.strptime(ts_str.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


def load_county_data(county: str) -> List[Dict[str, Any]]:
    """Load sequence vs timestamp data for a county."""
    ballots = []

    with BALLOTS_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("county", "").strip() != county:
                continue

            imprinted_id = row.get("imprinted_id", "").strip()
            timestamp_str = row.get("timestamp", "").strip()

            if not imprinted_id or not timestamp_str:
                continue

            ts = parse_timestamp(timestamp_str)
            if not ts:
                continue

            # Parse sequence from imprinted_id or use a sequence field if available
            # For now, we'll need to get sequence from the existing data structure
            # This assumes we have sequence data - we may need to load from the manifest-based data

            ballots.append(
                {
                    "county": county,
                    "imprinted_id": imprinted_id,
                    "timestamp": ts,
                }
            )

    return ballots


def load_sequence_data() -> Dict[str, List[Dict[str, Any]]]:
    """
    Load sequence vs timestamp data for all counties.

    This uses the same data structure as plot_sequence_vs_timestamp.py
    which loads from manifests and assigns sequence numbers.
    """
    # Import here to avoid circular dependencies
    import sys
    from pathlib import Path

    # Add parent directory to path for import
    sys.path.insert(0, str(Path(__file__).parent))
    from plot_sequence_vs_timestamp import load_and_process_county_data

    # Get the data processing function
    county_data, county_list = load_and_process_county_data()

    # Convert to the format we need: list of ballots with sequence and timestamp
    all_ballots: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for county, sequence_data in county_data.items():
        for seq_num, timestamp in sequence_data:
            all_ballots[county].append(
                {
                    "county": county,
                    "sequence": seq_num,
                    "timestamp": timestamp,
                }
            )

        # Sort by sequence
        all_ballots[county].sort(key=lambda x: x["sequence"])

    return all_ballots


def count_negative_deltas_and_collect_consecutive(
    county_ballots: List[Dict[str, Any]],
) -> Tuple[int, List[float]]:
    """
    Count negative deltas (audit board transitions) and collect consecutive deltas.

    Returns (negative_delta_count, consecutive_deltas_list).
    """
    if not county_ballots:
        return 0, []

    negative_delta_count = 0
    consecutive_deltas = []

    # Already sorted by sequence
    for i, ballot in enumerate(county_ballots):
        if i == 0:
            continue

        prev = county_ballots[i - 1]
        delta_sequence = ballot["sequence"] - prev["sequence"]
        delta_time = (ballot["timestamp"] - prev["timestamp"]).total_seconds()

        # Count negative deltas (audit board transitions)
        if delta_sequence < 0:
            negative_delta_count += 1

        # Collect consecutive deltas only (delta_sequence == 1)
        if delta_sequence == 1 and delta_time is not None:
            consecutive_deltas.append(delta_time)

    return negative_delta_count, consecutive_deltas


@app.command()
def detect(
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Output directory (default: output/audit_boards)",
    ),
    clean_threshold: int = typer.Option(
        8,
        "--clean-threshold",
        "-c",
        help="Maximum negative deltas to consider a county 'clean'",
    ),
) -> None:
    """Count negative deltas per county and generate delta statistics."""
    if output_dir is None:
        output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading sequence vs timestamp data...")
    all_county_data = load_sequence_data()

    print(f"Processing {len(all_county_data)} counties...")

    all_consecutive_deltas: List[float] = []
    county_consecutive_deltas: Dict[str, List[float]] = defaultdict(list)
    county_negative_delta_counts: Dict[str, int] = {}

    excluded_count = 0

    for county in sorted(all_county_data.keys()):
        if county in EXCLUDED_COUNTIES:
            print(f"\nSkipping {county} (excluded - complex case)")
            excluded_count += 1
            continue

        print(f"\nProcessing {county}...")
        county_ballots = all_county_data[county]

        # Count negative deltas and collect consecutive deltas
        negative_count, consecutive_deltas = count_negative_deltas_and_collect_consecutive(
            county_ballots
        )

        county_negative_delta_counts[county] = negative_count
        is_clean = negative_count < clean_threshold

        print(f"  Negative deltas (audit boards): {negative_count} {'✓ CLEAN' if is_clean else ''}")

        if consecutive_deltas:
            # Don't remove outliers - use statistics to identify them later
            all_consecutive_deltas.extend(consecutive_deltas)
            county_consecutive_deltas[county] = consecutive_deltas

            mean_delta = statistics.mean(consecutive_deltas)
            print(f"  Consecutive pairs: {len(consecutive_deltas)}, mean delta: {mean_delta:.1f}s")
        else:
            print("  No consecutive pairs found")

    print(f"\n{'='*60}")
    print(f"Processed {len(all_county_data) - excluded_count} counties")
    print(f"Excluded {excluded_count} counties")
    print(f"Total consecutive deltas: {len(all_consecutive_deltas)}")

    # Count clean counties
    clean_counties = [
        county for county, count in county_negative_delta_counts.items() if count < clean_threshold
    ]
    print(f"Clean counties (< {clean_threshold} negative deltas): {len(clean_counties)}")

    # Save negative delta counts
    negative_delta_file = output_dir / "negative_delta_counts.csv"
    print(f"\nSaving negative delta counts to {negative_delta_file}...")

    with negative_delta_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["county", "negative_delta_count", "is_clean"])
        writer.writeheader()
        for county in sorted(county_negative_delta_counts.keys()):
            count = county_negative_delta_counts[county]
            writer.writerow(
                {
                    "county": county,
                    "negative_delta_count": count,
                    "is_clean": count < clean_threshold,
                }
            )

    # Generate county statistics
    county_stats_file = output_dir / "county_statistics.csv"
    print(f"Saving county statistics to {county_stats_file}...")

    county_stats: List[Dict[str, Any]] = []
    # Separate filtered deltas for statistics and histograms
    filtered_county_deltas: Dict[str, List[float]] = {}
    all_filtered_deltas: List[float] = []

    for county in sorted(county_consecutive_deltas.keys()):
        deltas = county_consecutive_deltas[county]
        if not deltas:
            continue

        # Filter outliers: keep only deltas in range [0, 300] seconds
        # Negative deltas occur when boards alternate in time (expected when sorted by sequence)
        filtered_deltas = [d for d in deltas if 0 <= d <= 300.0]
        outlier_count = len(deltas) - len(filtered_deltas)

        if filtered_deltas:
            # Calculate statistics on filtered deltas (excluding outliers)
            mean_delta = statistics.mean(filtered_deltas)
            stddev_delta = statistics.stdev(filtered_deltas) if len(filtered_deltas) > 1 else 0.0
            median_delta = statistics.median(filtered_deltas)
            min_delta = min(filtered_deltas)
            max_delta = max(filtered_deltas)

            filtered_county_deltas[county] = filtered_deltas
            all_filtered_deltas.extend(filtered_deltas)
        else:
            # All deltas are outliers
            mean_delta = None
            stddev_delta = None
            median_delta = None
            min_delta = None
            max_delta = None

        county_stats.append(
            {
                "county": county,
                "neg_deltas": county_negative_delta_counts.get(county, 0),
                "total_pairs": len(deltas),
                "mean_sec": mean_delta,
                "stddev_sec": stddev_delta,
                "median_sec": median_delta,
                "min_sec": min_delta,
                "max_sec": max_delta,
                "outliers": outlier_count,
            }
        )

    with county_stats_file.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "county",
            "neg_deltas",
            "total_pairs",
            "mean_sec",
            "stddev_sec",
            "median_sec",
            "min_sec",
            "max_sec",
            "outliers",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(county_stats)

    # Generate histogram (using filtered deltas, excluding outliers >300s)
    print("\nGenerating histogram...")
    print(
        f"  Total deltas: {len(all_consecutive_deltas)}, after filtering outliers (>300s): {len(all_filtered_deltas)}"
    )
    plot_histogram(all_filtered_deltas, filtered_county_deltas, output_dir)

    print(f"\n✓ Done! Output saved to {output_dir}")


def plot_histogram(
    all_deltas: List[float],
    county_deltas: Dict[str, List[float]],
    output_dir: Path,
) -> None:
    """Generate histogram of consecutive deltas (outliers >300s excluded)."""
    if not all_deltas:
        print("  No deltas to plot")
        return

    # Overall statistics (already filtered to <=300s)
    mean_all = statistics.mean(all_deltas)
    median_all = statistics.median(all_deltas)
    stddev_all = statistics.stdev(all_deltas) if len(all_deltas) > 1 else 0.0

    print(
        f"  Overall (outliers >300s excluded): mean={mean_all:.1f}s, median={median_all:.1f}s, stddev={stddev_all:.1f}s"
    )

    # Create figure with subplots - now 2x3 to add zoomed views
    plt.figure(figsize=(18, 12))

    # Overall histogram (full range)
    ax1 = plt.subplot(2, 3, 1)
    ax1.hist(all_deltas, bins=100, edgecolor="black", alpha=0.7)
    ax1.axvline(mean_all, color="red", linestyle="--", linewidth=2, label=f"Mean: {mean_all:.1f}s")
    ax1.axvline(
        median_all, color="green", linestyle="--", linewidth=2, label=f"Median: {median_all:.1f}s"
    )
    ax1.set_xlabel("Delta Time (seconds)", fontsize=10)
    ax1.set_ylabel("Frequency", fontsize=10)
    ax1.set_title(f"Overall Histogram (n={len(all_deltas)})", fontsize=12, fontweight="bold")
    ax1.legend()
    ax1.grid(alpha=0.3)

    # Zoomed histogram (0-1000 seconds) with many bins
    ax2 = plt.subplot(2, 3, 2)
    # Filter to 0-1000 seconds for zoomed view
    deltas_zoomed = [d for d in all_deltas if 0 <= d <= 1000]
    if deltas_zoomed:
        ax2.hist(deltas_zoomed, bins=200, edgecolor="black", alpha=0.7)
        mean_zoomed = statistics.mean(deltas_zoomed)
        median_zoomed = statistics.median(deltas_zoomed)
        ax2.axvline(
            mean_zoomed, color="red", linestyle="--", linewidth=2, label=f"Mean: {mean_zoomed:.1f}s"
        )
        ax2.axvline(
            median_zoomed,
            color="green",
            linestyle="--",
            linewidth=2,
            label=f"Median: {median_zoomed:.1f}s",
        )
        ax2.set_xlabel("Delta Time (seconds)", fontsize=10)
        ax2.set_ylabel("Frequency", fontsize=10)
        ax2.set_title(
            f"Zoomed: 0-1000s (n={len(deltas_zoomed)}, {len(deltas_zoomed)/len(all_deltas)*100:.1f}%)",
            fontsize=12,
            fontweight="bold",
        )
        ax2.set_xlim(0, 1000)
        ax2.legend()
        ax2.grid(alpha=0.3)
    else:
        ax2.text(
            0.5, 0.5, "No data in 0-1000s range", ha="center", va="center", transform=ax2.transAxes
        )

    # Log scale for overall
    ax3 = plt.subplot(2, 3, 3)
    ax3.hist(all_deltas, bins=100, edgecolor="black", alpha=0.7)
    ax3.set_xscale("log")
    ax3.axvline(mean_all, color="red", linestyle="--", linewidth=2, label=f"Mean: {mean_all:.1f}s")
    ax3.axvline(
        median_all, color="green", linestyle="--", linewidth=2, label=f"Median: {median_all:.1f}s"
    )
    ax3.set_xlabel("Delta Time (seconds, log scale)", fontsize=10)
    ax3.set_ylabel("Frequency", fontsize=10)
    ax3.set_title("Overall Histogram (Log Scale)", fontsize=12, fontweight="bold")
    ax3.legend()
    ax3.grid(alpha=0.3)

    # County means distribution (using filtered deltas only - outliers excluded)
    ax4 = plt.subplot(2, 3, 4)
    county_means = [statistics.mean(deltas) for deltas in county_deltas.values() if deltas]
    if county_means:
        # Filter county means to reasonable range (should all be <= 300, but double-check)
        county_means_filtered = [m for m in county_means if 0 <= m <= 300]
        mean_of_means = statistics.mean(county_means_filtered) if county_means_filtered else 0.0
        median_of_means = statistics.median(county_means_filtered) if county_means_filtered else 0.0
        ax4.hist(county_means_filtered, bins=30, edgecolor="black", alpha=0.7)
        ax4.axvline(
            mean_of_means,
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Mean: {mean_of_means:.1f}s",
        )
        ax4.axvline(
            median_of_means,
            color="green",
            linestyle="--",
            linewidth=2,
            label=f"Median: {median_of_means:.1f}s",
        )
        ax4.set_xlabel("County Mean Delta Time (seconds)", fontsize=10)
        ax4.set_ylabel("Number of Counties", fontsize=10)
        ax4.set_title(
            f"Distribution of County Means (outliers >300s excluded)\n(n={len(county_means_filtered)})",
            fontsize=12,
            fontweight="bold",
        )
        ax4.set_xlim(0, 300)
        ax4.legend()
        ax4.grid(alpha=0.3)

    # County stddevs distribution (using filtered deltas only - outliers excluded)
    ax5 = plt.subplot(2, 3, 5)
    county_stddevs = [
        statistics.stdev(deltas) if len(deltas) > 1 else 0.0
        for deltas in county_deltas.values()
        if deltas
    ]
    if county_stddevs:
        # County stddevs should be reasonable now (much lower than before)
        # Still filter to reasonable range just in case
        county_stddevs_filtered = [s for s in county_stddevs if 0 <= s <= 300]
        mean_of_stddevs = (
            statistics.mean(county_stddevs_filtered) if county_stddevs_filtered else 0.0
        )
        median_of_stddevs = (
            statistics.median(county_stddevs_filtered) if county_stddevs_filtered else 0.0
        )
        ax5.hist(county_stddevs_filtered, bins=30, edgecolor="black", alpha=0.7)
        ax5.axvline(
            mean_of_stddevs,
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Mean: {mean_of_stddevs:.1f}s",
        )
        ax5.axvline(
            median_of_stddevs,
            color="green",
            linestyle="--",
            linewidth=2,
            label=f"Median: {median_of_stddevs:.1f}s",
        )
        ax5.set_xlabel("County StdDev Delta Time (seconds)", fontsize=10)
        ax5.set_ylabel("Number of Counties", fontsize=10)
        ax5.set_title(
            f"Distribution of County StdDevs (outliers >300s excluded)\n(n={len(county_stddevs_filtered)})",
            fontsize=12,
            fontweight="bold",
        )
        ax5.legend()
        ax5.grid(alpha=0.3)

    # Additional zoomed view: 0-500 seconds with even more detail
    ax6 = plt.subplot(2, 3, 6)
    deltas_zoomed2 = [d for d in all_deltas if 0 <= d <= 500]
    if deltas_zoomed2:
        ax6.hist(deltas_zoomed2, bins=250, edgecolor="black", alpha=0.7)
        mean_zoomed2 = statistics.mean(deltas_zoomed2)
        median_zoomed2 = statistics.median(deltas_zoomed2)
        ax6.axvline(
            mean_zoomed2,
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Mean: {mean_zoomed2:.1f}s",
        )
        ax6.axvline(
            median_zoomed2,
            color="green",
            linestyle="--",
            linewidth=2,
            label=f"Median: {median_zoomed2:.1f}s",
        )
        ax6.set_xlabel("Delta Time (seconds)", fontsize=10)
        ax6.set_ylabel("Frequency", fontsize=10)
        ax6.set_title(
            f"Zoomed: 0-500s (n={len(deltas_zoomed2)}, {len(deltas_zoomed2)/len(all_deltas)*100:.1f}%)",
            fontsize=12,
            fontweight="bold",
        )
        ax6.set_xlim(0, 500)
        ax6.legend()
        ax6.grid(alpha=0.3)
    else:
        ax6.text(
            0.5, 0.5, "No data in 0-500s range", ha="center", va="center", transform=ax6.transAxes
        )

    plt.tight_layout()

    hist_file = output_dir / "delta_histogram.png"
    plt.savefig(hist_file, dpi=150, bbox_inches="tight")
    print(f"  Saved histogram to {hist_file}")
    plt.close()


if __name__ == "__main__":
    app()
