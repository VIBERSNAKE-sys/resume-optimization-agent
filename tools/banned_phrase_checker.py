"""
Banned Phrase Checker — Pattern matching for banned constructions in resume text.

Detects:
- Conceptual verbs that can't be visualized
- Banned n-grams and boilerplate phrases
- Defensive framing constructions
- Meta-defensive language
- "Served as [title/role]" (title-claim construction)
- "demonstrates/demonstrating" in project outcomes
- Missing concrete objects
"""

import re
import json
import sys
from typing import Optional


# Each pattern: (regex, description, fix_suggestion)
BANNED_PATTERNS = [
    # Duties-speak
    (r'\bresponsible for\b', "duties-speak: 'responsible for'", "Replace with concrete action verb and owned outcome"),
    (r'\bduties included\b', "duties-speak: 'duties included'", "Replace with concrete action verbs"),
    (r'\bhelped with\b', "duties-speak: 'helped with'", "Replace with specific contribution and owned outcome"),
    (r'\bworked on\b', "duties-speak: 'worked on'", "Replace with concrete action verb"),

    # Title-claim constructions (NOT the action verb "served")
    (r'\bserved as\s+(?:the\s+)?(?:team\'?s?\s+)?(?:lead|manager|expert|advisor|coordinator|point\s+of\s+contact|poc|subject\s+matter|sme|primary)\b',
     "title-claim: 'Served as [role]'", "Replace with the action that demonstrates the role"),
    (r'\bacted as\s+(?:the\s+)?\w+', "title-claim: 'Acted as [role]'", "Replace with concrete action"),
    (r'\bfunctioned as\s+(?:the\s+)?\w+', "title-claim: 'Functioned as [role]'", "Replace with concrete action"),

    # Vague implementations
    (r'\bimplemented\s+(?:a\s+)?(?:digital\s+innovation|solution|innovation|strategy|approach|system|initiative|process)\b',
     "vague implementation", "Specify WHAT was implemented: 'deployed Teams/SharePoint integration'"),

    # Boilerplate n-grams
    (r'\bresults[-\s]driven\b', "boilerplate: 'results-driven'", "Remove — show results through bullets"),
    (r'\bproven track record\b', "boilerplate: 'proven track record'", "Remove — let evidence speak"),
    (r'\bpassionate\b', "boilerplate: 'passionate'", "Remove from professional text"),
    (r'\brobust\b', "boilerplate: 'robust'", "Replace with specific: '99.9% uptime', 'handles 10K concurrent users'"),
    (r'\bsynergi[ezy]\b', "boilerplate: 'synergy/synergies'", "Remove — describe the actual collaboration"),
    (r'\bdynamic team player\b', "boilerplate: 'dynamic team player'", "Remove"),
    (r'\bseasoned professional\b', "boilerplate: 'seasoned professional'", "Remove"),
    (r'\bself[-\s]starter\b', "boilerplate: 'self-starter'", "Remove — show initiative through action verbs"),
    (r'\bseeking\b', "summary boilerplate: 'seeking'", "Remove — lead with your strongest evidence"),
    (r'\bnow applying\b', "boilerplate: 'now applying'", "Remove"),
    (r'\bleverage[sd]?\b', "conceptual verb: 'leverage/leveraged'", "Replace with concrete action verb"),
    (r'\butilize[sd]?\b', "conceptual verb: 'utilize/utilized'", "Replace with 'used' or more specific verb"),

    # Metric composition / positioning errors
    (r'\bpositioned\s+\d', "metric error: 'positioned [metric]'", "Replace with 'achieved' or 'delivered'"),

    # Defensive / meta-defensive language
    (r'\bwithout overstating\b', "meta-defensive: 'without overstating'", "Remove — never narrate restraint"),
    (r'\bnot claiming\b', "meta-defensive: 'not claiming'", "Remove — omit the skill entirely instead"),
    (r'\bwhile acknowledging\b', "meta-defensive: 'while acknowledging'", "Remove — narrating limitations invites scrutiny"),
    (r'\bthrough personal initiative\b', "metadata leakage: 'through personal initiative'", "Remove — show initiative through action verbs (Identified, Proposed)"),
    (r'\bself[-\s]initiated\b', "metadata leakage: 'self-initiated'", "Remove — show the action, not the origin"),
    (r'\bwithout being asked\b', "metadata leakage: 'without being asked'", "Remove"),
    (r'\bindependently identified the need to\b', "metadata leakage", "Remove — state the action directly"),

    # Defensive disclaimers about technical division of labor
    (r'\bwhile\s+\w+\s+handled\b', "defensive disclaimer: 'while [team] handled'", "Replace with: 'partnered with', 'defined requirements for', 'guided'"),
    (r'\bthough I didn\'t\b', "defensive disclaimer", "Remove — don't highlight what you didn't do"),
    (r'\bwith\s+\w+\s+doing the\b', "defensive disclaimer: 'with [team] doing the'", "Reframe as collaboration"),

    # Self-referential narration in project outcomes
    (r'\bdemonstrat(?:es|ing)\b', "self-referential: 'demonstrates/demonstrating'",
     "Outcome must state what was PRODUCED, not what the project demonstrates. Replace with concrete result."),
    (r'\bapplicable to\b', "self-referential: 'applicable to'", "State the actual application or result"),
    (r'\brelevant to\b', "self-referential: 'relevant to'", "State the actual relevance through evidence"),
]

# Compile all patterns
COMPILED_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE), desc, fix)
    for pattern, desc, fix in BANNED_PATTERNS
]


def check_banned_phrases(text: str, item_id: str = "unknown") -> dict:
    """
    Check text for all banned phrase patterns.
    Returns dict with verdict and all violations found.
    """
    violations = []

    for compiled_pattern, description, fix_suggestion in COMPILED_PATTERNS:
        matches = compiled_pattern.findall(text)
        if matches:
            violations.append({
                "pattern": description,
                "matches": matches,
                "fix": fix_suggestion,
            })

    verdict = "FAIL" if violations else "PASS"

    return {
        "item_id": item_id,
        "text_preview": text[:100] + "..." if len(text) > 100 else text,
        "verdict": verdict,
        "violations": violations,
        "violation_count": len(violations),
    }


def check_conceptual_lead_verb(text: str) -> Optional[str]:
    """
    Check if bullet starts with a banned conceptual verb (not just contains it).
    Returns the offending verb if found, None otherwise.
    """
    CONCEPTUAL_LEAD_VERBS = [
        r'^ensuring\b', r'^facilitating\b', r'^positioning\b', r'^driving\b',
        r'^enabling\b', r'^demonstrating\b', r'^applying\b', r'^fostering\b',
        r'^championing\b', r'^spearheading\b', r'^leveraging\b', r'^utilizing\b',
        r'^supporting\b(?=\s+(?:the\s+)?(?:team|organization|department))',
    ]
    for pattern in CONCEPTUAL_LEAD_VERBS:
        if re.match(pattern, text.strip(), re.IGNORECASE):
            return text.split()[0]
    return None


def check_draft_files(
    draft_bullets_path: Optional[str] = None,
    draft_summary_path: Optional[str] = None,
    draft_projects_path: Optional[str] = None,
    draft_skills_path: Optional[str] = None,
) -> dict:
    """Check all draft files for banned phrases."""
    results = {
        "tool": "banned_phrase_checker",
        "items": {},
        "summary": {
            "total": 0,
            "passing": 0,
            "failing": 0,
        }
    }

    def add_result(item_id: str, text: str):
        check = check_banned_phrases(text, item_id)

        # Also check lead verb for bullets
        if "B" in item_id:  # rough heuristic for bullets
            bad_verb = check_conceptual_lead_verb(text)
            if bad_verb:
                check["violations"].insert(0, {
                    "pattern": f"conceptual lead verb: '{bad_verb}'",
                    "matches": [bad_verb],
                    "fix": f"Replace '{bad_verb}' with a concrete action verb (Built, Created, Reduced, etc.)",
                })
                check["verdict"] = "FAIL"
                check["violation_count"] = len(check["violations"])

        results["items"][item_id] = check
        results["summary"]["total"] += 1
        if check["verdict"] == "PASS":
            results["summary"]["passing"] += 1
        else:
            results["summary"]["failing"] += 1

    if draft_bullets_path:
        with open(draft_bullets_path) as f:
            draft = json.load(f)
        for bullet in draft.get("bullets", []):
            add_result(bullet["id"], bullet["text"])

    if draft_summary_path:
        with open(draft_summary_path) as f:
            add_result("SUMMARY", f.read().strip())

    if draft_projects_path:
        with open(draft_projects_path) as f:
            projects = json.load(f)
        for proj in projects.get("projects", []):
            if proj.get("decision") != "DROP":
                proj_id = proj.get("id", "unknown")
                for section in ["objective", "action", "outcome"]:
                    if proj.get(section):
                        add_result(f"{proj_id}_{section}", proj[section])

    if draft_skills_path:
        with open(draft_skills_path) as f:
            skills = json.load(f)
        skills_text = skills.get("skills_text", "")
        if skills_text:
            add_result("SKILLS", skills_text)

    return results


def main():
    """CLI usage."""
    if len(sys.argv) < 2:
        print("Usage: python banned_phrase_checker.py --text 'text to check'")
        print("   or: python banned_phrase_checker.py <draft_bullets.json> [summary.txt] [projects.json] [skills.json]")
        sys.exit(1)

    if sys.argv[1] == "--text":
        text = " ".join(sys.argv[2:])
        result = check_banned_phrases(text, "CLI_INPUT")
        print(f"Verdict: {result['verdict']}")
        if result["violations"]:
            for v in result["violations"]:
                print(f"  VIOLATION: {v['pattern']}")
                print(f"  Fix: {v['fix']}")
        else:
            print("  No banned phrases found.")
        return

    bullets_path = sys.argv[1] if len(sys.argv) > 1 else None
    summary_path = sys.argv[2] if len(sys.argv) > 2 else None
    projects_path = sys.argv[3] if len(sys.argv) > 3 else None
    skills_path = sys.argv[4] if len(sys.argv) > 4 else None

    results = check_draft_files(bullets_path, summary_path, projects_path, skills_path)

    print(f"\nBANNED PHRASE CHECK RESULTS")
    print(f"{'='*50}")
    print(f"Passing: {results['summary']['passing']} / {results['summary']['total']}")

    for item_id, check in results["items"].items():
        if check["verdict"] == "FAIL":
            print(f"[FAIL] {item_id}: {check['violation_count']} violation(s)")
            for v in check["violations"]:
                print(f"       -> {v['pattern']}")
                print(f"          Fix: {v['fix']}")
        else:
            print(f"[PASS] {item_id}")

    print("\n--- JSON OUTPUT ---")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
