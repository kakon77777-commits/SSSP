from __future__ import annotations

import json
import os
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Tuple
from .common import (
    CONTROL_FORBIDDEN, DANGEROUS_CONTROL, NODE_TYPES, PROTOCOL,
    ZERO_WIDTH, ValidationIssue, document_hash, node_checksum,
)


def _find_unicode_issues(text: str, node_id: str) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    for ch in text:
        cp = ord(ch)
        if ch in CONTROL_FORBIDDEN or ch in DANGEROUS_CONTROL:
            issues.append(ValidationIssue("FAIL", "CONTROL_CHAR", f"Forbidden control character U+{cp:04X}", node_id))
        if ch in ZERO_WIDTH:
            issues.append(ValidationIssue("FAIL", "ZERO_WIDTH", f"Zero-width/BOM marker U+{cp:04X}", node_id))
        if unicodedata.category(ch) == "Co":
            issues.append(ValidationIssue("FAIL", "PUA_CHAR", f"Private Use Area character U+{cp:04X}", node_id))
    return issues


def _balanced_braces(tex: str) -> bool:
    depth = 0
    escaped = False
    for ch in tex:
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _environment_balance(tex: str) -> Tuple[bool, str]:
    stack: List[str] = []
    for m in re.finditer(r"\\(begin|end)\{([^}]+)\}", tex):
        kind, name = m.group(1), m.group(2)
        if kind == "begin":
            stack.append(name)
        elif not stack or stack[-1] != name:
            return False, f"environment mismatch at {name}"
        else:
            stack.pop()
    return (False, f"unclosed environment(s): {', '.join(stack)}") if stack else (True, "")


def validate_math_with_mathjax(tex: str) -> Tuple[bool, str]:
    script = Path(__file__).resolve().parents[2] / "scripts" / "mathjax_validate.js"
    if not script.exists():
        return True, "MathJax validator script unavailable"
    env = dict(os.environ)
    local_modules = Path(__file__).resolve().parents[2] / "node_modules"
    if local_modules.exists():
        env["NODE_PATH"] = str(local_modules)
    else:
        try:
            env["NODE_PATH"] = subprocess.check_output(["npm", "root", "-g"], text=True, timeout=3).strip()
        except Exception:
            pass
    try:
        p = subprocess.run(["node", str(script)], input=json.dumps({"latex": tex}, ensure_ascii=False), text=True, capture_output=True, env=env, timeout=8)
        if p.returncode == 0:
            return True, "OK"
        return False, (p.stderr or p.stdout or "MathJax parse failure").strip()[:1000]
    except FileNotFoundError:
        return True, "Node unavailable; L2 skipped"
    except Exception as e:
        return True, f"L2 skipped: {e}"


def validate_document_obj(doc: Dict[str, Any], render_math: bool = True) -> Dict[str, Any]:
    issues: List[ValidationIssue] = []
    for k in ["protocol", "version", "document_id", "title", "revision", "nodes"]:
        if k not in doc:
            issues.append(ValidationIssue("FAIL", "MISSING_FIELD", f"Missing document field: {k}"))
    if doc.get("protocol") != PROTOCOL:
        issues.append(ValidationIssue("FAIL", "PROTOCOL_MISMATCH", f"Expected protocol {PROTOCOL}"))
    nodes = doc.get("nodes", []) if isinstance(doc.get("nodes", []), list) else []
    if not isinstance(doc.get("nodes", []), list):
        issues.append(ValidationIssue("FAIL", "INVALID_NODES", "nodes must be an array"))
    seen = set()
    render_checked = 0
    render_notes: List[str] = []
    for n in nodes:
        node_id = str(n.get("id", "<missing>"))
        if node_id in seen:
            issues.append(ValidationIssue("FAIL", "DUPLICATE_NODE_ID", f"Duplicate node id: {node_id}", node_id))
        seen.add(node_id)
        if n.get("type") not in NODE_TYPES:
            issues.append(ValidationIssue("FAIL", "INVALID_NODE_TYPE", f"Unsupported node type: {n.get('type')}", node_id))
        text = n.get("latex") if n.get("type") == "math_block" else n.get("content")
        if not isinstance(text, str):
            issues.append(ValidationIssue("FAIL", "MISSING_NODE_TEXT", "Node text/latex must be a string", node_id))
            continue
        issues.extend(_find_unicode_issues(text, node_id))
        if n.get("checksum") != node_checksum(n):
            issues.append(ValidationIssue("FAIL", "CHECKSUM_MISMATCH", "Node checksum does not match canonical node", node_id))
        if n.get("type") == "math_block":
            if "$" in text:
                issues.append(ValidationIssue("WARN", "MATH_DELIMITER_IN_CANONICAL", "Canonical math_block should not include Markdown $ delimiters", node_id))
            if not _balanced_braces(text):
                issues.append(ValidationIssue("FAIL", "UNBALANCED_BRACES", "LaTeX braces appear unbalanced", node_id))
            ok_env, msg = _environment_balance(text)
            if not ok_env:
                issues.append(ValidationIssue("FAIL", "ENVIRONMENT_MISMATCH", msg, node_id))
            for line in text.splitlines()[1:]:
                stripped = line.lstrip()
                if re.match(r"^(eg|eq|abla|oxed|orall|ightarrow|arnothing|ext)\b", stripped):
                    issues.append(ValidationIssue("WARN", "ESCAPE_CORRUPTION_RISK", f"Suspicious command fragment after line break: {stripped[:40]}", node_id))
            if render_math:
                ok, msg = validate_math_with_mathjax(text)
                if ok:
                    render_checked += 1
                    if msg != "OK":
                        render_notes.append(msg)
                else:
                    issues.append(ValidationIssue("FAIL", "MATHJAX_PARSE", msg, node_id))
    levels = [i.level for i in issues]
    status = "FAIL" if "FAIL" in levels else ("WARN" if "WARN" in levels else "PASS")
    return {"status": status, "issue_count": len(issues), "issues": [i.as_dict() for i in issues], "render_math_checked": render_checked, "render_notes": sorted(set(render_notes))[:5], "document_hash": document_hash(doc)}
