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

from .db_schema import create_schema


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


def main():  # pragma: no cover - Typer entrypoint
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
