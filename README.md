# SSSP — Structured Scholarly Source Protocol

SSSP 是一個 **AI-native scholarly authoring protocol** 的研究型 MVP。它把聊天／渲染畫面與正式學術來源分離，讓 AI 透過 typed nodes、revision、checksum、validation 與 transaction-like mutation 直接寫入 canonical source，而不是讓人從渲染後 DOM 複製 Markdown／LaTeX 再進行事後修復。

核心原則：

> **Chat is discussion. File is source. Render is a view. Mutation is transactional. Validation happens before commit.**

## 公開研究網站

SSSP 的雙語公開說明站位於：

```text
https://sssp.evemisslab.com/
```

網站同時提供公開、無驗證的 Streamable HTTP MCP：

```text
https://sssp.evemisslab.com/mcp
```

機器可讀狀態位於 `/.well-known/sssp.json`。這個 MCP 是共享研究實例；文件以 Durable Object SQLite 持久保存，但不具私人租戶隔離。請勿提交密碼、個資、私人草稿、憑證或任何機密內容。

本機建置與檢查：

```bash
npm run site:check
```

Cloudflare 部署設定以 `wrangler.jsonc` 為準。

## 為什麼做 SSSP

既有論文 corpus 已實際觀察到多種 rendered-source divergence：

- Canvas／網頁渲染後 DOM 被複製，而不是原始 LaTeX；
- `$` 同時作為貨幣字元與 math delimiter；
- 漏 delimiter 造成後續正文級聯失效；
- `\\` 等合法 TeX 被 repair regex 誤傷；
- `\\b`、`\\t`、`\\n` 等序列經錯誤 escape decoding 轉成控制字元；
- renderer 0 error，但公式語義已靜默損毀。

因此 SSSP 採 source-first：

```text
Discussion → Canonical Source → Validation → Rendered Views
```

而不是：

```text
Rendered View → Copy → Guess Source → Repair
```

完整案例目錄：[`docs/research/數學公式常見損毀模式_問題目錄.md`](docs/research/數學公式常見損毀模式_問題目錄.md)。

## v0.1 架構

SSSP 刻意拆成三層：

1. **Canonical Format** — typed scholarly nodes 與 ledgers。
2. **Mutation Protocol** — create / append / replace / validate / export / snapshot。
3. **MCP Adapter** — 目前第一個可執行介面；未來可另接 CLI、REST 或其他 agent protocol。

正式數學 source 存在 node field 中，不把 Markdown delimiter 當 canonical data：

```json
{
  "id": "eq-0001",
  "type": "math_block",
  "latex": "\\forall x\\in X,\\;P(x)"
}
```

Markdown 是 exporter 產生的 derived view。

## MCP tools

目前提供 7 個 tools：

```text
sssp.create_document
sssp.append_node
sssp.replace_node
sssp.read_node
sssp.validate_document
sssp.export_document
sssp.commit_version
```

server v0.3 同時提供本機 stdio 與公開 Streamable HTTP。公開端點使用 Cloudflare 的 stateless MCP handler（含 2025-era client compatibility），canonical 文件、audit 與 version snapshots 則獨立存放於 Durable Object SQLite，不會隨 MCP 連線結束而消失。

## ChatGPT / Claude 連線

兩邊使用同一組值：

```text
名稱 / Name：SSSP
說明 / Description：Canonical scholarly source tools
伺服器 URL：https://sssp.evemisslab.com/mcp
驗證 / Authentication：無驗證 / None
OAuth Client ID：留白
OAuth Client Secret：留白
```

ChatGPT 請勾選自訂 MCP 風險確認後建立；Claude 的 Advanced settings 不需填寫。詳細步驟與風險邊界見 [`docs/REMOTE_MCP_DEPLOY.md`](docs/REMOTE_MCP_DEPLOY.md)。

## 快速開始

需求：

- Python 3.10+
- Node.js 18+（MathJax L2 renderer validation）

安裝 renderer dependency：

```bash
npm install
```

啟動 MCP stdio server：

```bash
python3 src/mcp_server.py
```

server 僅把 MCP JSON-RPC 寫到 stdout；log 應走 stderr。

預設 canonical data root：

```text
./data
```

可覆寫：

```bash
export SSSP_ROOT=/absolute/path/to/sssp-data
python3 src/mcp_server.py
```

MCP host registration 範例見 [`docs/MCP_STDIO_EXAMPLE.md`](docs/MCP_STDIO_EXAMPLE.md)。

## 測試

```bash
npm run check
python3 tests/test_core.py
python3 tests/test_damage_regressions.py
python3 tests/test_mcp_smoke.py
python3 tests/test_remote_http.py
```

`npm run check` 會執行 TypeScript 檢查、Workers runtime 測試與雙語網站驗證。GitHub Actions 另執行四組 Python reference tests、Cloudflare dry run 與 Docker build。

## Validation layers

### L1 — Structural / character validation

目前包含：

- forbidden control bytes；
- PUA；
- zero-width characters；
- node checksum；
- duplicate IDs；
- math brace / environment 基礎檢查；
- canonical math 中的 Markdown `$` delimiter warning；
- `newline + eg/eq/abla` 類 silent escape corruption risk。

### L2 — TeX renderer validation

`scripts/mathjax_validate.js` 使用 MathJax TeX parser 解析 `math_block`。

### L3 — Semantic validation（規劃中）

v0.1 尚未宣稱能證明數學語義正確。未來目標包括 semantic diff、claim consistency 與 symbol/definition drift detection。

## Canonical data model

每篇文件包含：

- document metadata；
- ordered typed nodes；
- revision；
- SHA-256 node checksums；
- Semantic Ledger；
- Claim Ledger；
- audit log；
- immutable version snapshots；
- derived exports。

Schema：[`docs/sssp_document.schema.json`](docs/sssp_document.schema.json)。

## 文件

- [SSSP v0.1 技術白皮書](docs/SSSP_技術白皮書_v0.1.md)
- [AI Authoring Prompt](docs/SSSP_AUTHORING_PROMPT.md)
- [MCP stdio 接法](docs/MCP_STDIO_EXAMPLE.md)
- [Remote MCP v0.3 連線與部署](docs/REMOTE_MCP_DEPLOY.md)
- [數學公式常見損毀模式問題目錄](docs/research/數學公式常見損毀模式_問題目錄.md)
- [測試結果](TEST_RESULTS.md)

## 專案狀態

**v0.3 research MVP**。目前已提供 stdio、公開 Streamable HTTP、Zod tool schema、限流與 Durable Object SQLite 持久化，但尚未提供 production-grade：

- OAuth/OIDC authentication / authorization；
- multi-writer lock service；
- 完整 JSON Schema runtime enforcement；
- L3 semantic verifier；
- structured math AST；
- package / installer。

下一階段應優先使用真實論文做端到端 authoring trial，量測：

1. 新公式損毀率；
2. 本地 AI 後處理時間；
3. source/render divergence；
4. 多 agent revision conflict；
5. semantic drift false positive / false negative。

## Remote MCP v0.3

正式公開研究端點：

```text
https://sssp.evemisslab.com/mcp
```

它具備 Host／Origin 驗證、2 MiB request guard、每 Cloudflare location 每分鐘 120 次的匿名類別限流，以及文件、節點、snapshot 與總儲存量上限。`GET /healthz` 與 `GET /.well-known/sssp.json` 可用來檢查公開狀態。

本機 Python reference remote server 仍保留，可用 capability URL token 做隔離測試：

```bash
SSSP_ENDPOINT_TOKEN='YOUR_LONG_URL_SAFE_SECRET' \
python3 src/remote_server.py
```

部署與 ChatGPT 填表詳見 [`docs/REMOTE_MCP_DEPLOY.md`](docs/REMOTE_MCP_DEPLOY.md)。repo 亦附 `Dockerfile` 與 `render.yaml` 供一次性遠端測試。

> 注意：目前 `sssp.evemisslab.com/mcp` 是刻意公開的無驗證共享 workspace。它不是私人儲存服務；任何知道 `document_id` 的人都可能讀取或修改節點。正式多人／私人部署應加入 OAuth/OIDC 與 tenant ownership boundary。
