"""
Regression test: Compare current output to historical baseline.

This test verifies that calculate_opportunistic_risk.py produces
the expected output, showing differences as a diff.

BASELINE: ../colorado-rla-2018/neal_ignore/baseline_output.txt
- Captured before the discrepancy classification bug fix
- Shows Conejos County failing (risk=0.048408)
- Expected difference: Conejos should now pass (risk=0.012797)

WHAT IS MASKED: Database save messages (expected to differ)
WHAT IS SHOWN: All other output including contest results, risk values, summaries
"""

import subprocess
from pathlib import Path
import difflib
import pytest


# Path to baseline output (current correct output)
BASELINE_FILE = Path(__file__).parent / "baseline_output.txt"
SCRIPT_PATH = (
    Path(__file__).parent.parent / "src" / "auditcenter_analyze" / "calculate_opportunistic_risk.py"
)


def run_calculate_risk() -> str:
    """Run calculate_opportunistic_risk.py and return output."""
    result = subprocess.run(
        ["python3", str(SCRIPT_PATH), "--no-db"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout + result.stderr


def get_baseline() -> str:
    """Read baseline output from historical file."""
    if not BASELINE_FILE.exists():
        pytest.skip(f"Baseline file not found: {BASELINE_FILE}")

    with open(BASELINE_FILE, "r", encoding="utf-8") as f:
        return f.read()


def normalize_output(text: str) -> list[str]:
    """Normalize output for comparison by removing variable parts."""
    lines = text.split("\n")

    # Filter out lines that are expected to differ:
    # - Database save messages
    # - Timestamps
    # - Any debug output
    filtered = []
    for line in lines:
        # Skip lines we expect to be different
        if "Saved" in line and "database" in line:
            continue
        if "Database saved" in line:
            continue
        if line.strip().startswith("DEBUG"):
            continue
        filtered.append(line)

    return filtered


def test_output_matches_baseline(verbose=False):
    """Test baseline output with minimal output by default. Use test_baseline_output_verbose for detailed comparison."""
    if verbose:
        print("\n" + "=" * 80)
        print("BASELINE COMPARISON TEST")
        print("=" * 80)
        print(f"Baseline: {BASELINE_FILE}")
        print(f"Script:   {SCRIPT_PATH}")
        print("\nDifferences (excluding database save messages):")
        print("=" * 80)

    # Get current and baseline outputs
    try:
        current_output = run_calculate_risk()
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Script failed:\n{e.stderr}")

    baseline_output = get_baseline()

    # Normalize for comparison
    current_lines = normalize_output(current_output)
    baseline_lines = normalize_output(baseline_output)

    # Generate diff
    diff = list(
        difflib.unified_diff(
            baseline_lines,
            current_lines,
            fromfile="baseline",
            tofile="current",
            lineterm="",
        )
    )

    # Check if outputs are identical
    if diff:
        changed_lines = [line for line in diff if line.startswith("-") or line.startswith("+")]

        if verbose:
            print("\n" + "=" * 80)
            print("CHANGED LINES ONLY:")
            print("(Lines with - are from baseline, lines with + are from current)")
            print("=" * 80)

            for line in changed_lines:
                print(line)

            print(f"\nTotal changed lines: {len(changed_lines)}")

            # Also show summary of key differences
            print("\n" + "=" * 80)
            print("KEY DIFFERENCES SUMMARY:")
            print("=" * 80)

        # Analyze specific known differences (only in verbose mode)
        if verbose:
            print("\n" + "=" * 80)
            print("ROOT CAUSE ANALYSIS:")
            print("=" * 80)
        if verbose:
            analyze_differences(current_output, baseline_output, verbose=True)
    elif verbose:
        print("\n" + "=" * 80)
        print("✓ OUTPUT MATCHES BASELINE")
        print("=" * 80)

    # If there are differences, show them and fail
    if diff:
        changed_lines = [line for line in diff if line.startswith("-") or line.startswith("+")]
        if changed_lines:
            print(f"\nFound {len(changed_lines)} differences. Run in verbose mode for details.")
    assert (
        not diff
    ), "Output does not match baseline. Run 'pytest tests/test_baseline_output.py::test_baseline_output_verbose -s' for details."


def get_summary_section(output: str) -> str:
    """Extract the summary section from the output."""
    lines = output.split("\n")
    in_summary = False
    summary_lines = []

    for line in lines:
        if "SUMMARY" in line and ("=" in line or "=" * 10 in line):
            in_summary = True
            summary_lines.append(line)
            continue
        elif in_summary:
            # Stop at next major section
            if line.strip().startswith("===") and "SKIPPED" in line.upper():
                break
            # Include up to blank line after summary stats
            if line.strip() == "" and "Achieved risk limit" in "\n".join(summary_lines):
                # We've seen the summary stats, stop
                break
            summary_lines.append(line)

    return "\n".join(summary_lines)


def test_baseline_output_verbose():
    """Run detailed baseline comparison with full verbose output."""
    return test_output_matches_baseline(verbose=True)


def test_key_metrics_unchanged():
    """Test that key metrics (counts) haven't changed."""
    current_output = run_calculate_risk()

    # Simple assertion on full output (easier to debug)
    # Expected values (from handoff document and verified output)
    assert "Targeted contests: 64" in current_output
    assert "Achieved risk limit: 61/64" in current_output
    assert "Opportunistic contests: 658" in current_output
    assert "Below risk limit: 223/658" in current_output

    print("\n✓ Key metrics verified:")
    print("  - Targeted contests: 64, passing: 61/64")
    print("  - Opportunistic: 658, below limit: 223/658")


def analyze_differences(current_output: str, baseline_output: str, verbose: bool = False):
    """Analyze specific differences and explain root causes."""
    if not verbose:
        return

    import csv

    # Load discrepancy data from contest.csv
    contest_file = (
        Path(__file__).parent.parent / "data" / "2024" / "general" / "round3" / "contest.csv"
    )
    discrepancy_data = {}

    try:
        with open(contest_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                contest_name = row["contest_name"]
                discrepancy_data[contest_name] = {
                    "o1": int(row.get("one_vote_over_count", 0)),
                    "o2": int(row.get("two_vote_over_count", 0)),
                    "u1": int(row.get("one_vote_under_count", 0)),
                    "u2": int(row.get("two_vote_under_count", 0)),
                    "n": int(row.get("audited_sample_count", 0)),
                }
    except Exception as e:
        print(f"Could not load contest data: {e}")
        return

    import re

    baseline_contests = re.findall(
        r"[✓✗]\s+([^:]+?)\s+n=\s*\d+.*?risk=([0-9.e-]+)", baseline_output
    )
    current_contests = re.findall(r"[✓✗]\s+([^:]+?)\s+n=\s*\d+.*?risk=([0-9.e-]+)", current_output)

    baseline_dict = {name.strip(): risk for name, risk in baseline_contests}
    current_dict = {name.strip(): risk for name, risk in current_contests}

    changed_contests = []
    for contest_name in set(baseline_dict.keys()) | set(current_dict.keys()):
        baseline_risk = baseline_dict.get(contest_name, "N/A")
        current_risk = current_dict.get(contest_name, "N/A")

        if baseline_risk != current_risk and baseline_risk != "N/A" and current_risk != "N/A":
            disc = discrepancy_data.get(contest_name, {})
            changed_contests.append(
                {
                    "name": contest_name,
                    "baseline_risk": baseline_risk,
                    "current_risk": current_risk,
                    "discrepancies": disc,
                }
            )

    print(f"\nFOUND {len(changed_contests)} CONTESTS WITH CHANGED RISK VALUES:\n")

    for contest in sorted(
        changed_contests,
        key=lambda x: (
            abs(float(x["baseline_risk"]) - float(x["current_risk"]))
            if x["baseline_risk"] != "N/A" and x["current_risk"] != "N/A"
            else 0
        ),
        reverse=True,
    ):
        print(f"\n{contest['name']}:")
        print(f"  Risk: {contest['baseline_risk']} → {contest['current_risk']}")
        print(
            f"  Change: {float(contest['current_risk']) / float(contest['baseline_risk']):.2f}x"
            if contest["baseline_risk"] != "N/A" and contest["current_risk"] != "N/A"
            else ""
        )

        disc = contest["discrepancies"]
        if disc and disc.get("n", 0) > 0:
            has_disc = any(
                [disc.get("o1", 0), disc.get("o2", 0), disc.get("u1", 0), disc.get("u2", 0)]
            )
            if has_disc:
                print(f"  Sample size: n={disc.get('n', 'unknown')}")
                print(
                    f"  Discrepancies: o1={disc.get('o1', 0)}, o2={disc.get('o2', 0)}, u1={disc.get('u1', 0)}, u2={disc.get('u2', 0)}"
                )

                # Explain the impact
                if disc.get("o2", 0) > 0:
                    print(
                        f"  ⚠️  Has o2={disc.get('o2', 0)} (two-vote overstatements) - WORST for risk"
                    )
                elif disc.get("o1", 0) > 0:
                    print(
                        f"  ⚠️  Has o1={disc.get('o1', 0)} (one-vote overstatements) - BAD for risk"
                    )
                elif disc.get("u1", 0) > 0:
                    print(
                        f"  ✓  Has u1={disc.get('u1', 0)} (one-vote understatements) - less impact on risk"
                    )
                elif disc.get("u2", 0) > 0:
                    print(
                        f"  ✓  Has u2={disc.get('u2', 0)} (two-vote understatements) - least impact on risk"
                    )
                else:
                    print("  No discrepancies")
            else:
                print(f"  Sample size: n={disc.get('n', 'unknown')}, no discrepancies")
        else:
            print("  This contest appears in output but has audited_sample_count=0 in contest.csv")
            print("  Likely opportunistically sampled from statewide/county contests")
            print("  Current code counts these opportunistic ballots, baseline may not have")

            # Check if this is a pattern
            risk_ratio = (
                float(contest["current_risk"]) / float(contest["baseline_risk"])
                if contest["baseline_risk"] != "N/A" and contest["current_risk"] != "N/A"
                else 0
            )
            if 0.49 <= risk_ratio <= 0.54:
                print("  Pattern: ~0.5x ratio suggests baseline calculated risk differently")
                print("  Possibly different sample counting or diluted_margin formula")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
