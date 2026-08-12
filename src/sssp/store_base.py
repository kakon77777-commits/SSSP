from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional
from .common import (
    NODE_TYPES, PROTOCOL, PROTOCOL_VERSION, SSSPError, atomic_write_json,
    document_hash, node_checksum, safe_document_id, utc_now,
)
from .validation import validate_document_obj


class SSSPStoreBase:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _dir(self, document_id: str) -> Path:
        if not safe_document_id(document_id):
            raise SSSPError("INVALID_DOCUMENT_ID", "document_id must match [A-Za-z0-9._-]{1,128}")
        p = (self.root / document_id).resolve()
        if self.root not in p.parents and p != self.root:
            raise SSSPError("PATH_TRAVERSAL", "document path escapes configured root")
        return p

    def _doc_path(self, document_id: str) -> Path:
        return self._dir(document_id) / "document.json"

    def _audit(self, document_id: str, event: Dict[str, Any]) -> None:
        path = self._dir(document_id) / "audit.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"ts": utc_now(), **event}, ensure_ascii=False, separators=(",", ":")) + "\n")

    def create_document(self, document_id: str, title: str, actor: str = "assistant") -> Dict[str, Any]:
        d = self._dir(document_id)
        if self._doc_path(document_id).exists():
            raise SSSPError("DOCUMENT_EXISTS", f"Document already exists: {document_id}")
        now = utc_now()
        doc = {"protocol": PROTOCOL, "version": PROTOCOL_VERSION, "document_id": document_id, "title": title, "revision": 0, "created_at": now, "updated_at": now, "nodes": [], "semantic_ledger": {"terms": {}, "deprecated_terms": {}, "symbols": {}}, "claim_ledger": {}}
        d.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._doc_path(document_id), doc)
        self._audit(document_id, {"action": "create_document", "actor": actor, "revision": 0})
        return self.summary(doc)

    def load(self, document_id: str) -> Dict[str, Any]:
        p = self._doc_path(document_id)
        if not p.exists():
            raise SSSPError("DOCUMENT_NOT_FOUND", f"Unknown document: {document_id}")
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            raise SSSPError("DOCUMENT_CORRUPT", f"Cannot read canonical document: {e}")

    def summary(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        return {"document_id": doc["document_id"], "title": doc["title"], "revision": doc["revision"], "node_count": len(doc.get("nodes", [])), "document_hash": document_hash(doc)}

    def _ensure_revision(self, doc: Dict[str, Any], expected_revision: Optional[int]) -> None:
        if expected_revision is not None and doc.get("revision") != expected_revision:
            raise SSSPError("REVISION_CONFLICT", f"Expected revision {expected_revision}, current revision is {doc.get('revision')}", {"expected": expected_revision, "current": doc.get("revision")})

    def _normalize_node(self, node: Dict[str, Any], actor: str, reason: str) -> Dict[str, Any]:
        n = copy.deepcopy(node)
        node_id, node_type = n.get("id"), n.get("type")
        if not isinstance(node_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", node_id):
            raise SSSPError("INVALID_NODE_ID", "node.id must match [A-Za-z0-9._-]{1,128}")
        if node_type not in NODE_TYPES:
            raise SSSPError("INVALID_NODE_TYPE", f"Unsupported node type: {node_type}")
        if node_type == "math_block":
            if not isinstance(n.get("latex"), str) or not n["latex"].strip():
                raise SSSPError("INVALID_NODE", "math_block requires non-empty latex")
            n.pop("content", None)
        elif not isinstance(n.get("content"), str):
            raise SSSPError("INVALID_NODE", f"{node_type} requires string content")
        now = utc_now()
        n.setdefault("created_at", now)
        n["updated_at"] = now
        n["provenance"] = {"actor": actor, "reason": reason}
        n["checksum"] = node_checksum(n)
        return n

    def _validate_before_commit(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        report = validate_document_obj(candidate, render_math=True)
        if report["status"] == "FAIL":
            raise SSSPError("VALIDATION_FAILED", "Candidate document failed validation", report)
        return report
