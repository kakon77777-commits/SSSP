# 4. Canonical Document Model

## 4.1 Document

第一版 canonical document：

```json
{
  "protocol": "SSSP",
  "version": "0.1",
  "document_id": "paper-001",
  "title": "Example Paper",
  "revision": 3,
  "created_at": "...",
  "updated_at": "...",
  "nodes": [],
  "semantic_ledger": {},
  "claim_ledger": {}
}
```

所有寫入由 server 產生合法 JSON。AI 不應要求使用者手工複製整份 JSON。

---

## 4.2 Typed Nodes

MVP 支援：

```text
heading
paragraph
math_block
definition
claim
code
reference
note
```

一般 node：

```json
{
  "id": "node-0004",
  "type": "paragraph",
  "content": "...",
  "checksum": "sha256:...",
  "created_at": "...",
  "updated_at": "...",
  "provenance": {
    "actor": "assistant",
    "reason": "initial draft"
  }
}
```

數學 node：

```json
{
  "id": "eq-0001",
  "type": "math_block",
  "latex": "\\forall x\\in X,\\;P(x)",
  "checksum": "sha256:..."
}
```

注意 canonical source 中 **沒有 `$$` delimiter**。Delimiter 只由 exporter 生成。

---

# 5. Semantic Ledger

Semantic Ledger 用於保存跨篇或跨版本需要保持一致的語義狀態。

```json
{
  "terms": {
    "CPRR": {
      "canonical": "Content-Phase Relay Resolution",
      "status": "active"
    }
  },
  "deprecated_terms": {
    "RelayPhase Resolution": {
      "replacement": "CPRR"
    }
  },
  "symbols": {
    "\\mathfrak{B}": "Computational Substrate"
  }
}
```

目的：

- 防止同概念跨篇改名；
- 防止 deprecated term 復活；
- 防止同一符號跨章多義；
- 讓 AI 寫作前先取得 canonical definitions。

---

# 6. Claim Ledger

Claim Ledger 與正文分開，追蹤論述 epistemic status：

```json
{
  "claim-0042": {
    "type": "conjecture",
    "status": "provisional",
    "text": "...",
    "support": ["paper-03#node-42"],
    "provenance": "discussion-2026-08-12"
  }
}
```

MVP claim types：

```text
definition
observation
inference
conjecture
theorem
engineering_hypothesis
empirical_result
```

這能避免 AI 在多輪改寫中把：

```text
猜想 → 工作假說 → 已證明定理
```

無意間「升級」。

---

# 7. Mutation Protocol

## 7.1 原則

正式文件不得以「整篇重新輸出」作為一般修改方式。

核心 primitive：

```text
create_document
append_node
replace_node
read_node
validate_document
export_document
commit_version
```

之後可擴充：

```text
insert_node
move_node
delete_node
update_semantic_ledger
update_claim
begin_transaction
commit_transaction
rollback_transaction
```

---

## 7.2 Optimistic Concurrency

每份文件包含：

```text
revision = N
```

mutation request 可指定：

```text
expected_revision = N
```

若 server 目前已為：

```text
revision = N + 1
```

則拒絕：

```text
REVISION_CONFLICT
```

這是避免十幾個 AI 對話／Agent 同時修改同一文件時靜默覆寫的第一道保護。

---

## 7.3 Node checksum

每個 node 依 canonical JSON content 計算 SHA-256：

```text
checksum(node) = SHA256(canonical-json(node-without-checksum))
```

`replace_node` 可額外帶：

```text
expected_checksum
```

若 node 已改變，server 拒絕 stale write。

---

