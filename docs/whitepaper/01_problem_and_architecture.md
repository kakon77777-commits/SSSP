# Structured Scholarly Source Protocol（SSSP）v0.1 技術白皮書

## AI 原生學術來源、交易式寫入、驗證與 MCP 介面

**狀態：** Experimental / MVP Specification  
**版本：** v0.1  
**日期：** 2026-08-12  
**核心原則：** Source First / Rendered View Is Not Source

---

## 摘要

大型語言模型已能高速產生長篇論文、數學公式、技術白皮書與跨文件研究系列，但目前常見的聊天式寫作流程通常把「渲染畫面」同時當成閱讀介面與正式原稿。當公式經過 Markdown、KaTeX／MathJax、HTML DOM、clipboard、Unicode escape、再序列化與本地修復器等多個轉換層時，畫面上正確的內容可能在複製後發生字元級、結構級甚至靜默語義級損毀。

本白皮書以實際累積的公式損毀案例為需求基礎，包括：DOM 複製造成 LaTeX delimiters 損毀、渲染後公式被重複或攤平、`$` 同時作為貨幣與數學定界符、雙套數學方言造成解析歧義、單一 delimiter 缺失導致級聯失效、修復 regex 誤傷合法 `\\`、控制字元吞噬 `\\a \\b \\f \\n \\r \\t \\v` 類 LaTeX 指令，以及「renderer 0 error 但數學語意已改變」的 silent corruption。

本文提出 **Structured Scholarly Source Protocol（SSSP）**：一套把正式學術內容從聊天渲染介面中抽離，以 typed node、canonical source、optimistic concurrency、transactional mutation、provenance、Semantic Ledger、Claim Ledger 與多層 validator 為核心的 AI-native scholarly authoring protocol。

SSSP 將系統拆成三層：

1. **Canonical Format Layer**：定義正式 source 的 typed document model；
2. **Mutation Protocol Layer**：定義 AI 如何最小化、可驗證地修改文件；
3. **Adapter Layer**：第一個實作使用 Model Context Protocol（MCP），但 SSSP 不與 MCP 綁死。

MVP 不試圖建立完整數學 AST。數學內容先以 raw LaTeX field 保存，由 server serializer 負責 JSON escaping；Markdown／HTML／LaTeX／PDF 均視為衍生 view，不得反向成為 canonical source。MVP 提供：`create_document`、`append_node`、`replace_node`、`read_node`、`validate_document`、`export_document`、`commit_version` 七個 primitive，並以 SHA-256 node checksum、document revision、atomic write 與 validator 阻止大部分已知格式損毀進入 corpus。

---

# 1. 問題定義

## 1.1 當前工作流的根本錯誤

常見流程是：

```text
AI 對話生成
→ UI 渲染 Markdown/LaTeX
→ 使用者從畫面複製
→ Clipboard/DOM 轉換
→ 儲存成 Markdown
→ 本地 renderer 報錯
→ regex / AI 修復
→ 再渲染
→ 回歸修復
```

這是一條 **render-first, repair-later** 流程。

SSSP 改成：

```text
Human/AI discussion
→ structured mutation request
→ canonical source
→ validation
→ atomic commit
→ derived rendering/export
```

即：

```text
Canonical Source → Validation → Rendered Views
```

而不是：

```text
Rendered View → Copy → Guess Original Source
```

---

## 1.2 Rendered-Source Divergence（RSD）

定義 **Rendered-Source Divergence**：

> 當使用者看到的渲染表示，與後續機器處理所需的 canonical source 不再具有可靠可逆映射，且經 DOM、clipboard、escape、parser 或格式轉換後，無法保證 source identity 時，即發生 RSD。

典型案例：

- `\\[ ... \\]` 複製後收尾只剩裸 `]`；
- `_` 變 `\\_`；
- `}_{` 變成其他 markdown 字元組合；
- inline math wrapper 消失；
- 同一公式被複製成「攤平文字 + LaTeX + 攤平文字」三份；
- LaTeX 被替換成 Unicode rendered glyphs；
- 下標、框線只殘留 zero-width／PUA 標記。

SSSP 的核心設計不是「更強地修 RSD」，而是讓 canonical source 永遠不經過 RSD 路徑。

---

## 1.3 Silent Semantic Divergence（SSD）

比 RSD 更危險的是 **Silent Semantic Divergence**：

> 內容已發生數學或邏輯語義改變，但 parser／renderer 仍接受輸入，因此傳統 syntax validation 無法發現。

例如某些上游流程錯誤套用 C/Python 風格 `unicode_escape`，可能把 `\\neg` 的 `\\n` 解碼成真正換行，後續剩下 `eg`；KaTeX 可能仍把 `eg` 當變數字串渲染，因此「0 render errors」不等於語義未受損。

因此：

```text
Renderer Pass ≠ Semantic Integrity
```

SSSP validator 必須至少分成 Syntax、Render、Semantic-Risk 三層。

---

# 2. 設計目標

SSSP v0.1 的主要目標：

1. **Source First**：渲染畫面永遠不是 canonical source。
2. **Error Locality**：單一公式或節點錯誤不得吞掉後續整篇文件。
3. **Minimal Mutation**：AI 修改節點，不重新生成整篇文件。
4. **Typed Content**：paragraph、math、claim、definition 等具有不同型別。
5. **Single Canonical Math Representation**：canonical math node 不使用 Markdown `$...$` delimiter。
6. **Atomic Commit**：驗證失敗不得產生半完成寫入。
7. **Optimistic Concurrency**：多 AI／多對話不能靜默覆寫彼此修改。
8. **Provenance**：核心定義、claim 與節點需要來源與版本記錄。
9. **Derived Views Only**：Markdown、HTML、PDF 等由 source 編譯，不反向同步。
10. **Protocol Independence**：SSSP core 不依賴 MCP；MCP 只是 adapter。

非目標：

- v0.1 不建立完整數學語義 AST；
- v0.1 不自動證明公式數學正確；
- v0.1 不取代 Git；
- v0.1 不直接解決引用真實性與學術審查；
- v0.1 不嘗試把所有 legacy Markdown 自動無損轉換。

---

# 3. 系統分層

```text
┌─────────────────────────────────────┐
│ Human / AI Discussion Layer         │
│  brainstorming / dialogue / review  │
└────────────────┬────────────────────┘
                 │ commit intent
┌────────────────▼────────────────────┐
│ SSSP Mutation Protocol              │
│ typed operations / revision / tx    │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│ Canonical Scholarly Source          │
│ document.json + ledgers + versions  │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│ Validator Pipeline                  │
│ L1 syntax / L2 render / L3 risk     │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│ Export Compiler                     │
│ Markdown / LaTeX / HTML / PDF       │
└─────────────────────────────────────┘
```

Adapter 可為：

```text
MCP / CLI / REST / local API / future agent protocol
```

---
