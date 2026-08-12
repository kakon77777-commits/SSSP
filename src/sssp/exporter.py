from __future__ import annotations
from typing import Any, Dict, List
from .common import document_hash


def export_markdown(doc: Dict[str, Any]) -> str:
    out: List[str] = [f"# {doc.get('title','Untitled')}", ""]
    for n in doc.get("nodes", []):
        t = n.get("type")
        if t == "heading":
            level = int(n.get("level", 2)) if str(n.get("level", 2)).isdigit() else 2
            level = max(1, min(6, level))
            out.extend(["#" * level + " " + n.get("content", ""), ""])
        elif t in {"paragraph", "note", "reference"}:
            out.extend([n.get("content", ""), ""])
        elif t == "math_block":
            out.extend(["$$", n.get("latex", ""), "$$", ""])
        elif t == "definition":
            out.extend([f"**定義｜{n.get('label','')}**".rstrip("｜"), "", n.get("content", ""), ""])
        elif t == "claim":
            meta = n.get("claim", {}) if isinstance(n.get("claim"), dict) else {}
            out.extend([f"**Claim [{meta.get('type','claim')} / {meta.get('status','unspecified')}]**", "", n.get("content", ""), ""])
        elif t == "code":
            out.extend([f"```{n.get('language','')}", n.get("content", ""), "```", ""])
    out.extend(["---", f"<!-- SSSP source revision: {doc.get('revision')} -->", f"<!-- SSSP source hash: {document_hash(doc)} -->", ""])
    return "\n".join(out)
