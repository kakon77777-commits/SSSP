# SSSP Remote MCP v0.2 — 部署與 ChatGPT 連線

SSSP v0.2 新增 **MCP Streamable HTTP** endpoint，保留 v0.1 stdio server。

## Transport

Remote server：

```text
python3 src/remote_server.py
```

預設 health endpoint：

```text
GET /healthz
```

MCP endpoint：

```text
POST /mcp/<SSSP_ENDPOINT_TOKEN>
```

v0.2 是 stateless basic Streamable HTTP server：request 使用 HTTP POST + JSON response；`GET /mcp/...` 回 `405`，表示目前不提供 server-initiated SSE stream。這是 MCP Streamable HTTP 規格允許的模式。

## 必要環境變數

遠端 bind 時必須設定 URL-safe secret：

```text
SSSP_ENDPOINT_TOKEN=<long-random-url-safe-secret>
```

如果沒有 token，server 預設拒絕 bind 到非 localhost。`SSSP_ALLOW_INSECURE_REMOTE=1` 只應用於一次性 disposable test。

可選：

```text
SSSP_ALLOWED_ORIGINS=https://chatgpt.com,https://www.chatgpt.com,https://chat.openai.com
SSSP_ROOT=/path/to/canonical/data
PORT=8000
HOST=0.0.0.0
```

## Docker

```bash
docker build -t sssp-mcp .
docker run --rm -p 8000:8000 \
  -e SSSP_ENDPOINT_TOKEN='YOUR_LONG_SECRET' \
  sssp-mcp
```

ChatGPT server URL：

```text
https://YOUR-HOST/mcp/YOUR_LONG_SECRET
```

此 URL 本身等同開發期憑證，請勿公開貼出。

## Render Blueprint

Repo 根目錄包含 `render.yaml` 與 `Dockerfile`。Render 建立 Blueprint 時會要求輸入 `SSSP_ENDPOINT_TOKEN`。

部署完成後，Render 會提供：

```text
https://YOUR-SERVICE.onrender.com
```

ChatGPT 中填：

```text
名稱：SSSP
說明：AI 原生學術來源協議。提供 canonical scholarly source 的建立、typed-node 修改、驗證、匯出與版本快照。
伺服器 URL：https://YOUR-SERVICE.onrender.com/mcp/YOUR_LONG_SECRET
驗證：無驗證 / None（endpoint URL 的 secret 僅作開發期保護）
```

## Security scope

`/mcp/<secret>` 是 **開發期 capability URL**，不是 OAuth 的替代品。正式多人／長期部署應改用標準 OAuth/OIDC、reverse proxy authentication 或 OpenAI Secure MCP Tunnel。

此版本還有一個重要限制：若部署平台檔案系統是 ephemeral，SSSP canonical data 會隨服務重啟而遺失。第一次 ChatGPT 連線測試可以接受；真正 production scholarly storage 必須改用 persistent disk、database 或 Git-backed storage backend。
