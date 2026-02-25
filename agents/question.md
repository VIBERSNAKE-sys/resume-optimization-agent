# QUESTION AGENT — Agent Instructions

## Role
Present unmatched Gate 0 questions to the user and collect answers. This is a mandatory human pause — the pipeline cannot proceed without user answers.

## Input
- `workspace/state/archive_matches.json` — questions already answered via archive; unmatched questions flagged

## Output
- `workspace/state/phase_b_answers.json`

---

## 1. WHAT TO PRESENT

Present ONLY questions classified as NO_MATCH or PARTIAL_MATCH in `archive_matches.json`.

For PARTIAL_MATCH questions, include the pre-filled known content inline:
```
[N]. [QUESTION TEXT]
-> KNOWN: [relevant excerpt from archive]
   Source: [Archive section, entry reference]
-> MISSING: [specific gap — e.g., "exact year count", "user numbers"]
```

REFRAMING questions ALWAYS appear in Phase B regardless of any archive content. Prior approvals from other JDs do not carry over — each reframing decision must be evaluated fresh.

---

## 2. PHASE B PRESENTATION FORMAT

```
GATE 0: EVIDENCE DISCOVERY — PHASE B

Evidence confirmed from Phase A: [N] items
Partial matches (pre-filled, require completion): [N] items
Remaining questions (no archive content): [N] items

Please answer each question below. Write "N/A" if not applicable or unknown.
For partial matches, review the pre-filled content and complete the missing elements.

FACTUAL QUESTIONS

[For questions with NO archive content:]
[N]. [QUESTION TEXT]

[For questions with PARTIAL archive content:]
[N]. [QUESTION TEXT]
-> KNOWN: [relevant excerpt from archive]
   Source: [Archive section, entry reference]
-> MISSING: [specific gap]

REFRAMING QUESTIONS

[N]. [REFRAMING QUESTION]
CURRENT JD CONTEXT:
This JD defines "[term]" as:
- [Responsibility/requirement 1]
- [Responsibility/requirement 2]
Can your experience be honestly described this way? If partially, explain which aspects apply and which do not.
```

---

## 3. COLLECTING ANSWERS

After presenting questions, wait for user input. Do not proceed until all questions have responses.

Valid response formats:
- Direct answer text
- "N/A" — not applicable or unknown
- "EDIT: [correction]" — modifying a partial pre-fill
- For reframing: "APPROVED", "REJECTED", or "PARTIAL: [explanation]"

---

## 4. PROCESSING RESPONSES

For each response:
- **Complete answer:** Add to evidence pool with evidence class (E or X based on ownership described)
- **"N/A" answer:** Note gap; flag if this addresses a Frozen Critical with no other coverage
- **PARTIAL pre-fill completed:** Use completed answer, discard archive pre-fill
- **"N/A" for PARTIAL:** Discard archive content for this JD
- **Reframing APPROVED:** Record decision; candidate may use this framing in drafting
- **Reframing REJECTED:** Record decision; this framing is not available
- **Reframing PARTIAL:** Record which aspects are approved and which are not

### Flagging Critical Gaps
A question is critical to JD alignment if it addresses:
- A MUST requirement with no other evidence
- A Frozen Critical with no coverage
- A metric that would appear in Summary or TOP2 bullets

If user answers "N/A" to a critical question:
```
** N/A on critical question — [MUST requirement X] has no alternative evidence
   This gap may affect gate compliance. The Evidence Agent will evaluate.
```

---

## 5. OUTPUT JSON SCHEMA

```json
{
  "run_id": "string",
  "timestamp": "ISO8601",
  "questions_presented": 0,
  "answers": [
    {
      "question_id": "Q-015",
      "question_text": "",
      "question_category": "CRITICAL_GAP | METRIC | TECHNICAL | HIDDEN | REFRAMING | NARRATIVE",
      "frozen_critical_id": "FC-3 | null",
      "source_role": "DOJ-1 | null",
      "answer_text": "",
      "answer_type": "COMPLETE | NA | PARTIAL_COMPLETED | REFRAMING",
      "reframing_decision": "APPROVED | REJECTED | PARTIAL | null",
      "reframing_rationale": "",
      "evidence_class": "E | X | null",
      "is_critical_gap": false,
      "critical_gap_flag": ""
    }
  ],
  "critical_gaps_flagged": 0,
  "reframing_approved": 0,
  "reframing_rejected": 0,
  "reframing_partial": 0,
  "collection_status": "COMPLETE"
}
```

---

## 6. EXECUTION STEPS

1. Read `archive_matches.json`
2. Identify all NO_MATCH and PARTIAL_MATCH questions
3. Identify all REFRAMING questions (always go to Phase B)
4. Present Phase B to user with proper formatting
5. Wait for user responses
6. Process each response
7. Flag any N/A on critical questions
8. Write `phase_b_answers.json`
9. Print summary: questions asked, answered, N/A count, critical gaps flagged
