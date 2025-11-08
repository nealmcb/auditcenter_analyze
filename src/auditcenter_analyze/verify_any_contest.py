#!/usr/bin/env python3
"""
General-purpose random ballot selection verification for 2024 General Election.

Usage:
    python3 verify_any_contest.py --contest "Contest Name" --county "County Name"

Or use the default (Bent County Commissioner-District 1)
"""

import hashlib
import csv
import sys
import argparse
import re
from pathlib import Path
from typing import List, Tuple, Optional


def generate_random_numbers(seed: str, count: int, domain_size: int) -> List[int]:
    """
    Generate pseudo-random numbers using SHA-256.

    Based on: us.freeandfair.corla.crypto.PseudoRandomNumberGenerator
    """
    selections = []
    i = 0

    while len(selections) < count:
        i += 1
        hash_input = f"{seed},{i}"
        hash_output = hashlib.sha256(hash_input.encode("utf-8")).digest()
        int_output = int.from_bytes(hash_output, byteorder="big")
        pick = (int_output % domain_size) + 1
        selections.append(pick)

    return selections


def load_ballot_manifest(manifest_file: str) -> List[Tuple[str, str, str, int]]:
    """Load ballot manifest and create index mapping."""

    def normalize(name: str) -> str:
        return re.sub(r"[^a-z0-9]", "", name.lower())

    def find_column(columns: List[str], candidates: List[str]) -> Optional[str]:
        normalized_map = {normalize(col): col for col in columns if col}
        for candidate in candidates:
            key = normalize(candidate)
            if key in normalized_map:
                return normalized_map[key]
        return None

    with open(manifest_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            return []

    county_col = find_column(fieldnames, ["county"])
    if not county_col:
        raise ValueError(f"Could not find county column in manifest. Columns: {fieldnames}")

    tabulator_col = find_column(
        fieldnames,
        [
            "tabulator",
            "tabulator id",
            "scanner",
            "scanner id",
            "device id",
            "device",
        ],
    )
    if not tabulator_col:
        raise ValueError(f"Could not find tabulator column in manifest. Columns: {fieldnames}")

    batch_col = find_column(
        fieldnames,
        [
            "batch",
            "batch number",
            "batch no",
            "batch id",
            "batch #",
        ],
    )
    if not batch_col:
        raise ValueError(f"Could not find batch column in manifest. Columns: {fieldnames}")

    count_col = find_column(
        fieldnames,
        [
            "# of ballot cards",
            "# of ballots",
            "# of ballot",
            "number of ballots",
            "count",
            "# cards",
            "# ballot cards",
            "# ballots",
            "# of cards",
            "# in batch",
            ". of ballots",
            "#of ballot cards",
            "# of ballot cards",
            "# of ballots cards",
            "# of ballots cards",
        ],
    )
    if not count_col:
        raise ValueError(f"Could not find ballot count column in manifest. Columns: {fieldnames}")

    ballots: List[Tuple[str, str, str, int]] = []
    with open(manifest_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                num_cards = int(row[count_col])
            except (TypeError, ValueError):
                continue

            county = row.get(county_col, "").strip()
            tabulator = row.get(tabulator_col, "").strip()
            batch = row.get(batch_col, "").strip()

            for position in range(1, num_cards + 1):
                ballots.append((county, tabulator, batch, position))

    return ballots


def ballot_to_imprinted_id(county: str, tabulator: str, batch: str, position: int) -> str:
    """Convert ballot tuple to imprinted_id format."""
    return f"{tabulator}-{batch}-{position}"


def get_contest_counties(contest_name: str, base_path: Path) -> List[str]:
    """Return counties in which the contest appears."""
    counties: List[str] = []
    contests_by_county = base_path / "contestsByCounty.csv"

    if contests_by_county.exists():
        with open(contests_by_county, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("contest_name") == contest_name and row.get("county_name"):
                    counties.append(row["county_name"])

    if counties:
        return sorted(set(counties))

    # Fallback to contestComparison data
    for r in [3, 2, 1]:
        comparison_file = base_path / f"round{r}" / "contestComparison.csv"
        if not comparison_file.exists():
            continue
        with open(comparison_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("contest_name") == contest_name and row.get("county_name"):
                    counties.append(row["county_name"])
        if counties:
            break

    return sorted(set(counties))


def resolve_manifest_file(base_path: Path, county_name: str) -> Optional[Path]:
    """Find the manifest file for a county, trying common naming patterns."""

    candidates = [
        f"{county_name}BallotManifest.csv",
        f"{county_name.replace(' ', '')}BallotManifest.csv",
        f"{county_name.replace(' ', '_')}BallotManifest.csv",
        f"{county_name.replace(' ', '-') }BallotManifest.csv",
    ]

    search_roots = [base_path, base_path / "ballotManifests"]

    for root in search_roots:
        for candidate in candidates:
            path = root / candidate
            if path.exists():
                return path

    return None


def find_contest(contest_name: str, contest_file: str) -> Optional[dict]:
    """Find contest in contest.csv file."""
    with open(contest_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["contest_name"] == contest_name:
                return row
    return None


def load_actual_selections(comparison_file: str, contest_name: str) -> List[str]:
    """Load actual ballot selections from contest comparison file."""
    selections = []

    with open(comparison_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["contest_name"] == contest_name:
                selections.append(row["imprinted_id"])

    return selections


def verify_contest(contest_name: str, county: Optional[str] = None, base_path=None) -> bool:
    """
    Verify random ballot selection for a given contest.

    Args:
        contest_name: Name of the contest to verify
        county: County name (for finding manifest), can be inferred from contest name
        base_path: Base path to audit data

    Returns:
        True if verification successful, False otherwise
    """

    # Set default path if not provided
    if base_path is None:
        base_path = Path(__file__).parent.parent.parent / "data" / "2024" / "general"

    SEED = "53417960661093690826"

    print("=" * 80)
    print("RANDOM BALLOT SELECTION VERIFICATION")
    print("=" * 80)
    print(f"Contest: {contest_name}")
    if county:
        print(f"County: {county}")
    print()

    # Find contest in round 3, 2, or 1 (use latest available)
    contest_data = None
    round_num = None

    for r in [3, 2, 1]:
        contest_file = f"{base_path}/round{r}/contest.csv"
        try:
            contest_data = find_contest(contest_name, contest_file)
            if contest_data:
                round_num = r
                print(f"✓ Found contest data in round {r}")
                break
        except FileNotFoundError:
            continue

    if not contest_data:
        print(f"✗ ERROR: Could not find contest '{contest_name}' in any round")
        return False

    # Extract parameters
    ballot_card_count = int(contest_data["ballot_card_count"])
    contest_ballot_card_count = int(contest_data["contest_ballot_card_count"])
    audited_sample_count = int(contest_data["audited_sample_count"])
    status = contest_data["random_audit_status"]

    print(f"  Status: {status}")
    print(f"  County Ballot Card Count: {ballot_card_count:,}")
    print(f"  Contest Ballot Card Count: {contest_ballot_card_count:,}")
    print(f"  Audited Sample Count: {audited_sample_count}")
    print()

    # Check if any ballots were examined
    # Note: audited_sample_count may be 0 for opportunistic contests even if ballots were examined
    # We need to check contestComparison.csv for the actual count
    audit_reason = contest_data["audit_reason"]

    if audited_sample_count == 0:
        # Check if this is opportunistic - may have examined ballots anyway
        if audit_reason == "opportunistic_benefits":
            # Check contestComparison.csv for actual examined ballots
            comparison_file = f"{base_path}/round{round_num}/contestComparison.csv"
            actual_examined = 0
            try:
                with open(comparison_file, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row["contest_name"] == contest_name and row.get("county_name") == county:
                            actual_examined += 1
            except FileNotFoundError:
                pass

            if actual_examined > 0:
                print(
                    "ℹ NOTE: This contest was NOT targeted for RLA (audit_reason = opportunistic_benefits)"
                )
                print(
                    f"  BUT {actual_examined} ballot cards with this contest were examined opportunistically"
                )
                print("  (appeared on ballots pulled for other targeted contests).")
                print()
                print(
                    "  The contest.csv shows audited_sample_count = 0 because the contest wasn't targeted,"
                )
                print(
                    f"  but we can see from contestComparison.csv that {actual_examined} ballots were examined."
                )
                print()
                print(
                    "  Random selection verification: The ballots were selected for a DIFFERENT contest."
                )
                print(
                    "  To verify selection, you would need to identify which targeted contest drove the selection."
                )
                print()

                # Could calculate what sample size would have been if targeted
                try:
                    diluted_margin = float(contest_data["min_margin"]) / (
                        float(contest_data["min_margin"]) + 2 * contest_ballot_card_count
                    )
                    gamma = 1 / diluted_margin
                    import math

                    risk_limit = 0.03
                    estimated_sample = math.ceil(-2 * gamma * math.log(risk_limit) / diluted_margin)
                    print(
                        "  If this contest HAD been targeted for RLA, the estimated sample size would have been:"
                    )
                    print(
                        f"    ~{estimated_sample} ballots (based on margin of {contest_data['min_margin']})"
                    )
                except Exception:
                    pass

                print()
                return False

        print("⚠ WARNING: This contest has audited_sample_count = 0 in contest.csv.")
        print("  No physical ballots were specifically selected for this contest.")
        print()
        print("  Possible reasons:")
        print("    - Not targeted for RLA (audit_reason != county_wide_contest/state_wide_contest)")
        print("    - Targeted but not yet started")
        print("    - Ended in an earlier round with no ballots examined")
        print()
        return False

    # Determine county coverage
    contest_counties = get_contest_counties(contest_name, base_path)
    multi_county = len(contest_counties) > 1
    domain_size = contest_ballot_card_count

    if multi_county:
        print("ℹ Detected multi-county contest. Trying alphabetical manifest combination...")
        print(f"  Counties involved ({len(contest_counties)}): {', '.join(contest_counties)}")

        combined_manifest: List[Tuple[str, str, str, int]] = []
        unresolved_counties: List[str] = []

        for county_name in contest_counties:
            manifest = resolve_manifest_file(base_path, county_name)
            if not manifest:
                unresolved_counties.append(county_name)
                continue

            try:
                ballots = load_ballot_manifest(str(manifest))
            except Exception as exc:
                print(f"  ✗ Failed to load manifest for {county_name}: {exc}")
                unresolved_counties.append(county_name)
                continue

            combined_manifest.extend(ballots)

        if unresolved_counties:
            print(
                f"  ⚠ Could not load manifests for: {', '.join(unresolved_counties)}. Aborting verification."
            )
            return False

        print(f"  ✓ Combined manifest size: {len(combined_manifest):,} ballot cards")
        if contest_ballot_card_count > len(combined_manifest):
            print(
                f"  ⚠ Contest ballot card count ({contest_ballot_card_count:,}) exceeds combined manifest size."
            )

        first_two = generate_random_numbers(SEED, 2, contest_ballot_card_count)
        print(f"  First two selections (contest domain): {first_two}")

        mapped = []
        for pick in first_two:
            if pick <= len(combined_manifest):
                county_name, tabulator, batch, position = combined_manifest[pick - 1]
                mapped.append(
                    (county_name, ballot_to_imprinted_id(county_name, tabulator, batch, position))
                )
            else:
                mapped.append(("OUT_OF_RANGE", f"index:{pick}"))

        comparison_file = f"{base_path}/round{round_num}/contestComparison.csv"
        try:
            actual_imprinted_ids = set(load_actual_selections(comparison_file, contest_name))
        except Exception:
            actual_imprinted_ids = set()

        for idx, (county_name, imprint) in enumerate(mapped, start=1):
            if county_name == "OUT_OF_RANGE":
                print(f"  ✗ Selection #{idx}: index {imprint} exceeds combined manifest size")
            else:
                status = "MATCH" if imprint in actual_imprinted_ids else "not found"
                print(f"  Selection #{idx}: {county_name} -> {imprint} ({status})")

        print()
        print(
            "✗ ERROR: Multi-county contest verification requires confirmed manifest ordering and contest presence per ballot."
        )
        print(
            "  The alphabetical combination attempt above shows the assumed ordering does not currently reconcile with audited selections."
        )
        return False

    # Single-county contests
    if not county:
        if contest_counties:
            county = contest_counties[0]
        else:
            contest_lower = contest_name.lower()
            if " county " in contest_lower:
                parts = contest_name.split(" County ")
                county = parts[0].split()[-1]
            elif contest_lower.startswith("bent "):
                county = "Bent"
            elif contest_lower.startswith("adams "):
                county = "Adams"

    if not county:
        print("✗ ERROR: Please specify --county parameter")
        return False

    manifest_path = resolve_manifest_file(base_path, county)
    if not manifest_path:
        print(f"✗ ERROR: Could not locate manifest file for {county} County")
        return False

    try:
        print(f"Loading manifest: {manifest_path}")
        ballot_manifest = load_ballot_manifest(str(manifest_path))
        print(f"✓ Loaded {len(ballot_manifest):,} ballot cards from manifest")
    except FileNotFoundError:
        print(f"✗ ERROR: Could not find manifest file: {manifest_path}")
        return False

    if len(ballot_manifest) != ballot_card_count:
        print(
            f"⚠ WARNING: Manifest has {len(ballot_manifest)} cards, county reports {ballot_card_count}"
        )

    if contest_ballot_card_count != ballot_card_count:
        print(f"ℹ NOTE: This is a DISTRICT-LEVEL contest within {county} County.")
        print(
            f"  Contest appears on {contest_ballot_card_count:,} of {ballot_card_count:,} ballot cards."
        )
        print()
        print(
            "  For single-county contests, random selection uses the FULL county ballot card count"
        )
        print(
            f"  as the domain [1, {ballot_card_count:,}], and some selected ballots will have this contest."
        )
        print()
        print(f"  Proceeding with verification using domain [1, {ballot_card_count:,}]...")
        print()
        domain_size = ballot_card_count
    print()

    # Generate random selections using contest domain size
    print(f"Generating {audited_sample_count} random selections from domain [1, {domain_size}]...")
    random_selections = generate_random_numbers(SEED, audited_sample_count, domain_size)
    print("✓ Generated selections")
    print(f"  First 5: {random_selections[:5]}")
    if audited_sample_count > 5:
        print(f"  Last:    {random_selections[-1]}")
    print()

    # Map to imprinted IDs
    print("Mapping to ballot cards...")
    expected_imprinted_ids = []

    for selection in random_selections:
        if selection > len(ballot_manifest):
            print(f"✗ ERROR: Selection {selection} exceeds manifest size {len(ballot_manifest)}")
            return False

        county_name, tabulator, batch, position = ballot_manifest[selection - 1]
        imprinted_id = ballot_to_imprinted_id(county_name, tabulator, batch, position)
        expected_imprinted_ids.append(imprinted_id)

    print("✓ Mapped all selections")
    print()

    # Load actual selections
    comparison_file = f"{base_path}/round{round_num}/contestComparison.csv"
    print(f"Loading actual selections from round {round_num}...")
    try:
        actual_imprinted_ids = load_actual_selections(comparison_file, contest_name)
        print(f"✓ Loaded {len(actual_imprinted_ids)} actual selections")
    except Exception as e:
        print(f"✗ ERROR: Could not load actual selections: {e}")
        return False
    print()

    # Compare
    print("=" * 80)
    print("VERIFICATION RESULTS")
    print("=" * 80)

    expected_sorted = sorted(expected_imprinted_ids)
    actual_sorted = sorted(actual_imprinted_ids)

    if expected_sorted == actual_sorted:
        print("✓✓✓ VERIFICATION SUCCESSFUL ✓✓✓")
        print()
        print("All ballot selections match the expected random selections!")
        print(f"Verified {len(expected_sorted)} ballots using seed {SEED}")
        return True
    else:
        print("✗✗✗ VERIFICATION FAILED ✗✗✗")
        print()

        expected_set = set(expected_sorted)
        actual_set = set(actual_sorted)

        missing = expected_set - actual_set
        extra = actual_set - expected_set
        matching = len(expected_set & actual_set)

        print(f"Matching: {matching} / {len(expected_sorted)}")

        if missing:
            print(f"\nExpected but NOT in audit ({len(missing)}):")
            for ballot in sorted(missing)[:10]:
                print(f"  - {ballot}")
            if len(missing) > 10:
                print(f"  ... and {len(missing) - 10} more")

        if extra:
            print(f"\nIn audit but NOT expected ({len(extra)}):")
            for ballot in sorted(extra)[:10]:
                print(f"  + {ballot}")
            if len(extra) > 10:
                print(f"  ... and {len(extra) - 10} more")

        return False


def list_counties(base_path: str):
    """List all counties that have data in contestComparison.csv"""
    counties = set()

    for r in [3, 2, 1]:
        comparison_file = f"{base_path}/round{r}/contestComparison.csv"
        try:
            with open(comparison_file, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if "county_name" in row:
                        counties.add(row["county_name"])
            break  # Use most recent round
        except FileNotFoundError:
            continue

    print("Counties with audit data:")
    print("-" * 80)
    for county in sorted(counties):
        print(f"  {county}")
    print(f"\nTotal: {len(counties)} counties")


def list_contests_for_county(county: str, base_path: str, targeted_only: bool = False):
    """List all contests that had ballots examined in a given county

    Args:
        county: County name
        base_path: Path to audit data
        targeted_only: If True, only show contests targeted for RLA (county_wide_contest/state_wide_contest)
    """
    # Get contests from comparison data
    contests = {}

    for r in [3, 2, 1]:
        comparison_file = f"{base_path}/round{r}/contestComparison.csv"
        try:
            with open(comparison_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if "county_name" in row and row["county_name"] == county:
                        contest = row["contest_name"]
                        if contest not in contests:
                            contests[contest] = 0
                        contests[contest] += 1
            break  # Use most recent round
        except FileNotFoundError:
            continue

    # Get audit reasons from contest data
    contest_info = {}
    for r in [3, 2, 1]:
        contest_file = f"{base_path}/round{r}/contest.csv"
        try:
            with open(contest_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    contest_name = row["contest_name"]
                    if contest_name in contests:
                        contest_info[contest_name] = {
                            "audit_reason": row["audit_reason"],
                            "status": row["random_audit_status"],
                        }
            break
        except FileNotFoundError:
            continue

    if not contests:
        print(f"No contests with examined ballots found for {county} County")
        return

    # Filter if targeted_only
    if targeted_only:
        contests = {
            k: v
            for k, v in contests.items()
            if k in contest_info
            and contest_info[k]["audit_reason"] in ["county_wide_contest", "state_wide_contest"]
        }
        if not contests:
            print(f"No contests targeted for RLA in {county} County")
            return
        print(f"Contests TARGETED for RLA in {county} County:")
    else:
        print(f"Contests with examined ballots in {county} County:")

    print("-" * 80)
    for contest, count in sorted(contests.items(), key=lambda x: x[1], reverse=True):
        if contest in contest_info:
            reason = contest_info[contest]["audit_reason"]
            if reason == "county_wide_contest":
                marker = "[TARGETED]"
            elif reason == "state_wide_contest":
                marker = "[STATE RLA]"
            elif reason == "opportunistic_benefits":
                marker = "[opportunistic]"
            else:
                marker = f"[{reason}]"
            print(f"  {contest:55s} {marker:18s} ({count:3d} ballots)")
        else:
            print(f"  {contest:70s} ({count:3d} ballots)")
    print(f"\nTotal: {len(contests)} contests with examined ballots")

    if not targeted_only:
        targeted_count = sum(
            1
            for c in contests.keys()
            if c in contest_info
            and contest_info[c]["audit_reason"] in ["county_wide_contest", "state_wide_contest"]
        )
        print(
            f"  {targeted_count} were targeted for RLA (county_wide_contest or state_wide_contest)"
        )
        print(
            f"  {len(contests) - targeted_count} had opportunistic examination (ballots pulled for other contests)"
        )


def list_counties_for_contest(contest_name: str, base_path: str):
    """List all counties that had ballots audited for a given contest"""
    counties = {}

    for r in [3, 2, 1]:
        comparison_file = f"{base_path}/round{r}/contestComparison.csv"
        try:
            with open(comparison_file, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["contest_name"] == contest_name:
                        if "county_name" in row:
                            county = row["county_name"]
                            if county not in counties:
                                counties[county] = 0
                            counties[county] += 1
            break  # Use most recent round
        except FileNotFoundError:
            continue

    if not counties:
        print(f"No counties found for contest: {contest_name}")
        return

    print(f"Counties with ballots audited for: {contest_name}")
    print("-" * 80)
    for county, count in sorted(counties.items(), key=lambda x: x[1], reverse=True):
        print(f"  {county:30s} ({count:3d} ballots)")
    print(f"\nTotal: {len(counties)} counties")


def main():
    parser = argparse.ArgumentParser(
        description="Verify random ballot selection for 2024 General Election contests"
    )
    parser.add_argument(
        "--contest",
        default="Bent County Commissioner-District 1",
        help="Contest name (must match exactly as in contest.csv)",
    )
    parser.add_argument(
        "--county", default=None, help="County name for manifest file (e.g., 'Bent', 'Adams')"
    )
    parser.add_argument("--list-contests", action="store_true", help="List all available contests")
    parser.add_argument(
        "--list-counties", action="store_true", help="List all counties with audit data"
    )
    parser.add_argument(
        "--list-contests-for-county",
        metavar="COUNTY",
        help="List contests that had ballots examined in specified county",
    )
    parser.add_argument(
        "--targeted-only",
        action="store_true",
        help="With --list-contests-for-county, only show contests targeted for RLA",
    )
    parser.add_argument(
        "--list-counties-for-contest",
        metavar="CONTEST",
        help="List counties that had ballots audited for specified contest",
    )

    args = parser.parse_args()

    # Use data symlink relative to this file location
    base_path = Path(__file__).parent.parent.parent / "data" / "2024" / "general"

    # Handle listing options
    if args.list_contests:
        print("Available contests in round 1:")
        print("-" * 80)
        with open(f"{base_path}/round1/contest.csv", "r") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 1):
                status = row["random_audit_status"]
                print(f"{i:3d}. {row['contest_name']:60s} [{status}]")
        return

    if args.list_counties:
        list_counties(base_path)
        return

    if args.list_contests_for_county:
        list_contests_for_county(args.list_contests_for_county, base_path, args.targeted_only)
        return

    if args.list_counties_for_contest:
        list_counties_for_contest(args.list_counties_for_contest, base_path)
        return

    # Infer county from contest name if not provided
    county = args.county
    if not county:
        contest_lower = args.contest.lower()
        # Extract county name from contest
        if " county " in contest_lower:
            parts = args.contest.split(" County ")
            county = parts[0].split()[-1]
        elif contest_lower.startswith("bent "):
            county = "Bent"
        elif contest_lower.startswith("adams "):
            county = "Adams"
        # Add more as needed

    success = verify_contest(args.contest, county)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
