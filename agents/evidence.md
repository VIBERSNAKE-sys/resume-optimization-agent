# EVIDENCE AGENT — Agent Instructions

## Role
Build the Evidence Ledger by mapping Q&A answers to Frozen Criticals. Select TOP2 roles. Assign bullet tiers. Run blocking Gates 1–6. Output `evidence_ledger.json`.

## Input
- `workspace/state/jd_ingestion_report.json`
- `workspace/state/archive_matches.json`
- `workspace/state/phase_b_answers.json`

## Output
`workspace/state/evidence_ledger.json`

---

## 1. KEY DEFINITIONS

**TOP2 WINDOW:** The first two roles on the resume (Role 1 = most recent, Role 2 = second most recent). These roles use the 27-word ceiling and receive full optimization attention.

**EVIDENCE-CLASS (E):** Evidence describes work personally executed, owned, or directly measured. The outcome can be claimed as the candidate's own.

**EXPOSURE-CLASS (X):** Evidence describes work participated in, supported, or observed without ownership. The candidate contributed but does not own the outcome.

**PRIME EXACT:** An exact JD phrase placed in a high-visibility location: Summary, Role1-B1, Role1-B2, or Skills. Never hosted in older roles.

**ORPHAN:** An exact JD phrase in Summary or Skills with no reflection in any body bullet.

---

## 2. EVIDENCE LEDGER CONSTRUCTION

### Step 1: Compile all answered questions
Merge `archive_matches.json` (Phase A answers) and `phase_b_answers.json` (Phase B answers) into a single evidence pool. Each answer has:
- Question ID
- Question text
- Answer text
- Evidence class (E or X, based on ownership described)
- Source role (RoleID or null if cross-role)
- Frozen Critical ID it addresses (null if no direct mapping)

### Step 2: Map evidence to Frozen Criticals
For each Frozen Critical from the ingestion report:
- Identify which answers provide direct evidence
- Classify coverage status:
  - **COVERED:** Evidence-class answer directly addresses the Critical
  - **PARTIAL:** Exposure-class answer, or Evidence-class answer that's adjacent but not direct
  - **GAP:** No answer addresses this Critical

### Step 3: Map evidence to roles
For each role in the resume:
- Collect all evidence items tagged to that role
- Classify each as E or X
- Count E-class items (needed for Gate 4)

### Step 4: Compile METRICS, TOOLS, REFRAMING, HIDDEN EVIDENCE, NARRATIVE STORIES
Extract and categorize from all answers:
- **METRICS:** Specific numbers with source role, baseline, and timeframe where known
- **TOOLS & METHODS:** Named tools/software/methodologies per role
- **REFRAMING DECISIONS:** APPROVED/REJECTED/PARTIAL with JD context
- **HIDDEN EVIDENCE:** Capabilities not on resume but confirmed via Phase B
- **NARRATIVE STORIES:** Origin stories, recognition events, key differentiators

---

## 3. TOP2 ROLE SELECTION

The TOP2 roles are the two most recent roles on the resume as listed in `employment_continuity.roles`. They are already identified in the ingestion report. Confirm them here.

TOP2 roles receive:
- 4 bullets each (or up to the allocation from ingestion report)
- 27-word bullet ceiling
- Full gate scrutiny (Gates 1, 1.5, 2, 3, 4, 6, 7 Tier 1 + Tier 2 if SENIOR/EXEC)

Non-TOP2 roles receive:
- 1–3 bullets per role (minimum 1, maximum 3)
- 25-word bullet ceiling
- Abbreviated gate scrutiny

---

## 4. BULLET TIER ASSIGNMENT

For each planned bullet slot across all roles, assign a tier based on evidence strength and Frozen Critical priority:

**Tier 1 (TOP2 roles — priority slots):**
- Must contain Evidence-class evidence
- Must address at least one Frozen Critical
- Must have metric or quantified outcome
- Bullet ordering within TOP2 roles: highest-priority Frozen Critical → lowest

**Tier 2 (TOP2 roles — supporting slots):**
- Evidence-class preferred; Exposure-class allowed (max 1 per role)
- Must address a Frozen Critical (variant acceptable)
- Metric preferred but not required

**Tier 3 (older roles):**
- 1–3 bullets per role (minimum 1)
- Must map to at least one Frozen Critical or be dropped
- Cannot create employment gaps by dropping entire role

**Bullet ordering rule within TOP2:** Sort bullets so the highest-priority Frozen Critical addressed appears first (B1), then descending priority. For ties: Evidence-class with metric > Evidence-class without metric > Exposure-class.

---

## 5. GATES 1–6 (BLOCKING)

All gates must show 0 violations. If any gate fails, pipeline halts with structured error. No downstream agent can override gate failures.

### Gate 1: Concrete Verb & Natural Language Check

BLOCKED if planned bullets would require:
- Conceptual verbs: Ensuring, facilitating, positioning, driving, enabling, leveraging, utilizing, demonstrating, applying (as lead), fostering, championing, spearheading (without concrete action)
- Keyword stuffing: "and [JD keyword]" artificially appended, multiple JD keywords in one bullet (>2), forced connectors ("while also", "additionally implementing")

This gate is checked during drafting, but Evidence Agent should flag if evidence pool would force these constructions.

### Gate 1.5: Framing Ladder Accuracy Check

BLOCKED if any bullet would use a verb tier higher than Evidence Ledger supports.

Framing Ladder (use HIGHEST accurate rung):
- **DELIVER verbs** (Built, Created, Developed): YOU produced the deliverable
- **COORDINATE verbs** (Coordinated, Directed, Managed): Others produced; you enabled
- **CONTRIBUTE verbs** (Supported, Assisted): Team outcome; your partial input

For each TOP2 bullet, the Evidence Agent must tag: who produced the primary deliverable per the evidence.

### Gate 2: Banned Phrase Check

BLOCKED if resume would contain:
- In Summary: "seeking", "passionate", "proven track record", "results-driven", "seasoned professional"
- Anywhere: "responsible for", "duties included", "helped with", "positioned [metric]"
- "Served as [title/role]", "Acted as [title/role]", "Functioned as [title/role]"
- "Implemented [vague noun]" without specifying what was implemented
- Defensive disclaimers: "while [team] handled", "though I didn't", "with [team] doing the"
- **Em dashes (—), en dashes (–), double hyphens (--) used as sentence breaks** — BANNED from all resume text
- Meta-defensive language: "without overstating", "not claiming", "while acknowledging limitations"

### Gate 3: Word Count Enforcement

BLOCKED if:
- Summary exceeds 75 words
- Any TOP2 bullet exceeds 27 words (hard ceiling) or falls below 18 words (floor)
- Any older role bullet exceeds 25 words (hard ceiling) or falls below 12 words (floor)

Target ranges (not ceilings):
- TOP2: target 22–26 words
- Older: target 14–18 words

Word counts MUST be verified by code execution, not estimation.

### Gate 4: Evidence Integrity Check

BLOCKED if:
- Fewer than 4 Evidence-class bullets in TOP2 window (first 6 bullets across top 2 roles)
- Prime exact hosted in an Exposure-class bullet
- Any metric appears without source attribution in the Evidence Ledger

Evidence-class quota for TOP2: ≥4 of 6 bullets must be Evidence-class.
Exposure-class quota for TOP2: ≤1 exposure-led bullet in first 6 bullets.

### Gate 5: Skills Concreteness Check (ADVISORY — does not block)

Flag (do not halt) if Skills section would contain:
- Abstract: "Stakeholder Engagement", "Relationship Management", "Communication", "Leadership", "Problem-Solving", "Strategic Planning"
- Activity-nouns ending in -tion, -ment, -ing without concrete basis

Skills concreteness test (4 tests in order):
1. **Tool/Software test:** Named tool someone could download or log into? → CONCRETE
2. **Method test:** Named methodology with defined steps? → CONCRETE
3. **Deliverable test:** Discrete, tangible artifact (countable, transferable, persistent)? → CONCRETE
4. **Certification test:** Could be tested or certified? → CONCRETE

If skill fails all 4 tests → ABSTRACT → replace or remove.

### Gate 6: MUST-Evidence Placement & Quality Check

BLOCKED if:
- Any JD MUST requirement lacks Evidence-class body placement
- MUST requirement appears but is not the PRIMARY focus of the bullet

PRIMARY focus test: Requirement appears in first half of bullet, OR is the direct object of the main action verb, OR the bullet would not exist without this requirement.

NOT primary focus: Appears in trailing "while also" or "ensuring" clause, is one of 3+ items in a list, appears only in a parenthetical.

---

## 6. OUTPUT JSON SCHEMA

Write `workspace/state/evidence_ledger.json`:

```json
{
  "run_id": "string",
  "timestamp": "ISO8601",
  "frozen_criticals": [
    {
      "id": "FC-1",
      "text": "",
      "tier": "MUST | LIKELY_MUST | ADVISORY",
      "coverage_status": "COVERED | PARTIAL | GAP",
      "evidence_entries": [
        {
          "question_id": "Q-001",
          "answer_summary": "",
          "evidence_class": "E | X",
          "source_role": "DOJ-1 | null"
        }
      ]
    }
  ],
  "must_coverage_summary": {
    "total_must": 0,
    "covered": 0,
    "partial": 0,
    "gap": 0,
    "gap_list": []
  },
  "metrics": [
    {
      "id": "M-001",
      "description": "",
      "value": "",
      "source_role": "DOJ-1",
      "baseline": "",
      "timeframe": "",
      "used_in_bullet": null
    }
  ],
  "reframing_decisions": [
    {
      "question_id": "Q-010",
      "jd_phrase": "",
      "proposed_framing": "",
      "decision": "APPROVED | REJECTED | PARTIAL",
      "rationale": ""
    }
  ],
  "tools_and_methods": [
    {
      "name": "",
      "source_role": "DOJ-1",
      "evidence_class": "E | X"
    }
  ],
  "hidden_evidence": [
    {
      "capability": "",
      "context": "",
      "source_role": "DOJ-1 | null"
    }
  ],
  "narrative_stories": [
    {
      "accomplishment": "",
      "origin_story": "",
      "key_differentiator_category": "Initiative | Recognition | Impact beyond role | Cross-functional influence | Problem-solving",
      "source_role": "DOJ-1"
    }
  ],
  "roles": [
    {
      "role_id": "DOJ-1",
      "is_top2": true,
      "evidence_class_counts": {"E": 0, "X": 0},
      "planned_bullets": [
        {
          "id": "DOJ-1-B1",
          "tier": 1,
          "frozen_critical_ids": ["FC-1"],
          "evidence_class": "E",
          "framing_ladder_tier": "DELIVER | COORDINATE | CONTRIBUTE",
          "evidence_summary": "",
          "metric_id": "M-001 | null",
          "draft_guidance": ""
        }
      ]
    }
  ],
  "top2_roles": ["DOJ-1", "IMF-1"],
  "gate_results": {
    "gate_1": "PASS | FAIL | PENDING",
    "gate_1_5": "PASS | FAIL | PENDING",
    "gate_2": "PASS | FAIL | PENDING",
    "gate_3": "PASS | FAIL | PENDING",
    "gate_4": "PASS | FAIL | PENDING",
    "gate_5": "PASS | ADVISORY_FLAG | PENDING",
    "gate_6": "PASS | FAIL | PENDING"
  },
  "gate_failures": [
    {
      "gate": "gate_4",
      "reason": "",
      "affected_bullet": "DOJ-1-B1 | null"
    }
  ],
  "summary_planned": {
    "word_target": "45-75",
    "exact_phrases_required": 2,
    "marquee_metric_id": "M-001 | null"
  },
  "skills_planned": {
    "target_count": "10-12",
    "flagged_abstract": []
  },
  "ledger_status": "COMPLETE | BLOCKED",
  "blocking_reason": ""
}
```

## 7. EXECUTION STEPS

1. Read all three input files
2. Compile evidence pool from archive matches + Phase B answers
3. Map evidence to Frozen Criticals → assign coverage status
4. Map evidence to roles → classify E/X
5. Extract metrics, tools, reframing decisions, hidden evidence, narrative stories
6. Confirm TOP2 roles from ingestion report
7. Assign bullet tiers for all planned bullets
8. Run Gates 1–6 checks against planned evidence
9. Write `evidence_ledger.json`
10. Print gate summary to stdout

## 8. BLOCKING CONDITIONS

If any blocking gate (1, 1.5, 2, 3, 4, 6) fails:
- Set `ledger_status` to "BLOCKED"
- Set `blocking_reason` to the gate failure description
- Write the JSON (do not leave empty)
- Exit with non-zero code and print gate failure details
- Pipeline halts; no downstream agent runs
