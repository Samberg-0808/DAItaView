"""
Dynamic context budget strategy selector.

Thresholds (tokens):
  < 20 000  → FULL: inject all relevant layers in one pass
  20k–80k   → RAG:  semantic retrieval of top-K chunks + matched table annotations
  > 80 000  → MULTI_PASS: two LLM calls — identify tables first, then deep fetch
"""
import uuid
from dataclasses import dataclass
from typing import Literal

from backend.services.knowledge_service import KnowledgeService
from backend.services.token_estimator import estimate_tokens, estimate_tokens_for_chunks

FULL_THRESHOLD = 20_000
RAG_THRESHOLD = 80_000

Strategy = Literal["full", "rag", "multi_pass"]


@dataclass
class ContextPlan:
    strategy: Strategy
    always_included: list[str]          # Layer 1 + 2 (always sent)
    domain_chunks: dict[str, str]       # Layer 3 chunks
    table_chunks: dict[str, str]        # Layer 4 chunks
    example_chunks: dict[str, str]      # few-shot examples
    estimated_tokens: int


def build_context_plan(
    source_id: uuid.UUID,
    question: str,
    permitted_tables: list[str] | None = None,
) -> ContextPlan:
    ks = KnowledgeService

    always = ks.get_always_included(source_id)
    domains = ks.get_domain_chunks(source_id)
    tables_raw = ks.get_example_chunks(source_id)  # examples
    examples = ks.get_example_chunks(source_id)

    # Filter table chunks to permitted tables only
    all_table_chunks = {
        name: content
        for name in (_get_table_names(source_id))
        if (content := ks.get_table_chunk(source_id, name))
        and (permitted_tables is None or name in permitted_tables)
    }

    # Score relevance of domains and tables against the question
    relevant_domains = _keyword_match(question, domains)
    relevant_tables = _keyword_match(question, all_table_chunks)
    relevant_examples = _keyword_match(question, examples)

    all_chunks = (
        always
        + list(relevant_domains.values())
        + list(relevant_tables.values())
        + list(relevant_examples.values())
    )
    total_tokens = estimate_tokens_for_chunks(all_chunks)

    if total_tokens < FULL_THRESHOLD:
        strategy: Strategy = "full"
    elif total_tokens < RAG_THRESHOLD:
        strategy = "rag"
    else:
        strategy = "multi_pass"

    return ContextPlan(
        strategy=strategy,
        always_included=always,
        domain_chunks=relevant_domains,
        table_chunks=relevant_tables,
        example_chunks=relevant_examples,
        estimated_tokens=total_tokens,
    )


def _get_table_names(source_id: uuid.UUID) -> list[str]:
    from pathlib import Path
    from backend.config import settings
    table_dir = Path(settings.knowledge_path) / "sources" / str(source_id) / "tables"
    if not table_dir.exists():
        return []
    return [p.stem for p in table_dir.glob("*.md")]


def _keyword_match(question: str, chunks: dict[str, str]) -> dict[str, str]:
    """Return chunks whose name or content shares keywords with the question."""
    q_words = set(question.lower().split())
    scored = []
    for name, content in chunks.items():
        name_words = set(name.lower().replace("_", " ").split())
        content_words = set(content.lower().split())
        score = len(q_words & name_words) * 3 + len(q_words & content_words)
        scored.append((score, name, content))
    scored.sort(reverse=True)
    # Always include top matches; include all if scores are non-zero
    return {name: content for score, name, content in scored if score > 0}
