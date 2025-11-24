#!/usr/bin/env python3
"""
Regression analysis: Contest count vs delta time for counties with means 100-200 seconds.

Filters to counties with mean delta times between 100-200 seconds (excluding
multi-board counties) and performs regression analysis.
"""

from __future__ import annotations

import csv
import random
import statistics
from pathlib import Path

import matplotlib.pyplot as plt
import typer

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "timestamp_analysis"
STATS_CSV = OUTPUT_DIR / "county_statistics.csv"
BALLOTS_CSV = OUTPUT_DIR / "ballot_timestamps.csv"

app = typer.Typer(help=__doc__)


def remove_outliers_iqr(data: list[float]) -> list[float]:
    """Remove outliers using IQR method."""
    if len(data) < 4:
        return data  # Need at least 4 points for IQR

    sorted_data = sorted(data)
    q1_index = len(sorted_data) // 4
    q3_index = 3 * len(sorted_data) // 4

    q1 = sorted_data[q1_index]
    q3 = sorted_data[q3_index]
    iqr = q3 - q1

    if iqr == 0:
        return data  # No variation, no outliers

    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    filtered = [x for x in data if lower_bound <= x <= upper_bound]
    return filtered


def linear_regression(x: list[float], y: list[float]) -> dict | None:
    """Simple linear regression implementation."""
    n = len(x)
    if n < 2:
        return None

    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)

    # Calculate slope and intercept
    numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return None

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean

    # Calculate R-squared
    y_pred = [intercept + slope * xi for xi in x]
    ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
    ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

    # Calculate correlation coefficient
    if n > 1:
        x_std = statistics.stdev(x)
        y_std = statistics.stdev(y)
        correlation = (statistics.covariance(x, y) / (x_std * y_std)) if (x_std * y_std) != 0 else 0
    else:
        correlation = 0

    # Standard error of slope
    if n > 2 and ss_res > 0:
        se_slope = (ss_res / (n - 2)) ** 0.5 / (denominator**0.5) if denominator > 0 else 0
    else:
        se_slope = 0

    return {
        "slope": slope,
        "intercept": intercept,
        "r_squared": r_squared,
        "correlation": correlation,
        "se_slope": se_slope,
        "n": n,
    }


@app.command()
def by_county(
    min_mean: float = typer.Option(100.0, "--min-mean", help="Minimum mean delta time"),
    max_mean: float = typer.Option(200.0, "--max-mean", help="Maximum mean delta time"),
    output_csv: Path = typer.Option(
        OUTPUT_DIR / "regression_by_county.csv",
        "--output",
        "-o",
        help="Output CSV file",
    ),
) -> None:
    """Perform regression of contest count vs delta time for each county separately."""

    # Identify qualifying counties
    qualifying_counties = []
    with STATS_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mean_sec = float(row["mean_seconds"])
            if min_mean <= mean_sec <= max_mean:
                qualifying_counties.append(row["county"])

    print(f"{len(qualifying_counties)} counties with means between {min_mean}-{max_mean} seconds\n")

    # Load ballot data grouped by county
    county_data: dict[str, dict] = {}

    with BALLOTS_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            county = row["county"]
            if county not in qualifying_counties:
                continue

            contest_count = int(row["contest_count"])
            delta_str = row.get("delta_seconds", "").strip()

            if delta_str:
                try:
                    delta = float(delta_str)
                    # Exclude None, negative, and very large gaps (>1 hour)
                    if 0 < delta < 3600:
                        if county not in county_data:
                            county_data[county] = {"x": [], "y": []}
                        county_data[county]["x"].append(contest_count)
                        county_data[county]["y"].append(delta)
                except (ValueError, TypeError):
                    pass

    # Perform regression for each county
    results = []

    for county in sorted(county_data.keys()):
        x = county_data[county]["x"]
        y = county_data[county]["y"]

        if len(y) < 4:
            continue  # Skip counties with too few points

        # Remove outliers per county
        sorted_y = sorted(y)
        q1_index = len(sorted_y) // 4
        q3_index = 3 * len(sorted_y) // 4
        q1 = sorted_y[q1_index]
        q3 = sorted_y[q3_index]
        iqr = q3 - q1

        if iqr == 0:
            x_filtered = x
            y_filtered = y
            outliers_removed = 0
        else:
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            x_filtered = []
            y_filtered = []
            for i, delta in enumerate(y):
                if lower_bound <= delta <= upper_bound:
                    x_filtered.append(x[i])
                    y_filtered.append(delta)

            outliers_removed = len(y) - len(y_filtered)

        # Perform regression
        result = linear_regression(x_filtered, y_filtered)

        if result and len(x_filtered) >= 2:
            results.append(
                {
                    "county": county,
                    "n": result["n"],
                    "n_before_outliers": len(y),
                    "outliers_removed": outliers_removed,
                    "contest_min": min(x_filtered) if x_filtered else 0,
                    "contest_max": max(x_filtered) if x_filtered else 0,
                    "delta_min": min(y_filtered) if y_filtered else 0,
                    "delta_max": max(y_filtered) if y_filtered else 0,
                    "intercept": result["intercept"],
                    "slope": result["slope"],
                    "r_squared": result["r_squared"],
                    "correlation": result["correlation"],
                    "se_slope": result["se_slope"],
                }
            )

    # Sort by R-squared descending
    results.sort(key=lambda r: r["r_squared"], reverse=True)

    # Write to CSV
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "county",
                "n",
                "n_before_outliers",
                "outliers_removed",
                "contest_min",
                "contest_max",
                "delta_min",
                "delta_max",
                "intercept",
                "slope",
                "r_squared",
                "correlation",
                "se_slope",
            ],
        )
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    print("=" * 80)
    print("REGRESSION BY COUNTY (sorted by R², descending)")
    print("=" * 80)
    print(f"{'County':<20} {'N':>4} {'Outliers':>8} {'R²':>8} {'Slope':>10} {'Intercept':>10}")
    print("-" * 80)

    for r in results:
        print(
            f"{r['county']:<20} {r['n']:>4} {r['outliers_removed']:>8} "
            f"{r['r_squared']:>8.4f} {r['slope']:>10.4f} {r['intercept']:>10.2f}"
        )

    print(f"\n✓ Saved regression results to {output_csv}")


@app.command()
def plot_by_county(
    min_mean: float = typer.Option(100.0, "--min-mean", help="Minimum mean delta time"),
    max_mean: float = typer.Option(200.0, "--max-mean", help="Maximum mean delta time"),
    output_plot: Path = typer.Option(
        OUTPUT_DIR / "regression_by_county_grid.png",
        "--output",
        "-o",
        help="Output plot file",
    ),
    cols: int = typer.Option(7, "--cols", "-c", help="Number of columns in grid"),
    rows: int = typer.Option(5, "--rows", "-r", help="Number of rows in grid"),
) -> None:
    """Create a grid of regression plots, one per county."""

    # Identify qualifying counties
    qualifying_counties = []
    with STATS_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mean_sec = float(row["mean_seconds"])
            if min_mean <= mean_sec <= max_mean:
                qualifying_counties.append(row["county"])

    print(f"{len(qualifying_counties)} counties with means between {min_mean}-{max_mean} seconds")

    # Load ballot data grouped by county
    county_data: dict[str, dict] = {}

    with BALLOTS_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            county = row["county"]
            if county not in qualifying_counties:
                continue

            contest_count = int(row["contest_count"])
            delta_str = row.get("delta_seconds", "").strip()

            if delta_str:
                try:
                    delta = float(delta_str)
                    if 0 < delta < 3600:
                        if county not in county_data:
                            county_data[county] = {"x": [], "y": []}
                        county_data[county]["x"].append(contest_count)
                        county_data[county]["y"].append(delta)
                except (ValueError, TypeError):
                    pass

    # Create grid of subplots
    counties_sorted = sorted(county_data.keys())
    n_counties = len(counties_sorted)

    # First pass: determine global axis limits by processing all counties
    all_x_filtered = []
    all_y_filtered = []

    for county in counties_sorted:
        x = county_data[county]["x"]
        y = county_data[county]["y"]

        if len(y) < 4:
            continue

        # Remove outliers (same logic as below)
        sorted_y = sorted(y)
        q1_index = len(sorted_y) // 4
        q3_index = 3 * len(sorted_y) // 4
        q1 = sorted_y[q1_index]
        q3 = sorted_y[q3_index]
        iqr = q3 - q1

        if iqr > 0:
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            x_filtered = [x[i] for i, delta in enumerate(y) if lower_bound <= delta <= upper_bound]
            y_filtered = [delta for delta in y if lower_bound <= delta <= upper_bound]
        else:
            x_filtered = x
            y_filtered = y

        if len(set(x_filtered)) >= 2 and len(x_filtered) >= 2:
            all_x_filtered.extend(x_filtered)
            all_y_filtered.extend(y_filtered)

    # Set global axis limits with some padding
    x_min, x_max = min(all_x_filtered), max(all_x_filtered)
    y_min, y_max = min(all_y_filtered), max(all_y_filtered)

    # Add padding (5% on each side)
    x_range = x_max - x_min
    y_range = y_max - y_min
    x_min_global = max(0, x_min - x_range * 0.05)
    x_max_global = x_max + x_range * 0.05
    y_min_global = max(0, y_min - y_range * 0.05)
    y_max_global = y_max + y_range * 0.05

    # Calculate actual grid size needed
    n_rows = min(rows, (n_counties + cols - 1) // cols)  # Round up division
    n_cols = min(cols, n_counties)

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols * 2.5, n_rows * 2.5))
    fig.suptitle(
        f"Regression: Contest Count vs Delta Time by County\n(Mean delta {min_mean}-{max_mean} seconds, outliers removed)",
        fontsize=14,
        fontweight="bold",
        y=0.995,
    )

    # Flatten axes if needed
    if n_counties == 1:
        axes = [axes]
    elif n_rows == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    # Plot each county
    for idx, county in enumerate(counties_sorted[: n_rows * n_cols]):
        ax = axes[idx]
        x = county_data[county]["x"]
        y = county_data[county]["y"]

        if len(y) < 4:
            ax.text(
                0.5,
                0.5,
                f"{county}\nInsufficient data",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
            ax.set_xlabel("")
            ax.set_ylabel("")
            continue

        # Remove outliers per county
        sorted_y = sorted(y)
        q1_index = len(sorted_y) // 4
        q3_index = 3 * len(sorted_y) // 4
        q1 = sorted_y[q1_index]
        q3 = sorted_y[q3_index]
        iqr = q3 - q1

        if iqr > 0:
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            x_filtered = []
            y_filtered = []
            for i, delta in enumerate(y):
                if lower_bound <= delta <= upper_bound:
                    x_filtered.append(x[i])
                    y_filtered.append(delta)
        else:
            x_filtered = x
            y_filtered = y

        # Handle counties with uniform contest count (still show delta time spread)
        if len(set(x_filtered)) < 2:
            unique_contest_val = list(set(x_filtered))[0] if x_filtered else "?"

            # Still plot the delta time spread at that single contest value
            if x_filtered and y_filtered:
                # Use a small horizontal jitter to show multiple points
                x_plot = [unique_contest_val] * len(y_filtered)
                # Add slight jitter for visibility
                random.seed(42)  # For reproducibility
                x_jittered = [x_val + random.uniform(-0.2, 0.2) for x_val in x_plot]

                ax.scatter(x_jittered, y_filtered, alpha=0.5, s=15, color="steelblue")

                # Show mean and range
                mean_delta = statistics.mean(y_filtered)

                ax.axhline(
                    mean_delta, color="red", linestyle="--", linewidth=1, alpha=0.7, label="Mean"
                )
                ax.text(
                    unique_contest_val,
                    mean_delta,
                    f" {mean_delta:.0f}s",
                    va="center",
                    fontsize=6,
                    color="red",
                )

                # Title
                ax.set_title(
                    f"{county}\nUniform contest count ({unique_contest_val})\nn={len(y_filtered)}",
                    fontsize=9,
                    fontweight="bold",
                )

                # Set uniform axes
                ax.set_xlim(x_min_global, x_max_global)
                ax.set_ylim(y_min_global, y_max_global)

                # Labels
                if idx >= (n_rows - 1) * n_cols:  # Bottom row
                    ax.set_xlabel("Contests", fontsize=7)
                if idx % n_cols == 0:  # Left column
                    ax.set_ylabel("Delta (s)", fontsize=7)

                ax.tick_params(labelsize=6)
                ax.grid(alpha=0.3)
            else:
                ax.text(
                    0.5,
                    0.5,
                    f"{county}\nInsufficient data",
                    ha="center",
                    va="center",
                    transform=ax.transAxes,
                    fontsize=8,
                )
                ax.set_xlabel("")
                ax.set_ylabel("")
            continue

        # Perform regression
        result = linear_regression(x_filtered, y_filtered)

        if result and len(x_filtered) >= 2:
            # Scatter plot
            ax.scatter(x_filtered, y_filtered, alpha=0.5, s=15, color="steelblue")

            # Regression line
            x_min, x_max = min(x_filtered), max(x_filtered)
            if x_min != x_max:
                x_line = [x_min, x_max]
                y_line = [result["intercept"] + result["slope"] * xi for xi in x_line]
                ax.plot(x_line, y_line, "r-", linewidth=1.5, alpha=0.8)

            # Title with county name and R²
            ax.set_title(
                f"{county}\nR²={result['r_squared']:.3f}, n={result['n']}",
                fontsize=9,
                fontweight="bold",
            )

            # Small axis labels
            if idx >= (n_rows - 1) * n_cols:  # Bottom row
                ax.set_xlabel("Contests", fontsize=7)
            if idx % n_cols == 0:  # Left column
                ax.set_ylabel("Delta (s)", fontsize=7)

            ax.tick_params(labelsize=6)
            ax.grid(alpha=0.3)

            # Set uniform axes for all plots
            ax.set_xlim(x_min_global, x_max_global)
            ax.set_ylim(y_min_global, y_max_global)
        else:
            ax.text(
                0.5,
                0.5,
                f"{county}\nInsufficient data",
                ha="center",
                va="center",
                transform=ax.transAxes,
                fontsize=8,
            )
            ax.set_xlabel("")
            ax.set_ylabel("")

    # Hide unused subplots
    for idx in range(len(counties_sorted), len(axes)):
        axes[idx].axis("off")

    plt.tight_layout()
    output_plot.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_plot, dpi=300, bbox_inches="tight")
    print(f"✓ Saved grid plot to {output_plot}")
    plt.close()


@app.command()
def main(
    min_mean: float = typer.Option(100.0, "--min-mean", help="Minimum mean delta time"),
    max_mean: float = typer.Option(200.0, "--max-mean", help="Maximum mean delta time"),
    output_plot: Path = typer.Option(
        OUTPUT_DIR / "regression_contests_vs_time.png",
        "--output",
        "-o",
        help="Output plot file",
    ),
) -> None:
    """Perform regression of contest count vs delta time."""

    # Identify qualifying counties
    qualifying_counties = []
    with STATS_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mean_sec = float(row["mean_seconds"])
            if min_mean <= mean_sec <= max_mean:
                qualifying_counties.append(row["county"])

    print(f"{len(qualifying_counties)} counties with means between {min_mean}-{max_mean} seconds\n")

    # Load ballot data and filter to qualifying counties
    x_contests = []
    y_deltas = []

    with BALLOTS_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            county = row["county"]
            if county not in qualifying_counties:
                continue

            contest_count = int(row["contest_count"])
            delta_str = row.get("delta_seconds", "").strip()

            if delta_str:
                try:
                    delta = float(delta_str)
                    # Exclude None, negative, and very large gaps (>1 hour)
                    if 0 < delta < 3600:
                        x_contests.append(contest_count)
                        y_deltas.append(delta)
                except (ValueError, TypeError):
                    pass

    print(f"Total data points (before outlier removal): {len(x_contests)}")
    print(f"Contest count range: {min(x_contests)} - {max(x_contests)}")
    print(f"Delta range: {min(y_deltas):.1f} - {max(y_deltas):.1f} seconds\n")

    # Remove outliers from delta times using IQR method
    if len(y_deltas) < 4:
        x_filtered = x_contests
        y_filtered = y_deltas
        outliers_removed = 0
    else:
        sorted_y = sorted(y_deltas)
        q1_index = len(sorted_y) // 4
        q3_index = 3 * len(sorted_y) // 4
        q1 = sorted_y[q1_index]
        q3 = sorted_y[q3_index]
        iqr = q3 - q1

        if iqr == 0:
            x_filtered = x_contests
            y_filtered = y_deltas
            outliers_removed = 0
        else:
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            x_filtered = []
            y_filtered = []
            for i, delta in enumerate(y_deltas):
                if lower_bound <= delta <= upper_bound:
                    x_filtered.append(x_contests[i])
                    y_filtered.append(delta)

            outliers_removed = len(x_contests) - len(x_filtered)

    outliers_removed = len(x_contests) - len(x_filtered)
    print(
        f"Outliers removed: {outliers_removed} ({100.0 * outliers_removed / len(x_contests):.1f}%)"
    )
    print(f"Data points after outlier removal: {len(x_filtered)}")
    print(f"Delta range after filtering: {min(y_filtered):.1f} - {max(y_filtered):.1f} seconds\n")

    # Perform linear regression on filtered data
    result = linear_regression(x_filtered, y_filtered)

    if not result:
        print("Error: Could not perform regression")
        return

    print("=" * 80)
    print("REGRESSION: Contest Count vs Delta Time")
    print("=" * 80)
    print(
        f"Equation: delta_time = {result['intercept']:.2f} + {result['slope']:.4f} * contest_count"
    )
    print(f"R-squared: {result['r_squared']:.4f}")
    print(f"R (correlation): {result['correlation']:.4f}")
    print(f"Std error of slope: {result['se_slope']:.4f}")
    print(f"Number of data points: {result['n']}")
    print("\nInterpretation:")
    print(f"  Each additional contest adds {result['slope']:.2f} seconds to examination time")
    print(f"  Base time (intercept): {result['intercept']:.2f} seconds")
    print(
        f"  For a ballot with 30 contests: {result['intercept'] + result['slope'] * 30:.1f} seconds"
    )
    print(
        f"  For a ballot with 40 contests: {result['intercept'] + result['slope'] * 40:.1f} seconds"
    )

    # Create scatter plot with regression line
    fig, ax = plt.subplots(figsize=(12, 8))

    # Scatter plot (filtered data)
    ax.scatter(
        x_filtered,
        y_filtered,
        alpha=0.3,
        s=20,
        color="steelblue",
        label="Data points (outliers removed)",
    )

    # Regression line
    x_min, x_max = min(x_filtered), max(x_filtered)
    x_line = [x_min, x_max]
    y_line = [result["intercept"] + result["slope"] * x for x in x_line]
    ax.plot(
        x_line,
        y_line,
        "r-",
        linewidth=2,
        label=f"Regression: y = {result['intercept']:.2f} + {result['slope']:.4f}x",
    )

    ax.set_xlabel("Number of Contests on Ballot", fontsize=12, fontweight="bold")
    ax.set_ylabel("Time Between Consecutive Ballots (seconds)", fontsize=12, fontweight="bold")
    ax.set_title(
        f"Regression: Contest Count vs Delta Time (Outliers Removed)\n"
        f"Counties with mean delta {min_mean}-{max_mean} seconds (n={result['n']}, R²={result['r_squared']:.4f})",
        fontsize=13,
        fontweight="bold",
    )
    ax.grid(alpha=0.3)
    ax.legend(fontsize=10)

    # Add text box with regression stats
    stats_text = (
        f"R² = {result['r_squared']:.4f}\n"
        f"R = {result['correlation']:.4f}\n"
        f"Slope = {result['slope']:.4f} sec/contest\n"
        f"SE(slope) = {result['se_slope']:.4f}\n"
        f"Outliers removed: {outliers_removed}"
    )
    ax.text(
        0.05,
        0.95,
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
    )

    plt.tight_layout()
    output_plot.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_plot, dpi=300, bbox_inches="tight")
    print(f"\n✓ Saved plot to {output_plot}")
    plt.close()


if __name__ == "__main__":
    app()
