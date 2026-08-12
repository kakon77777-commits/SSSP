# 20. Roadmap

## v0.1 — Source-first MCP MVP

- typed JSON source；
- seven tools；
- SHA-256；
- revision；
- atomic write；
- L1 validator；
- MathJax L2 validator；
- Markdown exporter；
- snapshot versioning。

## v0.2 — Ledgers & Transactions

- dedicated Semantic Ledger tools；
- Claim Ledger tools；
- multi-node transactions；
- richer provenance；
- resource exposure via MCP。

## v0.3 — Semantic Diff

- AI-assisted semantic comparison；
- theorem/claim status preservation；
- cross-node symbol consistency；
- bibliography validation hooks。

## v0.5 — Structured Mathematics

- partial math AST for high-risk primitives；
- renderer-independent operators；
- AST → LaTeX compiler。

## v1.0 — AI-Native Scholarly Authoring Protocol

- multi-agent concurrency；
- signed commits；
- reproducible publication bundles；
- provenance graph；
- schema migration；
- multiple adapters。

---

# 21. 核心命題

SSSP 的最核心主張不是：

```text
Markdown 很差。
```

而是：

```text
Human-readable rendering and machine-canonical scholarly source
should not be the same mutable object.
```

Markdown 仍然非常適合閱讀、Git diff 與發布。

真正的改變是：

```text
Markdown becomes a compiled view.
```

而不是唯一 source of truth。

---

# 22. 結論

AI 時代學術寫作的瓶頸正在從「能不能快速生成文字」轉向「快速生成後，內容能否以可靠、可追蹤、可重用的形式沉澱」。

如果正式內容仍經過：

```text
render → copy → escape → repair
```

生成速度越快，只會把更多後處理債務推給本地 Agent。

SSSP 的方向是反過來：

```text
Discussion is ephemeral.
Canonical source is structured.
Mutations are transactional.
Validation happens before commit.
Rendering is derived.
```

最終目標不是讓 AI 更會「修壞掉的論文」，而是讓新論文從生成的第一刻起，就不進入那條會損毀的資料路徑。

---

## 參考規格與需求來源

1. Model Context Protocol Specification, revision 2025-11-25：Base Protocol、Lifecycle、stdio/Streamable HTTP、Tools。
2. JSON-RPC 2.0 Specification。
3. CommonMark 0.31.2 Specification，特別是 backslash escapes、characters、inline/block parsing。
4. 使用者提供：《數學公式常見損毀模式 — 為新格式設計準備的問題目錄》，作為本白皮書的主要 failure corpus 與工程需求來源。
