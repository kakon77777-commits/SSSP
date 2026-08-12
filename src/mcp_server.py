#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from sssp_core import SSSPError, SSSPStore

MCP_VERSION = "2025-11-25"
SERVER_INFO = {"name": "sssp-mcp", "title": "SSSP Scholarly Source Server", "version": "0.2.0"}
ROOT = Path(os.environ.get("SSSP_ROOT", Path(__file__).resolve().parent.parent / "data"))
STORE = SSSPStore(ROOT)

from mcp_tools import TOOLS


def send(obj: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def rpc_error(req_id, code: int, message: str, data=None):
    out = {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
    if data is not None:
        out["error"]["data"] = data
    send(out)


def tool_result(value: Dict[str, Any], is_error: bool = False) -> Dict[str, Any]:
    text = json.dumps(value, ensure_ascii=False, indent=2)
    return {"content": [{"type": "text", "text": text}], "structuredContent": value, "isError": is_error}


def call_tool(name: str, a: Dict[str, Any]) -> Dict[str, Any]:
    if name == "sssp.create_document":
        return STORE.create_document(a["document_id"], a["title"], a.get("actor", "assistant"))
    if name == "sssp.append_node":
        return STORE.append_node(a["document_id"], a["node"], a.get("expected_revision"), a.get("actor", "assistant"), a.get("reason", "append node"))
    if name == "sssp.replace_node":
        return STORE.replace_node(a["document_id"], a["node_id"], a["replacement"], a.get("expected_revision"), a.get("expected_checksum"), a.get("actor", "assistant"), a.get("reason", "replace node"))
    if name == "sssp.read_node":
        return STORE.read_node(a["document_id"], a["node_id"])
    if name == "sssp.validate_document":
        return STORE.validate_document(a["document_id"])
    if name == "sssp.export_document":
        return STORE.export_document(a["document_id"], a.get("format", "markdown"))
    if name == "sssp.commit_version":
        return STORE.commit_version(a["document_id"], a.get("label", "snapshot"))
    raise SSSPError("UNKNOWN_TOOL", f"Unknown tool: {name}")


def handle(msg: Dict[str, Any]) -> None:
    method = msg.get("method")
    req_id = msg.get("id")
    if method == "initialize":
        requested = msg.get("params", {}).get("protocolVersion", MCP_VERSION)
        version = MCP_VERSION if requested != MCP_VERSION else requested
        send({
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
                "instructions": "Use SSSP tools for canonical scholarly source. Rendered chat/Markdown is not the source of truth."
            }
        })
        return
    if method == "notifications/initialized":
        return
    if method == "ping":
        send({"jsonrpc": "2.0", "id": req_id, "result": {}})
        return
    if method == "tools/list":
        send({"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}})
        return
    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        if not isinstance(name, str) or not isinstance(args, dict):
            rpc_error(req_id, -32602, "Invalid tools/call parameters")
            return
        try:
            value = call_tool(name, args)
            send({"jsonrpc": "2.0", "id": req_id, "result": tool_result(value, False)})
        except SSSPError as e:
            if e.code == "UNKNOWN_TOOL":
                rpc_error(req_id, -32602, e.message, {"code": e.code})
            else:
                send({"jsonrpc": "2.0", "id": req_id, "result": tool_result({"code": e.code, "message": e.message, "data": e.data}, True)})
        except Exception as e:
            send({"jsonrpc": "2.0", "id": req_id, "result": tool_result({"code": "INTERNAL", "message": str(e)}, True)})
        return
    if req_id is not None:
        rpc_error(req_id, -32601, f"Method not found: {method}")


def main() -> None:
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
            if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
                rpc_error(msg.get("id") if isinstance(msg, dict) else None, -32600, "Invalid Request")
                continue
            handle(msg)
        except json.JSONDecodeError as e:
            rpc_error(None, -32700, "Parse error", {"detail": str(e)})
        except Exception as e:
            print(f"SSSP server internal error: {e}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
