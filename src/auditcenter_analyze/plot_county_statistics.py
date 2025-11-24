#!/usr/bin/env python3
"""
Plot county statistics from timestamp analysis.

Creates visualizations of county statistics including coefficient of variation,
mean vs standard deviation, and other metrics.
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import typer

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "timestamp_analysis"
STATS_CSV = OUTPUT_DIR / "county_statistics.csv"

app = typer.Typer(help=__doc__)


@app.command()
def comprehensive(
    output_file: Path = typer.Option(
        OUTPUT_DIR / "county_statistics_comprehensive.png",
        "--output",
        "-o",
        help="Output file for comprehensive single plot",
    ),
) -> None:
    """Generate single comprehensive plot with CV, stdev, mean, and sample count."""
    
    if not STATS_CSV.exists():
        raise FileNotFoundError(f"Statistics file not found: {STATS_CSV}")
    
    # Load data
    counties = []
    counts = []
    means = []
    stdevs = []
    cvs = []
    
    with STATS_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            counties.append(row["county"])
            counts.append(int(row["count"]))
            means.append(float(row["mean_seconds"]))
            stdevs.append(float(row["stdev_seconds"]))
            cvs.append(float(row["coefficient_of_variation"]))
    
    # Create single comprehensive plot with dual axes
    fig, ax1 = plt.subplots(figsize=(14, max(16, len(counties) * 0.4)))
    fig.suptitle(
        "County Statistics: CV, Standard Deviation, Mean, and Sample Count\n(Sorted by Coefficient of Variation, Descending)",
        fontsize=14,
        fontweight="bold",
        y=0.995,
    )
    
    # Second axis for CV and count (dimensionless/metric values)
    ax2 = ax1.twiny()
    
    y_pos = np.arange(len(counties))
    
    # Plot mean ± stddev as horizontal bars (centered on mean, width = 2*stddev)
    # Bars go from (mean - stddev) to (mean + stddev)
    bar_lefts = [m - s for m, s in zip(means, stdevs)]
    bar_widths = [2 * s for s in stdevs]
    ax1.barh(y_pos, bar_widths, left=bar_lefts, height=0.6, label="Mean ± StdDev (seconds)", 
             color="mediumseagreen", alpha=0.7, edgecolor="darkgreen", linewidth=0.5)
    
    # Plot mean as center line marker
    ax1.scatter(means, y_pos, color="darkgreen", marker="|", s=200, zorder=5, 
                label="Mean (seconds)")
    
    # Plot CV and sample count as dots on second axis
    # Normalize CV and count to a reasonable scale for visualization
    cv_max = max(cvs)
    count_max = max(counts)
    # Scale CV to 0-1, then map to reasonable x-axis range (maybe 0-1000 for second axis)
    cv_scaled = [cv / cv_max * 800 for cv in cvs]  # Scale to 0-800 range
    count_scaled = [c / count_max * 800 for c in counts]  # Scale to 0-800 range
    
    ax2.scatter(cv_scaled, y_pos, color="steelblue", s=60, alpha=0.8, marker="o", 
                label="CV", zorder=4)
    ax2.scatter(count_scaled, y_pos, color="purple", s=60, alpha=0.8, marker="s", 
                label="Sample Count", zorder=4)
    
    # Set labels and limits
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(counties, fontsize=8)
    ax1.set_xlabel("Time (seconds) - Mean ± StdDev shown as bars", 
                   fontsize=11, fontweight="bold", color="darkgreen")
    ax1.set_ylabel("County (sorted by CV, descending)", fontsize=11, fontweight="bold")
    ax1.grid(axis="x", alpha=0.3)
    ax1.invert_yaxis()
    ax1.tick_params(axis="x", labelcolor="darkgreen")
    
    # Set second axis labels
    ax2.set_xlabel("Normalized Scale (0-800) - CV (circles) and Sample Count (squares)", 
                   fontsize=11, fontweight="bold", color="steelblue")
    ax2.set_xlim(0, 850)
    ax2.tick_params(axis="x", labelcolor="steelblue")
    
    # Create custom legend combining both axes
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="lower right", fontsize=9)
    
    # Add CV values as text next to dots
    for i, (y, cv, cv_s) in enumerate(zip(y_pos, cvs, cv_scaled)):
        ax2.text(cv_s + 20, y, f"{cv:.3f}", va="center", fontsize=6, 
                color="steelblue", fontweight="bold")
    
    plt.tight_layout()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"✓ Saved comprehensive plot to {output_file}")
    plt.close()


@app.command()
def main(
    output_plots: Path = typer.Option(
        OUTPUT_DIR / "county_statistics_plots.png",
        "--output",
        "-o",
        help="Output file for 4-panel plot",
    ),
    output_all_cv: Path = typer.Option(
        OUTPUT_DIR / "county_statistics_all_cv.png",
        "--output-cv",
        "-c",
        help="Output file for all counties CV plot",
    ),
) -> None:
    """Generate plots of county statistics."""
    
    if not STATS_CSV.exists():
        raise FileNotFoundError(f"Statistics file not found: {STATS_CSV}")
    
    # Load data
    counties = []
    counts = []
    means = []
    stdevs = []
    cvs = []
    
    with STATS_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            counties.append(row["county"])
            counts.append(int(row["count"]))
            means.append(float(row["mean_seconds"]))
            stdevs.append(float(row["stdev_seconds"]))
            cvs.append(float(row["coefficient_of_variation"]))
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(
        "County Statistics: Time Between Consecutive Ballots (Outliers Removed)",
        fontsize=16,
        fontweight="bold",
    )
    
    # 1. Coefficient of Variation (bar chart, top counties)
    ax1 = axes[0, 0]
    top_n = 20
    indices = list(range(top_n))
    ax1.barh(indices, cvs[:top_n], color="steelblue")
    ax1.set_yticks(indices)
    ax1.set_yticklabels(counties[:top_n], fontsize=9)
    ax1.set_xlabel("Coefficient of Variation (std dev / mean)", fontsize=10)
    ax1.set_title(
        f"Top {top_n} Counties by Coefficient of Variation",
        fontsize=11,
        fontweight="bold",
    )
    ax1.grid(axis="x", alpha=0.3)
    ax1.invert_yaxis()
    
    # 2. Mean vs Standard Deviation (scatter plot)
    ax2 = axes[0, 1]
    ax2.scatter(means, stdevs, alpha=0.6, s=50, color="coral")
    for i, county in enumerate(counties):
        if counts[i] > 100:  # Label only counties with >100 samples
            ax2.annotate(county, (means[i], stdevs[i]), fontsize=7, alpha=0.7)
    ax2.set_xlabel("Mean (seconds)", fontsize=10)
    ax2.set_ylabel("Standard Deviation (seconds)", fontsize=10)
    ax2.set_title("Mean vs Standard Deviation", fontsize=11, fontweight="bold")
    ax2.grid(alpha=0.3)
    
    # 3. Mean time per county (bar chart, sorted by mean)
    ax3 = axes[1, 0]
    sorted_by_mean = sorted(zip(counties, means), key=lambda x: x[1], reverse=True)
    top_mean_counties = sorted_by_mean[:20]
    top_mean_names = [x[0] for x in top_mean_counties]
    top_mean_values = [x[1] for x in top_mean_counties]
    indices_mean = list(range(len(top_mean_counties)))
    ax3.barh(indices_mean, top_mean_values, color="mediumseagreen")
    ax3.set_yticks(indices_mean)
    ax3.set_yticklabels(top_mean_names, fontsize=9)
    ax3.set_xlabel("Mean Time Between Ballots (seconds)", fontsize=10)
    ax3.set_title(
        f"Top {len(top_mean_counties)} Counties by Mean Time",
        fontsize=11,
        fontweight="bold",
    )
    ax3.grid(axis="x", alpha=0.3)
    ax3.invert_yaxis()
    
    # 4. Sample count vs coefficient of variation
    ax4 = axes[1, 1]
    ax4.scatter(counts, cvs, alpha=0.6, s=50, color="purple")
    ax4.set_xlabel("Sample Count (after outlier removal)", fontsize=10)
    ax4.set_ylabel("Coefficient of Variation", fontsize=10)
    ax4.set_title("Sample Count vs Coefficient of Variation", fontsize=11, fontweight="bold")
    ax4.grid(alpha=0.3)
    
    plt.tight_layout()
    output_plots.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_plots, dpi=300, bbox_inches="tight")
    print(f"✓ Saved 4-panel plot to {output_plots}")
    plt.close()
    
    # Also create a detailed bar chart of all counties by CV
    fig2, ax = plt.subplots(figsize=(12, max(16, len(counties) * 0.3)))
    y_pos = np.arange(len(counties))
    bars = ax.barh(y_pos, cvs, color="steelblue", alpha=0.7)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(counties, fontsize=8)
    ax.set_xlabel(
        "Coefficient of Variation (std dev / mean)",
        fontsize=11,
        fontweight="bold",
    )
    ax.set_title(
        "All Counties: Coefficient of Variation (Sorted Descending)",
        fontsize=13,
        fontweight="bold",
    )
    ax.grid(axis="x", alpha=0.3)
    ax.invert_yaxis()
    
    # Add value labels on bars
    for i, (bar, cv) in enumerate(zip(bars, cvs)):
        width = bar.get_width()
        ax.text(
            width + 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{cv:.3f}",
            ha="left",
            va="center",
            fontsize=7,
        )
    
    plt.tight_layout()
    output_all_cv.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_all_cv, dpi=300, bbox_inches="tight")
    print(f"✓ Saved detailed CV plot to {output_all_cv}")
    plt.close()


if __name__ == "__main__":
    app()

