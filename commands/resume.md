# /resume — Resume Optimization Pipeline

Run the full resume optimization pipeline for a given job description.

## Usage

```
/resume <jd_file> [--resume <resume_file>]
```

## Examples

```
/resume openai-policy-manager.txt
/resume input/meta-pm.txt --resume input/my_resume.txt
```

## What This Does

Triggers the multi-agent pipeline:
1. Parses and classifies the JD (Ingestion Agent)
2. Looks up existing evidence from Q&A Archive
3. Asks you targeted questions to gather evidence (Human Pause)
4. Builds Evidence Ledger and validates gates 1-6
5. Drafts optimized bullets, summary, projects, skills
6. Independently verifies all text (word counts, banned phrases, em dashes, sentence flow)
7. Presents decisions requiring your input (Human Pause)
8. Assembles and generates final_resume.docx

## Human Interaction Points

You will be asked for input at:
- **Phase B questions**: Evidence gathering questions not answered by your archive
- **Decision Point**: Deduplication choices, pruning decisions, word count trade-offs

## Prerequisites

1. `claude` CLI installed (Claude Code)
2. `python3` with `python-docx`: `pip install python-docx`
3. Job description saved as a `.txt` file
4. Resume saved as `workspace/input/resume.txt` (or pass via `--resume`)

## Output

- `workspace/output/final_resume.docx` — The optimized resume
- `workspace/output/assembly_report.json` — ATS confidence score and gate status
- `logs/run_<timestamp>.json` — Full performance log

## Slash Command Implementation

```bash
python3 /Users/connorkinsella/Documents/resume-agent/src/orchestrator.py "$@"
```
