"""
Word Counter — Code-based word count utility.

Used by the Verification Agent to count words in resume bullets,
summary, and other text. Word counts from this tool are the ONLY
accepted evidence of Gate 3 compliance. No estimation.
"""

import json
import sys
from pathlib import Path


def count_words(text: str) -> int:
    """Count words in text by splitting on whitespace."""
    return len(text.split())


def count_all_bullets(bullets: list[dict]) -> dict[str, int]:
    """
    Count words for a list of bullet objects.
    Each bullet must have 'id' and 'text' fields.
    Returns dict of bullet_id -> word_count.
    """
    results = {}
    for bullet in bullets:
        bullet_id = bullet.get("id", "unknown")
        text = bullet.get("text", "")
        results[bullet_id] = count_words(text)
    return results


def check_word_count(
    text: str,
    is_top2: bool,
    is_summary: bool = False,
) -> dict:
    """
    Check if text is within allowed word count range.
    Returns pass/fail with count and limits.
    """
    count = count_words(text)

    if is_summary:
        ceiling = 75
        floor = 45
        target_min = 45
        target_max = 75
    elif is_top2:
        ceiling = 27
        floor = 18
        target_min = 22
        target_max = 26
    else:  # older role
        ceiling = 25
        floor = 12
        target_min = 14
        target_max = 18

    within_ceiling = count <= ceiling
    above_floor = count >= floor
    in_target = target_min <= count <= target_max

    verdict = "PASS" if (within_ceiling and above_floor) else "FAIL"

    result = {
        "word_count": count,
        "ceiling": ceiling,
        "floor": floor,
        "target_range": f"{target_min}-{target_max}",
        "within_ceiling": within_ceiling,
        "above_floor": above_floor,
        "in_target": in_target,
        "verdict": verdict,
    }

    if not within_ceiling:
        result["failure_reason"] = f"Exceeds ceiling: {count} words (max {ceiling})"
    elif not above_floor:
        result["failure_reason"] = f"Below floor: {count} words (min {floor})"

    return result


def verify_draft_bullets(draft_bullets_path: str) -> dict:
    """
    Load draft_bullets.json and verify word counts for all bullets.
    Returns verification results dict.
    """
    with open(draft_bullets_path) as f:
        draft = json.load(f)

    results = {
        "tool": "word_counter",
        "bullets": {},
        "summary": {
            "total": 0,
            "passing": 0,
            "failing": 0,
            "at_ceiling": 0,
            "below_floor": 0,
        }
    }

    for bullet in draft.get("bullets", []):
        bullet_id = bullet["id"]
        text = bullet["text"]
        is_top2 = bullet.get("is_top2", False)

        check = check_word_count(text, is_top2=is_top2)
        results["bullets"][bullet_id] = check
        results["summary"]["total"] += 1

        if check["verdict"] == "PASS":
            results["summary"]["passing"] += 1
        else:
            results["summary"]["failing"] += 1

        if check["word_count"] >= (27 if is_top2 else 25):
            results["summary"]["at_ceiling"] += 1
        if not check["above_floor"]:
            results["summary"]["below_floor"] += 1

    return results


def main():
    """CLI usage: python word_counter.py <draft_bullets.json>"""
    if len(sys.argv) < 2:
        print("Usage: python word_counter.py <draft_bullets.json>")
        print("   or: python word_counter.py --text 'bullet text here'")
        sys.exit(1)

    if sys.argv[1] == "--text":
        # Single text count mode
        text = " ".join(sys.argv[2:])
        count = count_words(text)
        print(f"Word count: {count}")
        print("Words:", text.split())
        return

    draft_path = sys.argv[1]
    results = verify_draft_bullets(draft_path)

    print(f"\nWORD COUNT VERIFICATION")
    print(f"{'='*50}")
    print(f"Total bullets: {results['summary']['total']}")
    print(f"Passing: {results['summary']['passing']}")
    print(f"Failing: {results['summary']['failing']}")
    print()

    for bullet_id, check in results["bullets"].items():
        status = "[PASS]" if check["verdict"] == "PASS" else "[FAIL]"
        in_target = " (in target)" if check["in_target"] else ""
        ceiling = check["ceiling"]
        floor = check["floor"]
        count = check["word_count"]
        print(f"{status} {bullet_id}: {count} words (floor:{floor} target:{check['target_range']} ceiling:{ceiling}){in_target}")
        if check["verdict"] == "FAIL":
            print(f"       -> {check['failure_reason']}")

    # Print JSON to stdout for piping
    print("\n--- JSON OUTPUT ---")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
