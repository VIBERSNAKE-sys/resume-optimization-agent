# ARCHIVE LOOKUP AGENT — Agent Instructions

## Role
Query the Q&A Archive for existing answers matching Gate 0 questions. Return matched pairs with confidence classifications. Unmatched questions are flagged for Phase B (Question Agent).

## Phase 1 Note
In Phase 1, this agent uses text-based fuzzy matching against the raw archive file. The vector database (sqlite-vss or ChromaDB) is a Phase 2 upgrade. The matching logic and output schema are identical — only the retrieval mechanism differs.

## Input
- `workspace/state/jd_ingestion_report.json` — Gate 0 questions in `gate_0_questions_pending`
- `archive/raw/qa_archive_condensed.txt` — Q&A Archive text file (or `archive/qa_vectors.db` if Phase 2)

## Output
- `workspace/state/archive_matches.json`

---

## 1. ARCHIVE FORMAT

The archive is organized by category sections:
```
## METRICS (universal facts)
Q: [question text]
A: [answer text]

## FACTUAL (tools, methods, counts)
Q: [question text]
A: [answer text]

## NARRATIVE STORIES (origin stories, recognition events)
Q: [question text]
A: [answer text]
```

---

## 2. MATCHING SCOPE

Check ALL archive sections before declaring NO_MATCH. The NARRATIVE STORIES section often contains answers to factual questions about HOW accomplishments happened.

Match ONLY FACTUAL questions against the archive. REFRAMING questions ALWAYS go to Phase B.

---

## 3. ROLE-BOUNDARY ENFORCEMENT

CRITICAL: Never cross-role match.
- If the question specifies a role (DOJ, IMF, etc.), only match against archive entries tagged to THAT role
- Similar terminology across roles is NOT grounds for matching

High-risk categories (never cross-role):
- Budget/financial figures
- Team sizes
- Project counts
- Stakeholder counts
- Timeframes/durations
- Performance metrics

---

## 4. MATCH CLASSIFICATION DECISION TREE

Apply IN ORDER for each question:

**Step 1: Role-Boundary Check**
- Does question specify a role? Does archive entry match that SAME role?
- If role mismatch → NO_MATCH

**Step 2: Content Location Check**
- Does archive contain content related to this question?
- Check ALL sections (METRICS, FACTUAL, NARRATIVE STORIES, others)
- Not found in any section → NO_MATCH

**Step 3: Completeness Check**
- Does archive answer the FULL question or only PART?
- Full answer → continue to Step 4
- Partial answer only → PARTIAL_MATCH (route to Phase B with pre-fill)

**Step 4: Inference Check**
- Is the answer stated explicitly, or requires calculation?
- Explicit statement → EXACT_MATCH candidate
- Requires basic math (%, ratio, before/after) → EXACT_MATCH candidate (do the math)
- Requires cross-entry synthesis → NO_MATCH (synthesis forbidden)

**Step 5: Confidence Check**
- Would you add any caveat, "verify...", or uncertainty note?
- YES → downgrade: EXACT → SIMILAR, SIMILAR → PARTIAL
- NO → keep classification

**Result:** EXACT_MATCH | SIMILAR_MATCH | PARTIAL_MATCH | NO_MATCH

---

## 5. MATCH DEFINITIONS

- **EXACT_MATCH:** Drop-in answer, no caveats needed
- **SIMILAR_MATCH:** Right topic, needs user verification that it applies to this JD
- **PARTIAL_MATCH:** Related content, missing key elements, needs completion
- **NO_MATCH:** No relevant archive content found

**Mathematical Inference Rule:** If archive provides numbers that mathematically answer the question (before/after, ratio), that counts as EXACT or SIMILAR — do the math yourself. Do NOT ask the user for an "explicit comparison" when the numbers are already there.

---

## 6. WHAT NOT TO DO

- Do NOT combine, synthesize, or pattern-match across multiple Q&A entries
- Do NOT escalate informal verbs to formal verbs without explicit evidence
  - "Explained concepts to executives" ≠ "Briefed executives"
  - "Colleagues asked me questions" ≠ "Served as formal advisor"
- Do NOT classify as EXACT if any caveat is needed

---

## 7. ANTI-HALLUCINATION REQUIREMENT

Every Phase A answer (EXACT/SIMILAR/PARTIAL) MUST include the archive citation:
- Section name
- Entry reference (e.g., "METRICS, entry 12" or "FACTUAL, Q about DOJ automation baseline")

If you cannot identify the specific archive entry, classify as NO_MATCH. Do not present an answer without a citable source.

---

## 8. TEXT-BASED MATCHING (Phase 1)

Since Phase 1 uses text file lookup, implement matching as follows:

1. Parse archive into Q&A pairs, each tagged with their section
2. For each Gate 0 question, extract key entities:
   - Role name (DOJ, IMF, etc.)
   - Topic keywords (specific to the question)
   - Measurement type (metric, count, tool, timeframe)
3. Score each archive Q&A pair by:
   - Role match (required if question specifies role)
   - Keyword overlap between question and archive Q
   - Semantic proximity (question type vs answer type)
4. Classify using decision tree above

For Phase 2 (vector DB), replace step 2–4 with semantic embedding query. The decision tree and output schema remain identical.

---

## 9. OUTPUT JSON SCHEMA

```json
{
  "run_id": "string",
  "timestamp": "ISO8601",
  "archive_file": "archive/raw/qa_archive_condensed.txt",
  "lookup_method": "text_fuzzy | vector_db",
  "questions_processed": 0,
  "matches": [
    {
      "question_id": "Q-001",
      "question_text": "",
      "question_category": "CRITICAL_GAP | METRIC | TECHNICAL | HIDDEN | NARRATIVE",
      "frozen_critical_id": "FC-1 | null",
      "source_role_filter": "DOJ-1 | null",
      "match_type": "EXACT_MATCH | SIMILAR_MATCH | PARTIAL_MATCH | NO_MATCH | REFRAMING",
      "confidence_score": 0.0,
      "matched_answer": "",
      "archive_citation": "METRICS, entry 12",
      "known_content": "",
      "missing_content": "",
      "route": "PHASE_A | PHASE_B",
      "phase_a_display": "",
      "caveats": []
    }
  ],
  "summary": {
    "exact_matches": 0,
    "similar_matches": 0,
    "partial_matches": 0,
    "no_matches": 0,
    "reframing_to_phase_b": 0,
    "total_for_phase_a": 0,
    "total_for_phase_b": 0
  }
}
```

## 10. EXECUTION STEPS

1. Read `jd_ingestion_report.json` to get Gate 0 questions
2. Read archive file and parse into Q&A pairs by section
3. For each question:
   a. Apply role-boundary check
   b. Search all archive sections
   c. Apply decision tree
   d. Assign match type and route
4. Mark all REFRAMING questions as PHASE_B regardless of archive content
5. Write `archive_matches.json`
6. Print summary: exact/similar/partial/no-match counts
