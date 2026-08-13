export const PROTOCOL = "SSSP" as const;
export const PROTOCOL_VERSION = "0.1" as const;
export const SERVICE_VERSION = "0.3.0" as const;

export const NODE_TYPES = [
  "heading",
  "paragraph",
  "math_block",
  "definition",
  "claim",
  "code",
  "reference",
  "note",
] as const;

export type NodeType = (typeof NODE_TYPES)[number];

export interface SSSPNode {
  id: string;
  type: NodeType;
  content?: string;
  latex?: string;
  level?: number;
  label?: string;
  language?: string;
  claim?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  provenance: {
    actor: string;
    reason: string;
  };
  checksum: string;
  [key: string]: unknown;
}

export interface SSSPDocument {
  protocol: typeof PROTOCOL;
  version: typeof PROTOCOL_VERSION;
  document_id: string;
  title: string;
  revision: number;
  created_at: string;
  updated_at: string;
  nodes: SSSPNode[];
  semantic_ledger: {
    terms: Record<string, unknown>;
    deprecated_terms: Record<string, unknown>;
    symbols: Record<string, unknown>;
  };
  claim_ledger: Record<string, unknown>;
}

export interface ValidationIssue {
  level: "FAIL" | "WARN";
  code: string;
  message: string;
  node_id?: string;
}

export interface ValidationReport {
  status: "PASS" | "WARN" | "FAIL";
  issue_count: number;
  issues: ValidationIssue[];
  render_math_checked: number;
  render_notes: string[];
  document_hash: string;
}

export interface DocumentSummary {
  document_id: string;
  title: string;
  revision: number;
  node_count: number;
  document_hash: string;
}

export interface StoreErrorPayload {
  code: string;
  message: string;
  data: unknown;
}

export type StoreResult<T> =
  | { ok: true; value: T }
  | { ok: false; error: StoreErrorPayload };

export class SSSPError extends Error {
  readonly code: string;
  readonly data: unknown;

  constructor(code: string, message: string, data: unknown = {}) {
    super(message);
    this.name = "SSSPError";
    this.code = code;
    this.data = data;
  }
}
