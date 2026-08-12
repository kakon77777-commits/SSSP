#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from typing import Any, Dict, Tuple

from mcp_server import MCP_VERSION, SERVER_INFO, TOOLS, call_tool, tool_result
from sssp_core import SSSPError

SUPPORTED_PROTOCOL_VERSIONS = {"2025-11-25", "2025-06-18", "2025-03-26"}
DEFAULT_ALLOWED_ORIGINS = {
    "https://chatgpt.com",
    "https://www.chatgpt.com",
    "https://chat.openai.com",
    "http://localhost",
    "http://127.0.0.1",
}


def _jsonrpc_error(req_id: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
    if data is not None:
        out["error"]["data"] = data
    return out


def _negotiate_version(requested: str | None) -> str:
    if requested in SUPPORTED_PROTOCOL_VERSIONS:
        return str(requested)
    return MCP_VERSION


def dispatch(msg: Dict[str, Any]) -> Tuple[int, Dict[str, Any] | None]:
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
        return 400, _jsonrpc_error(msg.get("id") if isinstance(msg, dict) else None, -32600, "Invalid Request")

    method = msg.get("method")
    req_id = msg.get("id")

    if method == "initialize":
        requested = (msg.get("params") or {}).get("protocolVersion")
        return 200, {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": _negotiate_version(requested),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {**SERVER_INFO, "version": "0.2.0"},
                "instructions": "Use SSSP tools for canonical scholarly source. Rendered chat/Markdown is not the source of truth.",
            },
        }

    if method == "notifications/initialized":
        return 202, None

    if method == "ping":
        return 200, {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        return 200, {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        if not isinstance(name, str) or not isinstance(args, dict):
            return 200, _jsonrpc_error(req_id, -32602, "Invalid tools/call parameters")
        try:
            value = call_tool(name, args)
            return 200, {"jsonrpc": "2.0", "id": req_id, "result": tool_result(value, False)}
        except SSSPError as exc:
            if exc.code == "UNKNOWN_TOOL":
                return 200, _jsonrpc_error(req_id, -32602, exc.message, {"code": exc.code})
            return 200, {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": tool_result({"code": exc.code, "message": exc.message, "data": exc.data}, True),
            }
        except Exception as exc:
            return 200, {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": tool_result({"code": "INTERNAL", "message": str(exc)}, True),
            }

    if req_id is not None:
        return 200, _jsonrpc_error(req_id, -32601, f"Method not found: {method}")
    return 202, None


class MCPHTTPHandler(BaseHTTPRequestHandler):
    server_version = "SSSPRemoteMCP/0.2"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[http] {self.address_string()} - {fmt % args}", file=sys.stderr, flush=True)

    @property
    def endpoint_path(self) -> str:
        token = os.environ.get("SSSP_ENDPOINT_TOKEN", "").strip()
        if token:
            return f"/mcp/{token}"
        return "/mcp"

    def _allowed_origins(self) -> set[str]:
        raw = os.environ.get("SSSP_ALLOWED_ORIGINS", "").strip()
        if not raw:
            return set(DEFAULT_ALLOWED_ORIGINS)
        return {x.strip() for x in raw.split(",") if x.strip()}

    def _origin_ok(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        allowed = self._allowed_origins()
        return "*" in allowed or origin in allowed

    def _path_ok(self) -> bool:
        return urlsplit(self.path).path.rstrip("/") == self.endpoint_path.rstrip("/")

    def _write_json(self, status: int, body: Dict[str, Any] | None, extra_headers: Dict[str, str] | None = None) -> None:
        payload = b"" if body is None else json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        if body is not None:
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
        else:
            self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    def _protocol_header_ok(self) -> bool:
        version = self.headers.get("MCP-Protocol-Version")
        if not version:
            return True
        return version in SUPPORTED_PROTOCOL_VERSIONS

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/healthz":
            self._write_json(200, {"ok": True, "service": "sssp-mcp", "version": "0.2.0"})
            return
        if self._path_ok():
            self._write_json(405, {"error": "SSE stream not enabled"}, {"Allow": "POST"})
            return
        self._write_json(404, {"error": "not found"})

    def do_DELETE(self) -> None:
        if self._path_ok():
            self._write_json(405, {"error": "stateless server has no deletable MCP session"}, {"Allow": "POST"})
            return
        self._write_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if not self._path_ok():
            self._write_json(404, {"error": "not found"})
            return
        if not self._origin_ok():
            self._write_json(403, _jsonrpc_error(None, -32000, "Origin not allowed"))
            return
        if not self._protocol_header_ok():
            self._write_json(400, _jsonrpc_error(None, -32600, "Unsupported MCP-Protocol-Version"))
            return

        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._write_json(400, _jsonrpc_error(None, -32700, "Invalid Content-Length"))
            return
        max_bytes = int(os.environ.get("SSSP_MAX_REQUEST_BYTES", str(2 * 1024 * 1024)))
        if size <= 0 or size > max_bytes:
            self._write_json(413 if size > max_bytes else 400, _jsonrpc_error(None, -32700, "Invalid request body size"))
            return

        raw = self.rfile.read(size)
        try:
            msg = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._write_json(400, _jsonrpc_error(None, -32700, "Parse error", {"detail": str(exc)}))
            return

        status, response = dispatch(msg)
        self._write_json(status, response)


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    token = os.environ.get("SSSP_ENDPOINT_TOKEN", "").strip()
    if host not in {"127.0.0.1", "localhost"} and not token and os.environ.get("SSSP_ALLOW_INSECURE_REMOTE") != "1":
        raise SystemExit("Refusing remote bind without SSSP_ENDPOINT_TOKEN. Set a URL-safe secret token or SSSP_ALLOW_INSECURE_REMOTE=1 for disposable testing.")
    endpoint = f"/mcp/{token}" if token else "/mcp"
    print(f"SSSP remote MCP v0.2 listening on http://{host}:{port}{endpoint}", file=sys.stderr, flush=True)
    ThreadingHTTPServer((host, port), MCPHTTPHandler).serve_forever()


if __name__ == "__main__":
    main()
