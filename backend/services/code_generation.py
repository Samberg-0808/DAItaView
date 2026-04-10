"""
LLM Code Generation Service.

Pipeline per turn:
  1. Assemble prompt (knowledge curriculum + schema + question history + current question)
  2. Call Claude → thinking phase + (code | clarification questions)
  3. If clarification: return to caller, resume after user answers
  4. Validate code (dangerous patterns + table permission check)
  5. Return code to execution engine; retry up to 2x on execution failure
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Literal

import anthropic

from backend.config import settings
from backend.services.context_strategy import ContextPlan, Strategy, build_context_plan
from backend.services.embedding_service import retrieve_top_k
from backend.services.token_estimator import estimate_tokens

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
MODEL = "claude-sonnet-4-6"

DANGEROUS_PATTERNS = re.compile(
    r"\b(os|sys|subprocess|eval|exec|__import__|__builtins__|open|shutil|socket|requests|urllib|httpx)\b"
)

MAX_HISTORY_TOKENS = 10_000
KEEP_LAST_N_TURNS = 10


@dataclass
class ClarificationRequest:
    kind: Literal["clarification"]
    thinking: str
    questions: list[dict]  # [{text: str, options: list[str] | None}]


@dataclass
class GeneratedCode:
    kind: Literal["code"]
    thinking: str
    code: str


GenerationResult = ClarificationRequest | GeneratedCode


def assemble_history(turns: list[dict]) -> str:
    """
    Build question history string from prior turns.
    Each turn: {question: str, clarification_qa: list[{question, answer}] | None}
    Never includes result data. Summarises oldest turns if > MAX_HISTORY_TOKENS.
    """
    if not turns:
        return ""

    lines = []
    for t in turns:
        lines.append(f"User: {t['question']}")
        for qa in t.get("clarification_qa") or []:
            lines.append(f"  Clarification Q: {qa['question']}")
            lines.append(f"  Clarification A: {qa['answer']}")

    full_history = "\n".join(lines)
    if estimate_tokens(full_history) <= MAX_HISTORY_TOKENS:
        return full_history

    # Summarise oldest turns, keep last N verbatim
    keep = turns[-KEEP_LAST_N_TURNS:]
    summarised = turns[:-KEEP_LAST_N_TURNS]
    summary_questions = [t["question"] for t in summarised]
    summary = "Earlier in this session the user explored: " + "; ".join(summary_questions[:20])

    recent_lines = [summary]
    for t in keep:
        recent_lines.append(f"User: {t['question']}")
        for qa in t.get("clarification_qa") or []:
            recent_lines.append(f"  Clarification Q: {qa['question']}")
            recent_lines.append(f"  Clarification A: {qa['answer']}")
    return "\n".join(recent_lines)


def build_prompt(
    question: str,
    schema: dict,
    plan: ContextPlan,
    history: str,
    prior_code: str | None = None,
    execution_error: str | None = None,
) -> str:
    parts = []

    # Knowledge curriculum
    for chunk in plan.always_included:
        parts.append(chunk)

    if plan.strategy == "full":
        for name, content in {**plan.domain_chunks, **plan.table_chunks, **plan.example_chunks}.items():
            parts.append(f"### {name}\n{content}")
    elif plan.strategy == "rag":
        all_chunks = {**plan.domain_chunks, **plan.table_chunks}
        top = retrieve_top_k(question, all_chunks, k=8)
        for name, content in top.items():
            parts.append(f"### {name}\n{content}")
        for name, content in plan.example_chunks.items():
            parts.append(f"### Example: {name}\n{content}")

    # Schema (already permission-filtered)
    schema_lines = []
    for table, info in schema.items():
        cols = ", ".join(f"{c['name']} ({c['type']})" for c in info.get("columns", []))
        schema_lines.append(f"Table `{table}`: {cols}")
        if info.get("sample_rows"):
            schema_lines.append(f"  Sample: {info['sample_rows'][0]}")
    parts.append("## Available Schema\n" + "\n".join(schema_lines))

    # Conversation history
    if history:
        parts.append(f"## Conversation History\n{history}")

    # Retry context
    if prior_code and execution_error:
        parts.append(
            f"## Previous Attempt (Failed)\n"
            f"```python\n{prior_code}\n```\n"
            f"Error: {execution_error}\n"
            f"Please fix the code."
        )

    # Current question + instructions
    parts.append(
        f"## Current Question\n{question}\n\n"
        "## Instructions\n"
        "First, output a <thinking> block where you reason about:\n"
        "  1. Which tables and columns are needed\n"
        "  2. Which business rules from the knowledge base apply\n"
        "  3. Any ambiguities — if an ambiguity would MATERIALLY change the code, emit "
        "a <clarify> block instead of code (see format below). "
        "For minor ambiguities, state your assumption and proceed.\n\n"
        "Then output EITHER:\n"
        "  A) Executable Python code in a ```python block that assigns the final result to "
        "a variable named `result` (must be a pandas DataFrame or plotly Figure).\n"
        "  B) A <clarify> block with structured questions if you cannot proceed without answers.\n\n"
        "<clarify> format:\n"
        "<clarify>\n"
        "- question: What do you mean by X?\n"
        "  options: [option1, option2, other]\n"
        "- question: Which time period?\n"
        "  options: []\n"
        "</clarify>\n\n"
        "IMPORTANT: Never use os, sys, subprocess, eval, exec, open, or any network calls."
    )

    return "\n\n---\n\n".join(parts)


def extract_thinking(response_text: str) -> str:
    m = re.search(r"<thinking>(.*?)</thinking>", response_text, re.DOTALL)
    return m.group(1).strip() if m else ""


def extract_clarify(response_text: str) -> list[dict] | None:
    m = re.search(r"<clarify>(.*?)</clarify>", response_text, re.DOTALL)
    if not m:
        return None
    questions = []
    for line in m.group(1).strip().splitlines():
        line = line.strip()
        if line.startswith("- question:"):
            questions.append({"text": line[len("- question:"):].strip(), "options": []})
        elif line.startswith("options:") and questions:
            opts_str = line[len("options:"):].strip().strip("[]")
            questions[-1]["options"] = [o.strip() for o in opts_str.split(",") if o.strip()]
    return questions if questions else None


def extract_code(response_text: str) -> str | None:
    m = re.search(r"```python\s*(.*?)```", response_text, re.DOTALL)
    return m.group(1).strip() if m else None


def scan_dangerous_patterns(code: str) -> str | None:
    """Return the first dangerous pattern found, or None if clean."""
    m = DANGEROUS_PATTERNS.search(code)
    return m.group(0) if m else None


def validate_table_permissions(code: str, permitted_tables: list[str] | None) -> str | None:
    """Return violated table name if code references a restricted table, else None."""
    if permitted_tables is None:
        return None  # full access
    # Heuristic: look for table names as quoted strings or identifiers in FROM/JOIN clauses
    referenced = re.findall(r'\b(?:FROM|JOIN|read_csv_auto|read_parquet|read_json_auto)\s+[`"\']?(\w+)[`"\']?', code, re.IGNORECASE)
    for table in referenced:
        if table not in permitted_tables:
            return table
    return None


async def generate_code(
    question: str,
    schema: dict,
    source_id: uuid.UUID,
    history_turns: list[dict],
    permitted_tables: list[str] | None,
    prior_code: str | None = None,
    execution_error: str | None = None,
) -> GenerationResult:
    plan = build_context_plan(source_id, question, permitted_tables)

    # For multi-pass strategy: Pass 1 identifies tables, Pass 2 generates code
    if plan.strategy == "multi_pass" and not prior_code:
        plan = await _multi_pass_refine(question, plan, schema)

    history = assemble_history(history_turns)
    prompt = build_prompt(question, schema, plan, history, prior_code, execution_error)

    response = _client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text
    thinking = extract_thinking(text)

    clarify_questions = extract_clarify(text)
    if clarify_questions:
        return ClarificationRequest(kind="clarification", thinking=thinking, questions=clarify_questions)

    code = extract_code(text)
    if not code:
        # Fallback: treat entire response minus thinking as code attempt
        code = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL).strip()

    return GeneratedCode(kind="code", thinking=thinking, code=code)


async def _multi_pass_refine(question: str, plan: ContextPlan, schema: dict) -> ContextPlan:
    """Pass 1: ask LLM which tables/domains are needed, then enrich the plan."""
    from backend.services.knowledge_service import KnowledgeService

    summary_prompt = (
        "\n\n".join(plan.always_included)
        + f"\n\nAvailable tables: {list(schema.keys())}\n"
        + f"Available domains: {list(plan.domain_chunks.keys())}\n\n"
        + f"Question: {question}\n\n"
        + "List the table names and domain names needed to answer this question. "
        "Respond as JSON: {\"tables\": [...], \"domains\": [...]}"
    )
    resp = _client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": summary_prompt}],
    )
    import json
    try:
        needed = json.loads(resp.content[0].text)
        needed_tables = needed.get("tables", [])
        needed_domains = needed.get("domains", [])
    except Exception:
        return plan  # fall back to original plan

    # Enrich plan with only the identified chunks
    source_id = None  # will be set by caller context — use plan chunks as proxy
    enriched_tables = {t: plan.table_chunks.get(t, "") for t in needed_tables if t in plan.table_chunks}
    enriched_domains = {d: plan.domain_chunks.get(d, "") for d in needed_domains if d in plan.domain_chunks}

    return ContextPlan(
        strategy="multi_pass",
        always_included=plan.always_included,
        domain_chunks=enriched_domains,
        table_chunks=enriched_tables,
        example_chunks=plan.example_chunks,
        estimated_tokens=plan.estimated_tokens,
    )
