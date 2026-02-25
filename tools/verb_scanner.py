"""
Verb Scanner — Cross-resume verb deduplication scan.

Extracts the opening verb from every bullet across all roles.
Flags verbs appearing 3+ times (mandatory replacement) and
2 times (advisory replacement).
"""

import re
import json
import sys
from collections import Counter
from typing import Optional


# Common opening verb patterns to extract
VERB_EXTRACT_PATTERN = re.compile(
    r'^([A-Z][a-z]+(?:-[a-z]+)?)',  # First capitalized word (optionally hyphenated)
    re.MULTILINE
)

# Verbs that should never be opening verbs in resume bullets
ALWAYS_FLAGGED_LEAD_VERBS = {
    "ensuring", "facilitating", "positioning", "driving", "enabling",
    "demonstrating", "applying", "fostering", "championing", "leveraging",
    "utilizing", "spearheading",
}

# Maps vague verbs to precise alternatives based on what follows
VERB_UPGRADE_SUGGESTIONS = {
    "managed": ["Directed", "Oversaw", "Administered", "Led"],
    "helped": ["Supported", "Assisted", "Contributed to", "Partnered with"],
    "worked": ["Collaborated", "Partnered", "Executed", "Delivered"],
    "used": ["Deployed", "Applied", "Implemented", "Operated"],
    "created": ["Developed", "Designed", "Built", "Authored"],
    "made": ["Produced", "Generated", "Delivered", "Developed"],
    "did": ["Executed", "Performed", "Completed", "Delivered"],
    "got": ["Secured", "Obtained", "Achieved", "Acquired"],
    "handled": ["Managed", "Administered", "Processed", "Resolved"],
    "ran": ["Led", "Directed", "Executed", "Operated"],
    "set": ["Established", "Configured", "Defined", "Implemented"],
    "put": ["Deployed", "Established", "Implemented", "Introduced"],
    "gave": ["Delivered", "Provided", "Presented", "Offered"],
    "showed": ["Demonstrated", "Presented", "Revealed", "Displayed"],
    "wrote": ["Authored", "Drafted", "Produced", "Developed"],
    "built": ["Developed", "Engineered", "Constructed", "Designed"],
    "led": ["Directed", "Spearheaded", "Orchestrated", "Guided"],
    "coordinated": ["Orchestrated", "Aligned", "Organized", "Managed"],
}


def extract_opening_verb(text: str) -> Optional[str]:
    """
    Extract the opening verb from a bullet.
    Handles: "Led team...", "Co-developed...", "Built and deployed..."
    Returns normalized lowercase verb.
    """
    text = text.strip()

    # Handle "Co-" prefix (e.g., "Co-developed", "Co-led")
    co_match = re.match(r'^Co-([A-Za-z]+)', text, re.IGNORECASE)
    if co_match:
        return f"co-{co_match.group(1).lower()}"

    # Handle regular opening verb
    match = re.match(r'^([A-Za-z]+)', text)
    if match:
        return match.group(1).lower()

    return None


def scan_bullets(bullets: list[dict]) -> dict:
    """
    Scan list of bullet objects for verb deduplication.
    Returns verb frequency analysis.
    """
    verb_to_bullets = {}  # verb -> list of bullet_ids

    for bullet in bullets:
        bullet_id = bullet.get("id", "unknown")
        text = bullet.get("text", "")
        verb = extract_opening_verb(text)

        if verb:
            if verb not in verb_to_bullets:
                verb_to_bullets[verb] = []
            verb_to_bullets[verb].append({
                "bullet_id": bullet_id,
                "role_id": bullet.get("role_id", ""),
                "is_top2": bullet.get("is_top2", False),
                "text_preview": text[:60] + "..." if len(text) > 60 else text,
            })

    # Categorize
    flags_3plus = []
    flags_2 = []
    clean = []

    for verb, occurrences in sorted(verb_to_bullets.items()):
        count = len(occurrences)
        # Check if any verb is in the always-flagged list
        is_conceptual = verb.replace("co-", "") in ALWAYS_FLAGGED_LEAD_VERBS

        entry = {
            "verb": verb,
            "count": count,
            "occurrences": occurrences,
            "is_conceptual_verb": is_conceptual,
            "suggestions": VERB_UPGRADE_SUGGESTIONS.get(verb, []),
        }

        if is_conceptual or count >= 3:
            entry["flag_level"] = "MANDATORY"
            entry["action"] = "Must replace with more precise verb in at least N-2 occurrences"
            flags_3plus.append(entry)
        elif count == 2:
            entry["flag_level"] = "ADVISORY"
            entry["action"] = "Replace if more precise verb exists; keep if in distant roles and both uses accurate"
            flags_2.append(entry)
        else:
            entry["flag_level"] = "OK"
            clean.append(entry)

    return {
        "tool": "verb_scanner",
        "total_bullets_scanned": len(bullets),
        "unique_verbs": len(verb_to_bullets),
        "flags_3plus": flags_3plus,
        "flags_2": flags_2,
        "clean_verbs": [e["verb"] for e in clean],
        "full_table": {verb: [occ["bullet_id"] for occ in occs]
                       for verb, occs in verb_to_bullets.items()},
        "summary": {
            "mandatory_flags": len(flags_3plus),
            "advisory_flags": len(flags_2),
            "clean": len(clean),
        }
    }


def check_draft_bullets(draft_bullets_path: str) -> dict:
    """Load draft_bullets.json and scan for verb deduplication."""
    with open(draft_bullets_path) as f:
        draft = json.load(f)

    bullets = draft.get("bullets", [])
    return scan_bullets(bullets)


def main():
    """CLI usage: python verb_scanner.py <draft_bullets.json>"""
    if len(sys.argv) < 2:
        print("Usage: python verb_scanner.py <draft_bullets.json>")
        sys.exit(1)

    results = check_draft_bullets(sys.argv[1])

    print(f"\nCROSS-RESUME VERB SCAN")
    print(f"{'='*50}")
    print(f"Bullets scanned: {results['total_bullets_scanned']}")
    print(f"Unique verbs: {results['unique_verbs']}")
    print()

    if results["flags_3plus"]:
        print(f"MANDATORY REPLACEMENTS ({len(results['flags_3plus'])} verbs):")
        for entry in results["flags_3plus"]:
            verb_display = f"'{entry['verb']}'"
            if entry["is_conceptual_verb"]:
                verb_display += " [CONCEPTUAL VERB — always banned as lead]"
            print(f"  {verb_display}: appears {entry['count']}x")
            for occ in entry["occurrences"]:
                top2_tag = " [TOP2]" if occ["is_top2"] else ""
                print(f"    - {occ['bullet_id']}{top2_tag}: {occ['text_preview']}")
            if entry["suggestions"]:
                print(f"    Suggestions: {', '.join(entry['suggestions'][:3])}")
        print()

    if results["flags_2"]:
        print(f"ADVISORY FLAGS ({len(results['flags_2'])} verbs):")
        for entry in results["flags_2"]:
            print(f"  '{entry['verb']}': appears {entry['count']}x in {[occ['bullet_id'] for occ in entry['occurrences']]}")
        print()

    if not results["flags_3plus"] and not results["flags_2"]:
        print("No verb deduplication flags. All verbs appear ≤1 time.")

    print("\n--- JSON OUTPUT ---")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
