#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SITE = Path(__file__).resolve().parent
DIST = ROOT / "dist-site"
ORIGIN = "https://sssp.evemisslab.com"
REPOSITORY = "https://github.com/kakon77777-commits/SSSP"


PAGES = {
    "en": {
        "lang": "en",
        "path": "/",
        "other_path": "/zh/",
        "other_label": "繁體中文",
        "skip": "Skip to content",
        "theme": "Switch colour scheme",
        "nav_label": "Primary navigation",
        "nav": [
            ("#problem", "Problem"),
            ("#protocol", "Protocol"),
            ("#tools", "Tools"),
            ("#status", "Status"),
        ],
        "eyebrow": "EVEMISSLAB / RESEARCH MVP · v0.2",
        "title": "The source survives the conversation.",
        "standfirst": (
            "SSSP is an AI-native protocol for scholarly writing. It gives agents typed nodes, "
            "revisions, checksums and validation—so canonical source is edited directly, while "
            "Markdown and rendered pages remain derived views."
        ),
        "primary_cta": "Explore the protocol",
        "source_cta": "View source",
        "specimen_label": "Canonical specimen",
        "specimen_title": "A formula that remains a formula",
        "specimen_state": "validated",
        "specimen_revision": "revision 3",
        "principle_label": "The invariant",
        "principle": ["Discussion", "Canonical source", "Validation", "Rendered views"],
        "stats": [
            ("08", "typed node kinds"),
            ("07", "MCP tools"),
            ("02", "implemented validation layers"),
            ("01", "canonical source"),
        ],
        "problem_kicker": "01 / THE FAILURE MODE",
        "problem_title": "Render success is not source integrity.",
        "problem_intro": (
            "A page can look correct while the expression underneath it has already changed. "
            "SSSP moves validation in front of the commit instead of asking a repair pass to guess the source later."
        ),
        "failures": [
            ("Copied view", "Canvas or DOM output is copied instead of the original LaTeX source."),
            ("Silent escape", "Sequences such as \\b, \\t or \\n are decoded into control characters."),
            ("Cascade repair", "A broad repair regex fixes one delimiter and damages valid TeX elsewhere."),
        ],
        "contrast_bad": "Rendered view → copy → guess source → repair",
        "contrast_good": "Discussion → canonical source → validate → render",
        "protocol_kicker": "02 / PROTOCOL ANATOMY",
        "protocol_title": "One source. Deliberately different views.",
        "protocol_intro": (
            "The canonical document is a typed, revisioned object. Exports are compiled from it; "
            "the audit trail records how it changed. Use the controls to inspect the same node through each lens."
        ),
        "lens_label": "Choose a view",
        "lenses": [
            ("canonical", "Canonical", "Canonical source"),
            ("export", "Export", "Derived Markdown export"),
            ("audit", "Audit", "Mutation audit record"),
        ],
        "lens_note": {
            "canonical": "Typed data is authoritative. Delimiters are not part of the math payload.",
            "export": "Markdown is generated from canonical data and can be regenerated at any time.",
            "audit": "Revision, actor, reason and checksum travel with the mutation record.",
        },
        "pillars": [
            ("Canonical format", "Typed scholarly nodes plus semantic and claim ledgers."),
            ("Mutation protocol", "Create, append and replace operations guarded by revisions and checksums."),
            ("MCP adapter", "A seven-tool interface over stdio or basic Streamable HTTP."),
        ],
        "tools_kicker": "03 / EXECUTABLE SURFACE",
        "tools_title": "Seven tools, one authority boundary.",
        "tools_intro": (
            "Agents mutate the canonical document through explicit operations. Read, validation, export and snapshot "
            "remain named steps rather than invisible side effects."
        ),
        "tool_groups": [
            ("Mutate", [
                ("sssp.create_document", "Create a canonical document."),
                ("sssp.append_node", "Append one typed node, then validate before atomic commit."),
                ("sssp.replace_node", "Replace one node with revision and checksum conflict protection."),
            ]),
            ("Inspect", [
                ("sssp.read_node", "Read canonical data without going through a rendered export."),
                ("sssp.validate_document", "Run structural, character and MathJax validation."),
            ]),
            ("Derive", [
                ("sssp.export_document", "Compile a derived Markdown view."),
                ("sssp.commit_version", "Create an immutable validated snapshot."),
            ]),
        ],
        "validation_title": "Validation is layered—and its boundary is named.",
        "layers": [
            ("L1", "Structural / character", "implemented", "Control bytes, PUA, zero-width markers, checksums, duplicate IDs and basic TeX structure."),
            ("L2", "Renderer", "implemented", "MathJax parses each canonical math block before a validated snapshot is created."),
            ("L3", "Semantic", "planned", "Claim consistency, symbol drift and semantic diff remain research work—not present-tense guarantees."),
        ],
        "status_kicker": "04 / STATUS & BOUNDARIES",
        "status_title": "A research MVP that says where it stops.",
        "status_intro": (
            "SSSP v0.2 is executable and tested. It is not yet a production multi-writer scholarly service. "
            "The public site explains the protocol; it does not expose an unauthenticated write endpoint."
        ),
        "available_title": "Available now",
        "available": [
            "Typed canonical documents and ledgers",
            "Revision and checksum conflict protection",
            "L1 structural and L2 MathJax validation",
            "Immutable snapshots and Markdown export",
            "MCP over stdio and basic Streamable HTTP",
        ],
        "not_yet_title": "Not claimed yet",
        "not_yet": [
            "OAuth/OIDC authorization",
            "A multi-writer lock service",
            "Full runtime JSON Schema enforcement",
            "An L3 theorem or meaning checker",
            "Production persistent scholarly storage",
        ],
        "start_title": "Run the reference implementation",
        "start_intro": "Clone the repository, install the pinned MathJax dependency, then start the local MCP server.",
        "copy": "Copy",
        "copied": "Copied",
        "docs": "Read the deployment notes",
        "footer_line": "Chat is discussion. File is source. Render is a view.",
        "footer_meta": "SSSP v0.2 · Research MVP · 2026",
    },
    "zh": {
        "lang": "zh-Hant",
        "path": "/zh/",
        "other_path": "/",
        "other_label": "English",
        "skip": "跳至內容",
        "theme": "切換配色",
        "nav_label": "主要導覽",
        "nav": [
            ("#problem", "問題"),
            ("#protocol", "協定"),
            ("#tools", "工具"),
            ("#status", "狀態"),
        ],
        "eyebrow": "EVEMISSLAB / 研究型 MVP · v0.2",
        "title": "對話會結束，來源仍然活著。",
        "standfirst": (
            "SSSP 是一套 AI 原生的學術寫作協定。它讓代理直接操作具型別節點、版本、校驗和與驗證，"
            "使 canonical source 保持權威；Markdown 與渲染頁面則只是可重新產生的衍生視圖。"
        ),
        "primary_cta": "探索協定",
        "source_cta": "查看原始碼",
        "specimen_label": "Canonical 範本",
        "specimen_title": "一條始終是公式的公式",
        "specimen_state": "已驗證",
        "specimen_revision": "版本 3",
        "principle_label": "不變量",
        "principle": ["討論", "Canonical source", "驗證", "渲染視圖"],
        "stats": [
            ("08", "種具型別節點"),
            ("07", "個 MCP 工具"),
            ("02", "層已實作驗證"),
            ("01", "份 canonical source"),
        ],
        "problem_kicker": "01 / 失效模式",
        "problem_title": "渲染成功，不等於來源完整。",
        "problem_intro": (
            "頁面可以看起來完全正常，底下的式子卻早已變形。SSSP 把驗證放到 commit 之前，"
            "不再讓事後修復流程反過來猜原始來源。"
        ),
        "failures": [
            ("複製視圖", "複製 Canvas 或 DOM 的輸出，而不是原始 LaTeX source。"),
            ("靜默 escape", "\\b、\\t 或 \\n 等序列被解碼成控制字元。"),
            ("級聯修復", "寬泛的 repair regex 修好一個 delimiter，卻破壞其他合法 TeX。"),
        ],
        "contrast_bad": "渲染視圖 → 複製 → 猜來源 → 修復",
        "contrast_good": "討論 → canonical source → 驗證 → 渲染",
        "protocol_kicker": "02 / 協定解剖",
        "protocol_title": "一份來源，刻意不同的視圖。",
        "protocol_intro": (
            "Canonical document 是具型別、具版本的物件；export 由它編譯而來，audit trail 記錄它如何改變。"
            "用下方控制項，查看同一個節點在三種視角下的樣子。"
        ),
        "lens_label": "選擇視圖",
        "lenses": [
            ("canonical", "Canonical", "Canonical source"),
            ("export", "Export", "衍生 Markdown export"),
            ("audit", "Audit", "Mutation audit record"),
        ],
        "lens_note": {
            "canonical": "具型別資料才是權威；delimiter 並不屬於 math payload。",
            "export": "Markdown 從 canonical data 產生，任何時候都能重新編譯。",
            "audit": "版本、操作者、原因與校驗和都跟著 mutation record 走。",
        },
        "pillars": [
            ("Canonical format", "具型別的學術節點，加上 semantic 與 claim ledgers。"),
            ("Mutation protocol", "Create、append、replace 都受 revision 與 checksum 保護。"),
            ("MCP adapter", "七個工具，可透過 stdio 或 basic Streamable HTTP 使用。"),
        ],
        "tools_kicker": "03 / 可執行介面",
        "tools_title": "七個工具，一條權威邊界。",
        "tools_intro": (
            "代理透過明確的操作改變 canonical document；讀取、驗證、export 與 snapshot 都是具名步驟，"
            "而不是藏在背後的副作用。"
        ),
        "tool_groups": [
            ("寫入", [
                ("sssp.create_document", "建立 canonical document。"),
                ("sssp.append_node", "附加一個具型別節點，驗證後才原子提交。"),
                ("sssp.replace_node", "以 revision 與 checksum 衝突保護取代單一節點。"),
            ]),
            ("檢查", [
                ("sssp.read_node", "不經 rendered export，直接讀 canonical data。"),
                ("sssp.validate_document", "執行結構、字元與 MathJax 驗證。"),
            ]),
            ("衍生", [
                ("sssp.export_document", "編譯衍生的 Markdown 視圖。"),
                ("sssp.commit_version", "建立不可變、已驗證的 snapshot。"),
            ]),
        ],
        "validation_title": "驗證分層，而且邊界有名字。",
        "layers": [
            ("L1", "結構 / 字元", "已實作", "控制字元、PUA、zero-width marker、校驗和、重複 ID 與 TeX 基礎結構。"),
            ("L2", "Renderer", "已實作", "建立已驗證 snapshot 前，MathJax 會解析每個 canonical math block。"),
            ("L3", "語義", "規劃中", "Claim consistency、symbol drift 與 semantic diff 仍是研究工作，不是現在式保證。"),
        ],
        "status_kicker": "04 / 狀態與邊界",
        "status_title": "一個會說自己停在哪裡的研究型 MVP。",
        "status_intro": (
            "SSSP v0.2 已可執行並通過測試，但還不是 production multi-writer 學術服務。"
            "公開網站負責說明協定，不會裸露一個未驗證身分的寫入端點。"
        ),
        "available_title": "目前可用",
        "available": [
            "具型別 canonical documents 與 ledgers",
            "Revision 與 checksum 衝突保護",
            "L1 結構驗證與 L2 MathJax 驗證",
            "不可變 snapshot 與 Markdown export",
            "MCP stdio 與 basic Streamable HTTP",
        ],
        "not_yet_title": "尚未宣稱",
        "not_yet": [
            "OAuth/OIDC 授權",
            "Multi-writer lock service",
            "完整 runtime JSON Schema enforcement",
            "L3 theorem 或 meaning checker",
            "Production persistent scholarly storage",
        ],
        "start_title": "執行參考實作",
        "start_intro": "Clone repository、安裝鎖定版本的 MathJax，接著啟動本機 MCP server。",
        "copy": "複製",
        "copied": "已複製",
        "docs": "閱讀部署說明",
        "footer_line": "Chat 是討論。File 是來源。Render 是視圖。",
        "footer_meta": "SSSP v0.2 · 研究型 MVP · 2026",
    },
}


CODE_VIEWS = {
    "canonical": """{
  \"id\": \"eq-0001\",
  \"type\": \"math_block\",
  \"latex\": \"\\\\forall x\\\\in X,\\\\;P(x)\",
  \"checksum\": \"sha256:4b8c…e21f\"
}""",
    "export": """## Stability claim

$$
\\forall x\\in X,\\;P(x)
$$

<!-- derived from eq-0001 -->""",
    "audit": """{
  \"operation\": \"append_node\",
  \"revision_before\": 2,
  \"revision_after\": 3,
  \"actor\": \"assistant\",
  \"reason\": \"add stability claim\"
}""",
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_nav(page: dict) -> str:
    return "".join(f'<a href="{esc(path)}">{esc(label)}</a>' for path, label in page["nav"])


def render_stats(page: dict) -> str:
    return "".join(
        f'<li><strong>{esc(number)}</strong><span>{esc(label)}</span></li>'
        for number, label in page["stats"]
    )


def render_failures(page: dict) -> str:
    return "".join(
        f'<article class="failure-card"><span class="failure-index">0{i}</span>'
        f'<h3>{esc(title)}</h3><p>{esc(body)}</p></article>'
        for i, (title, body) in enumerate(page["failures"], 1)
    )


def render_lenses(page: dict) -> tuple[str, str]:
    buttons = []
    panels = []
    for index, (key, label, accessible) in enumerate(page["lenses"]):
        selected = "true" if index == 0 else "false"
        hidden = "" if index == 0 else " hidden"
        buttons.append(
            f'<button type="button" class="lens-tab" role="tab" aria-selected="{selected}" '
            f'aria-controls="lens-{key}" id="tab-{key}" data-lens="{key}">{esc(label)}</button>'
        )
        panels.append(
            f'<section class="lens-panel" role="tabpanel" tabindex="0" id="lens-{key}" '
            f'aria-labelledby="tab-{key}"{hidden}>'
            f'<div class="code-head"><span>{esc(accessible)}</span><span>eq-0001</span></div>'
            f'<pre><code>{esc(CODE_VIEWS[key])}</code></pre>'
            f'<p>{esc(page["lens_note"][key])}</p></section>'
        )
    return "".join(buttons), "".join(panels)


def render_pillars(page: dict) -> str:
    return "".join(
        f'<article><span>0{i}</span><h3>{esc(title)}</h3><p>{esc(body)}</p></article>'
        for i, (title, body) in enumerate(page["pillars"], 1)
    )


def render_tools(page: dict) -> str:
    groups = []
    for group, tools in page["tool_groups"]:
        rows = "".join(
            f'<li><code>{esc(name)}</code><span>{esc(description)}</span></li>'
            for name, description in tools
        )
        groups.append(
            f'<section class="tool-group"><h3>{esc(group)}</h3><ul>{rows}</ul></section>'
        )
    return "".join(groups)


def render_layers(page: dict) -> str:
    return "".join(
        f'<article class="layer"><div class="layer-id">{esc(level)}</div>'
        f'<div><div class="layer-title"><h3>{esc(title)}</h3><span>{esc(state)}</span></div>'
        f'<p>{esc(body)}</p></div></article>'
        for level, title, state, body in page["layers"]
    )


def render_list(items: list[str]) -> str:
    return "".join(f'<li>{esc(item)}</li>' for item in items)


def render_page(key: str) -> str:
    page = PAGES[key]
    other_lang = "zh-Hant" if key == "en" else "en"
    tabs, panels = render_lenses(page)
    canonical = ORIGIN + page["path"]
    json_ld = {
        "@context": "https://schema.org",
        "@type": "SoftwareSourceCode",
        "name": "SSSP — Structured Scholarly Source Protocol",
        "codeRepository": REPOSITORY,
        "url": ORIGIN,
        "version": "0.2.0",
        "programmingLanguage": ["Python", "JavaScript"],
        "description": page["standfirst"],
        "author": {"@type": "Organization", "name": "EveMissLab"},
    }
    principle = "".join(
        f'<li><span>0{i}</span>{esc(item)}</li>'
        for i, item in enumerate(page["principle"], 1)
    )
    return f"""<!doctype html>
<html lang="{esc(page['lang'])}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SSSP — Structured Scholarly Source Protocol</title>
  <meta name="description" content="{esc(page['standfirst'])}">
  <link rel="canonical" href="{canonical}">
  <link rel="alternate" hreflang="en" href="{ORIGIN}/">
  <link rel="alternate" hreflang="zh-Hant" href="{ORIGIN}/zh/">
  <link rel="alternate" hreflang="x-default" href="{ORIGIN}/">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="EveMissLab">
  <meta property="og:title" content="SSSP — The source survives the conversation.">
  <meta property="og:description" content="{esc(page['standfirst'])}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{ORIGIN}/og.png">
  <meta property="og:image:width" content="1536">
  <meta property="og:image:height" content="1024">
  <meta property="og:locale" content="{'en_US' if key == 'en' else 'zh_TW'}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="theme-color" content="#efeee8" media="(prefers-color-scheme: light)">
  <meta name="theme-color" content="#111310" media="(prefers-color-scheme: dark)">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&amp;family=Instrument+Serif:ital@0;1&amp;family=Inter:wght@400;500;600;700&amp;family=Noto+Sans+TC:wght@400;500;600;700&amp;display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/assets/styles.css">
  <script type="application/ld+json">{json.dumps(json_ld, ensure_ascii=False)}</script>
</head>
<body>
  <a class="skip-link" href="#main">{esc(page['skip'])}</a>
  <header class="topbar">
    <div class="shell topbar-inner">
      <a class="brand" href="{esc(page['path'])}" aria-label="SSSP home"><span class="brand-mark">S³</span><span>SSSP</span></a>
      <nav aria-label="{esc(page['nav_label'])}">{render_nav(page)}</nav>
      <div class="topbar-actions">
        <a class="language" href="{esc(page['other_path'])}" hreflang="{other_lang}">{esc(page['other_label'])}</a>
        <button class="theme-toggle" type="button" data-theme-toggle aria-label="{esc(page['theme'])}"><span aria-hidden="true">◐</span></button>
      </div>
    </div>
  </header>

  <main id="main">
    <section class="hero shell">
      <div class="hero-copy">
        <p class="kicker">{esc(page['eyebrow'])}</p>
        <h1>{esc(page['title'])}</h1>
        <p class="standfirst">{esc(page['standfirst'])}</p>
        <div class="hero-actions">
          <a class="button button-primary" href="#protocol">{esc(page['primary_cta'])}</a>
          <a class="button button-secondary" href="{REPOSITORY}">{esc(page['source_cta'])}<span aria-hidden="true">↗</span></a>
        </div>
      </div>
      <aside class="specimen" aria-label="{esc(page['specimen_label'])}">
        <div class="specimen-top"><span>{esc(page['specimen_label'])}</span><span>math_block</span></div>
        <div class="specimen-body">
          <div class="specimen-node"><span>eq-0001</span><span>{esc(page['specimen_revision'])}</span></div>
          <h2>{esc(page['specimen_title'])}</h2>
          <div class="formula" aria-label="for every x in X, P of x">∀x∈X, P(x)</div>
          <div class="checksum"><span>sha256</span><code>4b8c9ef7…e21f</code></div>
        </div>
        <div class="specimen-foot"><span class="status-dot"></span>{esc(page['specimen_state'])}<span>L1 + L2</span></div>
      </aside>
    </section>

    <section class="signal" aria-label="{esc(page['principle_label'])}">
      <div class="shell signal-inner">
        <p>{esc(page['principle_label'])}</p>
        <ol>{principle}</ol>
      </div>
    </section>

    <ul class="stats shell" aria-label="SSSP at a glance">{render_stats(page)}</ul>

    <section class="section shell" id="problem">
      <div class="section-head">
        <p class="kicker">{esc(page['problem_kicker'])}</p>
        <div><h2>{esc(page['problem_title'])}</h2><p>{esc(page['problem_intro'])}</p></div>
      </div>
      <div class="failure-grid">{render_failures(page)}</div>
      <div class="contrast" aria-label="Source workflow comparison">
        <div class="contrast-row contrast-bad"><span>×</span><code>{esc(page['contrast_bad'])}</code></div>
        <div class="contrast-row contrast-good"><span>✓</span><code>{esc(page['contrast_good'])}</code></div>
      </div>
    </section>

    <section class="section section-ink" id="protocol">
      <div class="shell">
        <div class="section-head">
          <p class="kicker">{esc(page['protocol_kicker'])}</p>
          <div><h2>{esc(page['protocol_title'])}</h2><p>{esc(page['protocol_intro'])}</p></div>
        </div>
        <div class="lens">
          <div class="lens-tabs" role="tablist" aria-label="{esc(page['lens_label'])}">{tabs}</div>
          <div class="lens-panels">{panels}</div>
        </div>
        <div class="pillars">{render_pillars(page)}</div>
      </div>
    </section>

    <section class="section shell" id="tools">
      <div class="section-head">
        <p class="kicker">{esc(page['tools_kicker'])}</p>
        <div><h2>{esc(page['tools_title'])}</h2><p>{esc(page['tools_intro'])}</p></div>
      </div>
      <div class="tools-grid">{render_tools(page)}</div>
      <div class="validation">
        <h2>{esc(page['validation_title'])}</h2>
        <div class="layers">{render_layers(page)}</div>
      </div>
    </section>

    <section class="section section-status" id="status">
      <div class="shell">
        <div class="section-head">
          <p class="kicker">{esc(page['status_kicker'])}</p>
          <div><h2>{esc(page['status_title'])}</h2><p>{esc(page['status_intro'])}</p></div>
        </div>
        <div class="boundary-grid">
          <article><div class="boundary-head boundary-now"><span>●</span><h3>{esc(page['available_title'])}</h3></div><ul>{render_list(page['available'])}</ul></article>
          <article><div class="boundary-head boundary-later"><span>○</span><h3>{esc(page['not_yet_title'])}</h3></div><ul>{render_list(page['not_yet'])}</ul></article>
        </div>
        <div class="quickstart">
          <div><p class="kicker">REFERENCE IMPLEMENTATION</p><h2>{esc(page['start_title'])}</h2><p>{esc(page['start_intro'])}</p><a href="{REPOSITORY}/blob/main/docs/REMOTE_MCP_DEPLOY.md">{esc(page['docs'])} <span aria-hidden="true">↗</span></a></div>
          <div class="terminal">
            <div class="terminal-bar"><span>powershell</span><button type="button" data-copy-command data-copy-label="{esc(page['copy'])}" data-copied-label="{esc(page['copied'])}">{esc(page['copy'])}</button></div>
            <pre><code>git clone {REPOSITORY}.git
cd SSSP
npm install
python src/mcp_server.py</code></pre>
          </div>
        </div>
      </div>
    </section>
  </main>

  <footer>
    <div class="shell footer-grid">
      <div><a class="brand footer-brand" href="{esc(page['path'])}"><span class="brand-mark">S³</span><span>SSSP</span></a><p>{esc(page['footer_line'])}</p></div>
      <div class="footer-links"><a href="https://evemisslab.com/">EveMissLab</a><a href="{REPOSITORY}">GitHub</a><span>{esc(page['footer_meta'])}</span></div>
    </div>
  </footer>
  <script src="/assets/app.js" defer></script>
</body>
</html>
"""


def render_404() -> str:
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>Not found · SSSP</title><link rel="stylesheet" href="/assets/styles.css"></head>
<body><main class="not-found shell"><p class="kicker">404 / NOT FOUND</p><h1>This address is not part of the protocol.</h1>
<p>The public SSSP site documents the research MVP. Start from the canonical entry point.</p><a class="button button-primary" href="/">Return to SSSP</a></main></body></html>
"""


def render_sitemap() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url><loc>{ORIGIN}/</loc><xhtml:link rel="alternate" hreflang="en" href="{ORIGIN}/"/><xhtml:link rel="alternate" hreflang="zh-Hant" href="{ORIGIN}/zh/"/></url>
  <url><loc>{ORIGIN}/zh/</loc><xhtml:link rel="alternate" hreflang="en" href="{ORIGIN}/"/><xhtml:link rel="alternate" hreflang="zh-Hant" href="{ORIGIN}/zh/"/></url>
</urlset>
"""


def main() -> int:
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "assets").mkdir(parents=True)
    (DIST / "zh").mkdir()

    (DIST / "index.html").write_text(render_page("en"), encoding="utf-8")
    (DIST / "zh" / "index.html").write_text(render_page("zh"), encoding="utf-8")
    (DIST / "404.html").write_text(render_404(), encoding="utf-8")
    (DIST / "sitemap.xml").write_text(render_sitemap(), encoding="utf-8")
    (DIST / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {ORIGIN}/sitemap.xml\n", encoding="utf-8"
    )

    for asset in ("styles.css", "app.js"):
        shutil.copyfile(SITE / "src" / asset, DIST / "assets" / asset)
    og_image = SITE / "src" / "og.png"
    if not og_image.exists():
        raise FileNotFoundError("site/src/og.png is required before the release build")
    shutil.copyfile(og_image, DIST / "og.png")

    assert 'lang="en"' in (DIST / "index.html").read_text(encoding="utf-8")
    assert 'lang="zh-Hant"' in (DIST / "zh" / "index.html").read_text(encoding="utf-8")
    print(f"built SSSP public site into {DIST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
