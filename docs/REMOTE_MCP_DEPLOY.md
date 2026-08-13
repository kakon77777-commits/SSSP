# SSSP Remote MCP v0.3 — ChatGPT / Claude 連線與部署

SSSP 的公開研究端點已部署為 MCP Streamable HTTP：

```text
https://sssp.evemisslab.com/mcp
```

它刻意採用 **無驗證**。ChatGPT 與 Claude 都從各自的雲端服務連入這個 HTTPS URL，不需要本機常駐程序。

## ChatGPT 自訂連接器

```text
名稱：SSSP
說明：Canonical scholarly source tools
伺服器 URL：https://sssp.evemisslab.com/mcp
驗證：無驗證
```

勾選自訂 MCP 風險確認後建立。URL 必須包含結尾的 `/mcp`。

## Claude custom connector

```text
Name：SSSP
Remote MCP server URL：https://sssp.evemisslab.com/mcp
OAuth Client ID：留白
OAuth Client Secret：留白
```

按下 **Add** 後，在對話的 Connectors 選單啟用 SSSP。

## 公開資料邊界

這是一個共享、無驗證的研究 workspace：

- 不要寫入密碼、API key、個資、私人草稿、未公開研究或任何機密內容；
- `actor` 只是未驗證的 provenance 顯示字串，不代表真實身分；
- 任何知道 `document_id` 的人都可能讀取或修改其中的節點；
- 沒有 list/delete document tool，但不可把難猜的 `document_id` 當成安全機制；
- replace 操作仍以 revision 與 checksum 偵測衝突，但不提供 ownership authorization。

目前的防濫用邊界包括 Host／Origin 驗證、2 MiB request guard、Cloudflare rate-limit binding，以及文件、節點、MathJax、snapshot 與總儲存量上限。這些措施控制公開研究服務的風險與成本，**不是 authentication**。

## 架構

```text
ChatGPT / Claude
        │ HTTPS Streamable HTTP
        ▼
sssp.evemisslab.com/mcp
        │ stateless MCP tool request
        ▼
SSSPStore Durable Object
        │ strongly consistent transaction
        ▼
SQLite canonical documents / audit / immutable snapshots
```

MCP transport 本身不保存 scholarly state。每次 tool call 都可獨立重建 server；canonical 文件則存於獨立的 Durable Object SQLite，因此不會因連線結束、Worker eviction 或重新部署而消失。

## 健康與 discovery

```text
GET https://sssp.evemisslab.com/healthz
GET https://sssp.evemisslab.com/.well-known/sssp.json
```

初始化測試（PowerShell）：

```powershell
$body = @{
  jsonrpc = "2.0"
  id = 1
  method = "initialize"
  params = @{
    protocolVersion = "2025-11-25"
    capabilities = @{}
    clientInfo = @{ name = "manual-check"; version = "1.0" }
  }
} | ConvertTo-Json -Depth 8

Invoke-WebRequest `
  -Uri "https://sssp.evemisslab.com/mcp" `
  -Method Post `
  -ContentType "application/json" `
  -Headers @{ Accept = "application/json, text/event-stream" } `
  -Body $body
```

回應可為 JSON 或 `text/event-stream`；兩者都是 Streamable HTTP 的合法 response mode。

## 驗證與部署

```bash
npm ci
npx wrangler types --check
npm run check
npx wrangler deploy --dry-run
npm run site:deploy
```

`wrangler.jsonc` 是 binding、SQLite Durable Object migration、rate limit、assets、observability 與 custom domain 的 source of truth。舊 migration 不可修改；新增 Durable Object schema 變更時應加入新的 migration tag。

## 本機 reference servers

本機 stdio server：

```bash
python3 src/mcp_server.py
```

Python Streamable HTTP reference server 仍保留給隔離測試，預設要求 capability URL token：

```bash
SSSP_ENDPOINT_TOKEN='YOUR_LONG_URL_SAFE_SECRET' \
python3 src/remote_server.py
```

這個 Python path 使用檔案系統 storage，與正式 `sssp.evemisslab.com/mcp` 的 Durable Object backend 不同。`SSSP_ALLOW_INSECURE_REMOTE=1` 只適合 disposable local testing。
