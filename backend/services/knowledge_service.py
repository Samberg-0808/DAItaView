"""
Knowledge file service.

Directory layout (enforced):
  knowledge/
    global.md                               ← Layer 1: always included
    sources/<source_id>/
      overview.md                           ← Layer 2: always included when source active
      domains/<domain_name>.md              ← Layer 3: retrieved by domain match
      tables/<table_name>.md                ← Layer 4: retrieved when table referenced
      examples/<topic>.md                   ← Few-shot examples, retrieved by similarity
"""
import re
import uuid
from pathlib import Path
from typing import Literal

from backend.config import settings

KnowledgeLayer = Literal["global", "overview", "domain", "table", "example"]


def _knowledge_root() -> Path:
    return Path(settings.knowledge_path)


def _source_dir(source_id: uuid.UUID) -> Path:
    return _knowledge_root() / "sources" / str(source_id)


def _layer_path(source_id: uuid.UUID | None, layer: KnowledgeLayer, name: str = "") -> Path:
    root = _knowledge_root()
    if layer == "global":
        return root / "global.md"
    sd = _source_dir(source_id)
    if layer == "overview":
        return sd / "overview.md"
    if layer == "domain":
        return sd / "domains" / f"{name}.md"
    if layer == "table":
        return sd / "tables" / f"{name}.md"
    if layer == "example":
        return sd / "examples" / f"{name}.md"
    raise ValueError(f"Unknown layer: {layer}")


class KnowledgeService:
    @staticmethod
    def read_file(source_id: uuid.UUID | None, layer: KnowledgeLayer, name: str = "") -> str | None:
        path = _layer_path(source_id, layer, name)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    @staticmethod
    def write_file(source_id: uuid.UUID | None, layer: KnowledgeLayer, name: str, content: str) -> None:
        path = _layer_path(source_id, layer, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def delete_file(source_id: uuid.UUID | None, layer: KnowledgeLayer, name: str = "") -> None:
        path = _layer_path(source_id, layer, name)
        if path.exists():
            path.unlink()

    @staticmethod
    def list_files(source_id: uuid.UUID) -> dict:
        """Return a structured file tree for a source."""
        sd = _source_dir(source_id)
        tree: dict = {
            "global": _knowledge_root() / "global.md",
            "overview": sd / "overview.md",
            "domains": [],
            "tables": [],
            "examples": [],
        }
        for sub, key in [("domains", "domains"), ("tables", "tables"), ("examples", "examples")]:
            d = sd / sub
            if d.exists():
                tree[key] = [p.stem for p in sorted(d.glob("*.md"))]
        return {
            "global_exists": (tree["global"]).exists(),
            "overview_exists": tree["overview"].exists(),
            "domains": tree["domains"],
            "tables": tree["tables"],
            "examples": tree["examples"],
        }

    @staticmethod
    def get_always_included(source_id: uuid.UUID) -> list[str]:
        """Return Layer 1 + Layer 2 content (always injected)."""
        chunks = []
        global_text = KnowledgeService.read_file(None, "global")
        if global_text:
            chunks.append(f"## Global Company Knowledge\n{global_text}")
        overview = KnowledgeService.read_file(source_id, "overview")
        if overview:
            chunks.append(f"## Data Source Overview\n{overview}")
        return chunks

    @staticmethod
    def get_domain_chunks(source_id: uuid.UUID) -> dict[str, str]:
        """Return {domain_name: content} for all domains of a source."""
        sd = _source_dir(source_id) / "domains"
        if not sd.exists():
            return {}
        return {p.stem: p.read_text(encoding="utf-8") for p in sd.glob("*.md")}

    @staticmethod
    def get_table_chunk(source_id: uuid.UUID, table_name: str) -> str | None:
        return KnowledgeService.read_file(source_id, "table", table_name)

    @staticmethod
    def get_example_chunks(source_id: uuid.UUID) -> dict[str, str]:
        sd = _source_dir(source_id) / "examples"
        if not sd.exists():
            return {}
        return {p.stem: p.read_text(encoding="utf-8") for p in sd.glob("*.md")}
