"""Load a domain pack: its corpus of versioned policies and its labelled cases."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

CLAUSE = re.compile(r"^\*\*(\d+\.\d+)\*\*\s+(.+)$")


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    version: str
    status: str  # current | superseded
    meta: dict
    clauses: dict[str, str]
    body: str

    @property
    def is_current(self) -> bool:
        return self.status == "current"


@dataclass
class Pack:
    name: str
    title: str
    root: Path
    documents: list[Document]
    config: dict = field(default_factory=dict)

    def doc(self, doc_id: str, version: str) -> Document | None:
        for d in self.documents:
            if d.doc_id == doc_id and d.version == version:
                return d
        return None

    def current(self, doc_id: str) -> Document | None:
        for d in self.documents:
            if d.doc_id == doc_id and d.is_current:
                return d
        return None

    def cases(self, split: str) -> list[dict]:
        path = self.root / self.config["cases"][split]
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _parse_document(path: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path.name}: missing front matter")
    head, _, body = text[4:].partition("\n---\n")
    meta = yaml.safe_load(head) or {}
    clauses: dict[str, str] = {}
    for line in body.splitlines():
        m = CLAUSE.match(line.strip())
        if m:
            clauses[m.group(1)] = m.group(2)
    return Document(
        doc_id=str(meta["id"]),
        title=str(meta["title"]),
        version=str(meta["version"]),
        status=str(meta["status"]),
        meta={k: str(v) for k, v in meta.items()},
        clauses=clauses,
        body=body.strip(),
    )


def load_pack(root: str | Path) -> Pack:
    root = Path(root)
    config = yaml.safe_load((root / "pack.yaml").read_text(encoding="utf-8"))
    corpus_dir = root / config.get("corpus_dir", "corpus")
    documents = [_parse_document(p) for p in sorted(corpus_dir.glob("*.md"))]
    return Pack(name=config["name"], title=config["title"], root=root, documents=documents, config=config)
