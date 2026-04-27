#!/usr/bin/env python3
"""
Analyze selection vs. comparison inconsistencies across all Colorado RLA audits.

Three classes of flaw from SELECTION_FLAWS.md / Copilot analysis:

  1. selection_only  — CVR IDs in contestSelection but NOT in contestComparison
                       (ballots drawn but never audited; symptom of Bug 1:
                        cumulative contest_cvr_ids, no per-round filter)

  2. comparison_only — CVR IDs in contestComparison but NOT in contestSelection
                       (ballots audited for a contest they were never drawn for;
                        symptom of Bug 2: SQL JOIN on audit_reason, not contest id)

  3. identical_rounds — contestSelection data is bit-for-bit identical across rounds
                        (confirms the cumulative-list issue; no new draws recorded
                         per round in the export)

  4. name_collision   — the same contest name string appears under multiple counties
                        in contestsByCounty (the ContestCounter.groupingBy(name)
                        bug that merges county contests across county lines)
"""

import ast
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

DATA_ROOT = Path(__file__).parent / "data"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def load_selection(path: Path) -> dict[str, set[int]]:
    """Return {contest_name: set(cvr_ids)} from a contestSelection.csv."""
    result: dict[str, set[int]] = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            name = row.get("contest_name", "").strip()
            raw = row.get("contest_cvr_ids", "[]").strip()
            if not raw or raw == "[]":
                ids: set[int] = set()
            else:
                try:
                    ids = set(json.loads(raw))
                except json.JSONDecodeError:
                    try:
                        ids = set(ast.literal_eval(raw))
                    except Exception:
                        ids = set()
            result[name] = ids
    return result


def load_comparison(path: Path) -> dict[str, set[int]]:
    """Return {contest_name: set(cvr_ids)} from a contestComparison.csv."""
    result: dict[str, set[int]] = defaultdict(set)
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            name = row.get("contest_name", "").strip()
            raw = row.get("cvr_id", "").strip()
            if raw:
                try:
                    result[name].add(int(raw))
                except ValueError:
                    pass
    return dict(result)


def load_contests_by_county(path: Path) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# per-election-round analysis
# ---------------------------------------------------------------------------

def analyse_round(
    label: str,
    sel_path: Path,
    cmp_path: Path,
) -> dict:
    sel = load_selection(sel_path)
    cmp = load_comparison(cmp_path)

    all_contests = sorted(set(sel) | set(cmp))
    results = []
    for contest in all_contests:
        sel_ids = sel.get(contest, set())
        cmp_ids = cmp.get(contest, set())
        sel_only = sel_ids - cmp_ids
        cmp_only = cmp_ids - sel_ids
        both = sel_ids & cmp_ids

        if sel_only or cmp_only:
            results.append({
                "contest": contest,
                "sel_total": len(sel_ids),
                "cmp_total": len(cmp_ids),
                "both": len(both),
                "sel_only": len(sel_only),
                "cmp_only": len(cmp_only),
                "sel_only_ids": sorted(sel_only)[:10],   # first 10 for display
                "cmp_only_ids": sorted(cmp_only)[:10],
            })

    return {
        "label": label,
        "sel_path": str(sel_path.relative_to(DATA_ROOT.parent)),
        "cmp_path": str(cmp_path.relative_to(DATA_ROOT.parent)),
        "flaws": results,
    }


# ---------------------------------------------------------------------------
# identical-rounds check
# ---------------------------------------------------------------------------

def check_identical_rounds(election_dir: Path, round_dirs: list[Path]) -> list[dict]:
    """Check whether contestSelection files are identical across rounds."""
    sel_files = []
    for rd in sorted(round_dirs):
        for name in ("contestSelection.csv", "contest_selection.csv"):
            p = rd / name
            if p.exists():
                sel_files.append(p)
                break

    if len(sel_files) < 2:
        return []

    contents = {}
    for p in sel_files:
        contents[p] = p.read_bytes()

    results = []
    base_path, base_content = sel_files[0], contents[sel_files[0]]
    for p in sel_files[1:]:
        if contents[p] == base_content:
            results.append({
                "round_a": str(base_path.relative_to(DATA_ROOT.parent)),
                "round_b": str(p.relative_to(DATA_ROOT.parent)),
                "note": "bit-for-bit identical — cumulative list, no per-round view",
            })
    return results


# ---------------------------------------------------------------------------
# name-collision check
# ---------------------------------------------------------------------------

def check_name_collisions(path: Path) -> list[dict]:
    """Find contest names that appear under more than one county."""
    rows = load_contests_by_county(path)
    by_name: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        name = row.get("contest_name", "").strip()
        county = row.get("county_name", "").strip()
        if name and county:
            by_name[name].append(county)

    collisions = []
    for name, counties in by_name.items():
        if len(set(counties)) > 1:
            collisions.append({
                "contest_name": name,
                "counties": sorted(set(counties)),
                "county_count": len(set(counties)),
            })
    return sorted(collisions, key=lambda x: -x["county_count"])


# ---------------------------------------------------------------------------
# walk all elections
# ---------------------------------------------------------------------------

def find_round_pairs(base: Path):
    """
    Yield (election_label, [(round_label, sel_path, cmp_path_or_None)], round_dirs)
    for every election we can find.
    """
    # We search for directories that directly contain a selection file
    for root, dirs, files in os.walk(base):
        dirs.sort()
        root_path = Path(root)
        sel_name = None
        cmp_name = None
        for f in files:
            if f in ("contestSelection.csv", "contest_selection.csv"):
                sel_name = f
            if f in ("contestComparison.csv", "contest_comparison.csv",
                     "CVRtoAuditBoardInterpretativeComparison.csv"):
                cmp_name = f
        if sel_name:
            yield root_path, sel_name, cmp_name


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("=" * 72)
    print("Colorado RLA AuditCenter: Selection/Comparison Inconsistency Scan")
    print("=" * 72)

    # --- Phase 1: per-round selection vs comparison -----------------------
    print("\n## Phase 1: Selection-vs-Comparison per Round\n")

    all_round_results = []
    for round_dir, sel_name, cmp_name in find_round_pairs(DATA_ROOT):
        sel_path = round_dir / sel_name
        if cmp_name:
            cmp_path = round_dir / cmp_name
            label = str(round_dir.relative_to(DATA_ROOT.parent))
            r = analyse_round(label, sel_path, cmp_path)
            all_round_results.append(r)
            if r["flaws"]:
                print(f"### {r['label']}")
                for flaw in r["flaws"]:
                    print(f"  Contest: {flaw['contest']}")
                    print(f"    sel={flaw['sel_total']}  cmp={flaw['cmp_total']}  "
                          f"both={flaw['both']}  "
                          f"sel_only={flaw['sel_only']}  cmp_only={flaw['cmp_only']}")
                    if flaw["sel_only_ids"]:
                        print(f"    sel_only sample cvr_ids: {flaw['sel_only_ids']}")
                    if flaw["cmp_only_ids"]:
                        print(f"    cmp_only sample cvr_ids: {flaw['cmp_only_ids']}")
                print()

    # Summary counts
    total_with_flaws = sum(1 for r in all_round_results if r["flaws"])
    total_sel_only_contests = sum(
        sum(1 for f in r["flaws"] if f["sel_only"] > 0)
        for r in all_round_results
    )
    total_cmp_only_contests = sum(
        sum(1 for f in r["flaws"] if f["cmp_only"] > 0)
        for r in all_round_results
    )
    print(f"Rounds with at least one flaw:  {total_with_flaws}/{len(all_round_results)}")
    print(f"Contest-rounds with sel_only > 0: {total_sel_only_contests}")
    print(f"Contest-rounds with cmp_only > 0: {total_cmp_only_contests}")

    # --- Phase 2: identical rounds ----------------------------------------
    print("\n## Phase 2: Identical contestSelection Across Rounds\n")

    # Group round dirs by election (parent)
    election_rounds: dict[Path, list[Path]] = defaultdict(list)
    for round_dir, sel_name, _ in find_round_pairs(DATA_ROOT):
        parent = round_dir.parent
        election_rounds[parent].append(round_dir)

    identical_found = []
    for election_dir, round_dirs in sorted(election_rounds.items()):
        if len(round_dirs) < 2:
            continue
        idems = check_identical_rounds(election_dir, round_dirs)
        for item in idems:
            identical_found.append(item)
            print(f"  IDENTICAL: {item['round_a']}")
            print(f"         == {item['round_b']}")

    if not identical_found:
        print("  (none found)")

    # --- Phase 3: name collisions -----------------------------------------
    print("\n## Phase 3: Contest-Name Collisions Across Counties\n")

    for root, dirs, files in os.walk(DATA_ROOT):
        dirs.sort()
        for f in files:
            if f in ("contestsByCounty.csv", "contests_by_county.csv"):
                p = Path(root) / f
                label = str(p.relative_to(DATA_ROOT.parent))
                collisions = check_name_collisions(p)
                if collisions:
                    print(f"### {label}")
                    for c in collisions[:20]:  # top 20
                        print(f"  '{c['contest_name']}' → {c['counties']}")
                    if len(collisions) > 20:
                        print(f"  ... and {len(collisions) - 20} more")
                    print()

    print("\n## Done")


if __name__ == "__main__":
    main()
