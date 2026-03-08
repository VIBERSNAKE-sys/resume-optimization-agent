# Resume Agent

A multi-agent resume optimization system built on the [Claude Code](https://docs.anthropic.com/en/docs/claude-code) Agent SDK. It takes a job description and your personal Q&A evidence archive, then runs a gate-validated pipeline of 11 specialized agents to produce a tailored `.docx` resume.

## How It Works

The pipeline coordinates agents through JSON state files, with mandatory human checkpoints and a strict gate system that halts on any violation:

```
Job Description + Resume
        │
        ▼
  ┌─────────────┐
  │  Ingestion   │──▶ JD parsing, role classification, Frozen Criticals
  └──────┬──────┘
         ▼
  ┌──────────────┐
  │Archive Lookup │──▶ Fuzzy-match questions against your Q&A archive
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │   Question    │──▶ Human Pause #1: answer remaining evidence gaps
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │   Evidence    │──▶ Evidence Ledger + Gates 1-6
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │   Drafting    │──▶ Bullet writing, summary, projects, skills
  └──────┬───────┘
         ▼
  ┌──────────────┐     ┌──────────┐
  │ Verification  │◀──▶│ Revision │  (up to 2 revision cycles)
  └──────┬───────┘     └──────────┘
         ▼
  ┌────────────────┐
  │ Decision Point  │──▶ Human Pause #2: trade-offs and overrides
  └──────┬─────────┘
         ▼
  ┌──────────────┐
  │   Assembly    │──▶ Gate 8, final .docx output
  └──────────────┘
```

## Gate System

Every gate must pass with 0 violations before the pipeline continues. Gate failures halt execution immediately.

| Gate | Stage | What It Checks |
|------|-------|----------------|
| 0 | Ingestion | Evidence discovery -- questions + archive coverage |
| 1 | Evidence | Concrete verbs, no keyword stuffing |
| 1.5 | Evidence | Framing Ladder accuracy (no overclaiming) |
| 2 | Evidence | Banned phrases, em dash ban |
| 3 | Evidence | Word count enforcement (code-based, never estimated) |
| 4 | Evidence | Evidence integrity, evidence class quota |
| 5 | Evidence | Skills concreteness (advisory, non-blocking) |
| 6 | Evidence | MUST-evidence placement and quality |
| 7 | Verification | Professional language (Tier 1 all roles, Tier 2 Senior/Exec) |
| 8 | Assembly | Proofreading, human authenticity |

## Prerequisites

- Python 3.10+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- `python-docx` for `.docx` generation:
  ```bash
  pip install python-docx
  ```

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/resume-agent.git
   cd resume-agent
   ```

2. Place your base resume template at `templates/Resume Template.docx` (or pass `--resume` at runtime).

3. Populate your Q&A Evidence Archive at `archive/raw/qa_archive_condensed.txt`:
   ```
   ## METRICS (universal facts)
   Q: What was the revenue impact of the platform migration?
   A: $2.3M annual savings verified by finance team.

   ## FACTUAL (tools, methods, counts)
   Q: Which cloud platforms have you worked with?
   A: AWS (3 years), GCP (2 years), deployed 40+ production services.

   ## NARRATIVE STORIES (origin stories, recognition events)
   Q: Describe a time you led a cross-functional initiative.
   A: Led the API standardization effort across 4 teams...
   ```

## Usage

Run the full pipeline with a job description file:

```bash
python src/orchestrator.py input/job_description.txt
```

Or provide a specific resume to tailor against:

```bash
python src/orchestrator.py input/job_description.txt --resume input/resume.txt
```

The pipeline will pause twice for your input (Question Agent and Decision Point Agent), then output the final resume to `workspace/output/final_resume.docx`.

### Running Individual Tools

Each verification tool runs standalone for debugging:

```bash
python tools/word_counter.py workspace/state/draft_bullets.json
python tools/em_dash_checker.py --text "Led team—completing the project"
python tools/banned_phrase_checker.py --text "Responsible for managing stakeholders"
python tools/verb_scanner.py workspace/state/draft_bullets.json
python tools/fragment_detector.py --text "Applying AI governance frameworks."
```

## Project Structure

```
resume-agent/
├── agents/           # Agent instruction files (.md) -- one per pipeline agent
├── tools/            # Python verification tools (word count, em dash, etc.)
├── src/
│   └── orchestrator.py   # Pipeline entry point
├── modules/          # Prompt engineering source modules
├── workspace/        # Runtime state (gitignored)
├── archive/          # Q&A Evidence Archive
├── commands/         # Slash command definitions
├── logs/             # Cumulative performance logs
└── tests/            # Test cases and historical runs
```

### Agents

| Agent | File | Role |
|-------|------|------|
| Ingestion | `agents/ingestion.md` | JD parsing, role classification, Frozen Criticals |
| Archive Lookup | `agents/archive_lookup.md` | Q&A Archive fuzzy matching |
| Question | `agents/question.md` | Interactive evidence collection (Human Pause #1) |
| Evidence | `agents/evidence.md` | Evidence Ledger construction, Gates 1-6 |
| Drafting | `agents/drafting.md` | Bullet writing, summary, projects, skills |
| Verification | `agents/verification.md` | Gate 7, code-based word count, em dash, banned phrases |
| Decision Point | `agents/decision_point.md` | Trade-off decisions (Human Pause #2) |
| Assembly | `agents/assembly.md` | D2 generation, Gate 8, .docx output |
| Orchestrator | `agents/orchestrator.md` | Pipeline coordination |
| Improvement | `agents/improvement.md` | Performance analysis across runs |
| Auditor | `agents/auditor.md` | Prompt module analysis and rule inventory |

### Tools

| Tool | Purpose |
|------|---------|
| `word_counter.py` | Code-based word count (no estimation allowed) |
| `em_dash_checker.py` | Detects banned em dashes, en dashes, double hyphens |
| `banned_phrase_checker.py` | Catches "responsible for", "served as", etc. |
| `verb_scanner.py` | Validates concrete action verbs in bullets |
| `fragment_detector.py` | Detects sentence fragments |
| `docx_generator.py` | Assembles the final .docx resume file |

## Design Principles

- **Single responsibility**: Each agent does one thing and produces one output file.
- **State via files**: Agents communicate through JSON in `workspace/state/`, not function calls.
- **Human-in-the-loop**: Two mandatory pause points ensure the human reviews evidence and trade-offs before final output.
- **Independent verification**: The Verification Agent has no access to Drafting Agent reasoning and runs code-based checks independently.
- **Gate failures halt the pipeline**: No downstream agent runs if a blocking gate fails.
- **No fabricated metrics**: Every number in the final resume binds to the Evidence Ledger with provenance.

## License

MIT
