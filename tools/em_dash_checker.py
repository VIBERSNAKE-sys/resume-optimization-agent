"""
Em Dash Checker — Regex-based em dash / en dash / double hyphen detection.

Em dashes (—), en dashes (–), and double hyphens (--) used as sentence
breaks are banned from all resume text. This tool detects them.

Note: Hyphens within compound words (e.g., "CTO-sponsored", "on-time")
are NOT violations. The check targets sentence-break usage.
"""

import re
import json
import sys
from typing import Optional


# Patterns for sentence-break dashes
# These capture: em dash, en dash, double hyphen (when not in compound word)
EM_DASH_PATTERN = re.compile(r'\u2014')  # — em dash (always a violation)
EN_DASH_PATTERN = re.compile(r'\u2013')  # – en dash (always a violation when used as sentence break)
DOUBLE_HYPHEN_PATTERN = re.compile(r'(?<!\w)--(?!\w)|(?<=\s)--(?=\s)')  # -- between words


def check_em_dash(text: str, item_id: str = "unknown") -> dict:
    """
    Check text for banned em/en dashes and double hyphens.
    Returns dict with verdict and any violations found.
    """
    violations = []

    em_matches = EM_DASH_PATTERN.findall(text)
    if em_matches:
        violations.append({
            "type": "em_dash",
            "character": "—",
            "count": len(em_matches),
            "fix": "Replace with comma, colon, or restructure sentence"
        })

    en_matches = EN_DASH_PATTERN.findall(text)
    if en_matches:
        violations.append({
            "type": "en_dash",
            "character": "–",
            "count": len(en_matches),
            "fix": "Replace with comma, colon, or restructure sentence"
        })

    dh_matches = DOUBLE_HYPHEN_PATTERN.findall(text)
    if dh_matches:
        violations.append({
            "type": "double_hyphen",
            "character": "--",
            "count": len(dh_matches),
            "fix": "Replace with comma, colon, or restructure sentence"
        })

    verdict = "FAIL" if violations else "PASS"

    return {
        "item_id": item_id,
        "text_preview": text[:80] + "..." if len(text) > 80 else text,
        "verdict": verdict,
        "violations": violations,
        "violation_count": sum(v["count"] for v in violations),
    }


def check_all_text(texts: dict[str, str]) -> dict:
    """
    Check multiple text items. texts = {id: text}
    Returns summary with per-item results.
    """
    results = {
        "tool": "em_dash_checker",
        "items": {},
        "summary": {
            "total": len(texts),
            "passing": 0,
            "failing": 0,
        }
    }

    for item_id, text in texts.items():
        check = check_em_dash(text, item_id)
        results["items"][item_id] = check
        if check["verdict"] == "PASS":
            results["summary"]["passing"] += 1
        else:
            results["summary"]["failing"] += 1

    return results


def check_draft_files(
    draft_bullets_path: Optional[str] = None,
    draft_summary_path: Optional[str] = None,
    draft_projects_path: Optional[str] = None,
) -> dict:
    """Check all draft files for em dash violations."""
    texts = {}

    if draft_bullets_path:
        with open(draft_bullets_path) as f:
            draft = json.load(f)
        for bullet in draft.get("bullets", []):
            texts[bullet["id"]] = bullet["text"]

    if draft_summary_path:
        with open(draft_summary_path) as f:
            texts["SUMMARY"] = f.read().strip()

    if draft_projects_path:
        with open(draft_projects_path) as f:
            projects = json.load(f)
        for proj in projects.get("projects", []):
            if proj.get("decision") != "DROP":
                proj_id = proj.get("id", "unknown")
                # Check objective, action, outcome separately
                for section in ["objective", "action", "outcome"]:
                    if proj.get(section):
                        texts[f"{proj_id}_{section}"] = proj[section]

    return check_all_text(texts)


def main():
    """CLI usage."""
    if len(sys.argv) < 2:
        print("Usage: python em_dash_checker.py --text 'text to check'")
        print("   or: python em_dash_checker.py <draft_bullets.json> [summary.txt] [draft_projects.json]")
        sys.exit(1)

    if sys.argv[1] == "--text":
        text = " ".join(sys.argv[2:])
        result = check_em_dash(text, "CLI_INPUT")
        print(f"Verdict: {result['verdict']}")
        if result["violations"]:
            for v in result["violations"]:
                print(f"  VIOLATION: {v['type']} — {v['count']} instance(s)")
                print(f"  Fix: {v['fix']}")
        else:
            print("  No em dash violations found.")
        return

    # File mode
    bullets_path = sys.argv[1] if len(sys.argv) > 1 else None
    summary_path = sys.argv[2] if len(sys.argv) > 2 else None
    projects_path = sys.argv[3] if len(sys.argv) > 3 else None

    results = check_draft_files(bullets_path, summary_path, projects_path)

    print(f"\nEM DASH CHECK RESULTS")
    print(f"{'='*50}")
    print(f"Passing: {results['summary']['passing']} / {results['summary']['total']}")

    for item_id, check in results["items"].items():
        status = "[PASS]" if check["verdict"] == "PASS" else "[FAIL]"
        print(f"{status} {item_id}")
        if check["violations"]:
            for v in check["violations"]:
                print(f"       -> {v['type']}: {v['count']} found. Fix: {v['fix']}")

    print("\n--- JSON OUTPUT ---")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
