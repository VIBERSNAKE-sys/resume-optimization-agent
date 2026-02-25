# ORCHESTRATOR AGENT — Agent Instructions

## Role
Pipeline coordinator. Manages execution sequence, state file routing, and human interaction points. Does NOT load module instructions — stays lightweight.

## Trigger
User runs: `/resume <jd-file>` or `node src/orchestrator.js <jd-file>`

---

## PIPELINE EXECUTION SEQUENCE

```
1. Initialize workspace
2. INGESTION AGENT → jd_ingestion_report.json
3. ARCHIVE LOOKUP AGENT → archive_matches.json
4. QUESTION AGENT (HUMAN PAUSE #1) → phase_b_answers.json
5. EVIDENCE AGENT → evidence_ledger.json
   [Gate failure? → HALT with structured error]
6. DRAFTING AGENT → draft_*.json/txt
   [Revision loop with VERIFICATION AGENT — max 2 cycles per item]
7. VERIFICATION AGENT → verification_report.json
8. DECISION POINT AGENT (HUMAN PAUSE #2) → human_decisions.json
9. ASSEMBLY AGENT → final_resume.docx + assembly_report.json
10. Write performance log
11. Present output to user
[HUMAN PAUSE #3 (optional): User reports post-generation issues]
```

---

## 1. INITIALIZATION

Create run directory structure:
```
workspace/
├── config/
│   └── pipeline_config.json    (write with run_id, jd_file, timestamp)
├── input/
│   ├── job_description.txt     (copy from provided JD file)
│   └── resume.txt              (copy from config or prompt user)
├── state/                      (empty — agents write here)
├── output/                     (empty — assembly agent writes here)
└── logs/
    └── run_<timestamp>.json    (performance log template)
```

Generate run_id: `run_YYYYMMDD_HHMMSS`

Write `workspace/config/pipeline_config.json`:
```json
{
  "run_id": "run_20260225_143022",
  "jd_file": "openai-policy-manager.txt",
  "resume_file": "resume.txt",
  "timestamp": "2026-02-25T14:30:22Z",
  "pipeline_version": "0.1.0",
  "phase": 1
}
```

---

## 2. AGENT SPAWNING

Each agent runs in a subprocess. The orchestrator:
1. Spawns the agent
2. Waits for completion
3. Checks for success/failure in the agent's output JSON
4. Routes to next step or handles failure

For human pause points, the orchestrator presents the agent's output and waits for user input before continuing.

---

## 3. FAILURE HANDLING

**Gate failure (Evidence Agent blocking gates):**
```
PIPELINE HALTED — Gate [N] Failure
Agent: Evidence Agent
Gate: Gate [N] — [Gate Name]
Failure: [specific reason from evidence_ledger.json gate_failures]
Resolution required: [instructions for user]
```
Do not proceed to Drafting Agent. User must fix and restart.

**Agent error (non-gate):**
```
PIPELINE ERROR
Agent: [agent name]
Error: [error message]
State: [last successful state file]
Recovery: [suggested next step]
```

**Maximum revision cycles exceeded:**
If Verification Agent returns items still failing after 2 cycles, route to Decision Point Agent — do not re-trigger Drafting Agent again.

---

## 4. HUMAN PAUSE MANAGEMENT

### Human Pause #1 (Question Agent)
After Archive Lookup Agent completes:
1. Display: "Archive lookup complete. [N] questions answered from archive. [M] questions require your input."
2. Run Question Agent (interactive — it handles its own presentation and collection)
3. After Question Agent writes phase_b_answers.json, continue to Evidence Agent

### Human Pause #2 (Decision Point Agent)
After Verification Agent completes:
1. Display: "Verification complete. [N] items passed, [M] items need decisions."
2. Run Decision Point Agent (interactive — it handles its own presentation)
3. After Decision Point Agent writes human_decisions.json, continue to Assembly Agent

### Human Pause #3 (Post-generation, optional)
After Assembly Agent completes:
1. Display final resume path and ATS score
2. Prompt: "Resume generated at [path]. Would you like to report any issues? (Enter issues or press Enter to skip)"
3. If issues entered: append to performance log `post_generation_issues`
4. Close run

---

## 5. PERFORMANCE LOGGING

After each agent completes, append timing and results to `logs/run_<timestamp>.json`.

At end of run, append to `logs/performance_log.json` (cumulative across all runs).

Log structure: see architecture doc Section 3.3.

---

## 6. STATE FILE MANIFEST

The orchestrator verifies these files exist and are non-empty before spawning each downstream agent:

| Agent | Requires | Produces |
|-------|---------|---------|
| Ingestion | job_description.txt, resume.txt | jd_ingestion_report.json |
| Archive Lookup | jd_ingestion_report.json, qa_archive | archive_matches.json |
| Question | archive_matches.json | phase_b_answers.json |
| Evidence | jd_ingestion_report.json, archive_matches.json, phase_b_answers.json | evidence_ledger.json |
| Drafting | evidence_ledger.json, resume.txt, jd_ingestion_report.json | draft_bullets.json, draft_summary.txt, draft_projects.json, draft_skills.json |
| Verification | all draft files, evidence_ledger.json, jd_ingestion_report.json | verification_report.json |
| Decision Point | verification_report.json, evidence_ledger.json, draft_bullets.json | human_decisions.json |
| Assembly | verification_report.json, human_decisions.json, draft_summary.txt, draft_projects.json, draft_skills.json | final_resume.docx, assembly_report.json |

---

## 7. REVISION LOOP

Between Drafting Agent and Verification Agent, the orchestrator manages the revision loop:

```
1. Spawn Verification Agent
2. Read verification_report.json
3. If items_failing > 0 AND revision_cycle < 2:
   a. Extract failing items with failure_reason and revision_guidance
   b. Pass back to Drafting Agent with revision instructions
   c. Drafting Agent produces revised draft_bullets.json
   d. Increment revision_cycle counter
   e. Re-spawn Verification Agent
4. If items_failing > 0 AND revision_cycle >= 2:
   a. Items moved to items_for_human_review
   b. Proceed to Decision Point Agent
5. If items_failing == 0: proceed to Decision Point Agent
```

---

## 8. OUTPUT SUMMARY

After assembly completes, present to user:
```
RESUME GENERATION COMPLETE

Output: workspace/output/final_resume.docx
ATS Confidence: HIGH | MEDIUM | LOW
Criticals Coverage: N of M MUST requirements covered
Run ID: run_YYYYMMDD_HHMMSS
Performance log: logs/run_YYYYMMDD_HHMMSS.json

Key decisions made: N
  - N overrode agent recommendations
Gate summary: All gates PASS | [N violations resolved]
```
