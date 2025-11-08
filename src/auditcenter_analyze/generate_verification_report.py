#!/usr/bin/env python3
"""
Generate comprehensive verification report for a targeted RLA contest.

This report demonstrates the complete cryptographic chain from seed to selected ballots,
showing how anyone can independently verify the random ballot selection process.

Usage:
    python3 generate_verification_report.py --contest "Crowley County Commissioner - District 3"
    python3 generate_verification_report.py --contest-id 198
"""

import hashlib
import sqlite3
import sys
from pathlib import Path
from typing import Optional
import argparse

# Import verification functions from existing scripts
try:
    from auditcenter_analyze.verify_any_contest import (
        load_ballot_manifest,
        ballot_to_imprinted_id,
    )
except ImportError:
    # Handle direct script execution
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from auditcenter_analyze.verify_any_contest import (
        load_ballot_manifest,
        ballot_to_imprinted_id,
    )


def get_sha256_hex(hash_input: str) -> str:
    """Generate SHA-256 hash and return as hex string."""
    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()


def generate_random_number_verbose(seed: str, index: int, domain_size: int) -> dict:
    """Generate a single random number with full cryptographic details."""
    hash_input = f"{seed},{index}"
    hash_output = hashlib.sha256(hash_input.encode("utf-8")).digest()
    hash_hex = hash_output.hex()
    int_output = int.from_bytes(hash_output, byteorder="big")
    pick = (int_output % domain_size) + 1

    return {
        "index": index,
        "hash_input": hash_input,
        "hash_hex": hash_hex,
        "hash_int": int_output,
        "modulo": int_output % domain_size,
        "result": pick,
    }


def load_contest_from_db(
    db_path: Path, contest_name: Optional[str] = None, contest_id: Optional[int] = None
) -> Optional[dict]:
    """Load contest data from database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if contest_id:
        c.execute("SELECT * FROM contests WHERE contest_id = ?", (contest_id,))
    elif contest_name:
        c.execute("SELECT * FROM contests WHERE name = ?", (contest_name,))
    else:
        return None

    row = c.fetchone()
    if not row:
        conn.close()
        return None

    contest = dict(row)

    # Get vote totals
    c.execute(
        """
        SELECT choice, votes, source
        FROM vote_totals
        WHERE contest_id = ?
        AND source = 'tabulateCounty'
        ORDER BY votes DESC
    """,
        (contest["contest_id"],),
    )
    vote_totals = [dict(row) for row in c.fetchall()]

    # Get counties
    c.execute(
        """
        SELECT co.county_id, co.name, co.ballot_card_count
        FROM counties co
        JOIN contest_counties cc ON co.county_id = cc.county_id
        WHERE cc.contest_id = ?
    """,
        (contest["contest_id"],),
    )
    counties = [dict(row) for row in c.fetchall()]

    # Get risk analysis
    c.execute(
        """
        SELECT * FROM contest_risk_analysis
        WHERE contest_id = ?
        ORDER BY round DESC
        LIMIT 1
    """,
        (contest["contest_id"],),
    )
    risk_row = c.fetchone()
    risk_analysis = dict(risk_row) if risk_row else None

    # Get county sampling details
    c.execute(
        """
        SELECT * FROM county_sampling_details
        WHERE contest_id = ?
    """,
        (contest["contest_id"],),
    )
    county_details = [dict(row) for row in c.fetchall()]

    # Get actual selected ballots
    c.execute(
        """
        SELECT DISTINCT imprinted_id
        FROM ballot_comparisons
        WHERE contest_id = ?
        ORDER BY imprinted_id
    """,
        (contest["contest_id"],),
    )
    selected_ballots = [row[0] for row in c.fetchall()]

    conn.close()

    contest["vote_totals"] = vote_totals
    contest["counties"] = counties
    contest["risk_analysis"] = risk_analysis
    contest["county_details"] = county_details
    contest["selected_ballots"] = selected_ballots

    return contest


def count_winners(winners_str: Optional[str]) -> int:
    """Count the number of winners from the winners string.
    
    The winners field stores winner names in quotes, possibly multiple.
    Format examples: "Name" or "Name1" "Name2"
    """
    if not winners_str:
        return 0
    # Remove quotes and split by quote-space-quote pattern or just count quoted strings
    # Simple approach: count occurrences of quoted strings
    import re
    quoted_names = re.findall(r'"([^"]+)"', winners_str)
    return len(quoted_names)


def get_seed_from_db(db_path: Path, round_num: int = 3) -> Optional[str]:
    """Get random seed from database.

    Tries the requested round first, then falls back to round 1,
    as the seed is typically stored for round 1 but applies to all rounds.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Try requested round first
    c.execute("SELECT seed FROM audit_random_seed WHERE round = ?", (round_num,))
    row = c.fetchone()

    # Fall back to round 1 if not found
    if not row:
        c.execute("SELECT seed FROM audit_random_seed WHERE round = ?", (1,))
        row = c.fetchone()

    conn.close()
    return row[0] if row else None


def find_manifest_file(county_name: str, data_dir: Path) -> Optional[Path]:
    """Find ballot manifest file for a county."""
    # Try various naming conventions
    possible_names = [
        f"{county_name}BallotManifest.csv",
        f"{county_name}_BallotManifest.csv",
        f"{county_name}-BallotManifest.csv",
        f"{county_name.replace(' ', '')}BallotManifest.csv",
    ]

    manifest_dir = data_dir / "ballotManifests"
    for name in possible_names:
        manifest_file = manifest_dir / name
        if manifest_file.exists():
            return manifest_file

    return None


def generate_report(
    contest: dict, seed: str, manifest_file: Path, output_file: Optional[Path] = None
) -> str:
    """Generate comprehensive verification report in Markdown format."""
    report_lines = []

    # Header
    report_lines.append("# Cryptographic Verification Report")
    report_lines.append(f"**Contest:** {contest['name']}")
    report_lines.append(f"**Contest ID:** {contest['contest_id']}")
    report_lines.append("")
    report_lines.append(
        "This report demonstrates the complete cryptographic chain from random seed"
    )
    report_lines.append(
        "to selected ballots, allowing independent verification of the audit process."
    )
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Section 1: Contest Overview
    report_lines.append("## 1. Contest Overview")
    report_lines.append("")
    report_lines.append(f"- **Contest Name:** {contest['name']}")
    report_lines.append(f"- **Audit Reason:** {contest.get('audit_reason', 'N/A')}")
    num_winners = count_winners(contest.get('winners'))
    report_lines.append(f"- **Number of Winners:** {num_winners}")
    report_lines.append("")
    report_lines.append("### Counties Involved")
    for county in contest["counties"]:
        report_lines.append(
            f"- **{county['name']} County:** {county['ballot_card_count']:,} ballot cards"
        )
    report_lines.append("")
    report_lines.append("### Vote Totals")
    report_lines.append("")
    report_lines.append("| Candidate | Votes |")
    report_lines.append("|-----------|-------|")
    for vt in contest["vote_totals"]:
        report_lines.append(f"| {vt['choice']} | {vt['votes']:,} |")
    report_lines.append("")
    if contest.get("winners"):
        report_lines.append(f"**Winner(s):** {contest['winners']}")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Section 2: Ballot Manifest (moved before RLA inputs per user request)
    report_lines.append("## 2. Ballot Manifest")
    report_lines.append("")
    if contest["counties"]:
        county = contest["counties"][0]
        report_lines.append(f"- **County:** {county['name']}")
        report_lines.append(f"- **Total Ballot Cards:** {county['ballot_card_count']:,}")
        report_lines.append(f"- **Manifest File:** `{manifest_file.name}`")
        report_lines.append("")
        report_lines.append("The manifest file contains batch-level data with:")
        report_lines.append("- Tabulator ID")
        report_lines.append("- Batch number")
        report_lines.append("- Number of ballot cards in each batch")
        report_lines.append("")
        report_lines.append("From this, we create an ordered list of all ballot positions,")
        report_lines.append("each identified by `tabulator-batch-position` (imprinted_id).")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Section 3: RLA Input Parameters
    report_lines.append("## 3. RLA Input Parameters")
    report_lines.append("")
    risk = contest.get("risk_analysis")
    if risk:
        report_lines.append("- **Risk Limit:** 0.03 (3%)")
        report_lines.append("- **Gamma:** 1.03905")
        report_lines.append(f"- **Minimum Margin:** {contest.get('min_margin', 'N/A'):,} votes")
        # For single-county contests, use county ballot_card_count for diluted margin
        if contest["counties"] and len(contest["counties"]) == 1:
            county = contest["counties"][0]
            county_ballot_count = county['ballot_card_count']
            min_margin = contest.get('min_margin', 0)
            if min_margin and county_ballot_count:
                diluted_margin = min_margin / county_ballot_count
                report_lines.append(f"- **County Ballot Card Count:** {county_ballot_count:,}")
                report_lines.append(f"- **Diluted Margin:** {diluted_margin:.6f}")
                report_lines.append(
                    f"  - Calculated as: min_margin / county_ballot_card_count = "
                    f"{min_margin} / {county_ballot_count}"
                )
        else:
            # Multi-county contest - skip for now per user request
            report_lines.append(
                f"- **Contest Ballot Card Count:** {contest.get('contest_ballot_card_count', 'N/A'):,}"
            )
            diluted_margin = contest.get("diluted_margin")
            if diluted_margin:
                report_lines.append(f"- **Diluted Margin:** {diluted_margin:.6f}")
                report_lines.append("  - (Multi-county calculation - see documentation)")
        report_lines.append(f"- **Sample Size:** {risk.get('sample_size', 'N/A')}")
        report_lines.append(f"- **Discrepancies Found:** {risk.get('discrepancies', 'N/A')}")
        risk_value = risk.get('risk_value')
        if risk_value is not None:
            risk_percentage = risk_value * 100
            report_lines.append(f"- **Risk Level:** {risk_percentage:.3f}%")
        else:
            report_lines.append("- **Risk Level:** N/A")
        report_lines.append(
            f"- **Achieved Risk Limit:** {'✓ Yes' if risk.get('achieved_risk_limit') else '✗ No'}"
        )
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Section 4: Sample Size Calculation
    report_lines.append("## 4. Sample Size Calculation")
    report_lines.append("")
    report_lines.append("The sample size is determined using the Kaplan-Markov risk calculation")
    report_lines.append("method, which depends on:")
    report_lines.append(
        "1. The diluted margin (difference between winner and runner-up, divided by total ballots)"
    )
    report_lines.append("2. The risk limit (0.03 = 3%)")
    report_lines.append("3. The gamma parameter (1.03905)")
    report_lines.append("")
    if risk:
        report_lines.append(
            f"For this contest, the required sample size is **{risk.get('sample_size', 'N/A')} ballots**."
        )
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Section 5: Random Seed
    report_lines.append("## 5. Random Seed")
    report_lines.append("")
    report_lines.append(f"**Seed Value:** `{seed}`")
    report_lines.append("")
    report_lines.append("This seed was generated publicly and committed before the audit began.")
    report_lines.append("It ensures that ballot selection cannot be manipulated, as the seed")
    report_lines.append("must have been created after the ballot manifests were finalized.")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Section 6: Cryptographic Selection Process
    report_lines.append("## 6. Cryptographic Selection Process")
    report_lines.append("")
    report_lines.append("Each ballot is selected using the following deterministic process:")
    report_lines.append("")
    report_lines.append("### Algorithm")
    report_lines.append("```")
    report_lines.append("for i in 1 to sample_size:")
    report_lines.append('    hash_input = seed + "," + i')
    report_lines.append("    hash_output = SHA-256(hash_input)")
    report_lines.append("    int_output = interpret_as_big_integer(hash_output)")
    report_lines.append("    selection = (int_output mod domain_size) + 1")
    report_lines.append("```")
    report_lines.append("")
    report_lines.append("### Detailed Calculations")
    report_lines.append("")

    if risk and manifest_file.exists():
        sample_size = risk.get("sample_size", 0)
        contest_ballot_count = contest.get("contest_ballot_card_count", 0)

        # Load manifest to map positions
        try:
            ballot_manifest = load_ballot_manifest(str(manifest_file))
            report_lines.append(f"Showing detailed calculations for all {sample_size} selections:")
            report_lines.append("")

            for i in range(1, min(sample_size + 1, 16)):  # Show first 15 in detail
                calc = generate_random_number_verbose(seed, i, contest_ballot_count)
                county, tabulator, batch, position = ballot_manifest[calc["result"] - 1]
                imprinted_id = ballot_to_imprinted_id(county, tabulator, batch, position)

                report_lines.append(f"#### Selection #{i}")
                report_lines.append("")
                report_lines.append(f"- **Hash Input:** `{calc['hash_input']}`")
                report_lines.append(f"- **SHA-256 Hash:** `{calc['hash_hex']}`")
                report_lines.append(f"- **As Integer:** `{calc['hash_int']}`")
                report_lines.append(
                    f"- **Modulo Operation:** `{calc['hash_int']} mod {contest_ballot_count} = {calc['modulo']}`"
                )
                report_lines.append(f"- **Add 1 (1-indexed):** `{calc['result']}`")
                report_lines.append(
                    f"- **Manifest Position:** Position {calc['result']} in ordered ballot list"
                )
                report_lines.append(
                    f"- **Ballot Details:** Batch {batch}, Position {position} in batch"
                )
                report_lines.append(f"- **Imprinted ID:** `{imprinted_id}`")
                report_lines.append("")

            if sample_size > 15:
                report_lines.append(
                    f"*... (remaining {sample_size - 15} selections calculated using the same process)*"
                )
                report_lines.append("")

                # Show just the results for the rest
                report_lines.append("#### Remaining Selections (Summary)")
                report_lines.append("")
                report_lines.append("| Selection # | Random # | Imprinted ID |")
                report_lines.append("|-------------|----------|--------------|")
                for i in range(16, sample_size + 1):
                    calc = generate_random_number_verbose(seed, i, contest_ballot_count)
                    county, tabulator, batch, position = ballot_manifest[calc["result"] - 1]
                    imprinted_id = ballot_to_imprinted_id(county, tabulator, batch, position)
                    report_lines.append(f"| {i} | {calc['result']} | `{imprinted_id}` |")
                report_lines.append("")
        except Exception as e:
            report_lines.append(f"*Error loading manifest: {e}*")
            report_lines.append("")

    report_lines.append("---")
    report_lines.append("")

    # Section 7: Actual Audit Selections
    report_lines.append("## 7. Actual Audit Selections")
    report_lines.append("")
    report_lines.append("The following ballots were actually examined during the audit:")
    report_lines.append("")
    report_lines.append("| # | Imprinted ID |")
    report_lines.append("|---|--------------|")
    for i, ballot_id in enumerate(contest["selected_ballots"], 1):
        report_lines.append(f"| {i} | `{ballot_id}` |")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Section 8: Verification Results
    report_lines.append("## 8. Verification Results")
    report_lines.append("")

    if risk and manifest_file.exists():
        sample_size = risk.get("sample_size", 0)
        contest_ballot_count = contest.get("contest_ballot_card_count", 0)

        try:
            ballot_manifest = load_ballot_manifest(str(manifest_file))
            expected_ballots = []
            for i in range(1, sample_size + 1):
                calc = generate_random_number_verbose(seed, i, contest_ballot_count)
                county, tabulator, batch, position = ballot_manifest[calc["result"] - 1]
                imprinted_id = ballot_to_imprinted_id(county, tabulator, batch, position)
                expected_ballots.append(imprinted_id)

            expected_sorted = sorted(expected_ballots)
            actual_sorted = sorted(contest["selected_ballots"])

            if expected_sorted == actual_sorted:
                report_lines.append("✓✓✓ **VERIFICATION SUCCESSFUL** ✓✓✓")
                report_lines.append("")
                report_lines.append("All ballot selections match the expected random selections!")
                report_lines.append(f"Verified {len(expected_sorted)} ballots using seed `{seed}`")
                report_lines.append("")
                report_lines.append("This confirms:")
                report_lines.append("- The random selection process was followed correctly")
                report_lines.append("- The cryptographic chain is intact")
                report_lines.append("- Anyone can reproduce these results independently")
            else:
                report_lines.append("✗✗✗ **VERIFICATION FAILED** ✗✗✗")
                report_lines.append("")
                expected_set = set(expected_sorted)
                actual_set = set(actual_sorted)
                missing = expected_set - actual_set
                extra = actual_set - expected_set
                matching = len(expected_set & actual_set)

                report_lines.append(f"Matching: {matching} / {len(expected_sorted)}")
                if missing:
                    report_lines.append(f"\nExpected but NOT in audit ({len(missing)}):")
                    for ballot in sorted(missing)[:10]:
                        report_lines.append(f"- `{ballot}`")
                    if len(missing) > 10:
                        report_lines.append(f"... and {len(missing) - 10} more")
                if extra:
                    report_lines.append(f"\nIn audit but NOT expected ({len(extra)}):")
                    for ballot in sorted(extra)[:10]:
                        report_lines.append(f"- `{ballot}`")
                    if len(extra) > 10:
                        report_lines.append(f"... and {len(extra) - 10} more")
        except Exception as e:
            report_lines.append(f"*Error during verification: {e}*")
    else:
        report_lines.append(
            "*Verification calculation requires manifest file and risk analysis data.*"
        )

    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Section 9: Reproducibility Instructions
    report_lines.append("## 9. Reproducibility Instructions")
    report_lines.append("")
    report_lines.append("To independently verify this audit:")
    report_lines.append("")
    report_lines.append("1. **Retrieve the seed:**")
    report_lines.append("   ```sql")
    report_lines.append(
        f"   SELECT seed FROM audit_random_seed WHERE round = {risk.get('round', 3)};"
    )
    report_lines.append("   ```")
    report_lines.append("")
    report_lines.append("2. **Get contest parameters:**")
    report_lines.append("   ```sql")
    report_lines.append("   SELECT contest_ballot_card_count, min_margin")
    report_lines.append("   FROM contests WHERE contest_id = ?;")
    report_lines.append("   ```")
    report_lines.append("")
    report_lines.append("3. **Load the ballot manifest:**")
    report_lines.append(f"   - File: `{manifest_file.name}`")
    report_lines.append("   - Create ordered list of all ballot positions")
    report_lines.append("")
    report_lines.append("4. **Generate random selections:**")
    report_lines.append("   - For each i from 1 to sample_size:")
    report_lines.append('   - Compute: `SHA-256(seed + "," + i)`')
    report_lines.append("   - Convert to integer and take modulo contest_ballot_card_count")
    report_lines.append("   - Add 1 for 1-indexing")
    report_lines.append("   - Map to ballot position in manifest")
    report_lines.append("")
    report_lines.append("5. **Compare with audit results:**")
    report_lines.append("   ```sql")
    report_lines.append("   SELECT DISTINCT imprinted_id")
    report_lines.append("   FROM ballot_comparisons")
    report_lines.append(f"   WHERE contest_id = {contest['contest_id']}")
    report_lines.append("   ORDER BY imprinted_id;")
    report_lines.append("   ```")
    report_lines.append("")
    report_lines.append("All steps are deterministic and reproducible by anyone with access to:")
    report_lines.append("- The ballot manifest (public record)")
    report_lines.append("- The random seed (publicly committed)")
    report_lines.append("- This verification algorithm (open source)")
    report_lines.append("")

    report = "\n".join(report_lines)

    if output_file:
        output_file.write_text(report)
        print(f"✓ Report written to {output_file}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Generate comprehensive verification report for an RLA contest"
    )
    parser.add_argument("--contest", type=str, help="Contest name (must match database exactly)")
    parser.add_argument("--contest-id", type=int, help="Contest ID from database")
    parser.add_argument(
        "--db",
        type=str,
        default="output/colorado_rla.db",
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/2024/general",
        help="Path to audit center data directory",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: print to stdout)",
    )
    parser.add_argument("--round", type=int, default=3, help="Audit round number")

    args = parser.parse_args()

    if not args.contest and not args.contest_id:
        parser.error("Must specify either --contest or --contest-id")

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"Error: Data directory not found at {data_dir}")
        sys.exit(1)

    # Load contest data
    contest = load_contest_from_db(db_path, contest_name=args.contest, contest_id=args.contest_id)
    if not contest:
        print("Error: Contest not found in database")
        sys.exit(1)

    # Get seed
    seed = get_seed_from_db(db_path, args.round)
    if not seed:
        print(f"Error: Random seed not found in database for round {args.round}")
        sys.exit(1)

    # Find manifest file
    if not contest["counties"]:
        print("Error: No counties found for this contest")
        sys.exit(1)

    county_name = contest["counties"][0]["name"]
    manifest_file = find_manifest_file(county_name, data_dir)
    if not manifest_file:
        print(f"Error: Could not find manifest file for {county_name} County")
        sys.exit(1)

    # Generate report
    output_file = Path(args.output) if args.output else None
    report = generate_report(contest, seed, manifest_file, output_file)

    if not output_file:
        print(report)


if __name__ == "__main__":
    main()
