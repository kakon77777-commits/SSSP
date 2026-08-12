from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

PROTOCOL = "SSSP"
PROTOCOL_VERSION = "0.1"
NODE_TYPES = {"heading", "paragraph", "math_block", "definition", "claim", "code", "reference", "note"}
CONTROL_FORBIDDEN = {chr(i) for i in range(0x00, 0x20)} - {"\n", "\r", "\t"}
ZERO_WIDTH = {"\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"}
DANGEROUS_CONTROL = {chr(x) for x in [0x07, 0x08, 0x0B, 0x0C]}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def node_for_hash(node: Dict[str, Any]) -> Dict[str, Any]:
    x = copy.deepcopy(node)
    x.pop("checksum", None)
    return x


def node_checksum(node: Dict[str, Any]) -> str:
    return sha256_text(canonical_json(node_for_hash(node)))


def document_hash(doc: Dict[str, Any]) -> str:
    return sha256_text(canonical_json(doc))


def safe_document_id(document_id: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9._-]{1,128}", document_id or ""))


def atomic_write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@dataclass
class ValidationIssue:
    level: str
    code: str
    message: str
    node_id: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        d = {"level": self.level, "code": self.code, "message": self.message}
        if self.node_id:
            d["node_id"] = self.node_id
        return d


class SSSPError(Exception):
    def __init__(self, code: str, message: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data or {}
