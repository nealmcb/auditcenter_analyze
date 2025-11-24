#!/usr/bin/env python3
"""
Plot relationship between discrepancy count and mean "normal" entry time.

Loads discrepancy data per county and plots against mean delta time
(from county statistics, outliers >300s excluded).
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import typer

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "audit_boards"
BALLOTS_CSV = (
    Path(__file__).parent.parent.parent / "output" / "timestamp_analysis" / "ballot_timestamps.csv"
)
COUNTY_STATS_CSV = OUTPUT_DIR / "county_statistics.csv"

app = typer.Typer(help=__doc__)


@app.command()
def main() -> None:
    """Plot mean entry time vs discrepancy count per county."""
    print("Loading discrepancy data...")

    # Load discrepancy counts per county
    county_discrepancies: Dict[str, int] = defaultdict(int)
    county_total_ballots: Dict[str, int] = defaultdict(int)

    with BALLOTS_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            county = row.get("county", "").strip()
            if not county:
                continue

            discrepancy_count = int(row.get("discrepancy_count", "0") or "0")
            county_discrepancies[county] += discrepancy_count
            county_total_ballots[county] += 1

    print(f"Loaded discrepancy data for {len(county_discrepancies)} counties")

    # Load county statistics (mean "normal" entry time)
    print("Loading county statistics...")
    county_means: Dict[str, float] = {}

    with COUNTY_STATS_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            county = row.get("county", "").strip()
            mean_sec_str = row.get("mean_sec", "").strip()
            if county and mean_sec_str:
                try:
                    county_means[county] = float(mean_sec_str)
                except ValueError:
                    continue

    print(f"Loaded mean entry times for {len(county_means)} counties")

    # Combine data
    plot_data: List[Tuple[str, int, float, int, float]] = []

    for county in county_discrepancies.keys():
        discrepancy_count = county_discrepancies[county]
        total_ballots = county_total_ballots[county]
        mean_sec = county_means.get(county)

        if mean_sec is not None and total_ballots > 0:
            discrepancy_rate = discrepancy_count / total_ballots
            plot_data.append((county, discrepancy_count, mean_sec, total_ballots, discrepancy_rate))

    # Sort by discrepancy count for first plot
    plot_data_by_count = sorted(plot_data, key=lambda x: x[1])

    # Sort by discrepancy rate for second plot
    plot_data_by_rate = sorted(plot_data, key=lambda x: x[4])

    print(f"\nPrepared data for {len(plot_data)} counties")
    print(f"Total discrepancies: {sum(d[1] for d in plot_data)}")
    print("Counties with discrepancies:")
    for county, disc_count, mean_sec, total, disc_rate in plot_data_by_count:
        if disc_count > 0:
            print(
                f"  {county}: {disc_count} discrepancies ({disc_rate*100:.2f}% rate, {mean_sec:.1f}s mean entry time)"
            )

    # ===== PLOT 1: Discrepancy Count vs Entry Time =====
    discrepancy_counts = [d[1] for d in plot_data_by_count]
    mean_times = [d[2] for d in plot_data_by_count]
    total_ballots_list = [d[3] for d in plot_data_by_count]

    fig1, ax1 = plt.subplots(figsize=(14, 8))

    # Scatter plot with size proportional to total ballots
    sizes = [max(20, b * 2) for b in total_ballots_list]  # Scale size

    scatter1 = ax1.scatter(
        discrepancy_counts,
        mean_times,
        s=sizes,
        alpha=0.6,
        c=discrepancy_counts,
        cmap="YlOrRd",
        edgecolors="black",
        linewidth=0.5,
    )

    # Labels and title
    ax1.set_xlabel("Number of Discrepancies", fontsize=12, fontweight="bold")
    ax1.set_ylabel("Mean 'Normal' Entry Time (seconds)", fontsize=12, fontweight="bold")
    ax1.set_title(
        "Mean Entry Time vs Discrepancy Count (Counties sorted by discrepancies)\n"
        "Size = total ballots, Color = discrepancy count (outliers >300s excluded from mean)",
        fontsize=13,
        fontweight="bold",
    )

    # Add colorbar
    cbar1 = plt.colorbar(scatter1, ax=ax1)
    cbar1.set_label("Discrepancy Count", fontsize=10)

    # Grid
    ax1.grid(alpha=0.3, linestyle="--")

    # Annotate counties with discrepancies > 0
    for county, disc_count, mean_time, total, disc_rate in plot_data_by_count:
        if disc_count > 0:
            ax1.annotate(
                county,
                (disc_count, mean_time),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=7,
                alpha=0.7,
            )

    plt.tight_layout()

    output_file1 = OUTPUT_DIR / "discrepancies_vs_entry_time.png"
    output_file1.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file1, dpi=150, bbox_inches="tight")
    print(f"\n✓ Saved discrepancy count plot to {output_file1}")
    plt.close()

    # ===== PLOT 2: Discrepancy Rate vs Entry Time =====
    discrepancy_rates = [d[4] for d in plot_data_by_rate]
    mean_times_rate = [d[2] for d in plot_data_by_rate]
    total_ballots_rate = [d[3] for d in plot_data_by_rate]

    fig2, (ax2a, ax2b) = plt.subplots(1, 2, figsize=(20, 8))

    # Scatter plot with size proportional to total ballots
    sizes_rate = [max(20, b * 2) for b in total_ballots_rate]  # Scale size

    # Full range plot
    scatter2a = ax2a.scatter(
        discrepancy_rates,
        mean_times_rate,
        s=sizes_rate,
        alpha=0.6,
        c=[d[1] for d in plot_data_by_rate],  # Color by discrepancy count
        cmap="YlOrRd",
        edgecolors="black",
        linewidth=0.5,
    )

    # Labels and title
    ax2a.set_xlabel(
        "Discrepancy Rate (discrepancies per ballot examined)", fontsize=12, fontweight="bold"
    )
    ax2a.set_ylabel("Mean 'Normal' Entry Time (seconds)", fontsize=12, fontweight="bold")
    ax2a.set_title(
        "Mean Entry Time vs Discrepancy Rate (Full Range)\n"
        "Size = total ballots, Color = discrepancy count (outliers >300s excluded from mean)",
        fontsize=13,
        fontweight="bold",
    )

    # Format x-axis as percentage
    ax2a.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x*100:.1f}%"))

    # Add colorbar
    cbar2a = plt.colorbar(scatter2a, ax=ax2a)
    cbar2a.set_label("Discrepancy Count", fontsize=10)

    # Grid
    ax2a.grid(alpha=0.3, linestyle="--")

    # Annotate counties with discrepancies > 0
    for county, disc_count, mean_time, total, disc_rate in plot_data_by_rate:
        if disc_count > 0:
            ax2a.annotate(
                county,
                (disc_rate, mean_time),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=7,
                alpha=0.7,
            )

    # Zoomed plot: rates < 35%
    filtered_data = [(c, r, t, b, rate) for c, r, t, b, rate in plot_data_by_rate if rate < 0.35]

    if filtered_data:
        rates_zoom = [d[4] for d in filtered_data]
        times_zoom = [d[2] for d in filtered_data]
        ballots_zoom = [d[3] for d in filtered_data]
        sizes_zoom = [max(20, b * 2) for b in ballots_zoom]

        scatter2b = ax2b.scatter(
            rates_zoom,
            times_zoom,
            s=sizes_zoom,
            alpha=0.6,
            c=[d[1] for d in filtered_data],  # Color by discrepancy count
            cmap="YlOrRd",
            edgecolors="black",
            linewidth=0.5,
        )

        ax2b.set_xlabel(
            "Discrepancy Rate (discrepancies per ballot examined)", fontsize=12, fontweight="bold"
        )
        ax2b.set_ylabel("Mean 'Normal' Entry Time (seconds)", fontsize=12, fontweight="bold")
        ax2b.set_title(
            "Zoomed: Discrepancy Rate < 35%\n"
            "Size = total ballots, Color = discrepancy count (outliers >300s excluded from mean)",
            fontsize=13,
            fontweight="bold",
        )

        # Format x-axis as percentage
        ax2b.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x*100:.1f}%"))
        ax2b.set_xlim(0, 0.35)

        # Add colorbar
        cbar2b = plt.colorbar(scatter2b, ax=ax2b)
        cbar2b.set_label("Discrepancy Count", fontsize=10)

        # Grid
        ax2b.grid(alpha=0.3, linestyle="--")

        # Annotate counties with discrepancies > 0 in zoomed view
        for county, disc_count, mean_time, total, disc_rate in filtered_data:
            if disc_count > 0:
                ax2b.annotate(
                    county,
                    (disc_rate, mean_time),
                    xytext=(5, 5),
                    textcoords="offset points",
                    fontsize=7,
                    alpha=0.7,
                )

    plt.tight_layout()

    output_file2 = OUTPUT_DIR / "discrepancy_rate_vs_entry_time.png"
    output_file2.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file2, dpi=150, bbox_inches="tight")
    print(f"✓ Saved discrepancy rate plot (with zoom) to {output_file2}")
    plt.close()

    # Save data to CSV for reference
    data_file = OUTPUT_DIR / "discrepancies_vs_entry_time.csv"
    with data_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "county",
                "discrepancy_count",
                "discrepancy_rate",
                "mean_entry_time_sec",
                "total_ballots",
            ],
        )
        writer.writeheader()
        for county, disc_count, mean_time, total, disc_rate in plot_data_by_count:
            writer.writerow(
                {
                    "county": county,
                    "discrepancy_count": disc_count,
                    "discrepancy_rate": disc_rate,
                    "mean_entry_time_sec": mean_time,
                    "total_ballots": total,
                }
            )
    print(f"✓ Saved data to {data_file}")


if __name__ == "__main__":
    app()
