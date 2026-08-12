# SSSP Authoring Contract v0.1

將以下規則加入支援 SSSP 的 AI 系統提示詞／project instructions：

1. Chat content is discussion/view, not canonical scholarly source.
2. Never ask the user to copy rendered math back into canonical source.
3. Commit formal content through SSSP mutation tools when available.
4. Prefer minimal node mutation over full-document regeneration.
5. Read and preserve canonical terminology from the Semantic Ledger.
6. Preserve epistemic status from the Claim Ledger.
7. Never replace raw LaTeX source with rendered Unicode approximations.
8. Never apply `unicode_escape` or equivalent generic escape-decoding round trips to scholarly source.
9. Renderer success is not proof of semantic integrity.
10. A mutation is complete only after SSSP validation succeeds.
11. Do not silently overwrite a newer document revision or node checksum.
12. Derived Markdown/HTML/PDF is a view; never treat it as canonical source unless explicitly importing legacy material.
