"""
Fragment Detector — Sentence flow analysis for resume text.

Checks for:
1. Sentence fragments (missing finite verb)
2. Banned grammatical constructions (gerund stacks, "Led team completing")
3. Participle-only sentences (no finite verb)

Used by the Verification Agent for Gate 7 Tier 1 (Basic Readability).
"""

import re
import json
import sys
from typing import Optional


# Finite verb patterns (past tense action verbs typical in resumes)
FINITE_VERB_PATTERN = re.compile(
    r'\b(?:'
    r'built|created|developed|designed|wrote|authored|produced|launched|deployed|'
    r'reduced|increased|accelerated|streamlined|optimized|achieved|improved|'
    r'led|directed|managed|coordinated|organized|hired|trained|scheduled|'
    r'analyzed|evaluated|measured|tracked|calculated|assessed|identified|'
    r'implemented|integrated|configured|installed|established|defined|'
    r'negotiated|secured|delivered|completed|resolved|supported|'
    r'collaborated|partnered|advised|consulted|presented|reported|'
    r'built|drafted|reviewed|approved|verified|tested|validated|'
    r'migrated|upgraded|automated|digitized|standardized|'
    r'enabled|facilitated|drove|spearheaded|championed|'
    r'served|worked|coordinated|overseen|oversaw|'
    r'is|are|was|were|has|have|had|will|would|could|should|'
    r'co-developed|co-led|co-created|co-authored|co-designed'
    r')\b',
    re.IGNORECASE
)

# Participle-only (non-finite) verbs that should NOT be the only verb form
PARTICIPLE_ONLY_PATTERN = re.compile(
    r'\b(?:applying|achieving|demonstrating|delivering|enabling|'
    r'managing|leading|developing|building|creating|designing|'
    r'reducing|increasing|implementing|coordinating|supporting|'
    r'analyzing|evaluating|facilitating|driving|ensuring)\b',
    re.IGNORECASE
)

# Banned grammatical constructions
BANNED_CONSTRUCTIONS = [
    # "Led team completing" pattern
    (
        re.compile(r'\b(led|directed|guided|oversaw)\s+(?:\w+\s+)?(?:team|group|staff|squad)\s+\w+ing\b', re.IGNORECASE),
        "Pattern: 'Led [noun] [gerund]' — grammatically incorrect",
        "Fix: Use 'Led [noun] to [infinitive]' — e.g., 'Led team to complete'"
    ),
    # "Achieved success implementing" pattern
    (
        re.compile(r'\b(achieved|accomplished|attained)\s+\w+\s+\w+ing\b', re.IGNORECASE),
        "Pattern: 'Achieved [noun] [gerund]' — awkward construction",
        "Fix: Use 'Achieved [noun] through [method]'"
    ),
    # "Managed staff coordinating scheduling" pattern (double gerund after noun)
    (
        re.compile(r'\b(managed|supervised|oversaw)\s+(?:\w+\s+)?\w+ing\s+\w+ing\b', re.IGNORECASE),
        "Pattern: '[Verb] [noun] [gerund] [gerund]' — gerund stack",
        "Fix: Restructure — 'Managed [noun]' coordination and scheduling'"
    ),
]


def check_sentence_flow(text: str, item_id: str = "unknown") -> dict:
    """
    Check a sentence/bullet for grammatical issues.
    Returns dict with verdict and specific findings.
    """
    issues = []

    # Check for banned grammatical constructions
    for pattern, description, fix in BANNED_CONSTRUCTIONS:
        if pattern.search(text):
            issues.append({
                "type": "banned_construction",
                "description": description,
                "fix": fix,
            })

    # Fragment check: does the text have a finite verb?
    # (Only apply to sentences, not bullets — bullets may start with verb)
    sentences = re.split(r'[.!?]+', text)
    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if not sentence:
            continue

        has_finite_verb = bool(FINITE_VERB_PATTERN.search(sentence))
        has_only_participle = bool(PARTICIPLE_ONLY_PATTERN.search(sentence)) and not has_finite_verb

        if has_only_participle and not has_finite_verb:
            # This is a fragment
            participles = PARTICIPLE_ONLY_PATTERN.findall(sentence)
            issues.append({
                "type": "fragment",
                "description": f"Sentence/clause is a fragment — participl(s) {participles} without finite verb",
                "fix": "Change participial phrase to past tense: 'applying' → 'applied'",
                "sentence_preview": sentence[:80],
            })

    # Check for gerund stacking (3+ gerunds in sequence)
    gerund_stack = re.findall(r'\b\w+ing\b(?:\s*,\s*\b\w+ing\b){2,}', text, re.IGNORECASE)
    if gerund_stack:
        issues.append({
            "type": "gerund_stack",
            "description": f"Gerund stack: 3+ gerunds in sequence — {gerund_stack}",
            "fix": "Compress to one owned action + hard nouns: 'translating, facilitating, communicating' → 'translated technical requirements into executive status reports'"
        })

    verdict = "FAIL" if issues else "PASS"

    return {
        "item_id": item_id,
        "text_preview": text[:100] + "..." if len(text) > 100 else text,
        "verdict": verdict,
        "issues": issues,
        "issue_count": len(issues),
    }


def check_all_bullets(bullets: list[dict]) -> dict:
    """Check all bullets for sentence flow issues."""
    results = {
        "tool": "fragment_detector",
        "items": {},
        "summary": {
            "total": len(bullets),
            "passing": 0,
            "failing": 0,
        }
    }

    for bullet in bullets:
        bullet_id = bullet.get("id", "unknown")
        text = bullet.get("text", "")
        check = check_sentence_flow(text, bullet_id)
        results["items"][bullet_id] = check

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
    """Check all draft files for sentence flow issues."""
    all_items = {}

    if draft_bullets_path:
        with open(draft_bullets_path) as f:
            draft = json.load(f)
        for bullet in draft.get("bullets", []):
            check = check_sentence_flow(bullet["text"], bullet["id"])
            all_items[bullet["id"]] = check

    if draft_summary_path:
        with open(draft_summary_path) as f:
            summary_text = f.read().strip()
        check = check_sentence_flow(summary_text, "SUMMARY")
        all_items["SUMMARY"] = check

    if draft_projects_path:
        with open(draft_projects_path) as f:
            projects = json.load(f)
        for proj in projects.get("projects", []):
            if proj.get("decision") != "DROP":
                proj_id = proj.get("id", "unknown")
                for section in ["objective", "action", "outcome"]:
                    if proj.get(section):
                        check = check_sentence_flow(proj[section], f"{proj_id}_{section}")
                        all_items[f"{proj_id}_{section}"] = check

    passing = sum(1 for c in all_items.values() if c["verdict"] == "PASS")
    return {
        "tool": "fragment_detector",
        "items": all_items,
        "summary": {
            "total": len(all_items),
            "passing": passing,
            "failing": len(all_items) - passing,
        }
    }


def main():
    """CLI usage."""
    if len(sys.argv) < 2:
        print("Usage: python fragment_detector.py --text 'sentence to check'")
        print("   or: python fragment_detector.py <draft_bullets.json> [summary.txt] [projects.json]")
        sys.exit(1)

    if sys.argv[1] == "--text":
        text = " ".join(sys.argv[2:])
        result = check_sentence_flow(text, "CLI_INPUT")
        print(f"Verdict: {result['verdict']}")
        if result["issues"]:
            for issue in result["issues"]:
                print(f"  ISSUE: {issue['description']}")
                print(f"  Fix: {issue['fix']}")
        else:
            print("  No sentence flow issues found.")
        return

    bullets_path = sys.argv[1] if len(sys.argv) > 1 else None
    summary_path = sys.argv[2] if len(sys.argv) > 2 else None
    projects_path = sys.argv[3] if len(sys.argv) > 3 else None

    results = check_draft_files(bullets_path, summary_path, projects_path)

    print(f"\nSENTENCE FLOW CHECK RESULTS")
    print(f"{'='*50}")
    print(f"Passing: {results['summary']['passing']} / {results['summary']['total']}")

    for item_id, check in results["items"].items():
        if check["verdict"] == "FAIL":
            print(f"[FAIL] {item_id}:")
            for issue in check["issues"]:
                print(f"       -> {issue['description']}")
                print(f"          Fix: {issue['fix']}")

    print("\n--- JSON OUTPUT ---")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
