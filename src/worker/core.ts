import { createHash } from "node:crypto";

import { mathjax } from "mathjax-full/js/mathjax.js";
import { liteAdaptor } from "mathjax-full/js/adaptors/liteAdaptor.js";
import { RegisterHTMLHandler } from "mathjax-full/js/handlers/html.js";
import { TeX } from "mathjax-full/js/input/tex.js";
import { AllPackages } from "mathjax-full/js/input/tex/AllPackages.js";
import { SVG } from "mathjax-full/js/output/svg.js";

import {
  NODE_TYPES,
  PROTOCOL,
  PROTOCOL_VERSION,
  type DocumentSummary,
  type SSSPDocument,
  SSSPError,
  type SSSPNode,
  type ValidationIssue,
  type ValidationReport,
} from "./protocol";

export const LIMITS = {
  documentIdLength: 128,
  titleLength: 1_000,
  actorLength: 128,
  reasonLength: 1_000,
  labelLength: 256,
  nodeTextLength: 65_536,
  mathTextLength: 16_384,
  nodeBytes: 131_072,
  documentBytes: 2 * 1024 * 1024,
  nodesPerDocument: 128,
  mathNodesPerDocument: 64,
  documents: 100,
  liveDocumentBytes: 50 * 1024 * 1024,
  snapshotsPerDocument: 20,
  snapshotBytes: 200 * 1024 * 1024,
  auditRows: 20_000,
} as const;

const DOCUMENT_ID = /^[A-Za-z0-9._-]{1,128}$/;
const CHECKSUM = /^sha256:[0-9a-f]{64}$/;
const ZERO_WIDTH = new Set(["\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"]);

const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const texInput = new TeX({ packages: AllPackages });
const svgOutput = new SVG({ fontCache: "none" });
const mathDocument = mathjax.document("", { InputJax: texInput, OutputJax: svgOutput });

export function utcNow(): string {
  return new Date().toISOString();
}

function encodeCanonical(value: unknown): string {
  if (value === null || typeof value === "string" || typeof value === "boolean") {
    return JSON.stringify(value);
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new SSSPError("INVALID_JSON", "Canonical data cannot contain non-finite numbers");
    }
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => encodeCanonical(item === undefined ? null : item)).join(",")}]`;
  }
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    const entries = Object.keys(record)
      .filter((key) => record[key] !== undefined)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${encodeCanonical(record[key])}`);
    return `{${entries.join(",")}}`;
  }
  throw new SSSPError("INVALID_JSON", `Canonical data cannot contain ${typeof value}`);
}

export function canonicalJson(value: unknown): string {
  return encodeCanonical(value);
}

export function jsonByteLength(value: unknown): number {
  return new TextEncoder().encode(canonicalJson(value)).byteLength;
}

export function sha256Text(text: string): string {
  return `sha256:${createHash("sha256").update(text, "utf8").digest("hex")}`;
}

export function nodeChecksum(node: Record<string, unknown>): string {
  const withoutChecksum = { ...node };
  delete withoutChecksum.checksum;
  return sha256Text(canonicalJson(withoutChecksum));
}

export function documentHash(document: SSSPDocument): string {
  return sha256Text(canonicalJson(document));
}

export function isSafeDocumentId(documentId: string): boolean {
  return DOCUMENT_ID.test(documentId);
}

export function assertDocumentId(documentId: string): void {
  if (!isSafeDocumentId(documentId)) {
    throw new SSSPError(
      "INVALID_DOCUMENT_ID",
      "document_id must match [A-Za-z0-9._-]{1,128}",
    );
  }
}

function cloneRecord(value: Record<string, unknown>): Record<string, unknown> {
  return structuredClone(value);
}

function assertBoundedText(value: string, field: string, maximum: number): void {
  if (value.length > maximum) {
    throw new SSSPError(
      "INPUT_TOO_LARGE",
      `${field} exceeds the ${maximum.toLocaleString("en-US")} character limit`,
      { field, maximum, actual: value.length },
    );
  }
}

export function normalizeDisplayText(
  value: string | undefined,
  fallback: string,
  field: string,
  maximum: number,
): string {
  const resolved = value?.trim() || fallback;
  assertBoundedText(resolved, field, maximum);
  return resolved;
}

export function normalizeNode(
  rawNode: Record<string, unknown>,
  actor: string,
  reason: string,
  createdAt?: string,
): SSSPNode {
  const node = cloneRecord(rawNode);
  const nodeId = node.id;
  const nodeType = node.type;
  if (typeof nodeId !== "string" || !DOCUMENT_ID.test(nodeId)) {
    throw new SSSPError("INVALID_NODE_ID", "node.id must match [A-Za-z0-9._-]{1,128}");
  }
  if (typeof nodeType !== "string" || !NODE_TYPES.includes(nodeType as (typeof NODE_TYPES)[number])) {
    throw new SSSPError("INVALID_NODE_TYPE", `Unsupported node type: ${String(nodeType)}`);
  }

  if (nodeType === "math_block") {
    if (typeof node.latex !== "string" || !node.latex.trim()) {
      throw new SSSPError("INVALID_NODE", "math_block requires non-empty latex");
    }
    assertBoundedText(node.latex, "node.latex", LIMITS.mathTextLength);
    delete node.content;
  } else {
    if (typeof node.content !== "string") {
      throw new SSSPError("INVALID_NODE", `${nodeType} requires string content`);
    }
    assertBoundedText(node.content, "node.content", LIMITS.nodeTextLength);
    delete node.latex;
  }

  const now = utcNow();
  delete node.checksum;
  node.created_at = createdAt ?? now;
  node.updated_at = now;
  node.provenance = { actor, reason };
  node.checksum = nodeChecksum(node);

  if (jsonByteLength(node) > LIMITS.nodeBytes) {
    throw new SSSPError("INPUT_TOO_LARGE", "Canonical node exceeds the byte-size limit", {
      maximum: LIMITS.nodeBytes,
    });
  }
  return node as SSSPNode;
}

function findUnicodeIssues(text: string, nodeId: string): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  for (const character of text) {
    const codePoint = character.codePointAt(0) ?? 0;
    const forbiddenControl = codePoint < 0x20 && ![0x09, 0x0a, 0x0d].includes(codePoint);
    if (forbiddenControl) {
      issues.push({
        level: "FAIL",
        code: "CONTROL_CHAR",
        message: `Forbidden control character U+${codePoint.toString(16).toUpperCase().padStart(4, "0")}`,
        node_id: nodeId,
      });
    }
    if (ZERO_WIDTH.has(character)) {
      issues.push({
        level: "FAIL",
        code: "ZERO_WIDTH",
        message: `Zero-width/BOM marker U+${codePoint.toString(16).toUpperCase().padStart(4, "0")}`,
        node_id: nodeId,
      });
    }
    const privateUse =
      (codePoint >= 0xe000 && codePoint <= 0xf8ff) ||
      (codePoint >= 0xf0000 && codePoint <= 0xffffd) ||
      (codePoint >= 0x100000 && codePoint <= 0x10fffd);
    if (privateUse) {
      issues.push({
        level: "FAIL",
        code: "PUA_CHAR",
        message: `Private Use Area character U+${codePoint.toString(16).toUpperCase().padStart(4, "0")}`,
        node_id: nodeId,
      });
    }
  }
  return issues;
}

function bracesAreBalanced(tex: string): boolean {
  let depth = 0;
  let escaped = false;
  for (const character of tex) {
    if (escaped) {
      escaped = false;
      continue;
    }
    if (character === "\\") {
      escaped = true;
    } else if (character === "{") {
      depth += 1;
    } else if (character === "}") {
      depth -= 1;
      if (depth < 0) return false;
    }
  }
  return depth === 0;
}

function environmentBalance(tex: string): { ok: true } | { ok: false; message: string } {
  const stack: string[] = [];
  const pattern = /\\(begin|end)\{([^}]+)\}/g;
  for (const match of tex.matchAll(pattern)) {
    const kind = match[1];
    const name = match[2] ?? "";
    if (kind === "begin") {
      stack.push(name);
    } else if (stack.at(-1) !== name) {
      return { ok: false, message: `environment mismatch at ${name}` };
    } else {
      stack.pop();
    }
  }
  return stack.length > 0
    ? { ok: false, message: `unclosed environment(s): ${stack.join(", ")}` }
    : { ok: true };
}

function validateMathWithMathJax(tex: string): { ok: true } | { ok: false; message: string } {
  try {
    mathDocument.convert(tex, { display: true });
    return { ok: true };
  } catch (error) {
    return {
      ok: false,
      message: error instanceof Error ? error.message.slice(0, 1_000) : String(error).slice(0, 1_000),
    };
  }
}

function issue(
  issues: ValidationIssue[],
  level: ValidationIssue["level"],
  code: string,
  message: string,
  nodeId?: string,
): void {
  issues.push(nodeId === undefined ? { level, code, message } : { level, code, message, node_id: nodeId });
}

export function validateDocument(document: SSSPDocument, renderMath = true): ValidationReport {
  const issues: ValidationIssue[] = [];
  if (document.protocol !== PROTOCOL) {
    issue(issues, "FAIL", "PROTOCOL_MISMATCH", `Expected protocol ${PROTOCOL}`);
  }
  if (document.version !== PROTOCOL_VERSION) {
    issue(issues, "FAIL", "VERSION_MISMATCH", `Expected SSSP version ${PROTOCOL_VERSION}`);
  }
  if (!isSafeDocumentId(document.document_id)) {
    issue(issues, "FAIL", "INVALID_DOCUMENT_ID", "Invalid canonical document_id");
  }
  if (typeof document.title !== "string" || document.title.length === 0) {
    issue(issues, "FAIL", "INVALID_TITLE", "title must be a non-empty string");
  }
  if (!Number.isInteger(document.revision) || document.revision < 0) {
    issue(issues, "FAIL", "INVALID_REVISION", "revision must be a non-negative integer");
  }
  if (!Array.isArray(document.nodes)) {
    issue(issues, "FAIL", "INVALID_NODES", "nodes must be an array");
  }

  const seen = new Set<string>();
  let renderMathChecked = 0;
  for (const node of Array.isArray(document.nodes) ? document.nodes : []) {
    const nodeId = typeof node.id === "string" ? node.id : "<missing>";
    if (seen.has(nodeId)) {
      issue(issues, "FAIL", "DUPLICATE_NODE_ID", `Duplicate node id: ${nodeId}`, nodeId);
    }
    seen.add(nodeId);
    if (!NODE_TYPES.includes(node.type)) {
      issue(issues, "FAIL", "INVALID_NODE_TYPE", `Unsupported node type: ${String(node.type)}`, nodeId);
    }
    const text = node.type === "math_block" ? node.latex : node.content;
    if (typeof text !== "string") {
      issue(issues, "FAIL", "MISSING_NODE_TEXT", "Node text/latex must be a string", nodeId);
      continue;
    }
    issues.push(...findUnicodeIssues(text, nodeId));
    if (!CHECKSUM.test(node.checksum) || node.checksum !== nodeChecksum(node)) {
      issue(
        issues,
        "FAIL",
        "CHECKSUM_MISMATCH",
        "Node checksum does not match canonical node",
        nodeId,
      );
    }
    if (node.type !== "math_block") continue;

    if (text.includes("$")) {
      issue(
        issues,
        "WARN",
        "MATH_DELIMITER_IN_CANONICAL",
        "Canonical math_block should not include Markdown $ delimiters",
        nodeId,
      );
    }
    if (!bracesAreBalanced(text)) {
      issue(issues, "FAIL", "UNBALANCED_BRACES", "LaTeX braces appear unbalanced", nodeId);
    }
    const environment = environmentBalance(text);
    if (!environment.ok) {
      issue(issues, "FAIL", "ENVIRONMENT_MISMATCH", environment.message, nodeId);
    }
    for (const line of text.split(/\r?\n/).slice(1)) {
      const fragment = line.trimStart();
      if (/^(eg|eq|abla|oxed|orall|ightarrow|arnothing|ext)\b/.test(fragment)) {
        issue(
          issues,
          "WARN",
          "ESCAPE_CORRUPTION_RISK",
          `Suspicious command fragment after line break: ${fragment.slice(0, 40)}`,
          nodeId,
        );
      }
    }
    if (renderMath) {
      const rendered = validateMathWithMathJax(text);
      if (rendered.ok) {
        renderMathChecked += 1;
      } else {
        issue(issues, "FAIL", "MATHJAX_PARSE", rendered.message, nodeId);
      }
    }
  }

  const status = issues.some((entry) => entry.level === "FAIL")
    ? "FAIL"
    : issues.some((entry) => entry.level === "WARN")
      ? "WARN"
      : "PASS";
  return {
    status,
    issue_count: issues.length,
    issues,
    render_math_checked: renderMathChecked,
    render_notes: [],
    document_hash: documentHash(document),
  };
}

export function createDocument(documentId: string, title: string, now = utcNow()): SSSPDocument {
  assertDocumentId(documentId);
  const normalizedTitle = title.trim();
  if (!normalizedTitle) {
    throw new SSSPError("INVALID_TITLE", "title must be non-empty");
  }
  assertBoundedText(normalizedTitle, "title", LIMITS.titleLength);
  return {
    protocol: PROTOCOL,
    version: PROTOCOL_VERSION,
    document_id: documentId,
    title: normalizedTitle,
    revision: 0,
    created_at: now,
    updated_at: now,
    nodes: [],
    semantic_ledger: { terms: {}, deprecated_terms: {}, symbols: {} },
    claim_ledger: {},
  };
}

export function summarize(document: SSSPDocument): DocumentSummary {
  return {
    document_id: document.document_id,
    title: document.title,
    revision: document.revision,
    node_count: document.nodes.length,
    document_hash: documentHash(document),
  };
}

function markdownText(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export function exportMarkdown(document: SSSPDocument): string {
  const output: string[] = [`# ${document.title}`, ""];
  for (const node of document.nodes) {
    switch (node.type) {
      case "heading": {
        const requested = Number.isInteger(node.level) ? Number(node.level) : 2;
        const level = Math.max(1, Math.min(6, requested));
        output.push(`${"#".repeat(level)} ${markdownText(node.content)}`, "");
        break;
      }
      case "paragraph":
      case "note":
      case "reference":
        output.push(markdownText(node.content), "");
        break;
      case "math_block":
        output.push("$$", markdownText(node.latex), "$$", "");
        break;
      case "definition": {
        const label = markdownText(node.label);
        output.push(`**Definition${label ? `: ${label}` : ""}**`, "", markdownText(node.content), "");
        break;
      }
      case "claim": {
        const claim = node.claim && typeof node.claim === "object" ? node.claim : {};
        const type = markdownText(claim.type) || "claim";
        const status = markdownText(claim.status) || "unspecified";
        output.push(`**Claim [${type} / ${status}]**`, "", markdownText(node.content), "");
        break;
      }
      case "code":
        output.push(`\`\`\`${markdownText(node.language)}`, markdownText(node.content), "```", "");
        break;
    }
  }
  output.push(
    "---",
    `<!-- SSSP source revision: ${document.revision} -->`,
    `<!-- SSSP source hash: ${documentHash(document)} -->`,
    "",
  );
  return output.join("\n");
}

export function assertDocumentLimits(document: SSSPDocument): void {
  if (document.nodes.length > LIMITS.nodesPerDocument) {
    throw new SSSPError("DOCUMENT_LIMIT", "Document exceeds the node limit", {
      maximum: LIMITS.nodesPerDocument,
    });
  }
  const mathNodes = document.nodes.filter((node) => node.type === "math_block").length;
  if (mathNodes > LIMITS.mathNodesPerDocument) {
    throw new SSSPError("DOCUMENT_LIMIT", "Document exceeds the math-node limit", {
      maximum: LIMITS.mathNodesPerDocument,
    });
  }
  const bytes = jsonByteLength(document);
  if (bytes > LIMITS.documentBytes) {
    throw new SSSPError("DOCUMENT_LIMIT", "Canonical document exceeds the byte-size limit", {
      maximum: LIMITS.documentBytes,
      actual: bytes,
    });
  }
}
