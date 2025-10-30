#!/usr/bin/env python3
"""CLI to import auditcenter CSVs into a normalized SQLite database.

Phases implemented in this initial version:
 - Create schema
 - Provide dry-run scan and summary

Later phases will add concrete loaders per CSV.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import typer

try:
    from .db_schema import create_schema
    from .csv_loaders import (
        import_counties_and_manifests,
        import_contests_and_contest_counties,
        import_vote_totals,
        import_seed,
        import_round_data,
    )
except ImportError:
    # Fallback for when run as a script (not as a module)
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from auditcenter_analyze.db_schema import create_schema
    from auditcenter_analyze.csv_loaders import (
        import_counties_and_manifests,
        import_contests_and_contest_counties,
        import_vote_totals,
        import_seed,
        import_round_data,
    )


app = typer.Typer(add_completion=False, help="Import auditcenter CSVs to SQLite")


def open_connection(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path))
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


@app.command()
def init_db(
    db: Path = typer.Option(
        Path("output/colorado_rla.db"), exists=False, dir_okay=False, help="Target SQLite DB"
    ),
):
    """Create the SQLite schema (idempotent)."""
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = open_connection(db)
    create_schema(conn)
    typer.echo(f"Initialized schema at {db}")


@app.command()
def scan(
    data_dir: Path = typer.Option(
        Path("data/2024/general"), exists=True, file_okay=False, help="Root of auditcenter data"
    ),
    rounds: str = typer.Option("1,2,3", help="Comma-separated rounds to include"),
):
    """Dry-run: scan CSV availability and print a summary."""
    round_list = [r.strip() for r in rounds.split(",") if r.strip()]

    paths = {
        "manifests": data_dir / "ballotManifests",
        "contestsByCounty": data_dir / "contestsByCounty.csv",
        "tabulate": data_dir / "tabulate.csv",
        "tabulateCounty": data_dir / "tabulateCounty.csv",
        "seed": data_dir / "seed.csv",
    }

    for name, p in paths.items():
        typer.echo(f"{name:18s}: {'OK' if p.exists() else 'MISSING'} -> {p}")

    for r in round_list:
        base = data_dir / f"round{r}"
        for fname in ("contest.csv", "contestComparison.csv", "contestSelection.csv"):
            path = base / fname
            typer.echo(f"round{r}/{fname:20s}: {'OK' if path.exists() else 'MISSING'} -> {path}")


@app.command()
def import_all(
    db: Path = typer.Option(
        Path("output/colorado_rla.db"), dir_okay=False, help="Target SQLite DB"
    ),
    data_dir: Path = typer.Option(
        Path("data/2024/general"), exists=True, file_okay=False, help="Root of auditcenter data"
    ),
    rounds: str = typer.Option("1,2,3", help="Comma-separated rounds to include"),
):
    """Import all CSV files into the database."""
    # Create schema if doesn't exist
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = open_connection(db)
    create_schema(conn)

    # Step 1: Import counties and manifests
    typer.echo("Step 1: Loading counties and manifests...")
    manifests_dir = data_dir / "ballotManifests"
    county_map = import_counties_and_manifests(conn, manifests_dir, progress_callback=typer.echo)
    typer.echo(f"  ✓ Loaded {len(county_map)} counties\n")

    # Step 2: Import contests and contest-county mappings
    typer.echo("Step 2: Loading contests...")
    contests_by_county_file = data_dir / "contestsByCounty.csv"
    contest_map = import_contests_and_contest_counties(
        conn, contests_by_county_file, county_map, progress_callback=typer.echo
    )
    typer.echo(f"  ✓ Loaded {len(contest_map)} contests\n")

    # Step 3: Import vote totals
    typer.echo("Step 3: Loading vote totals...")
    tabulate_file = data_dir / "tabulate.csv"
    tabulate_county_file = data_dir / "tabulateCounty.csv"
    import_vote_totals(
        conn,
        tabulate_file,
        tabulate_county_file,
        contest_map,
        county_map,
        progress_callback=typer.echo,
    )
    typer.echo("  ✓ Loaded vote totals\n")

    # Step 4: Import seed (round 1)
    typer.echo("Step 4: Loading random seed...")
    seed_file = data_dir / "seed.csv"
    import_seed(conn, seed_file, round_num=1, progress_callback=typer.echo)
    typer.echo("  ✓ Loaded seed\n")

    # Step 5: Import round-specific data
    round_list = [r.strip() for r in rounds.split(",") if r.strip()]
    for round_num in round_list:
        round_dir = data_dir / f"round{round_num}"
        if round_dir.exists():
            typer.echo(f"Step 5: Loading round {round_num} data...")
            import_round_data(
                conn,
                round_dir,
                int(round_num),
                contest_map,
                county_map,
                progress_callback=typer.echo,
            )
            typer.echo("  ✓ Loaded round data\n")

    conn.close()
    typer.echo(f"✓ Import complete: {db}")


def main():  # pragma: no cover - Typer entrypoint
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
