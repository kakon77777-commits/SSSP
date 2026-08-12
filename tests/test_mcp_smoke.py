import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "src" / "mcp_server.py"


def send(p, obj):
    p.stdin.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")
    p.stdin.flush()


def recv(p):
    line = p.stdout.readline()
    if not line:
        raise RuntimeError("server closed stdout")
    return json.loads(line)


def call(p, i, name, args):
    send(p, {"jsonrpc":"2.0","id":i,"method":"tools/call","params":{"name":name,"arguments":args}})
    return recv(p)


def main():
    td = tempfile.mkdtemp(prefix="sssp-mcp-test-")
    env = dict(os.environ)
    env["SSSP_ROOT"] = td
    p = subprocess.Popen(["python3", str(SERVER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    try:
        send(p, {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"smoke","version":"0.1"}}})
        init = recv(p)
        assert init["result"]["protocolVersion"] == "2025-11-25"
        send(p, {"jsonrpc":"2.0","method":"notifications/initialized"})
        send(p, {"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}})
        tools = recv(p)
        names = {x["name"] for x in tools["result"]["tools"]}
        assert "sssp.create_document" in names and "sssp.commit_version" in names
        c = call(p, 3, "sssp.create_document", {"document_id":"mcp-paper","title":"MCP 測試"})
        assert c["result"]["isError"] is False
        a = call(p, 4, "sssp.append_node", {"document_id":"mcp-paper","expected_revision":0,"node":{"id":"eq-1","type":"math_block","latex":r"\neg P(x) \Rightarrow Q(x)"}})
        assert a["result"]["isError"] is False
        v = call(p, 5, "sssp.validate_document", {"document_id":"mcp-paper"})
        assert v["result"]["isError"] is False
        assert v["result"]["structuredContent"]["status"] in {"PASS","WARN"}
        e = call(p, 6, "sssp.export_document", {"document_id":"mcp-paper","format":"markdown"})
        assert e["result"]["isError"] is False
        s = call(p, 7, "sssp.commit_version", {"document_id":"mcp-paper","label":"smoke"})
        assert s["result"]["isError"] is False
        print(json.dumps({"ok": True, "tools": len(names), "validation": v["result"]["structuredContent"]["status"], "export": e["result"]["structuredContent"]["path"]}, ensure_ascii=False, indent=2))
    finally:
        p.stdin.close()
        try:
            p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            p.terminate()
        err = p.stderr.read()
        if err:
            print("[server stderr]", err)
        shutil.rmtree(td, ignore_errors=True)

if __name__ == "__main__":
    main()
