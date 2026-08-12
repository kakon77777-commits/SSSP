from __future__ import annotations

import copy
from typing import Any, Dict, Optional
from .common import SSSPError, atomic_write_json, atomic_write_text, document_hash, node_checksum, utc_now
from .exporter import export_markdown
from .store_base import SSSPStoreBase
from .validation import validate_document_obj


class SSSPStore(SSSPStoreBase):
    def append_node(self, document_id: str, node: Dict[str, Any], expected_revision: Optional[int] = None, actor: str = "assistant", reason: str = "append node") -> Dict[str, Any]:
        doc = self.load(document_id)
        self._ensure_revision(doc, expected_revision)
        n = self._normalize_node(node, actor, reason)
        if any(x.get("id") == n["id"] for x in doc["nodes"]):
            raise SSSPError("NODE_EXISTS", f"Node already exists: {n['id']}")
        candidate = copy.deepcopy(doc)
        candidate["nodes"].append(n)
        candidate["revision"] += 1
        candidate["updated_at"] = utc_now()
        report = self._validate_before_commit(candidate)
        atomic_write_json(self._doc_path(document_id), candidate)
        self._audit(document_id, {"action": "append_node", "actor": actor, "node_id": n["id"], "revision": candidate["revision"]})
        return {**self.summary(candidate), "node": n, "validation": report}

    def replace_node(self, document_id: str, node_id: str, replacement: Dict[str, Any], expected_revision: Optional[int] = None, expected_checksum: Optional[str] = None, actor: str = "assistant", reason: str = "replace node") -> Dict[str, Any]:
        doc = self.load(document_id)
        self._ensure_revision(doc, expected_revision)
        idx = next((i for i, n in enumerate(doc["nodes"]) if n.get("id") == node_id), None)
        if idx is None:
            raise SSSPError("NODE_NOT_FOUND", f"Unknown node: {node_id}")
        old = doc["nodes"][idx]
        if expected_checksum is not None and old.get("checksum") != expected_checksum:
            raise SSSPError("CHECKSUM_CONFLICT", "Node checksum differs from expected value", {"expected": expected_checksum, "current": old.get("checksum")})
        n = self._normalize_node({**replacement, "id": node_id}, actor, reason)
        n["created_at"] = old.get("created_at", n["created_at"])
        n["checksum"] = node_checksum(n)
        candidate = copy.deepcopy(doc)
        candidate["nodes"][idx] = n
        candidate["revision"] += 1
        candidate["updated_at"] = utc_now()
        report = self._validate_before_commit(candidate)
        atomic_write_json(self._doc_path(document_id), candidate)
        self._audit(document_id, {"action": "replace_node", "actor": actor, "node_id": node_id, "revision": candidate["revision"]})
        return {**self.summary(candidate), "node": n, "previous_checksum": old.get("checksum"), "validation": report}

    def read_node(self, document_id: str, node_id: str) -> Dict[str, Any]:
        doc = self.load(document_id)
        for n in doc["nodes"]:
            if n.get("id") == node_id:
                return {"document_id": document_id, "revision": doc["revision"], "node": n}
        raise SSSPError("NODE_NOT_FOUND", f"Unknown node: {node_id}")

    def validate_document(self, document_id: str) -> Dict[str, Any]:
        return validate_document_obj(self.load(document_id), render_math=True)

    def export_document(self, document_id: str, fmt: str = "markdown") -> Dict[str, Any]:
        if fmt != "markdown":
            raise SSSPError("UNSUPPORTED_EXPORT", "MVP supports only markdown export")
        doc = self.load(document_id)
        report = validate_document_obj(doc, render_math=True)
        if report["status"] == "FAIL":
            raise SSSPError("VALIDATION_FAILED", "Cannot export invalid canonical document", report)
        path = self._dir(document_id) / "exports" / f"{document_id}_r{doc['revision']}.md"
        atomic_write_text(path, export_markdown(doc))
        meta = {"protocol": "SSSP", "source_revision": doc["revision"], "source_hash": document_hash(doc), "compiler": "sssp-markdown-exporter/0.1", "exported_at": utc_now(), "path": str(path)}
        atomic_write_json(path.with_suffix(".meta.json"), meta)
        self._audit(document_id, {"action": "export_document", "format": fmt, "revision": doc["revision"], "path": str(path)})
        return {**meta, "validation": report}

    def commit_version(self, document_id: str, label: str = "snapshot") -> Dict[str, Any]:
        doc = self.load(document_id)
        report = validate_document_obj(doc, render_math=True)
        if report["status"] == "FAIL":
            raise SSSPError("VALIDATION_FAILED", "Cannot snapshot invalid canonical document", report)
        h = document_hash(doc).split(":", 1)[1][:12]
        p = self._dir(document_id) / "versions" / f"r{doc['revision']:06d}_{h}.json"
        if not p.exists():
            atomic_write_json(p, {"label": label, "snapshot_at": utc_now(), "document_hash": document_hash(doc), "document": doc})
        self._audit(document_id, {"action": "commit_version", "revision": doc["revision"], "label": label, "path": str(p)})
        return {"document_id": document_id, "revision": doc["revision"], "document_hash": document_hash(doc), "snapshot": str(p), "validation": report}
