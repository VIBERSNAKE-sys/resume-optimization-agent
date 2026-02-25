"""
Resume Agent Orchestrator — Main pipeline entry point.

Usage:
    python src/orchestrator.py <jd_file> [--resume <resume_file>]

Example:
    python src/orchestrator.py input/openai-policy-manager.txt
    python src/orchestrator.py input/openai-policy-manager.txt --resume input/resume.txt
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Project root
ROOT = Path(__file__).parent.parent
WORKSPACE = ROOT / "workspace"
LOGS_DIR = ROOT / "logs"
AGENTS_DIR = ROOT / "agents"
BASE_TEMPLATE = ROOT / "templates" / "Resume Template.docx"


# ─── Utilities ────────────────────────────────────────────────────────────────

def print_header(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def print_step(step: int, name: str):
    print(f"\n[{step}] {name}")
    print(f"    {'-'*40}")


def check_file_exists(path: Path, label: str) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        print(f"    ERROR: {label} not found or empty: {path}")
        return False
    return True


def read_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ─── Workspace Setup ──────────────────────────────────────────────────────────

def extract_resume_template() -> str:
    """
    Extract plain text from templates/Resume Template.docx.
    Returns the text content with paragraph breaks preserved.
    """
    try:
        import docx
        doc = docx.Document(str(BASE_TEMPLATE))
        lines = []
        for p in doc.paragraphs:
            lines.append(p.text)
        return "\n".join(lines)
    except ImportError:
        print("    ERROR: python-docx not installed. Run: pip install python-docx")
        sys.exit(1)
    except Exception as e:
        print(f"    ERROR: Could not read base resume template: {e}")
        sys.exit(1)


def initialize_workspace(run_id: str, jd_file: Path, resume_file: Path) -> Path:
    """Create workspace structure and write config."""
    run_dir = WORKSPACE
    for subdir in ["config", "input", "state", "output", "logs"]:
        (run_dir / subdir).mkdir(parents=True, exist_ok=True)

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Copy input files
    dest_jd = run_dir / "input" / "job_description.txt"
    dest_resume = run_dir / "input" / "resume.txt"

    shutil.copy(jd_file, dest_jd)

    if resume_file and resume_file.exists():
        # Explicit --resume override provided
        shutil.copy(resume_file, dest_resume)
        print(f"  Resume: {resume_file} (override)")
    elif BASE_TEMPLATE.exists():
        # Use canonical base resume template
        resume_text = extract_resume_template()
        dest_resume.write_text(resume_text, encoding="utf-8")
        print(f"  Resume: {BASE_TEMPLATE} (base template, extracted to workspace/input/resume.txt)")
    else:
        dest_resume.write_text("[PASTE RESUME TEXT HERE]\n")
        print("    WARNING: No resume template found. Edit workspace/input/resume.txt before running.")

    # Write pipeline config
    config = {
        "run_id": run_id,
        "jd_file": str(jd_file),
        "resume_file": str(resume_file) if resume_file else None,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "pipeline_version": "0.1.0",
        "phase": 1,
    }
    write_json(run_dir / "config" / "pipeline_config.json", config)

    # Initialize performance log entry
    perf_log_entry = {
        "run_id": run_id,
        "timestamp": config["timestamp"],
        "jd_file": str(jd_file),
        "target_role": "",
        "ingestion": {},
        "archive_lookup": {},
        "evidence": {},
        "verification": {},
        "human_decisions": {},
        "assembly": {},
        "post_generation_issues": [],
    }

    run_log_path = LOGS_DIR / f"{run_id}.json"
    write_json(run_log_path, perf_log_entry)

    return run_dir


# ─── Agent Runner ─────────────────────────────────────────────────────────────

def run_agent_claude(agent_name: str, agent_instructions_file: str, context: dict) -> bool:
    """
    Run an agent using Claude Code's Agent SDK (claude -p).
    The agent reads its instructions from agents/<agent_name>.md and
    operates on the workspace state files.

    In Phase 1, this runs claude non-interactively with the agent instructions.
    Returns True on success, False on failure.
    """
    agent_md = AGENTS_DIR / f"{agent_name}.md"
    if not agent_md.exists():
        print(f"    ERROR: Agent instructions not found: {agent_md}")
        return False

    instructions = agent_md.read_text()

    # Build the prompt
    context_json = json.dumps(context, indent=2)
    prompt = f"""You are the {agent_name.upper().replace('_', ' ')} for the resume optimization pipeline.

Your instructions:
{instructions}

Current pipeline context:
{context_json}

Execute your role now. Read the required input files, perform your analysis, and write the output file(s) to the workspace.
Print a summary of what you did when complete."""

    try:
        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=300,  # 5 minute timeout per agent
        )

        if result.returncode != 0:
            print(f"    AGENT ERROR (exit {result.returncode}):")
            print(f"    {result.stderr[:500]}")
            return False

        print(f"    Agent output:")
        for line in result.stdout.split("\n")[:20]:  # Print first 20 lines
            print(f"    | {line}")
        if result.stdout.count("\n") > 20:
            print(f"    | ... ({result.stdout.count(chr(10))} total lines)")

        return True

    except subprocess.TimeoutExpired:
        print(f"    TIMEOUT: Agent {agent_name} exceeded 5 minutes")
        return False
    except FileNotFoundError:
        print(f"    ERROR: 'claude' CLI not found. Install Claude Code CLI first.")
        print(f"    For development, check workspace/state/ for manually created state files.")
        return False


# ─── Pipeline Steps ──────────────────────────────────────────────────────────

def step_ingestion(run_dir: Path, run_id: str) -> bool:
    print_step(1, "INGESTION AGENT — Parsing job description")
    context = {
        "run_id": run_id,
        "workspace": str(run_dir),
        "input_jd": str(run_dir / "input" / "job_description.txt"),
        "input_resume": str(run_dir / "input" / "resume.txt"),
        "output": str(run_dir / "state" / "jd_ingestion_report.json"),
    }

    success = run_agent_claude("ingestion", "ingestion.md", context)
    if not success:
        return False

    output = run_dir / "state" / "jd_ingestion_report.json"
    if not check_file_exists(output, "jd_ingestion_report.json"):
        return False

    report = read_json(output)
    print(f"    Role: {report.get('target_role', 'unknown')}")
    print(f"    Level: {report.get('target_role_level', 'unknown')}")
    print(f"    Type: {report.get('application_type', 'unknown')}")
    print(f"    Frozen Criticals: {report.get('frozen_criticals_count', 0)}")
    print(f"    Employment Check: {report.get('employment_continuity', {}).get('status', 'unknown')}")
    print(f"    Gate 0 Questions: {len(report.get('gate_0_questions_pending', []))}")

    return True


def step_archive_lookup(run_dir: Path, run_id: str) -> bool:
    print_step(2, "ARCHIVE LOOKUP AGENT — Matching questions against archive")

    archive_path = ROOT / "archive" / "raw" / "qa_archive_condensed.txt"
    if not archive_path.exists():
        print(f"    NOTE: No archive found at {archive_path}. Creating empty archive_matches.json.")
        # Create empty matches file — all questions go to Phase B
        ingestion = read_json(run_dir / "state" / "jd_ingestion_report.json")
        questions = ingestion.get("gate_0_questions_pending", [])
        matches = {
            "run_id": run_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "archive_file": str(archive_path),
            "lookup_method": "text_fuzzy",
            "questions_processed": len(questions),
            "matches": [
                {
                    "question_id": q["id"],
                    "question_text": q["question_text"],
                    "question_category": q["category"],
                    "frozen_critical_id": q.get("frozen_critical_id"),
                    "match_type": "REFRAMING" if q["category"] == "REFRAMING" else "NO_MATCH",
                    "confidence_score": 0.0,
                    "matched_answer": "",
                    "archive_citation": "",
                    "route": "PHASE_B",
                }
                for q in questions
            ],
            "summary": {
                "exact_matches": 0,
                "similar_matches": 0,
                "partial_matches": 0,
                "no_matches": len([q for q in questions if q["category"] != "REFRAMING"]),
                "reframing_to_phase_b": len([q for q in questions if q["category"] == "REFRAMING"]),
                "total_for_phase_a": 0,
                "total_for_phase_b": len(questions),
            }
        }
        write_json(run_dir / "state" / "archive_matches.json", matches)
        print(f"    All {len(questions)} questions routed to Phase B (no archive)")
        return True

    context = {
        "run_id": run_id,
        "workspace": str(run_dir),
        "input_ingestion": str(run_dir / "state" / "jd_ingestion_report.json"),
        "input_archive": str(archive_path),
        "output": str(run_dir / "state" / "archive_matches.json"),
    }

    success = run_agent_claude("archive_lookup", "archive_lookup.md", context)
    if not success:
        return False

    output = run_dir / "state" / "archive_matches.json"
    if not check_file_exists(output, "archive_matches.json"):
        return False

    matches = read_json(output)
    summary = matches.get("summary", {})
    print(f"    Phase A (answered): {summary.get('total_for_phase_a', 0)}")
    print(f"    Phase B (pending): {summary.get('total_for_phase_b', 0)}")

    return True


def step_question_agent(run_dir: Path, run_id: str) -> bool:
    """
    HUMAN PAUSE #1: Run the Question Agent interactively.
    This requires user input — not automated.
    """
    print_step(3, "QUESTION AGENT — Human Pause #1")
    print()
    print("    The pipeline needs your answers to complete the evidence gathering.")
    print("    Running Question Agent (interactive)...")
    print()

    context = {
        "run_id": run_id,
        "workspace": str(run_dir),
        "input_matches": str(run_dir / "state" / "archive_matches.json"),
        "output": str(run_dir / "state" / "phase_b_answers.json"),
    }

    # For the Question Agent, we run it interactively
    success = run_agent_claude("question", "question.md", context)
    if not success:
        return False

    output = run_dir / "state" / "phase_b_answers.json"
    if not check_file_exists(output, "phase_b_answers.json"):
        return False

    answers = read_json(output)
    print(f"    Answers collected: {len(answers.get('answers', []))}")
    print(f"    Critical gaps: {answers.get('critical_gaps_flagged', 0)}")

    return True


def step_evidence(run_dir: Path, run_id: str) -> bool:
    print_step(4, "EVIDENCE AGENT — Building evidence ledger, running Gates 1-6")

    context = {
        "run_id": run_id,
        "workspace": str(run_dir),
        "input_ingestion": str(run_dir / "state" / "jd_ingestion_report.json"),
        "input_matches": str(run_dir / "state" / "archive_matches.json"),
        "input_answers": str(run_dir / "state" / "phase_b_answers.json"),
        "output": str(run_dir / "state" / "evidence_ledger.json"),
    }

    success = run_agent_claude("evidence", "evidence.md", context)
    if not success:
        return False

    output = run_dir / "state" / "evidence_ledger.json"
    if not check_file_exists(output, "evidence_ledger.json"):
        return False

    ledger = read_json(output)

    # Check for gate failures
    gate_results = ledger.get("gate_results", {})
    failures = ledger.get("gate_failures", [])

    print(f"    Gate 1: {gate_results.get('gate_1', 'unknown')}")
    print(f"    Gate 2: {gate_results.get('gate_2', 'unknown')}")
    print(f"    Gate 3: {gate_results.get('gate_3', 'unknown')}")
    print(f"    Gate 4: {gate_results.get('gate_4', 'unknown')}")
    print(f"    Gate 5: {gate_results.get('gate_5', 'unknown')} (advisory)")
    print(f"    Gate 6: {gate_results.get('gate_6', 'unknown')}")

    if ledger.get("ledger_status") == "BLOCKED":
        print_header("PIPELINE HALTED — Gate Failure")
        print(f"  Reason: {ledger.get('blocking_reason', 'unknown')}")
        print()
        for failure in failures:
            print(f"  Gate {failure['gate']}: {failure['reason']}")
        print()
        print("  Resolve gate failures and restart the pipeline.")
        return False

    must_summary = ledger.get("must_coverage_summary", {})
    print(f"    MUST coverage: {must_summary.get('covered', 0)}/{must_summary.get('total_must', 0)}")
    print(f"    TOP2 roles: {ledger.get('top2_roles', [])}")

    return True


def step_drafting(run_dir: Path, run_id: str) -> bool:
    print_step(5, "DRAFTING AGENT — Writing bullets, summary, projects, skills")

    context = {
        "run_id": run_id,
        "workspace": str(run_dir),
        "input_ledger": str(run_dir / "state" / "evidence_ledger.json"),
        "input_resume": str(run_dir / "input" / "resume.txt"),
        "input_ingestion": str(run_dir / "state" / "jd_ingestion_report.json"),
        "output_bullets": str(run_dir / "state" / "draft_bullets.json"),
        "output_summary": str(run_dir / "state" / "draft_summary.txt"),
        "output_projects": str(run_dir / "state" / "draft_projects.json"),
        "output_skills": str(run_dir / "state" / "draft_skills.json"),
    }

    success = run_agent_claude("drafting", "drafting.md", context)
    if not success:
        return False

    # Verify all draft outputs exist
    for output_file in ["draft_bullets.json", "draft_summary.txt", "draft_projects.json", "draft_skills.json"]:
        if not check_file_exists(run_dir / "state" / output_file, output_file):
            return False

    bullets = read_json(run_dir / "state" / "draft_bullets.json")
    print(f"    Bullets drafted: {len(bullets.get('bullets', []))}")

    return True


def step_verification(run_dir: Path, run_id: str, revision_cycle: int = 0) -> tuple[bool, bool]:
    """
    Run Verification Agent. Returns (success, needs_revision).
    """
    print_step(6, f"VERIFICATION AGENT — Independent checks (cycle {revision_cycle + 1})")

    context = {
        "run_id": run_id,
        "workspace": str(run_dir),
        "revision_cycle": revision_cycle,
        "input_bullets": str(run_dir / "state" / "draft_bullets.json"),
        "input_summary": str(run_dir / "state" / "draft_summary.txt"),
        "input_projects": str(run_dir / "state" / "draft_projects.json"),
        "input_skills": str(run_dir / "state" / "draft_skills.json"),
        "input_ledger": str(run_dir / "state" / "evidence_ledger.json"),
        "input_ingestion": str(run_dir / "state" / "jd_ingestion_report.json"),
        "output": str(run_dir / "state" / "verification_report.json"),
    }

    success = run_agent_claude("verification", "verification.md", context)
    if not success:
        return False, False

    output = run_dir / "state" / "verification_report.json"
    if not check_file_exists(output, "verification_report.json"):
        return False, False

    report = read_json(output)
    items_failing = report.get("items_failing", 0)
    items_for_human = len(report.get("items_for_human_review", []))

    print(f"    Gate 7: {report.get('gate_7_overall', 'unknown')}")
    print(f"    Passing: {report.get('items_passing', 0)}")
    print(f"    Failing: {items_failing}")
    print(f"    Escalated to human: {items_for_human}")

    needs_revision = items_failing > 0 and items_for_human < items_failing and revision_cycle < 2
    return True, needs_revision


def step_revision(run_dir: Path, run_id: str) -> bool:
    """Send failing items back to Drafting Agent for revision."""
    print_step(6.5, "DRAFTING AGENT — Revision pass (fixing verification failures)")

    report = read_json(run_dir / "state" / "verification_report.json")
    failing_items = [b for b in report.get("bullets", []) if b.get("verdict") == "FAIL"]

    context = {
        "run_id": run_id,
        "workspace": str(run_dir),
        "mode": "revision",
        "failing_items": failing_items,
        "input_bullets": str(run_dir / "state" / "draft_bullets.json"),
        "input_ledger": str(run_dir / "state" / "evidence_ledger.json"),
        "output_bullets": str(run_dir / "state" / "draft_bullets.json"),
    }

    success = run_agent_claude("drafting", "drafting.md", context)
    return success


def step_decision_point(run_dir: Path, run_id: str) -> bool:
    """HUMAN PAUSE #2: Decision Point Agent."""
    print_step(7, "DECISION POINT AGENT — Human Pause #2")
    print()
    print("    Presenting decisions requiring your input...")
    print()

    context = {
        "run_id": run_id,
        "workspace": str(run_dir),
        "input_verification": str(run_dir / "state" / "verification_report.json"),
        "input_ledger": str(run_dir / "state" / "evidence_ledger.json"),
        "input_bullets": str(run_dir / "state" / "draft_bullets.json"),
        "output": str(run_dir / "state" / "human_decisions.json"),
    }

    success = run_agent_claude("decision_point", "decision_point.md", context)
    if not success:
        return False

    output = run_dir / "state" / "human_decisions.json"
    if not check_file_exists(output, "human_decisions.json"):
        return False

    decisions = read_json(output)
    print(f"    Decisions made: {decisions.get('decisions_made', 0)}")
    print(f"    Overrides: {decisions.get('overrides_of_agent_recommendation', 0)}")

    return True


def step_assembly(run_dir: Path, run_id: str) -> bool:
    print_step(8, "ASSEMBLY AGENT — Building final resume")

    context = {
        "run_id": run_id,
        "workspace": str(run_dir),
        "input_verification": str(run_dir / "state" / "verification_report.json"),
        "input_decisions": str(run_dir / "state" / "human_decisions.json"),
        "input_summary": str(run_dir / "state" / "draft_summary.txt"),
        "input_projects": str(run_dir / "state" / "draft_projects.json"),
        "input_skills": str(run_dir / "state" / "draft_skills.json"),
        "input_ledger": str(run_dir / "state" / "evidence_ledger.json"),
        "input_ingestion": str(run_dir / "state" / "jd_ingestion_report.json"),
        "output_docx": str(run_dir / "output" / "final_resume.docx"),
        "output_report": str(run_dir / "output" / "assembly_report.json"),
    }

    success = run_agent_claude("assembly", "assembly.md", context)
    if not success:
        return False

    report_path = run_dir / "output" / "assembly_report.json"
    if not check_file_exists(report_path, "assembly_report.json"):
        return False

    report = read_json(report_path)
    print(f"    Gate 8: {report.get('gate_8_result', 'unknown')}")
    print(f"    ATS Confidence: {report.get('ats_confidence', {}).get('score', 'unknown')}")

    if report.get("gate_8_result") == "FAIL":
        print(f"    BLOCKED: Gate 8 failed — {report.get('failure_reason', '')}")
        return False

    return True


def update_performance_log(run_dir: Path, run_id: str):
    """Update the performance log after run completes."""
    log_path = LOGS_DIR / f"{run_id}.json"
    if not log_path.exists():
        return

    log = read_json(log_path)

    # Pull data from each agent's output
    try:
        ingestion = read_json(run_dir / "state" / "jd_ingestion_report.json")
        log["target_role"] = ingestion.get("target_role", "")
        log["ingestion"] = {
            "classifications": ingestion.get("classification_counts", {}),
            "frozen_criticals": ingestion.get("frozen_criticals_count", 0),
            "ambiguous_headers": ingestion.get("ambiguous_headers", []),
        }
    except Exception:
        pass

    try:
        matches = read_json(run_dir / "state" / "archive_matches.json")
        summary = matches.get("summary", {})
        log["archive_lookup"] = {
            "questions_generated": matches.get("questions_processed", 0),
            "exact_matches": summary.get("exact_matches", 0),
            "partial_matches": summary.get("partial_matches", 0),
            "no_matches": summary.get("no_matches", 0),
        }
    except Exception:
        pass

    try:
        ledger = read_json(run_dir / "state" / "evidence_ledger.json")
        log["evidence"] = {
            "gate_results": ledger.get("gate_results", {}),
            "top2_roles": ledger.get("top2_roles", []),
        }
    except Exception:
        pass

    try:
        verification = read_json(run_dir / "state" / "verification_report.json")
        log["verification"] = {
            "gate_7_overall": verification.get("gate_7_overall", ""),
            "revision_cycles": verification.get("revision_cycle", 0),
            "items_escalated_to_human": len(verification.get("items_for_human_review", [])),
        }
    except Exception:
        pass

    try:
        decisions = read_json(run_dir / "state" / "human_decisions.json")
        log["human_decisions"] = {
            "decisions_made": decisions.get("decisions_made", 0),
            "overrides_of_agent_recommendation": decisions.get("overrides_of_agent_recommendation", 0),
        }
    except Exception:
        pass

    try:
        assembly_report = read_json(run_dir / "output" / "assembly_report.json")
        log["assembly"] = {
            "gate_8_result": assembly_report.get("gate_8_result", ""),
            "final_word_counts": assembly_report.get("final_word_counts", {}),
            "ats_confidence": assembly_report.get("ats_confidence", {}),
            "output_file": assembly_report.get("output_file", ""),
        }
    except Exception:
        pass

    write_json(log_path, log)

    # Append to cumulative performance log
    perf_log = LOGS_DIR / "performance_log.json"
    if perf_log.exists():
        all_runs = read_json(perf_log)
        if not isinstance(all_runs, list):
            all_runs = [all_runs]
    else:
        all_runs = []

    all_runs.append(log)
    write_json(perf_log, all_runs)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Resume Optimization Agent Pipeline")
    parser.add_argument("jd_file", help="Path to job description text file")
    parser.add_argument("--resume", help="Path to resume text file", default=None)
    args = parser.parse_args()

    jd_file = Path(args.jd_file)
    resume_file = Path(args.resume) if args.resume else None

    if not jd_file.exists():
        print(f"ERROR: Job description file not found: {jd_file}")
        sys.exit(1)

    # Generate run ID
    run_id = f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    print_header(f"RESUME OPTIMIZATION PIPELINE — {run_id}")
    print(f"  JD: {jd_file}")

    # Initialize
    run_dir = initialize_workspace(run_id, jd_file, resume_file)
    print(f"  Workspace: {run_dir}")

    # ── Pipeline Execution ────────────────────────────────────────────────────

    # Step 1: Ingestion
    if not step_ingestion(run_dir, run_id):
        print("\nPIPELINE FAILED at Ingestion Agent.")
        sys.exit(1)

    # Step 2: Archive Lookup
    if not step_archive_lookup(run_dir, run_id):
        print("\nPIPELINE FAILED at Archive Lookup Agent.")
        sys.exit(1)

    # Step 3: Question Agent (Human Pause #1)
    if not step_question_agent(run_dir, run_id):
        print("\nPIPELINE FAILED at Question Agent.")
        sys.exit(1)

    # Step 4: Evidence Agent (blocking gates)
    if not step_evidence(run_dir, run_id):
        print("\nPIPELINE HALTED — gate failure requires resolution.")
        update_performance_log(run_dir, run_id)
        sys.exit(1)

    # Step 5: Drafting Agent
    if not step_drafting(run_dir, run_id):
        print("\nPIPELINE FAILED at Drafting Agent.")
        sys.exit(1)

    # Step 6: Verification + Revision Loop (max 2 cycles)
    for revision_cycle in range(3):  # 0, 1, 2
        success, needs_revision = step_verification(run_dir, run_id, revision_cycle)
        if not success:
            print("\nPIPELINE FAILED at Verification Agent.")
            sys.exit(1)
        if not needs_revision:
            break
        if revision_cycle < 2:
            if not step_revision(run_dir, run_id):
                print("\nPIPELINE FAILED at Drafting revision.")
                sys.exit(1)

    # Step 7: Decision Point (Human Pause #2)
    if not step_decision_point(run_dir, run_id):
        print("\nPIPELINE FAILED at Decision Point Agent.")
        sys.exit(1)

    # Step 8: Assembly
    if not step_assembly(run_dir, run_id):
        print("\nPIPELINE FAILED at Assembly Agent.")
        sys.exit(1)

    # ── Completion ────────────────────────────────────────────────────────────

    update_performance_log(run_dir, run_id)

    output_docx = run_dir / "output" / "final_resume.docx"
    assembly_report = read_json(run_dir / "output" / "assembly_report.json")

    print_header("RESUME GENERATION COMPLETE")
    print(f"  Output: {output_docx}")
    print(f"  ATS Confidence: {assembly_report.get('ats_confidence', {}).get('score', 'unknown')}")
    must_coverage = assembly_report.get('ats_confidence', {})
    print(f"  MUST Coverage: {must_coverage.get('must_covered', '?')}/{must_coverage.get('must_total', '?')}")
    print(f"  Run ID: {run_id}")
    print(f"  Log: {LOGS_DIR / f'{run_id}.json'}")
    print()
    print("  Review the resume. To report post-generation issues:")
    print(f"  Edit: {LOGS_DIR / f'{run_id}.json'}")
    print("  Add to 'post_generation_issues' array.")
    print()


if __name__ == "__main__":
    main()
