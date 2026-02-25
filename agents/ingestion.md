# INGESTION AGENT — Agent Instructions

## Role
Parse the job description, classify requirements, identify Frozen Criticals, run the Employment Continuity Check, and output `jd_ingestion_report.json`. This agent does NOT generate questions or access the Q&A Archive.

## Input
- `workspace/input/job_description.txt` — raw JD text
- `workspace/input/resume.txt` — base resume text, extracted from `templates/Resume Template.docx` at pipeline start. This is the canonical source for role order, existing bullet text, project entries, education, and certifications. Do NOT treat it as optional.
- `workspace/config/pipeline_config.json` — run metadata

## Output
`workspace/state/jd_ingestion_report.json`

---

## 1. REQUIREMENT CLASSIFICATION

### Classification Decision Logic

Apply these steps IN ORDER for each extracted requirement:

**Step 1: Section header check (highest authority)**
The section header the requirement falls under overrides all bullet-level signals.
- Header contains "Required" / "Must Have" / "Minimum" / "Required Qualifications" / "Minimum Qualifications" / "Basic Qualifications" → **MUST**
- Header contains "Preferred" / "Nice to Have" / "Plus" / "Bonus" / "Desired" → **ADVISORY**
- Header is "Qualifications" alone (without Required/Minimum/Basic modifier) → AMBIGUOUS → proceed to bullet-level analysis (Steps 2–6). If no MUST signals found, classify as LIKELY_MUST.
- No labeled header, or requirement appears before any header → proceed to Step 2.

**Step 2: MUST signals in text** → **MUST**
Signals: "required", "must have", "must be", "need", "essential", "mandatory"

**Step 3: ADVISORY signals in text** → **ADVISORY**
Signals: "preferred", "desired", "nice to have", "plus", "bonus", "ideally"

**Step 4: Work style / values only** → **SOFT**

**Step 5: Describes core job function** → **LIKELY_MUST**

**Step 6: Unclear** → **LIKELY_MUST** (conservative default)

**CRITICAL:** Header classification (Step 1) OVERRIDES bullet-level signals (Steps 2–6) in BOTH directions. A requirement under a "Required" header is MUST even if the text sounds soft. A requirement under a "Preferred" header is ADVISORY even if it sounds critical.

**Mixed signals rule:** If requirement contains both MUST and ADVISORY signals, classify by dominant signal. "Required" dominates "preferred."

### Auto-Drop Rules
Remove from consideration:
- EEO/legal boilerplate
- Benefits/perks/logistics (visa, relocation, interview windows)
- Company mission/values boilerplate

### Normalization
- Keep multi-word noun phrases (2–6 tokens)
- Preserve acronyms as-is
- Convert slashes/hyphens to spaces EXCEPT canonical: CI/CD, ISO/IEC 27001, SSO/MFA

---

## 2. JD INGESTION REPORT

### Target Role Level Detection
Auto-detect from title and years required:
- Title contains "Director", "VP", "Principal", "Chief", "Head of" → EXECUTIVE
- Title contains "Junior", "Associate", "Entry", "Intern", "Graduate" → ENTRY
- Years required 0–2 → ENTRY
- Title contains "Senior" or "Lead" AND years required >= 7 → SENIOR
- Title contains "Senior" or "Lead" OR years required >= 5 → SENIOR
- Years required >= 3 OR title contains "Specialist", "Analyst", "Coordinator" → MID
- Default → MID

### Application Type Detection
1. Target role at current employer → INTERNAL_TRANSFER
2. Most recent 2 roles in same function AND industry as target → SAME_FIELD
3. Otherwise → CAREER_CHANGE

### Parsing Confidence Calculation
```
Parsing Confidence = (Clearly Classifiable Requirements / Total Requirements) × 100
```
Clearly classifiable = has explicit MUST signal, explicit ADVISORY signal, or labeled header.
If < 80% → flag "LOW: recommend JD_CORE confirm"

### Frozen Criticals Selection
Target count: 10–12 Criticals

Selection process:
1. Start with ALL MUST requirements
2. If MUST count < 10: add LIKELY_MUST items in JD order until count reaches 10
3. If MUST count is 10–12: stop
4. If MUST count > 12: keep all MUST (do not cap)
5. If MUST + LIKELY_MUST < 10: add top ADVISORY items until count reaches 10

Priority within each tier (all else equal):
- Evidence available in resume > no evidence
- Domain-specific > generic
- Early JD position > late

For each Frozen Critical, check the resume for supporting evidence (Y/N).

---

## 3. EMPLOYMENT CONTINUITY CHECK

### Definitions
- Each unique (Company + Title + Date Range) combination = 1 position
- Promotion within same company with new title = separate position
- Same title, same company, continuous dates = 1 position

### RoleID Format
`[CompanyAbbrev]-[SequenceNumber]` where sequence 1 = most recent at that company.
Examples: DOJ-1, IMF-1, IMF-2

### Canonical Role List
The base resume (`workspace/input/resume.txt`) defines the authoritative role list. Extract all roles from it in the order they appear. The current role list is:

| RoleID | Company | Title | Dates |
|--------|---------|-------|-------|
| DOJ-1 | Department of Justice (Contractor via Amentum) | International Criminal Investigative Training Assistance Program Regional Advisor | 07/2024 – 07/2025 |
| IMF-1 | International Monetary Fund | Lead Division Coordinator, Asia & Pacific Department – Pacific Islands Division | 04/2022 – 07/2024 |
| IMF-2 | International Monetary Fund | Staff Coordinator, Asia & Pacific Department – Front Office | 03/2020 – 04/2022 |
| IMF-3 | International Monetary Fund | Special Office Support Staff Assistant, Human Resources Department | 03/2019 – 03/2020 |
| IMF-4 | International Monetary Fund (Contractor via Global Employment Solutions) | Junior Office Coordinator | 12/2018 – 03/2019 |
| DOES-1 | DC Department of Employment Services | Program Analyst, Office of Legislative Affairs | 12/2016 – 12/2018 |
| DOES-2 | DC Department of Employment Services | Legislative Affairs Assistant, Office of Legislative Affairs | 12/2015 – 12/2016 |
| SENATE-1 | United States Senate | Legislative Intern | 07/2015 – 12/2015 |

TOP2 roles are always DOJ-1 and IMF-1 (the two most recent).

### Check Process
1. List all roles from resume with RoleIDs
2. Count original positions
3. Plan D2 bullet allocation (4 bullets for TOP2, 2–3 for others, minimum 1 per role)
4. Verify: original count = planned count (no deletions)
5. Status: PASS if all roles preserved, FAIL if any missing

**Deletion is NEVER allowed.** Very old roles (pre-2015) may be listed under "Additional Experience" without bullets but must appear.

---

## 4. GATE 0 QUESTION GENERATION STUB

For Phase 1 MVP, generate the list of Gate 0 questions based on:
- Frozen Criticals with no resume evidence
- Metrics that appear vague or unquantified in resume
- Hidden evidence opportunities
- Reframing questions (CAREER_CHANGE only: minimum 4)

Question allocation:
- Base: determined by MUST gap count (1–2 per gap)
- Metric opportunities: 1 per unquantified bullet in TOP2 roles
- Technical depth: 1–2 per role if tools unclear
- Hidden evidence: minimum 2
- Narrative: 2–4
- Reframing: minimum 4 if CAREER_CHANGE, 1–2 otherwise
- Total range: 12–34 questions

Output questions as a list in `gate_0_questions_pending` array of the JSON.

---

## 5. OUTPUT JSON SCHEMA

Write `workspace/state/jd_ingestion_report.json` with this exact structure:

```json
{
  "run_id": "string",
  "jd_file": "string",
  "resume_file": "string",
  "target_role": "string",
  "target_company": "string",
  "timestamp": "ISO8601",
  "input_mode": "JD_RAW",
  "application_type": "CAREER_CHANGE | SAME_FIELD | INTERNAL_TRANSFER",
  "target_role_level": "EXECUTIVE | SENIOR | MID | ENTRY",
  "role_level_detection_path": "string",
  "parsing_confidence_pct": 0,
  "parsing_confidence_status": "OK | LOW",
  "raw_lines_count": 0,
  "pruned_lines_count": 0,
  "requirements": {
    "MUST": [{"text": "", "evidence_on_resume": false}],
    "LIKELY_MUST": [{"text": "", "evidence_on_resume": false}],
    "ADVISORY": [{"text": "", "evidence_on_resume": false}],
    "SOFT": [{"text": ""}]
  },
  "classification_counts": {
    "MUST": 0,
    "LIKELY_MUST": 0,
    "ADVISORY": 0,
    "SOFT": 0
  },
  "frozen_criticals": [
    {
      "id": "FC-1",
      "text": "",
      "tier": "MUST | LIKELY_MUST | ADVISORY",
      "evidence_on_resume": false,
      "jd_position": 0
    }
  ],
  "frozen_criticals_count": 0,
  "ambiguous_headers": [],
  "employment_continuity": {
    "roles": [
      {
        "role_id": "DOJ-1",
        "company": "",
        "title": "",
        "start_date": "",
        "end_date": "",
        "planned_bullet_count": 0,
        "is_top2": false
      }
    ],
    "original_position_count": 0,
    "d2_position_count": 0,
    "top2_roles": [],
    "status": "PASS | FAIL",
    "failure_reason": ""
  },
  "gate_0_questions_pending": [
    {
      "id": "Q-001",
      "category": "CRITICAL_GAP | METRIC | TECHNICAL | HIDDEN | REFRAMING | NARRATIVE",
      "frozen_critical_id": "FC-1 | null",
      "question_text": "",
      "role_context": "DOJ-1 | null"
    }
  ],
  "ingestion_status": "COMPLETE | FAILED",
  "failure_reasons": []
}
```

## 6. EXECUTION STEPS

1. Read `workspace/input/job_description.txt` and `workspace/input/resume.txt`
2. Read `workspace/config/pipeline_config.json` for run_id and metadata
3. Parse JD: extract all requirements, classify each per Section 1
4. Calculate parsing confidence
5. Detect target role level and application type
6. Select Frozen Criticals per Section 2
7. Check each Frozen Critical against resume for evidence (Y/N)
8. Run Employment Continuity Check per Section 3
9. Generate Gate 0 question list per Section 4
10. Write `jd_ingestion_report.json`
11. Print summary to stdout: role, level, application type, classification counts, Frozen Critical count, employment check status

## 7. BLOCKING CONDITIONS

Stop and write error to JSON if:
- Job description file is empty or unreadable
- Employment Continuity Check fails (roles missing from D2 plan)
- Fewer than 5 requirements could be classified (likely corrupt input)
