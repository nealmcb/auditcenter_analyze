#!/usr/bin/env python3
"""
Analyze timestamps in 2025 finalReports/contestComparison.csv.

Extract timing patterns and identify what happened in round 2.
"""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import typer

DATA_ROOT = Path(__file__).parent.parent.parent / "data" / "2025" / "finalReports"
COMPARISON_FILE = DATA_ROOT / "contestComparison.csv"
ROUND1_CONTESTS_FILE = (
    Path(__file__).parent.parent.parent / "data" / "2025" / "round1" / "contest.csv"
)
ROUND2_CONTESTS_FILE = (
    Path(__file__).parent.parent.parent / "data" / "2025" / "round2" / "contest.csv"
)
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "timestamp_analysis_2025"

app = typer.Typer(help=__doc__)


def parse_timestamp(ts_str: str) -> Optional[datetime]:
    """Parse timestamp string to datetime object."""
    if not ts_str or not ts_str.strip():
        return None
    try:
        # Format: 2025-11-18 09:33:59.346136
        return datetime.strptime(ts_str.strip(), "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        try:
            # Try without microseconds
            return datetime.strptime(ts_str.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


def load_round_contests() -> Tuple[set[str], set[str]]:
    """Load contests from round1 and round2 contest.csv files."""
    round1_contests = set()
    round2_contests = set()

    if ROUND1_CONTESTS_FILE.exists():
        with ROUND1_CONTESTS_FILE.open("r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                contest = row.get("contest_name", "").strip()
                if contest:
                    round1_contests.add(contest)

    if ROUND2_CONTESTS_FILE.exists():
        with ROUND2_CONTESTS_FILE.open("r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                contest = row.get("contest_name", "").strip()
                if contest:
                    round2_contests.add(contest)

    return round1_contests, round2_contests


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
        help="Output CSV file (default: output/timestamp_analysis_2025/ballot_timestamps.csv)",
    ),
    plot_output: Optional[Path] = typer.Option(
        None,
        "--plot",
        "-p",
        help="Output plot file (default: output/timestamp_analysis_2025/timeline.png)",
    ),
) -> None:
    """Extract timestamp data per imprinted_id from 2025 contestComparison.csv."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if output_csv is None:
        output_csv = OUTPUT_DIR / "ballot_timestamps.csv"
    if plot_output is None:
        plot_output = OUTPUT_DIR / "timeline.png"

    # Load round contests
    round1_contests, round2_contests = load_round_contests()
    print(f"Round 1 contests: {len(round1_contests)}")
    print(f"Round 2 contests: {len(round2_contests)}")

    # Group data by imprinted_id
    ballot_data: Dict[str, Dict] = defaultdict(
        lambda: {
            "county": "",
            "timestamps": [],
            "contests": set(),
            "discrepancies": 0,
            "round1_contests": set(),
            "round2_contests": set(),
        }
    )

    print(f"\nLoading {COMPARISON_FILE}...")
    with COMPARISON_FILE.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            imprinted_id = row.get("imprinted_id", "").strip()
            if not imprinted_id:
                continue

            county = row.get("county_name", "").strip()
            contest = row.get("contest_name", "").strip()
            ts_str = row.get("timestamp", "").strip()

            if not county or not contest or not ts_str:
                continue

            ts = parse_timestamp(ts_str)
            if not ts:
                continue

            ballot_data[imprinted_id]["county"] = county
            ballot_data[imprinted_id]["timestamps"].append(ts)
            ballot_data[imprinted_id]["contests"].add(contest)

            if contest in round1_contests:
                ballot_data[imprinted_id]["round1_contests"].add(contest)
            if contest in round2_contests:
                ballot_data[imprinted_id]["round2_contests"].add(contest)

            if has_discrepancy(row):
                ballot_data[imprinted_id]["discrepancies"] += 1

    print(f"Loaded {len(ballot_data)} ballots")

    # Process ballots - use last timestamp for each
    ballot_rows = []
    for imprinted_id, data in ballot_data.items():
        if not data["timestamps"]:
            continue

        # Use last timestamp
        timestamp = max(data["timestamps"])
        contest_count = len(data["contests"])
        round1_count = len(data["round1_contests"])
        round2_count = len(data["round2_contests"])

        # Determine round based on contests present
        # Note: Since round1 and round2 have the same contests, we'll use timing instead
        # Round 2 likely starts after a gap or on a specific date
        primary_round = 0  # Will determine by timing later

        ballot_rows.append(
            {
                "county": data["county"],
                "imprinted_id": imprinted_id,
                "timestamp": timestamp,
                "contest_count": contest_count,
                "round1_contest_count": round1_count,
                "round2_contest_count": round2_count,
                "primary_round": primary_round,
                "discrepancy_count": data["discrepancies"],
            }
        )

    # Sort by timestamp globally
    ballot_rows.sort(key=lambda x: x["timestamp"])

    # Identify round boundaries based on timing
    # Look for significant gaps or date boundaries
    # Round 2 likely starts on Nov 19 based on activity drop
    round2_start_date = datetime(2025, 11, 19, 0, 0, 0)

    # Alternatively, find the largest gap and use that as boundary
    if len(ballot_rows) > 1:
        max_gap = 0
        gap_index = 0
        for i in range(1, len(ballot_rows)):
            gap = (ballot_rows[i]["timestamp"] - ballot_rows[i - 1]["timestamp"]).total_seconds()
            if gap > max_gap and gap > 3600:  # At least 1 hour
                max_gap = gap
                gap_index = i

        if max_gap > 36000:  # More than 10 hours
            round2_start_time = ballot_rows[gap_index]["timestamp"]
            print(f"\nDetected potential round 2 start: {round2_start_time}")
            print(f"  Gap before: {max_gap/3600:.1f} hours")
        else:
            round2_start_time = round2_start_date
            print(f"\nUsing date boundary for round 2: {round2_start_date}")
    else:
        round2_start_time = round2_start_date

    # Assign rounds based on timing
    for row in ballot_rows:
        if row["timestamp"] >= round2_start_time:
            row["primary_round"] = 2
        else:
            row["primary_round"] = 1

    # Sort by county, then timestamp for delta calculation
    ballot_rows.sort(key=lambda x: (x["county"], x["timestamp"]))

    # Calculate deltas (time between consecutive ballots in same county)
    for i in range(1, len(ballot_rows)):
        if ballot_rows[i]["county"] == ballot_rows[i - 1]["county"]:
            delta = (ballot_rows[i]["timestamp"] - ballot_rows[i - 1]["timestamp"]).total_seconds()
            ballot_rows[i]["delta_seconds"] = delta
        else:
            ballot_rows[i]["delta_seconds"] = None

    if ballot_rows:
        ballot_rows[0]["delta_seconds"] = None

    # Re-sort by timestamp for output
    ballot_rows.sort(key=lambda x: x["timestamp"])

    # Write output CSV
    print(f"\nWriting {output_csv}...")
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "county",
            "imprinted_id",
            "timestamp",
            "contest_count",
            "round1_contest_count",
            "round2_contest_count",
            "primary_round",
            "discrepancy_count",
            "delta_seconds",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in ballot_rows:
            writer.writerow(row)

    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)

    round1_ballots = [r for r in ballot_rows if r["primary_round"] == 1]
    round2_ballots = [r for r in ballot_rows if r["primary_round"] == 2]
    round_unknown = [r for r in ballot_rows if r["primary_round"] == 0]

    print(f"\nTotal ballots: {len(ballot_rows)}")
    print(f"  Round 1: {len(round1_ballots)} ({100*len(round1_ballots)/len(ballot_rows):.1f}%)")
    print(f"  Round 2: {len(round2_ballots)} ({100*len(round2_ballots)/len(ballot_rows):.1f}%)")
    print(f"  Unknown: {len(round_unknown)} ({100*len(round_unknown)/len(ballot_rows):.1f}%)")

    if round1_ballots:
        r1_times = [r["timestamp"] for r in round1_ballots]
        print(f"\nRound 1 timing:")
        print(f"  First: {min(r1_times)}")
        print(f"  Last: {max(r1_times)}")
        print(f"  Duration: {max(r1_times) - min(r1_times)}")

    if round2_ballots:
        r2_times = [r["timestamp"] for r in round2_ballots]
        print(f"\nRound 2 timing:")
        print(f"  First: {max(r2_times) if r2_times else 'N/A'}")
        print(f"  Last: {max(r2_times)}")
        print(f"  Duration: {max(r2_times) - min(r2_times)}")
        print(f"  Ballots: {len(round2_ballots)}")
        print(f"  Counties involved: {len(set(r['county'] for r in round2_ballots))}")

        # Show counties with round 2 activity
        round2_by_county = defaultdict(int)
        for r in round2_ballots:
            round2_by_county[r["county"]] += 1

        print(f"\nRound 2 activity by county:")
        for county, count in sorted(round2_by_county.items(), key=lambda x: x[1], reverse=True):
            print(f"  {county}: {count} ballots")

    # Time range
    all_times = [r["timestamp"] for r in ballot_rows]
    print(f"\nOverall timing:")
    print(f"  First entry: {min(all_times)}")
    print(f"  Last entry: {max(all_times)}")
    print(f"  Total duration: {max(all_times) - min(all_times)}")

    # County-level summary
    county_stats = defaultdict(
        lambda: {
            "count": 0,
            "round1": 0,
            "round2": 0,
            "discrepancies": 0,
        }
    )

    for row in ballot_rows:
        county = row["county"]
        county_stats[county]["count"] += 1
        if row["primary_round"] == 1:
            county_stats[county]["round1"] += 1
        elif row["primary_round"] == 2:
            county_stats[county]["round2"] += 1
        county_stats[county]["discrepancies"] += row["discrepancy_count"]

    print(f"\nCounty-level summary (counties with round 2 activity):")
    counties_with_r2 = sorted(
        [(c, s) for c, s in county_stats.items() if s["round2"] > 0],
        key=lambda x: x[1]["round2"],
        reverse=True,
    )
    for county, stats in counties_with_r2[:20]:
        print(
            f"  {county:20s}: {stats['count']:4d} total, "
            f"R1: {stats['round1']:4d}, R2: {stats['round2']:4d}, "
            f"disc: {stats['discrepancies']:3d}"
        )

    # Create timeline plot
    print(f"\nCreating timeline plot...")
    create_timeline_plot(ballot_rows, plot_output)

    print(f"\n✓ Analysis complete!")
    print(f"  Output CSV: {output_csv}")
    print(f"  Plot: {plot_output}")


def create_timeline_plot(ballot_rows: List[Dict], output_file: Path) -> None:
    """Create a timeline plot showing all counties' audit activity."""

    # Group by county and round
    county_data = defaultdict(
        lambda: {
            "timestamps": [],
            "rounds": [],
            "sequence": [],
            "round1_timestamps": [],
            "round2_timestamps": [],
            "round1_sequence": [],
            "round2_sequence": [],
        }
    )

    # Assign sequence numbers by county and round
    county_sequences_r1 = defaultdict(int)
    county_sequences_r2 = defaultdict(int)

    for row in ballot_rows:
        county = row["county"]
        round_num = row["primary_round"]

        county_data[county]["timestamps"].append(row["timestamp"])
        county_data[county]["rounds"].append(round_num)

        if round_num == 1:
            county_sequences_r1[county] += 1
            seq = county_sequences_r1[county]
            county_data[county]["round1_timestamps"].append(row["timestamp"])
            county_data[county]["round1_sequence"].append(seq)
            county_data[county]["sequence"].append(seq)
        elif round_num == 2:
            county_sequences_r2[county] += 1
            seq = county_sequences_r2[county]
            county_data[county]["round2_timestamps"].append(row["timestamp"])
            county_data[county]["round2_sequence"].append(seq)
            county_data[county]["sequence"].append(seq)

    # Include ALL counties
    plot_counties = sorted(county_data.keys())

    # Create grid plot - 7 columns for all 63 counties
    n_counties = len(plot_counties)
    cols = 7
    rows = (n_counties + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(20, 3 * rows))
    axes = axes.flatten() if n_counties > 1 else [axes]

    for idx, county in enumerate(plot_counties):
        ax = axes[idx]
        data = county_data[county]

        has_r2 = len(data["round2_timestamps"]) > 0

        # Plot Round 1 (blue)
        if data["round1_timestamps"]:
            ax.scatter(
                data["round1_timestamps"],
                data["round1_sequence"],
                c="blue",
                alpha=0.5,
                s=8,
                label="Round 1" if idx == 0 else "",
            )

        # Plot Round 2 (red, larger)
        if data["round2_timestamps"]:
            ax.scatter(
                data["round2_timestamps"],
                data["round2_sequence"],
                c="red",
                alpha=0.9,
                s=50,
                marker="x",
                linewidths=2,
                label="Round 2" if idx == 0 else "",
            )

        title = county
        if has_r2:
            title += f" (R2: {len(data['round2_timestamps'])})"
        ax.set_title(title, fontsize=9, fontweight="bold")
        ax.set_xlabel("Time", fontsize=7)
        ax.set_ylabel("Sequence #", fontsize=7)
        ax.tick_params(labelsize=6)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d\n%H:%M"))
        ax.grid(alpha=0.3)

        # Add legend for first plot
        if idx == 0:
            ax.legend(loc="upper left", fontsize=6)

    # Hide unused subplots
    for idx in range(len(plot_counties), len(axes)):
        axes[idx].set_visible(False)

    plt.suptitle(
        "2025 Audit Timeline by County\nRound 1 (blue), Round 2 (red)",
        fontsize=14,
        fontweight="bold",
        y=0.995,
    )
    plt.tight_layout()

    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close()

    # Also create a combined plot showing all counties on one chart
    combined_file = output_file.parent / "timeline_combined.png"
    fig, ax = plt.subplots(figsize=(20, 12))

    # Plot each county with different colors
    import matplotlib.cm as cm

    all_counties = sorted(set(row["county"] for row in ballot_rows))
    colors_map = cm.tab20(range(len(all_counties)))
    county_to_color = {c: colors_map[i] for i, c in enumerate(all_counties)}

    # Plot round 1 first (all counties)
    for county in all_counties:
        data = county_data[county]
        county_color = county_to_color[county]
        offset = all_counties.index(county) * 10000

        # Round 1 points
        if data["round1_timestamps"]:
            ax.scatter(
                data["round1_timestamps"],
                [s + offset for s in data["round1_sequence"]],
                c=[county_color],
                marker="o",
                s=5,
                alpha=0.3,
            )

        # Round 2 points (highlighted)
        if data["round2_timestamps"]:
            ax.scatter(
                data["round2_timestamps"],
                [s + offset for s in data["round2_sequence"]],
                c="red",
                marker="x",
                s=100,
                linewidths=3,
                alpha=1.0,
                label=f"{county} (R2: {len(data['round2_timestamps'])})",
                zorder=10,  # Make sure round 2 points are on top
            )

    ax.set_xlabel("Timestamp", fontsize=12)
    ax.set_ylabel("Sequence Number (offset by county)", fontsize=12)
    ax.set_title(
        "2025 Audit Timeline - All Counties Combined\nRound 1 (faded circles), Round 2 (red X's)",
        fontsize=14,
        fontweight="bold",
    )
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    ax.tick_params(labelsize=8)
    ax.grid(alpha=0.3)

    # Add legend for round 2 counties only
    if any(len(county_data[c]["round2_timestamps"]) > 0 for c in all_counties):
        ax.legend(loc="upper left", fontsize=8, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(combined_file, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"  Combined plot: {combined_file}")

    # Create a focused plot showing just round 2 activity
    r2_file = output_file.parent / "round2_detail.png"
    fig, ax = plt.subplots(figsize=(14, 8))

    # Only plot counties with round 2 activity
    r2_counties = [c for c in all_counties if len(county_data[c]["round2_timestamps"]) > 0]

    for county in r2_counties:
        data = county_data[county]
        county_color = county_to_color[county]
        offset = r2_counties.index(county) * 1000

        # Round 1 context (faded)
        if data["round1_timestamps"]:
            ax.scatter(
                data["round1_timestamps"],
                [s + offset for s in data["round1_sequence"]],
                c=[county_color],
                marker="o",
                s=20,
                alpha=0.2,
                label=f"{county} (R1)" if county == r2_counties[0] else "",
            )

        # Round 2 (highlighted)
        if data["round2_timestamps"]:
            ax.scatter(
                data["round2_timestamps"],
                [s + offset for s in data["round2_sequence"]],
                c="red",
                marker="X",
                s=200,
                linewidths=3,
                alpha=1.0,
                label=f"{county} (R2: {len(data['round2_timestamps'])})",
                zorder=10,
            )

    ax.set_xlabel("Timestamp", fontsize=12)
    ax.set_ylabel("Sequence Number (offset by county)", fontsize=12)
    ax.set_title(
        "Round 2 Audit Activity Detail\nShowing only counties with Round 2 ballots",
        fontsize=14,
        fontweight="bold",
    )
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    ax.tick_params(labelsize=8)
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(r2_file, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"  Round 2 detail plot: {r2_file}")


if __name__ == "__main__":
    app()
