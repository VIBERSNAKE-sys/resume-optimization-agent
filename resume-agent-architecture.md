# Resume Optimization Agent System — Architecture Document

**Version:** 0.1 (Initial Design)
**Date:** February 25, 2026
**Status:** Design Phase

---

## 1. System Overview

This document defines the architecture for an autonomous, multi-agent resume optimization system built on Claude Code's Agent SDK. The system replaces the current three-module prompt-based workflow (executed manually in Claude.ai conversations) with a pipeline of specialized agents that execute independently, pass structured state between stages, and pause only when genuine human input is required.

A meta-level **Improvement Agent** observes pipeline performance over time and proposes architectural refinements — moving the system from accumulated guardrails toward structural constraints.

### 1.1 Design Principles

1. **Separation of concerns.** No agent both drafts and verifies its own output.
2. **Structured state passing.** All inter-agent communication happens through typed JSON files, not conversation context.
3. **Minimal human interruption.** The pipeline pauses for human input only at defined decision points, not for mechanical handoffs.
4. **Observable performance.** Every gate decision, draft revision, and human override is logged to a structured performance record.
5. **Earned autonomy.** The Improvement Agent begins as read-only analyst. Autonomy expands based on demonstrated judgment.

---

## 2. Agent Architecture

### 2.1 Agent Inventory

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR AGENT                          │
│         Coordinates pipeline, manages state, routes to human       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   INGESTION  │───▶│   ARCHIVE    │───▶│   QUESTION           │  │
│  │   AGENT      │    │   LOOKUP     │    │   AGENT              │  │
│  │              │    │   AGENT      │    │   (→ Human)          │  │
│  │  JD parsing, │    │              │    │                      │  │
│  │  classifica- │    │  Vector DB   │    │  Phase A match,      │  │
│  │  tion, FC    │    │  query for   │    │  Phase B generation, │  │
│  │  extraction  │    │  existing    │    │  answer collection   │  │
│  │              │    │  answers     │    │                      │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│         │                                         │                 │
│         ▼                                         ▼                 │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    EVIDENCE AGENT                            │   │
│  │                                                              │   │
│  │  Builds Evidence Ledger from archive answers + JD report.    │   │
│  │  Maps evidence to Frozen Criticals. Runs blocking gates 1-6. │   │
│  │  Selects TOP2 roles, assigns tiers, builds bullet drafts.    │   │
│  │                                                              │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   DRAFTING   │───▶│ VERIFICATION │───▶│   DECISION POINT     │  │
│  │   AGENT      │    │ AGENT        │    │   AGENT (→ Human)    │  │
│  │              │    │              │    │                      │  │
│  │  Writes      │    │  Separate    │    │  Surfaces dedup,     │  │
│  │  bullets,    │    │  context.    │    │  pruning, revision   │  │
│  │  summary,    │    │  Code-based  │    │  choices to user.    │  │
│  │  projects,   │    │  word count. │    │  Collects decisions. │  │
│  │  skills      │    │  Gate 7      │    │                      │  │
│  │              │    │  checks.     │    │                      │  │
│  │              │    │  No access   │    │                      │  │
│  │              │    │  to drafter  │    │                      │  │
│  │              │    │  reasoning.  │    │                      │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                                                   │                 │
│                                                   ▼                 │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    ASSEMBLY AGENT                            │   │
│  │                                                              │   │
│  │  Takes verified bullets + human decisions.                   │   │
│  │  Generates D2 (final resume). Runs Gate 8 checks.           │   │
│  │  Produces .docx output file.                                 │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   IMPROVEMENT AGENT                          │   │
│  │                                                              │   │
│  │  Reads performance logs across runs. Identifies failure      │   │
│  │  patterns. Proposes architectural changes. Tests proposals   │   │
│  │  against historical data. Reports to human for approval.     │   │
│  │                                                              │   │
│  │  PHASE 3: Read-only analyst → PHASE 4: Auto-test proposals  │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Agent Specifications

#### ORCHESTRATOR AGENT
- **Role:** Pipeline coordinator. Manages execution sequence, state file routing, and human interaction points.
- **Context:** Lightweight. Knows pipeline structure and state file locations. Does NOT load module instructions.
- **Tools:** File read/write, subprocess spawning (subagents), user prompt/response.
- **Triggers:** User initiates with JD file path or slash command (`/resume <jd-file>`).
- **Output:** Final resume file path + performance log path.

#### INGESTION AGENT (replaces Module 1, Sections 1-5)
- **Role:** Parse job description, classify requirements (MUST / LIKELY_MUST / NICE_TO_HAVE / ADVISORY), extract Frozen Criticals, run Employment Continuity Check.
- **Context:** JD classification rules only. ~5 pages of focused instructions.
- **Tools:** File read, text parsing.
- **Input:** Raw JD text file.
- **Output:** `jd_ingestion_report.json` — structured classification with header signals, bullet-level analysis, Frozen Critical list, continuity flags.
- **Key architectural constraint:** "Qualifications" header triggers bullet-level analysis (ambiguous handling). Compound headers ("Required Qualifications," "Minimum Qualifications") map to MUST.

#### ARCHIVE LOOKUP AGENT (replaces Module 1, Phase A)
- **Role:** Query the Q&A Archive for existing answers that match Gate 0 questions.
- **Context:** Archive access only. No JD classification rules.
- **Tools:** Vector database query (see Section 3.2), fuzzy matching.
- **Input:** `jd_ingestion_report.json` + generated Gate 0 questions.
- **Output:** `archive_matches.json` — matched Q/A pairs with confidence scores, unmatched questions flagged for Phase B.
- **Key architectural constraint:** Vector DB replaces full-archive-in-context. Solves the "lost in the middle" problem that caused Phase A hallucination.

#### QUESTION AGENT (replaces Module 1, Phase B) → HUMAN PAUSE
- **Role:** Present unmatched questions to user, collect answers.
- **Context:** Unmatched questions only. No archive, no JD.
- **Tools:** User prompt/response interface.
- **Input:** `archive_matches.json` (unmatched questions only).
- **Output:** `phase_b_answers.json` — user-provided answers keyed to question IDs.
- **Human interaction:** This is a mandatory pause. Pipeline cannot proceed without user answers.

#### EVIDENCE AGENT (replaces Module 2, Sections 1-3)
- **Role:** Build Evidence Ledger by mapping archive matches + Phase B answers to Frozen Criticals. Select TOP2 roles. Assign bullet tiers. Run blocking Gates 1-6.
- **Context:** Frozen Critical list, classification rules, evidence mapping logic, gate criteria. ~10 pages.
- **Tools:** File read/write, structured data manipulation.
- **Input:** `jd_ingestion_report.json` + `archive_matches.json` + `phase_b_answers.json`.
- **Output:** `evidence_ledger.json` — evidence mapped to FCs, role tiers, gate pass/fail status, bullet tier assignments.
- **Key architectural constraint:** Gates 1-6 are blocking. If any gate fails, pipeline halts with structured error. No downstream agent can override.

#### DRAFTING AGENT (replaces Module 2, Section 4)
- **Role:** Write bullet text, professional summary, project PAR entries, skills section.
- **Context:** Drafting rules only — NON-NEGOTIABLES, framing guidance, terminology translation, em dash ban, "Served as" ban, metadata leakage ban. ~15 pages.
- **Tools:** Text generation.
- **Input:** `evidence_ledger.json`.
- **Output:** `draft_bullets.json` — all drafted text with role/bullet IDs. Also `draft_summary.txt`, `draft_projects.json`, `draft_skills.json`.
- **Key architectural constraint:** Drafting Agent does NOT self-verify. It produces text and hands off. No word count assertions, no gate checks, no "this bullet is 27 words" claims.

#### VERIFICATION AGENT (replaces Module 2, Gates 7 + Section 7)
- **Role:** Independent verification of all drafted text. Code-based word counts. Gate 7 show-your-work analysis for TOP2 bullets. Sentence flow, em dash, fragment, and banned-phrase checks for all text. Cross-resume verb deduplication scan.
- **Context:** Gate criteria + drafted text ONLY. Does NOT receive Drafting Agent's reasoning, target counts, or self-assessments. ~8 pages.
- **Tools:** Python code execution (word counting), text analysis, file read/write.
- **Input:** `draft_bullets.json`, `draft_summary.txt`, `draft_projects.json`, `draft_skills.json`.
- **Output:** `verification_report.json` — per-bullet/per-text pass/fail with code-verified counts and written analysis. Failing items include specific failure reason and revision guidance.
- **Key architectural constraint:** This is the core anti-verification-theater mechanism. The Verification Agent literally cannot rubber-stamp because it never sees the drafter's work notes. It receives only the text and the rules.
- **Revision loop:** Failing items return to Drafting Agent with failure reasons. Maximum 2 revision cycles per item before escalation to human.

#### DECISION POINT AGENT (replaces Module 2, Decision Point Summary) → HUMAN PAUSE
- **Role:** Surface all items requiring human judgment — deduplication choices, pruning recommendations, revision trade-offs, older-role bullet relevance flags.
- **Context:** Decision points only. Presents options clearly with trade-off analysis.
- **Tools:** User prompt/response interface.
- **Input:** `verification_report.json` + `evidence_ledger.json` (decision-relevant subset).
- **Output:** `human_decisions.json` — user choices keyed to decision IDs.
- **Human interaction:** Mandatory pause. Presents structured choices, not open-ended questions.

#### ASSEMBLY AGENT (replaces Module 3)
- **Role:** Assemble final resume (D2) from verified bullets + human decisions. Run Gate 8 (human authenticity, overall coherence). Generate .docx output.
- **Context:** Assembly rules, D2 template structure, Gate 8 criteria. ~8 pages.
- **Tools:** File read/write, python-docx for document generation, code execution.
- **Input:** `verification_report.json` (passed items only) + `human_decisions.json` + `draft_summary.txt` + `draft_projects.json` + `draft_skills.json`.
- **Output:** `final_resume.docx` + `assembly_report.json` (Gate 8 results, final word counts, section structure).

#### IMPROVEMENT AGENT (new — no current module equivalent)
- **Role:** Analyze performance across pipeline runs. Identify failure patterns. Propose architectural improvements. Test proposals against historical data.
- **Context:** Performance logs from all runs. Module instruction files. Historical failure catalog.
- **Tools:** File read/write, data analysis, code execution for statistical analysis.
- **Input:** `performance_log.json` (accumulated across all runs).
- **Output:** `improvement_proposal.json` — proposed changes with: failure pattern identified, root cause analysis, proposed fix (patch vs. architectural), expected impact, regression test results.
- **Key architectural constraint:** Phase 3 = read-only analyst (proposals require human approval). Phase 4 = auto-test (can run proposals against historical data and present results, but still requires human approval to implement).
- **Anti-sycophancy constraint:** Every proposal must trace to a specific, documented failure pattern with measurable before/after criteria. Proposals that cannot cite specific failed runs are rejected.

---

## 3. Infrastructure Components

### 3.1 State Files (Inter-Agent Communication)

All agents communicate through structured JSON files in a shared workspace directory.

```
/workspace/
├── config/
│   ├── pipeline_config.json          # Global settings, file paths
│   └── user_preferences.json         # Style preferences, name, etc.
├── input/
│   └── job_description.txt           # Raw JD text
├── state/
│   ├── jd_ingestion_report.json      # Ingestion Agent output
│   ├── archive_matches.json          # Archive Lookup output
│   ├── phase_b_answers.json          # Question Agent output (human)
│   ├── evidence_ledger.json          # Evidence Agent output
│   ├── draft_bullets.json            # Drafting Agent output
│   ├── draft_summary.txt             # Drafting Agent output
│   ├── draft_projects.json           # Drafting Agent output
│   ├── draft_skills.json             # Drafting Agent output
│   ├── verification_report.json      # Verification Agent output
│   └── human_decisions.json          # Decision Point Agent output (human)
├── output/
│   ├── final_resume.docx             # Assembly Agent output
│   └── assembly_report.json          # Assembly Agent output
├── logs/
│   ├── run_<timestamp>.json          # Per-run performance log
│   └── performance_log.json          # Accumulated cross-run log
└── archive/
    └── qa_vectors.db                 # Vector database (see 3.2)
```

### 3.2 Q&A Archive — Vector Database

**Problem:** Current Q&A Archive is a flat text file (~1,560 lines after condensation). Loading it into LLM context causes "lost in the middle" degradation. Phase A hallucination incident traced directly to archive size exceeding model's reliable search capacity.

**Solution:** Convert archive to vector database with semantic search.

**Implementation:**
- **Storage:** SQLite + vector extension (sqlite-vss) or ChromaDB for local operation.
- **Indexing:** Each Q&A pair stored as a document. Question text embedded for semantic search. Answer text stored as retrieval payload.
- **Query:** Archive Lookup Agent queries with Gate 0 question text. Returns top-k matches with similarity scores. Confidence threshold determines EXACT MATCH vs. PARTIAL MATCH vs. NO MATCH.
- **Maintenance:** New Phase B answers appended to vector DB after each run. Periodic deduplication.
- **Migration:** One-time script to parse existing Q&A Archive text file, chunk into Q&A pairs, embed, and load into vector DB.

### 3.3 Performance Logging Schema

Every pipeline run generates a structured performance log.

```json
{
  "run_id": "run_20260225_143022",
  "timestamp": "2026-02-25T14:30:22Z",
  "jd_file": "openai_policy_manager.txt",
  "target_role": "AI Public Policy Manager",

  "ingestion": {
    "classifications": {
      "MUST": 6,
      "LIKELY_MUST": 5,
      "NICE_TO_HAVE": 1,
      "ADVISORY": 1
    },
    "frozen_criticals": 12,
    "ambiguous_headers": ["Qualifications"],
    "duration_seconds": 8
  },

  "archive_lookup": {
    "questions_generated": 26,
    "exact_matches": 21,
    "partial_matches": 2,
    "no_matches": 3,
    "duration_seconds": 3
  },

  "evidence": {
    "gate_results": {
      "gate_1": "PASS",
      "gate_2": "PASS",
      "gate_3": "PASS",
      "gate_4": "PASS",
      "gate_5": "PASS",
      "gate_6": "PASS"
    },
    "top2_roles": ["DOJ", "IMF_Coordinator_1"],
    "total_bullets_drafted": 18,
    "duration_seconds": 15
  },

  "verification": {
    "gate_7_results": [
      {
        "bullet_id": "DOJ-B1",
        "tier": "TOP2",
        "word_count": 25,
        "word_count_method": "code_execution",
        "check_1_sentence_flow": "PASS",
        "check_2_banned_phrases": "PASS",
        "check_3_specificity": "PASS",
        "em_dash_check": "PASS",
        "verdict": "PASS"
      }
    ],
    "non_bullet_checks": {
      "summary_fragment_check": "PASS",
      "project_demonstrates_check": "PASS",
      "em_dash_check": "PASS"
    },
    "cross_resume_verb_scan": {
      "flags_3plus": [],
      "flags_2": ["Coordinated"]
    },
    "revision_cycles": 1,
    "items_escalated_to_human": 0,
    "duration_seconds": 20
  },

  "human_decisions": {
    "decision_points_presented": 3,
    "decisions_made": 3,
    "overrides_of_agent_recommendation": 1
  },

  "assembly": {
    "gate_8_result": "PASS",
    "final_word_counts": {
      "summary": 52,
      "total_bullets": 18,
      "bullets_within_ceiling": 18
    },
    "output_file": "final_resume.docx",
    "duration_seconds": 12
  },

  "post_generation_issues": []
}
```

The `post_generation_issues` array is populated manually by the user after reviewing the resume. This is the primary feedback channel for the Improvement Agent.

```json
"post_generation_issues": [
  {
    "issue_id": "issue_001",
    "bullet_id": "IMF1-B3",
    "issue_type": "filler_phrase",
    "description": "Bullet contains 'tripling output volume in one-quarter the normally allotted time' — 'normally allotted time' is bureaucratic filler",
    "gate_that_should_have_caught": "gate_7_check_3",
    "severity": "medium"
  }
]
```

---

## 4. Execution Flow

### 4.1 Standard Pipeline Run

```
USER: /resume openai-policy-manager.txt
  │
  ▼
ORCHESTRATOR: Initialize workspace, load config
  │
  ▼
INGESTION AGENT: Parse JD → jd_ingestion_report.json
  │
  ▼
ARCHIVE LOOKUP AGENT: Query vector DB → archive_matches.json
  │
  ▼
QUESTION AGENT: Present unmatched questions
  │
  ▼
  ╔═══════════════════════════════════╗
  ║  HUMAN PAUSE #1: Answer questions ║
  ╚═══════════════════════════════════╝
  │
  ▼
EVIDENCE AGENT: Build ledger, run Gates 1-6 → evidence_ledger.json
  │
  ├── Gate failure? → HALT with structured error
  │
  ▼
DRAFTING AGENT: Write all text → draft_*.json/txt
  │
  ▼
VERIFICATION AGENT: Independent checks → verification_report.json
  │
  ├── Failures? → Return to DRAFTING AGENT (max 2 cycles)
  │              → Still failing? → Escalate to DECISION POINT AGENT
  │
  ▼
DECISION POINT AGENT: Present choices
  │
  ▼
  ╔════════════════════════════════════════╗
  ║  HUMAN PAUSE #2: Make decisions        ║
  ╚════════════════════════════════════════╝
  │
  ▼
ASSEMBLY AGENT: Build D2, run Gate 8 → final_resume.docx
  │
  ▼
ORCHESTRATOR: Write performance log, present resume to user
  │
  ▼
  ╔═══════════════════════════════════════════════╗
  ║  HUMAN PAUSE #3 (optional): Report issues     ║
  ║  User reviews resume, logs post_gen issues    ║
  ╚═══════════════════════════════════════════════╝
```

### 4.2 Improvement Agent Cycle (Asynchronous)

```
IMPROVEMENT AGENT: Triggered manually or after N runs
  │
  ▼
READ: Accumulated performance_log.json (all runs)
  │
  ▼
ANALYZE: Pattern detection
  │  - Which gates have highest false-pass rate?
  │  - Which bullet positions get most post-gen issues?
  │  - Which decision points do users override most?
  │  - Which revision cycles repeat the same failure type?
  │
  ▼
PROPOSE: Improvement with classification
  │  - PATCH: Add/modify a rule within existing agent
  │  - ARCHITECTURAL: Restructure agent boundaries or verification logic
  │  - CONSTRAINT: Replace a guardrail-style rule with structural impossibility
  │
  ▼
TEST (Phase 4 only): Replay historical runs with proposed change
  │  - Count: issues caught that were previously missed
  │  - Count: false positives introduced
  │  - Compare: total gate accuracy before/after
  │
  ▼
REPORT: improvement_proposal.json → Human review
  │
  ▼
  ╔═══════════════════════════════════════════════╗
  ║  HUMAN DECISION: Accept / Reject / Modify     ║
  ╚═══════════════════════════════════════════════╝
```

---

## 5. Architectural Constraints (Guardrails → Constraints Migration)

The current module system relies on guardrails — rules that tell the model what not to do, enforced by self-checks. The agent architecture converts key guardrails into structural constraints.

| Current Guardrail | Failure Mode | Agent Architecture Constraint |
|---|---|---|
| "Do not estimate word counts" | Model asserts "[27 words]" without counting | Verification Agent uses code execution. No estimation pathway exists. |
| "Show your work for Gate 7" | Model fills PASS/FAIL table without analysis | Verification Agent has no access to Drafting Agent's reasoning. Must analyze from scratch. |
| "Ban em dashes from resume text" | Model generates em dashes, self-check misses them | Verification Agent runs regex check via code. Binary detection, not judgment. |
| "Ban 'Served as' construction" | Model uses banned phrase, gate misses it | Verification Agent runs pattern match via code. Binary detection. |
| "Outcome must state what was produced, not what project demonstrates" | Model writes "demonstrating..." and self-check passes | Verification Agent runs keyword scan for banned narration words via code. |
| "Defend recommendations when challenged" | Model reverses correct reasoning under pressure | Automated pipeline has no adversarial challenge. Decision points present options, not arguments. |
| "Don't fabricate archive answers" | Model hallucinates answers when archive too large | Archive Lookup Agent queries vector DB. Returns only actual stored matches. Cannot fabricate. |
| "Sequential checkpoints to prevent context loss" | Output truncation in long generation | Each agent has isolated context window. No single agent produces 56 pages of output. |

---

## 6. File Structure (Claude Code Project)

```
resume-agent/
├── CLAUDE.md                         # Project-level instructions for Claude Code
├── package.json
│
├── agents/
│   ├── orchestrator.md               # Orchestrator agent instructions
│   ├── ingestion.md                  # JD parsing & classification rules
│   ├── archive_lookup.md             # Vector DB query logic
│   ├── question.md                   # Phase B question presentation
│   ├── evidence.md                   # Evidence mapping & Gates 1-6
│   ├── drafting.md                   # Bullet writing rules & NON-NEGOTIABLES
│   ├── verification.md               # Independent verification & Gate 7
│   ├── decision_point.md             # Decision presentation logic
│   ├── assembly.md                   # D2 generation & Gate 8
│   └── improvement.md                # Performance analysis & proposals
│
├── tools/
│   ├── word_counter.py               # Code-based word count utility
│   ├── em_dash_checker.py            # Regex-based em dash detection
│   ├── verb_scanner.py               # Cross-resume verb dedup
│   ├── banned_phrase_checker.py       # Pattern match for banned constructions
│   ├── fragment_detector.py          # Sentence flow analysis
│   └── docx_generator.py            # Resume document assembly
│
├── archive/
│   ├── migrate_archive.py            # One-time: text archive → vector DB
│   ├── qa_vectors.db                 # Vector database
│   └── raw/
│       └── qa_archive_condensed.txt  # Original text archive (backup)
│
├── templates/
│   └── resume_template.docx          # D2 formatting template
│
├── tests/
│   ├── test_ingestion.py             # Known JD → expected classification
│   ├── test_verification.py          # Known bullets → expected pass/fail
│   ├── test_banned_phrases.py        # Known violations → expected catches
│   └── historical/
│       ├── openai_run_001.json       # Historical run data for regression
│       └── pwc_run_002.json
│
├── logs/
│   └── performance_log.json          # Accumulated performance data
│
├── workspace/                        # Per-run working directory
│   ├── config/
│   ├── input/
│   ├── state/
│   ├── output/
│   └── logs/
│
└── commands/
    └── resume.md                     # Slash command: /resume <jd-file>
```

---

## 7. Development Phases

### Phase 1: Core Pipeline (MVP)
**Goal:** Functional sequential pipeline with file-based state passing.
**Scope:**
- Orchestrator Agent (basic sequencing)
- Ingestion Agent (JD classification)
- Evidence Agent (ledger building, Gates 1-6)
- Drafting Agent (bullet/summary/project/skills writing)
- Verification Agent (code-based checks, Gate 7)
- Assembly Agent (D2 generation, .docx output)
- Basic performance logging

**Not included:** Archive vector DB (use simplified text lookup), Question Agent (manual paste), Decision Point Agent (manual review), Improvement Agent.

**Success criteria:** Pipeline produces resume from JD + pre-answered questions that passes all gates without manual intervention. Word counts verified by code. Em dashes absent. No banned phrases.

### Phase 2: Human Interaction + Archive
**Goal:** Add human interaction points and solve the archive problem.
**Scope:**
- Archive Lookup Agent with vector DB
- Question Agent (present unmatched questions, collect answers)
- Decision Point Agent (present choices, collect decisions)
- Archive migration script

**Success criteria:** Full end-to-end run with only 2-3 human pauses. Archive lookup returns accurate matches without hallucination.

### Phase 3: Improvement Agent (Read-Only)
**Goal:** Performance analysis and improvement proposals.
**Scope:**
- Improvement Agent (read-only)
- Structured performance logging with post-generation issue tracking
- Historical run data collection (minimum 10 runs before activation)
- Proposal format with root-cause tracing requirement

**Success criteria:** After 10+ runs, Improvement Agent identifies at least one genuine failure pattern and proposes a fix that, when manually validated, would have prevented the identified failures without introducing false positives.

### Phase 4: Improvement Agent (Auto-Test)
**Goal:** Automated proposal testing against historical data.
**Scope:**
- Regression test framework
- Historical run replay capability
- Before/after comparison reporting
- Expanded Improvement Agent with test execution

**Success criteria:** Improvement Agent proposals include quantified before/after metrics from historical replay. Human approval rate for proposals exceeds 70%.

---

## 8. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Agent instructions lose fidelity during decomposition from 70-page modules | HIGH | HIGH | Systematic decomposition with per-agent test cases. Validate each agent independently against known inputs/outputs before integration. |
| Verification Agent develops own blind spots | MEDIUM | HIGH | Verification tools are code-based (regex, word count), not LLM judgment. Improvement Agent monitors false-pass rates. |
| Improvement Agent proposes sophisticated-sounding changes without evidence | MEDIUM | MEDIUM | Anti-sycophancy constraint: every proposal must cite specific failed runs. Proposals without measurable criteria auto-rejected. |
| Vector DB returns false matches for archive lookup | MEDIUM | MEDIUM | Confidence threshold tuning. PARTIAL MATCH category with human confirmation option. |
| Pipeline latency (multiple agent calls) slower than current single-conversation approach | LOW | LOW | Agents execute in seconds each. Total pipeline time likely comparable to current 5-minute Module 2 generation. Parallel execution possible for independent agents. |
| Claude Code API costs higher than Claude.ai subscription | MEDIUM | LOW | Monitor token usage per agent. Optimize context size. Lighter model (Sonnet/Haiku) for mechanical agents (verification, archive lookup). |

---

## 9. Open Questions

1. **Model routing:** Which agents need Opus-level reasoning vs. Sonnet/Haiku for mechanical tasks? Ingestion (classification judgment) and Drafting (writing quality) likely need Opus. Verification (code execution + pattern matching) might work fine with Sonnet. Archive Lookup could use Haiku.

2. **Cowork integration:** Once pipeline is stable, can the Orchestrator be wrapped as a Cowork plugin? User would interact through Cowork's GUI rather than terminal. Depends on Cowork plugin API maturity.

3. **Archive maintenance:** How to handle contradictory answers in the archive (user's experience evolves, old answers become inaccurate)? Version stamping? TTL on answers?

4. **Multi-resume comparison:** Should the system store and compare resumes generated for different JDs from the same user? Could inform the Improvement Agent about which bullet formulations perform best across targets.

5. **Portability:** Could this architecture serve other users, or is it inherently tied to Connor's Q&A Archive and evidence base? The pipeline logic is general; the archive is personal. A "new user onboarding" flow could bootstrap the archive through structured interview.

---

## 10. Relationship to Current Module Versions

| Current Module | Version | Agent(s) That Replace It |
|---|---|---|
| Module 1 (JD Ingestion + Questions) | v7.7 | Ingestion Agent + Archive Lookup Agent + Question Agent |
| Module 2 (Evidence + Drafting + Gates) | v7.19 | Evidence Agent + Drafting Agent + Verification Agent + Decision Point Agent |
| Module 3 (D2 Assembly) | v4.9 | Assembly Agent |
| (New) | — | Orchestrator Agent + Improvement Agent |

The current modules are the **specification** for the agents. Each agent's instruction file is derived from the relevant sections of the current modules, not written from scratch. The months of iteration that produced v7.19 and v4.9 are preserved — they just execute in a better architecture.
