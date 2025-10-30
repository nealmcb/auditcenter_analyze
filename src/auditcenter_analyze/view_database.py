#!/usr/bin/env python3
"""Launch datasette web interface to explore the audit database."""

import typer
from pathlib import Path
import subprocess

app = typer.Typer(help="Launch datasette web interface for Colorado RLA analysis")


@app.command()
def view(
    db_path: Path = typer.Option(
        None,
        "--db",
        help="Path to SQLite database file (default: output/colorado_rla.db)",
    ),
    metadata: Path = typer.Option(
        None,
        "--metadata",
        help="Path to metadata.json file (default: datasette/metadata.json)",
    ),
    port: int = typer.Option(8001, "--port", "-p", help="Port to run datasette on"),
    host: str = typer.Option(
        "127.0.0.1", "--host", help="Host to bind to (default: 127.0.0.1 for localhost)"
    ),
) -> None:
    """Launch datasette to explore the audit database in a web browser.

    The datasette web interface provides:
    - Browseable tables for contest_risk_analysis and county_sampling_details
    - Sorting, filtering, and faceting capabilities
    - Custom SQL query interface
    - Export to CSV/JSON

    Once launched, open http://localhost:8001 in your browser.
    Press Ctrl+C to stop the server.
    """
    # Resolve default paths relative to this script
    repo_root = Path(__file__).parent.parent.parent

    if db_path is None:
        db_path = repo_root / "output" / "colorado_rla.db"

    if metadata is None:
        metadata = repo_root / "datasette" / "metadata.json"

    # Check if database exists
    if not db_path.exists():
        typer.echo(f"Error: Database not found at {db_path}", err=True)
        typer.echo(
            "Run the analysis first: ./src/auditcenter_analyze/calculate_opportunistic_risk.py"
        )
        raise typer.Exit(1)

    # Check if metadata exists
    if not metadata.exists():
        typer.echo(f"Warning: Metadata file not found at {metadata}", err=True)
        typer.echo("Continuing without metadata file...")
        metadata_path = None
    else:
        metadata_path = str(metadata)

    # Build datasette command
    cmd = ["datasette", str(db_path), "--port", str(port), "--host", host]

    if metadata_path:
        cmd.extend(["--metadata", metadata_path])

    typer.echo(f"Launching datasette on http://{host}:{port}")
    typer.echo(f"Database: {db_path}")
    if metadata_path:
        typer.echo(f"Metadata: {metadata_path}")
    typer.echo("\nPress Ctrl+C to stop the server.\n")

    # Run datasette
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        typer.echo("\nShutting down datasette...")
        raise typer.Exit(0)
    except FileNotFoundError:
        typer.echo(
            "Error: datasette not found. Install with: uv pip install datasette datasette-vega",
            err=True,
        )
        raise typer.Exit(1)
    except subprocess.CalledProcessError:
        # Datasette failed to start - likely "address already in use"
        # Note: We can't easily parse stderr here without suppressing output
        # Just show a helpful message
        typer.echo("\nCould not start datasette. Common causes:", err=True)
        typer.echo(f"  - Datasette already running on port {port}")
        typer.echo(f"  - Another process using port {port}")
        typer.echo(f"\nIf datasette is already running, access it at: http://{host}:{port}")
        typer.echo(f"\nOtherwise, try: lsof -ti:{port} | xargs kill")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
