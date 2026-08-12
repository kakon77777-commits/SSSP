# MCP stdio 接法示例

SSSP-MCP v0.1 使用 stdio。MCP host 需要啟動：

```text
python3 /ABSOLUTE/PATH/SSSP_MCP_MVP/src/mcp_server.py
```

可選環境變數：

```text
SSSP_ROOT=/ABSOLUTE/PATH/TO/SSSP_DATA
```

許多 MCP host 使用類似以下的 server registration 概念，但各 host 的設定檔名稱與 schema 可能不同，請依該 host 當前文件調整：

```json
{
  "sssp": {
    "command": "python3",
    "args": ["/ABSOLUTE/PATH/SSSP_MCP_MVP/src/mcp_server.py"],
    "env": {
      "SSSP_ROOT": "/ABSOLUTE/PATH/TO/SSSP_DATA"
    }
  }
}
```

也可以不接任何 AI host，直接執行：

```bash
python3 tests/test_mcp_smoke.py
```

這會以真正的 MCP JSON-RPC lifecycle 呼叫 server。
