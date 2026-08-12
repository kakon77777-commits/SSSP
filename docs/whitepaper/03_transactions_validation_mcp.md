# 8. Transaction Semantics

MVP 每一個 mutation 本身以 atomic file replacement 實現 mini-transaction：

```text
read current
→ apply change in memory
→ validate candidate
→ write temp file
→ fsync/close
→ atomic replace
```

完整多節點 transaction 留到 v0.2：

```text
BEGIN
replace definition
replace equation
update claim ledger
validate
COMMIT
```

任何一步失敗：

```text
ROLLBACK
```

---

# 9. Validator Pipeline

## 9.1 L1 — Structural / Character Validation

必做：

- UTF-8；
- document schema；
- node ID uniqueness；
- required fields；
- control characters；
- PUA characters；
- zero-width markers；
- LaTeX braces rough balance；
- environment balance；
- forbidden escape-corruption signatures；
- duplicate node IDs；
- checksum integrity。

對 `math_block`，canonical format 不再使用 `$` delimiter，因此可整類移除：

- 貨幣 `$` vs math `$` ambiguity；
- inline delimiter 邊界 tokenizer 規則；
- missing `$` 吃掉後續段落的級聯模式。

---

## 9.2 L2 — Renderer Validation

MVP 以 MathJax TeX parser 實際解析所有 math nodes。

目的不是證明數學正確，而是抓：

- unknown command；
- malformed group；
- environment error；
- parser-level TeX defect。

Exporter 再跑 Markdown target validation 可作 v0.2。

---

## 9.3 L3 — Semantic-Risk Validation

v0.1 不使用大型模型做 semantic proof，而先做 risk flag：

- math node 修改比例極高；
- `\\neg` 類 operator 突然消失；
- relation operator 數量大幅改變；
- 數學 node 變成純字母文本；
- source 出現 PUA／zero-width；
- legacy import 中公式數量異常下降。

結果：

```text
PASS
WARNING_SEMANTIC_REVIEW
FAIL
```

未來可接 AI semantic diff：

```text
old mathematical meaning
vs
new mathematical meaning
```

但 AI semantic check 不能取代 deterministic validation。

---

# 10. Source vs Derived Views

SSSP 規定：

```text
Canonical source → exporter → Markdown / LaTeX / HTML / PDF
```

每個 export metadata 可包含：

```json
{
  "source_revision": 12,
  "source_hash": "...",
  "compiler": "sssp-md-exporter/0.1"
}
```

衍生 `.md` 若人工修改，不自動 merge 回 canonical source。

這是一條單向資料流。

---

# 11. Prompt Contract

在任何支援 SSSP 的 AI session 中，建議加入：

```text
SSSP AUTHORING CONTRACT

1. Chat output is discussion/view, not canonical scholarly source.
2. Never ask the user to copy rendered math back into source.
3. Commit formal content through SSSP mutation tools.
4. Prefer minimal node mutation over full-document regeneration.
5. Preserve canonical terminology from Semantic Ledger.
6. Preserve epistemic status from Claim Ledger.
7. Do not convert raw LaTeX into Unicode-rendered approximation.
8. Do not run unicode_escape or equivalent escape-decoding round trips.
9. A renderer pass is not proof of semantic integrity.
10. A mutation is complete only after validation succeeds.
```

對話可自由；commit 要嚴格。

---

# 12. MCP Adapter

SSSP core 與 MCP 分離。

```text
SSSP Core
 ├─ storage
 ├─ mutation
 ├─ validation
 ├─ versioning
 └─ export

Adapters
 ├─ MCP
 ├─ CLI
 ├─ REST (future)
 └─ other agent protocols (future)
```

MCP 適合 MVP，因為它提供標準化 client/server lifecycle、resources 與 model-controlled tools；stdio transport 使用逐行 UTF-8 JSON-RPC，可直接作本地 Agent integration。

SSSP-MCP v0.1 只宣告 `tools` capability。

---

# 13. MCP Tool Surface v0.1

## `sssp.create_document`

建立空白 canonical document。

輸入：

```json
{
  "document_id": "paper-001",
  "title": "..."
}
```

## `sssp.append_node`

新增 typed node。

## `sssp.replace_node`

以 expected revision/checksum 做安全替換。

## `sssp.read_node`

讀 canonical node。

## `sssp.validate_document`

執行 L1/L2/L3-risk validation。

## `sssp.export_document`

產生 derived Markdown。

## `sssp.commit_version`

建立 immutable version snapshot。

---

