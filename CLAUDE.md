# Resume Agent — CLAUDE.md

This project is a multi-agent resume optimization system built on the Claude Code Agent SDK. It converts job descriptions and Q&A evidence into tailored, gate-validated .docx resumes.

## Project Structure

```
resume-agent/
├── agents/           # Agent instruction files (.md) — one per pipeline agent
├── tools/            # Python tool scripts (word_counter, em_dash_checker, etc.)
├── src/              # Pipeline orchestrator
│   └── orchestrator.py
├── workspace/        # Runtime state (gitignored)
│   ├── config/       # Run metadata
│   ├── input/        # JD and resume text files
│   ├── state/        # Inter-agent JSON state files
│   ├── output/       # Final resume output
│   └── logs/         # Per-run performance log
├── archive/          # Q&A Evidence Archive
│   └── raw/          # qa_archive_condensed.txt
├── logs/             # Cumulative performance log across all runs
├── commands/         # Slash command definitions
└── tests/            # Test cases and historical runs
```

## Slash Commands

- `/resume <jd_file>` — Run the full pipeline for a job description

## Agent Files

Each agent has an instruction file in `agents/`:

| File | Agent | Role |
|------|-------|------|
| `ingestion.md` | Ingestion Agent | JD parsing, classification, Frozen Criticals |
| `archive_lookup.md` | Archive Lookup Agent | Q&A Archive matching |
| `question.md` | Question Agent | Phase B evidence collection (interactive) |
| `evidence.md` | Evidence Agent | Evidence Ledger, Gates 1-6 |
| `drafting.md` | Drafting Agent | Bullet writing, summary, projects, skills |
| `verification.md` | Verification Agent | Gate 7, code-based word count, em dash, banned phrases |
| `decision_point.md` | Decision Point Agent | Human pause — decisions and trade-offs |
| `assembly.md` | Assembly Agent | D2 generation, Gate 8, docx output |
| `orchestrator.md` | Orchestrator | Pipeline coordinator |
| `improvement.md` | Improvement Agent | Performance analysis (Phase 3+) |

## Python Tools

Each tool in `tools/` runs standalone for debugging:

```bash
python3 tools/word_counter.py workspace/state/draft_bullets.json
python3 tools/em_dash_checker.py --text "Led team—completing the project"
python3 tools/banned_phrase_checker.py --text "Responsible for managing stakeholders"
python3 tools/verb_scanner.py workspace/state/draft_bullets.json
python3 tools/fragment_detector.py --text "Applying AI governance frameworks."
```

## Pipeline Gate Structure

All gates must show 0 violations before proceeding:

| Gate | Location | Checks |
|------|----------|--------|
| Gate 0 | Ingestion | Evidence Discovery — questions + archive |
| Gate 1 | Evidence | Concrete verbs, no keyword stuffing |
| Gate 1.5 | Evidence | Framing Ladder accuracy (no overclaiming) |
| Gate 2 | Evidence | Banned phrases, em dash ban |
| Gate 3 | Evidence | Word count enforcement (code-based) |
| Gate 4 | Evidence | Evidence integrity, evidence class quota |
| Gate 5 | Evidence | Skills concreteness (ADVISORY — non-blocking) |
| Gate 6 | Evidence | MUST-evidence placement and quality |
| Gate 7 | Verification | Professional language (Tier 1 all roles, Tier 2 Senior/Exec) |
| Gate 8 | Assembly | Proofreading, human authenticity |

## NON-NEGOTIABLES (apply across all agents)

1. **No new numbers** — Every metric binds to Evidence Ledger. No aggregation without user approval.
2. **No em dashes** as sentence breaks (—, –, --). Hyphens in compound words are fine.
3. **No banned phrases** — "responsible for", "served as [title]", "demonstrates", etc.
4. **Code-based word counts** — Verification Agent never estimates counts.
5. **Evidence Ledger provenance** — Every bullet includes `Using:` provenance tag in draft.
6. **No self-verification** — Drafting Agent does not claim compliance. Verification Agent is independent.
7. **No deletions** — All roles from original resume must appear in D2.
8. **No meta-defensive language** — "without overstating", "not claiming" are banned.

## Running the Pipeline

```bash
# Full pipeline
python3 src/orchestrator.py input/jd_file.txt --resume input/resume.txt

# Run individual tools
python3 tools/word_counter.py workspace/state/draft_bullets.json
```

## Key Files During a Run

Active run state lives in `workspace/state/`:
- `jd_ingestion_report.json` → `archive_matches.json` → `phase_b_answers.json`
- → `evidence_ledger.json` → `draft_*.json` → `verification_report.json`
- → `human_decisions.json` → `final_resume.docx` + `assembly_report.json`

## Archive Structure

Place your Q&A Archive in `archive/raw/qa_archive_condensed.txt` using this format:

```
## METRICS (universal facts)
Q: [question]
A: [answer]

## FACTUAL (tools, methods, counts)
Q: [question]
A: [answer]

## NARRATIVE STORIES (origin stories, recognition events)
Q: [question]
A: [answer]
```

## Agent Design Principles

- **Single responsibility**: Each agent does one thing and produces one output
- **State via files**: Agents communicate through JSON files, not function calls
- **Human pauses are mandatory**: No auto-proceeding past Phase B or Decision Point
- **Independent verification**: Verification Agent has no access to Drafting Agent reasoning
- **Gate failures halt the pipeline**: No downstream agent runs if a blocking gate fails
- **Performance logging**: Every run generates a log for the Improvement Agent to analyze
