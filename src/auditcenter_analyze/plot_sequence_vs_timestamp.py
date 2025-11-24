#!/usr/bin/env python3
"""
Plot sequence number vs timestamp for selected counties.

Sorts imprinted_ids by manifest order (location, tabulator, batch, position),
assigns sequence numbers, and plots against timestamps.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.cm as cm
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import typer

DATA_ROOT = Path(__file__).parent.parent.parent / "data" / "2024" / "general"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "timestamp_analysis"
BALLOTS_CSV = OUTPUT_DIR / "ballot_timestamps.csv"
MANIFESTS_DIR = DATA_ROOT / "ballotManifests"

app = typer.Typer(help=__doc__)


def natural_sort_key(text: str) -> List:
    """Create a key for natural (human-friendly) sorting."""

    def convert(part: str):
        return int(part) if part.isdigit() else part.lower()

    return [convert(chunk) for chunk in re.split(r"(\d+)", text)]


def find_column(fieldnames: List[str], candidates: List[str]) -> str | None:
    """Return first matching column name from candidates (case-insensitive, handles spaces)."""
    # Normalize by stripping spaces and lowercasing
    normalized = {name.strip().lower(): name for name in fieldnames}
    for candidate in candidates:
        candidate_normalized = candidate.strip().lower()
        if candidate_normalized in normalized:
            return normalized[candidate_normalized]
    return None


def load_manifest_entries(manifest_path: Path) -> Dict[str, Dict[str, str]]:
    """Load manifest entries keyed by imprinted_id."""
    entries: Dict[str, Dict[str, str]] = {}

    with manifest_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])

        tabulator_col = find_column(fieldnames, ["Tabulator ID", "Tabulator", "Device ID"])
        batch_col = find_column(
            fieldnames, ["Batch ID", "Batch", "Batch Number", "Batch ", "Batch #"]
        )
        count_col = find_column(
            fieldnames,
            [
                "# of Ballot Cards",
                "# of ballot cards",
                "#of Ballot Cards",
                "# Ballot Cards",
                "# of Ballots Cards",
                "# of Ballot",
                "# of Ballots",
                ". of Ballots",
                "# ballots",
                "# cards",
                "# of cards",
                "# in Batch",
                "Number of Ballots",
            ],
        )
        location_col = find_column(fieldnames, ["Location", "Box # Location", "Box Location"])

        if not all([tabulator_col, batch_col, count_col]):
            raise ValueError(
                f"Manifest {manifest_path} missing required columns. Found: {fieldnames}"
            )

        for row in reader:
            tabulator = row.get(tabulator_col or "", "").strip()
            batch = row.get(batch_col or "", "").strip()
            try:
                card_count = int(row.get(count_col or "", "0"))
            except ValueError:
                continue

            location = row.get(location_col or "", "").strip() if location_col else ""

            for position in range(1, card_count + 1):
                imprinted_id = f"{tabulator}-{batch}-{position}"
                entries[imprinted_id] = {
                    "location": location,
                    "tabulator": tabulator,
                    "batch": batch,
                    "position": str(position),
                }

    return entries


def resolve_manifest_path(county: str) -> Path:
    """Find the manifest CSV for a county."""
    candidates = [
        f"{county}BallotManifest.csv",
        f"{county.replace(' ', '')}BallotManifest.csv",
        f"{county.replace(' ', '_')}BallotManifest.csv",
        f"{county.replace(' ', '-')}BallotManifest.csv",
    ]

    search_roots = [DATA_ROOT, MANIFESTS_DIR]
    for root in search_roots:
        for candidate in candidates:
            path = root / candidate
            if path.exists():
                return path
    raise FileNotFoundError(f"Could not find manifest for county '{county}' in {MANIFESTS_DIR}")


def parse_timestamp(ts_str: str) -> datetime | None:
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


def load_and_process_county_data(
    counties: str | None = None,
) -> Tuple[Dict[str, List[Tuple[int, datetime]]], List[str]]:
    """
    Load timestamp data and process county manifests.

    Returns:
        Tuple of (county_data dict, county_list)
    """
    # Load timestamp data first to get all counties
    print(f"Loading timestamp data from {BALLOTS_CSV}...")
    ballot_timestamps: Dict[str, Dict[str, Any]] = defaultdict(dict)
    all_counties_in_data: set[str] = set()

    with BALLOTS_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            county = row.get("county", "").strip()
            if not county:
                continue

            all_counties_in_data.add(county)

            if counties:
                county_list = [c.strip() for c in counties.split(",")]
                if county not in county_list:
                    continue

            imprinted_id = row.get("imprinted_id", "").strip()
            timestamp_str = row.get("timestamp", "").strip()

            if not imprinted_id or not timestamp_str:
                continue

            ts = parse_timestamp(timestamp_str)
            if not ts:
                continue

            key = (county, imprinted_id)
            # Use first timestamp encountered (should be only one per ballot)
            if key not in ballot_timestamps:
                ballot_timestamps[key] = {
                    "county": county,
                    "imprinted_id": imprinted_id,
                    "timestamp": ts,
                }

    # Determine which counties to process
    if counties:
        county_list = [c.strip() for c in counties.split(",")]
    else:
        county_list = sorted(all_counties_in_data)

    print(
        f"Analyzing {len(county_list)} counties: {', '.join(county_list[:5])}{'...' if len(county_list) > 5 else ''}"
    )
    print(f"Found {len(ballot_timestamps)} ballots across all counties")

    # Load manifest data and sort by audit board order
    county_data: Dict[str, List[Tuple[int, datetime]]] = {}

    for county in county_list:
        print(f"\nProcessing {county}...")
        try:
            manifest_path = resolve_manifest_path(county)
            manifest_entries = load_manifest_entries(manifest_path)
            print(f"  Loaded {len(manifest_entries)} entries from manifest")
        except (FileNotFoundError, ValueError) as e:
            print(f"  Warning: {e}")
            continue

        # Collect ballots for this county with their sort keys
        sortable = []
        for (c, imprinted_id), data in ballot_timestamps.items():
            if c != county:
                continue

            entry = manifest_entries.get(imprinted_id)
            if not entry:
                # Try to parse from imprinted_id if not in manifest
                parts = imprinted_id.split("-")
                if len(parts) == 3:
                    entry = {
                        "location": "",
                        "tabulator": parts[0],
                        "batch": parts[1],
                        "position": parts[2],
                    }
                else:
                    continue

            # Create sort key: location (natural), tabulator, batch, position
            try:
                sortable.append(
                    (
                        natural_sort_key(entry["location"]),
                        (
                            int(entry["tabulator"])
                            if entry["tabulator"].isdigit()
                            else entry["tabulator"]
                        ),
                        int(entry["batch"]) if entry["batch"].isdigit() else entry["batch"],
                        (
                            int(entry["position"])
                            if entry["position"].isdigit()
                            else entry["position"]
                        ),
                        imprinted_id,
                        data["timestamp"],
                    )
                )
            except (ValueError, AttributeError):
                continue

        # Sort by audit board order
        sortable.sort(key=lambda x: (x[0], x[1], x[2], x[3]))

        # Assign sequence numbers and extract timestamps
        sequence_data = []
        for seq_num, (_, _, _, _, imprinted_id, timestamp) in enumerate(sortable, start=1):
            sequence_data.append((seq_num, timestamp))

        county_data[county] = sequence_data
        print(f"  {len(sequence_data)} ballots sorted and sequenced")

    return county_data, county_list


@app.command(name="grid")
def main(
    counties: str = typer.Option(
        None,
        "--counties",
        "-c",
        help="Comma-separated list of counties (default: all counties in data)",
    ),
) -> None:
    """Plot sequence number vs timestamp for selected counties in a grid layout."""
    county_data, county_list = load_and_process_county_data(counties)

    # Create plot
    n_counties = len(county_data)
    if n_counties == 0:
        print("No data to plot!")
        return

    # Use 7x10 grid for all counties
    rows, cols = 7, 10

    fig, axes = plt.subplots(rows, cols, figsize=(20, 14))
    axes = axes.flatten()

    # Sort counties alphabetically for consistent ordering
    sorted_counties = sorted(county_data.items())

    for idx, (county, data) in enumerate(sorted_counties):
        ax = axes[idx]

        if not data:
            ax.text(
                0.5,
                0.5,
                f"{county}\nNo data",
                ha="center",
                va="center",
                transform=ax.transAxes,
                fontsize=12,
            )
            ax.set_xlabel("")
            ax.set_ylabel("")
            continue

        sequences, timestamps = zip(*data)

        # Labels (smaller for grid)
        ax.set_title(f"{county}\n({len(data)} ballots)", fontsize=8, fontweight="bold")

        # Only label axes on edges
        if idx >= (rows - 1) * cols:  # Bottom row
            ax.set_xlabel("Sequence", fontsize=7)
        if idx % cols == 0:  # Left column
            ax.set_ylabel("Time", fontsize=7)

        # Format timestamp axis (smaller fonts for grid)
        ax.tick_params(axis="x", labelsize=6)
        ax.tick_params(axis="y", labelsize=5)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=0)
        plt.setp(ax.yaxis.get_majorticklabels(), rotation=45, ha="right")

        # Format y-axis to show date/time more clearly (fewer ticks for small plots)
        ax.yaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.yaxis.set_major_locator(mdates.HourLocator(interval=4))

        # Smaller scatter points for grid
        ax.scatter(sequences, timestamps, alpha=0.6, s=5, color="steelblue")

        # Grid
        ax.grid(alpha=0.3, linestyle="--", axis="both")

    # Hide extra subplots
    for idx in range(n_counties, rows * cols):
        axes[idx].set_visible(False)

    plt.tight_layout()

    output_file = OUTPUT_DIR / "sequence_vs_timestamp_by_county.png"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    print(f"\n✓ Saved plot to {output_file}")
    plt.close()


@app.command(name="combined")
def plot_combined(
    counties: str = typer.Option(
        None,
        "--counties",
        "-c",
        help="Comma-separated list of counties (default: all counties in data)",
    ),
) -> None:
    """Plot all counties on a single plot with different colors."""
    county_data, county_list = load_and_process_county_data(counties)

    # Create plot
    n_counties = len(county_data)
    if n_counties == 0:
        print("No data to plot!")
        return

    fig, ax = plt.subplots(figsize=(16, 10))

    # Generate distinct colors for each county
    # Use a colormap that gives good color separation
    cmap = cm.get_cmap("tab20")
    colors = [cmap(i / max(n_counties, 1)) for i in range(n_counties)]

    # Sort counties for consistent color assignment
    sorted_counties = sorted(county_data.items())

    # Plot each county
    for idx, (county, data) in enumerate(sorted_counties):
        if not data:
            continue

        sequences, timestamps = zip(*data)
        color = colors[idx % len(colors)]

        # Plot with county label for legend
        ax.scatter(
            sequences,
            timestamps,
            alpha=0.5,
            s=10,
            color=color,
            label=f"{county} ({len(data)})",
        )

    # Format timestamp axis
    ax.tick_params(axis="x", labelsize=10)
    ax.tick_params(axis="y", labelsize=9)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0)
    plt.setp(ax.yaxis.get_majorticklabels(), rotation=45, ha="right")

    # Format y-axis to show date/time
    ax.yaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    ax.yaxis.set_major_locator(mdates.HourLocator(interval=2))

    # Labels and title
    ax.set_xlabel("Sequence Number", fontsize=12, fontweight="bold")
    ax.set_ylabel("Timestamp", fontsize=12, fontweight="bold")
    ax.set_title(
        f"Sequence vs Timestamp for All Counties\n({n_counties} counties, {sum(len(data) for data in county_data.values())} total ballots)",
        fontsize=14,
        fontweight="bold",
    )

    # Grid
    ax.grid(alpha=0.3, linestyle="--", axis="both")

    # Legend - place outside the plot area
    # For many counties, use a multi-column legend with smaller font
    if n_counties > 40:
        ncol = 4
        fontsize = 5
    elif n_counties > 25:
        ncol = 3
        fontsize = 6
    else:
        ncol = 2
        fontsize = 7

    ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.02, 1),
        fontsize=fontsize,
        ncol=ncol,
        framealpha=0.9,
        markerscale=0.8,
        columnspacing=0.5,
    )

    plt.tight_layout()

    output_file = OUTPUT_DIR / "sequence_vs_timestamp_combined.png"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    # Save with extra space for legend
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    print(f"\n✓ Saved combined plot to {output_file}")
    plt.close()


if __name__ == "__main__":
    app()
