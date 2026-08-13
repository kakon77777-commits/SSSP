#!/usr/bin/env python3
from __future__ import annotations

import json
import struct
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist-site"
EXPECTED_TOOLS = {
    "sssp.create_document",
    "sssp.append_node",
    "sssp.replace_node",
    "sssp.read_node",
    "sssp.validate_document",
    "sssp.export_document",
    "sssp.commit_version",
}


class Document(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.references: list[str] = []
        self.lang = ""
        self.title = ""
        self._in_title = False
        self.json_ld: list[str] = []
        self._in_json_ld = False
        self._json_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html":
            self.lang = values.get("lang") or ""
        if tag == "title":
            self._in_title = True
        if values.get("id"):
            self.ids.add(str(values["id"]))
        for key in ("href", "src"):
            value = values.get(key)
            if value:
                self.references.append(value)
        if tag == "script" and values.get("type") == "application/ld+json":
            self._in_json_ld = True
            self._json_buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag == "script" and self._in_json_ld:
            self.json_ld.append("".join(self._json_buffer))
            self._in_json_ld = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_json_ld:
            self._json_buffer.append(data)


def local_target(page: Path, reference: str) -> Path | None:
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or reference.startswith(("mailto:", "tel:")):
        return None
    path = parsed.path
    if not path or path == "/":
        return DIST / "index.html"
    if path.startswith("/"):
        candidate = DIST / path.lstrip("/")
    else:
        candidate = page.parent / path
    if candidate.is_dir() or path.endswith("/"):
        candidate = candidate / "index.html"
    return candidate


def validate_page(path: Path, expected_lang: str) -> str:
    raw = path.read_text(encoding="utf-8")
    parser = Document()
    parser.feed(raw)
    assert parser.lang == expected_lang, f"{path}: expected lang={expected_lang}, got {parser.lang}"
    assert parser.title == "SSSP — Structured Scholarly Source Protocol"
    assert len(parser.json_ld) == 1, f"{path}: expected one JSON-LD block"
    structured = json.loads(parser.json_ld[0])
    assert structured["@type"] == "SoftwareSourceCode"
    assert structured["version"] == "0.3.0"

    for reference in parser.references:
        parsed = urlsplit(reference)
        if reference.startswith("#"):
            assert reference[1:] in parser.ids, f"{path}: missing fragment {reference}"
            continue
        candidate = local_target(path, reference)
        if candidate is not None:
            assert candidate.exists(), f"{path}: missing local asset {reference}"
        if parsed.fragment and not parsed.path:
            assert parsed.fragment in parser.ids, f"{path}: missing fragment #{parsed.fragment}"

    controls = [ord(char) for char in raw if ord(char) < 32 and char not in "\n\r\t"]
    assert not controls, f"{path}: forbidden control bytes {controls}"
    assert "YOUR_" not in raw and "TODO" not in raw, f"{path}: unresolved placeholder"
    return raw


def validate_png(path: Path) -> None:
    raw = path.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n", f"{path}: invalid PNG signature"
    width, height = struct.unpack(">II", raw[16:24])
    assert (width, height) == (1536, 1024), f"{path}: unexpected dimensions {width}x{height}"


def main() -> int:
    required = [
        DIST / "index.html",
        DIST / "zh" / "index.html",
        DIST / "404.html",
        DIST / "assets" / "styles.css",
        DIST / "assets" / "app.js",
        DIST / "og.png",
        DIST / "robots.txt",
        DIST / "sitemap.xml",
    ]
    for path in required:
        assert path.is_file(), f"missing build artifact: {path}"

    english = validate_page(DIST / "index.html", "en")
    chinese = validate_page(DIST / "zh" / "index.html", "zh-Hant")
    for tool in EXPECTED_TOOLS:
        assert tool in english and tool in chinese, f"missing tool copy: {tool}"
        assert english.count(tool) == 1 and chinese.count(tool) == 1, f"duplicate tool copy: {tool}"
    endpoint = "https://sssp.evemisslab.com/mcp"
    assert endpoint in english and endpoint in chinese, "missing public MCP endpoint"

    validate_png(DIST / "og.png")
    config = json.loads((ROOT / "wrangler.jsonc").read_text(encoding="utf-8"))
    assert config["routes"] == [{"pattern": "sssp.evemisslab.com", "custom_domain": True}]
    assert config["assets"]["directory"] == "./dist-site"
    assert config["assets"]["not_found_handling"] == "404-page"

    sitemap = (DIST / "sitemap.xml").read_text(encoding="utf-8")
    assert sitemap.count("<url>") == 2
    print("validated 2 localized pages, 7 tools, local assets, metadata, PNG, and deployment config")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
