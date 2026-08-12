# 14. MCP 安全模型

MCP Tools 是 model-controlled action，因此 SSSP server 必須：

- 所有 document ID 限制在 configured root；
- 防 path traversal；
- 驗證所有 input；
- mutation 留 audit record；
- 遠端 transport 未來必須加 auth；
- MVP 先 stdio，避免開放 network surface；
- 不讓 tool 直接執行任意 shell；
- exporter 只能寫在 document workspace。

對高風險 mutation，可由 host UI 增加 human confirmation。

---

# 15. 目錄結構

```text
data/
  paper-001/
    document.json
    versions/
      000001_<hash>.json
    exports/
      paper-001_r1.md
    audit.jsonl
```

Canonical truth：

```text
document.json
```

不是 export。

---

# 16. Export 規則 v0.1

`heading`：

```markdown
## heading content
```

`paragraph`：原樣文本。

`math_block`：

```markdown
$$
<latex>
$$
```

`definition`：使用標題 + 內容。

`claim`：使用 claim type/status metadata 產生可讀 Markdown。

`code`：fenced code。

因此 `$` delimiter 只在 compiler/exporter 中由單一實作生成，AI 不需要自己管理 delimiter 配對。

---

# 17. Legacy Import

舊 Markdown 是高風險來源。

SSSP v0.1 不宣稱自動完整修復 legacy corpus。

建議流程：

```text
legacy .md
→ detection
→ parse candidates
→ quarantine suspicious nodes
→ AI/manual repair
→ SSSP canonical import
→ validation
```

一旦轉入 canonical SSSP 後，不再回到 repair-centered workflow。

---

# 18. 實驗設計

第一個實驗不測「AI 寫得比較好」，只測格式可靠性。

## Experiment A — Roundtrip Integrity

對 1000 個包含：

- `\\boxed`
- `\\forall`
- `\\neg`
- `\\nabla`
- `\\text`
- `\\rightarrow`
- `\\varnothing`
- `\\begin{aligned}`
- 貨幣 `$`

的節點進行：

```text
create → serialize → load → export → render
```

要求 canonical hash 完全一致。

## Experiment B — Concurrent Mutation

兩個 client 同時持有 revision N。

A commit 成功後 B 用 N 寫入，必須得到 revision conflict。

## Experiment C — Known Damage Regression

把既有 A–J 損毀案例轉成 regression fixtures。

目標：

```text
known silent corruption cannot enter canonical document unnoticed
```

## Experiment D — Minimal Mutation

比較：

```text
full paper regeneration
vs
node replacement
```

的非目標字元變動數量。

---

# 19. 成功指標

SSSP MVP 第一階段不追求 fancy UI。

核心 KPI：

```text
Canonical corruption rate
Validation recall on known damage cases
False positive rate
Non-target mutation size
Revision conflict correctness
Roundtrip source hash stability
Export reproducibility
```

第一階段最重要的是：

```text
新產生的正式論文不再需要後端 AI 大規模修公式。
```

---
