import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "src" / "remote_server.py"
TOKEN = "test-token-0123456789abcdef"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def post(url, obj, version=None, origin=None):
    body = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode()
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if version:
        headers["MCP-Protocol-Version"] = version
    if origin:
        headers["Origin"] = origin
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        raw = r.read()
        return r.status, json.loads(raw) if raw else None


def main():
    td = tempfile.mkdtemp(prefix="sssp-http-test-")
    port = free_port()
    env = dict(os.environ)
    env.update({
        "SSSP_ROOT": td,
        "HOST": "127.0.0.1",
        "PORT": str(port),
        "SSSP_ENDPOINT_TOKEN": TOKEN,
        "SSSP_ALLOWED_ORIGINS": "https://chatgpt.com,http://127.0.0.1",
    })
    p = subprocess.Popen(["python3", str(SERVER)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    base = f"http://127.0.0.1:{port}"
    mcp = f"{base}/mcp/{TOKEN}"
    try:
        deadline = time.time() + 8
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"{base}/healthz", timeout=1) as r:
                    if r.status == 200:
                        break
            except Exception:
                time.sleep(0.1)
        else:
            raise RuntimeError("remote server did not become healthy")

        status, init = post(mcp, {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"http-smoke","version":"0.1"}}}, origin="https://chatgpt.com")
        assert status == 200 and init["result"]["protocolVersion"] == "2025-11-25"

        status, no_body = post(mcp, {"jsonrpc":"2.0","method":"notifications/initialized"}, version="2025-11-25")
        assert status == 202 and no_body is None

        status, tools = post(mcp, {"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}, version="2025-11-25")
        names = {x["name"] for x in tools["result"]["tools"]}
        assert "sssp.create_document" in names and "sssp.commit_version" in names

        status, create = post(mcp, {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"sssp.create_document","arguments":{"document_id":"remote-paper","title":"Remote MCP 測試"}}}, version="2025-11-25")
        assert create["result"]["isError"] is False

        status, append = post(mcp, {"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"sssp.append_node","arguments":{"document_id":"remote-paper","expected_revision":0,"node":{"id":"eq-1","type":"math_block","latex":r"\forall x\in X,\;P(x)"}}}}, version="2025-11-25")
        assert append["result"]["isError"] is False

        try:
            post(mcp, {"jsonrpc":"2.0","id":5,"method":"ping"}, version="2099-01-01")
            raise AssertionError("unsupported protocol version should fail")
        except urllib.error.HTTPError as e:
            assert e.code == 400

        try:
            post(mcp, {"jsonrpc":"2.0","id":6,"method":"ping"}, origin="https://evil.example")
            raise AssertionError("untrusted origin should fail")
        except urllib.error.HTTPError as e:
            assert e.code == 403

        try:
            urllib.request.urlopen(urllib.request.Request(mcp, method="GET"), timeout=2)
            raise AssertionError("GET /mcp should return 405 when SSE is disabled")
        except urllib.error.HTTPError as e:
            assert e.code == 405

        print(json.dumps({"ok": True, "transport": "streamable-http-json", "tools": len(names), "endpoint": f"/mcp/{TOKEN}"}, ensure_ascii=False, indent=2))
    finally:
        p.terminate()
        try:
            p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            p.kill()
        err = p.stderr.read()
        if err:
            print("[server stderr]", err)
        shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    main()
