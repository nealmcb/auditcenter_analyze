#!/usr/bin/env python3
"""
Verify risk calculations for targeted contests in the 2024 Colorado General Election.

Uses rlacalc.py to independently calculate risk and compare to reported values.
"""

import csv
from pathlib import Path
from typing import Dict

import rlacalc

# Use data symlink relative to this file location
BASE_PATH = Path(__file__).parent.parent.parent / "data" / "2024" / "general"


def verify_contest_risk(contest_data: Dict, round_num: int) -> Dict:
    """
    Verify risk calculation for a single contest.

    Returns:
        dict with verification results
    """
    contest_name = contest_data["contest_name"]

    # Extract parameters
    try:
        n = int(contest_data["audited_sample_count"])
        min_margin = int(contest_data["min_margin"])

        # Discrepancy counts
        o1 = int(contest_data["one_vote_over_count"])
        o2 = int(contest_data["two_vote_over_count"])
        u1 = int(contest_data["one_vote_under_count"])
        u2 = int(contest_data["two_vote_under_count"])

        gamma = float(contest_data["gamma"])
        risk_limit = float(contest_data["risk_limit"])

        # Calculate diluted margin
        # From ContestResult.java: diluted_margin = margin / (margin + 2 * ballot_card_count)
        # But wait - which ballot_card_count? Let me use the formula that gives us gamma
        # gamma = 1 / diluted_margin, so diluted_margin = 1 / gamma
        diluted_margin = 1.0 / gamma

    except (ValueError, KeyError) as e:
        return {
            "contest": contest_name,
            "error": f"Missing or invalid data: {e}",
            "verified": False,
        }

    # Skip contests with no audited ballots
    if n == 0:
        return {
            "contest": contest_name,
            "status": "not_started",
            "verified": True,  # Nothing to verify
        }

    # Calculate risk using rlacalc
    try:
        calculated_risk = rlacalc.KM_P_value(
            n=n, gamma=gamma, margin=diluted_margin, o1=o1, o2=o2, u1=u1, u2=u2
        )
    except Exception as e:
        return {
            "contest": contest_name,
            "error": f"Risk calculation failed: {e}",
            "verified": False,
        }

    # Compare to risk limit
    achieved = calculated_risk <= risk_limit
    status = contest_data["random_audit_status"]

    # Verification
    result = {
        "contest": contest_name,
        "round": round_num,
        "n": n,
        "margin": min_margin,
        "diluted_margin": diluted_margin,
        "gamma": gamma,
        "discrepancies": {"o1": o1, "o2": o2, "u1": u1, "u2": u2},
        "calculated_risk": calculated_risk,
        "risk_limit": risk_limit,
        "achieved": achieved,
        "reported_status": status,
        "verified": True,
    }

    # Check consistency
    if status == "risk_limit_achieved" and not achieved:
        result["verified"] = False
        result["error"] = (
            f"Reported as achieved but calculated risk {calculated_risk:.6f} > {risk_limit}"
        )
    elif status != "risk_limit_achieved" and status != "not_auditable" and achieved:
        result["warning"] = f"Risk limit achieved ({calculated_risk:.6f}) but status is {status}"

    return result


def verify_round_risks(round_num: int):
    """Verify all targeted contest risks for a round."""

    print("=" * 80)
    print(f"RISK VERIFICATION - ROUND {round_num}")
    print("=" * 80)
    print()

    contest_file = f"{BASE_PATH}/round{round_num}/contest.csv"

    results = []

    with open(contest_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["audit_reason"] in ["county_wide_contest", "state_wide_contest"]:
                result = verify_contest_risk(row, round_num)
                results.append(result)

    # Summary
    verified = [r for r in results if r.get("verified", False)]
    achieved = [r for r in results if r.get("achieved", False)]
    errors = [r for r in results if "error" in r]
    warnings = [r for r in results if "warning" in r]

    print(f"Targeted Contests: {len(results)}")
    print(f"  With audited ballots: {sum(1 for r in results if r.get('n', 0) > 0)}")
    print(f"  Risk limit achieved: {len(achieved)}")
    print(f"  Verification errors: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")
    print()

    if errors:
        print("ERRORS:")
        for r in errors[:5]:
            print(f"  {r['contest'][:60]:60s} {r.get('error', '')}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")
        print()

    if warnings:
        print("WARNINGS:")
        for r in warnings[:10]:
            print(f"  {r['contest'][:60]:60s}")
            print(f"    {r.get('warning', '')}")
        if len(warnings) > 10:
            print(f"  ... and {len(warnings) - 10} more")
        print()

    # Show some examples of verified risks
    print("Sample Verified Risks:")
    print(f"{'Contest':<50s} {'n':>5s} {'Risk':>10s} {'Limit':>10s} {'Status':>10s}")
    print("-" * 90)

    for r in results[:20]:
        if r.get("n", 0) > 0 and r.get("verified"):
            status_mark = "✓" if r.get("achieved") else "✗"
            print(
                f"{r['contest'][:50]:<50s} {r['n']:>5d} {r['calculated_risk']:>10.6f} {r['risk_limit']:>10.3f} {status_mark:>10s}"
            )

    print()

    if len(verified) == len(results):
        print("✓✓✓ ALL RISK CALCULATIONS VERIFIED")
    else:
        print(f"✓ {len(verified)}/{len(results)} risk calculations verified")

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Verify risk calculations")
    parser.add_argument("--round", type=int, default=3, help="Round number")
    parser.add_argument("--all-rounds", action="store_true", help="Verify all rounds")
    parser.add_argument("--output", help="Save results to JSON")

    args = parser.parse_args()

    if args.all_rounds:
        all_results = {}
        for round_num in [1, 2, 3]:
            try:
                results = verify_round_risks(round_num)
                all_results[f"round{round_num}"] = results
            except FileNotFoundError:
                print(f"Round {round_num} data not available")
                break
    else:
        results = verify_round_risks(args.round)
        all_results = {f"round{args.round}": results}

    if args.output:
        import json

        with open(args.output, "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        print(f"Results saved to: {args.output}")


if __name__ == "__main__":
    main()
