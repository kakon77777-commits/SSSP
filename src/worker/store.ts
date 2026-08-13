import { DurableObject } from "cloudflare:workers";

import {
  LIMITS,
  assertDocumentId,
  assertDocumentLimits,
  canonicalJson,
  createDocument as newDocument,
  documentHash,
  exportMarkdown,
  jsonByteLength,
  normalizeDisplayText,
  normalizeNode,
  summarize,
  utcNow,
  validateDocument,
} from "./core";
import {
  type DocumentSummary,
  type SSSPDocument,
  SSSPError,
  type SSSPNode,
  type StoreResult,
  type ValidationReport,
} from "./protocol";

interface DocumentRow extends Record<string, SqlStorageValue> {
  canonical_json: string;
}

interface CountRow extends Record<string, SqlStorageValue> {
  count: number;
}

interface BytesRow extends Record<string, SqlStorageValue> {
  bytes: number;
}

interface SnapshotRow extends Record<string, SqlStorageValue> {
  label: string;
  snapshot_at: string;
}

export interface AppendResult extends DocumentSummary {
  node: SSSPNode;
  validation: ValidationReport;
}

export interface ReplaceResult extends AppendResult {
  previous_checksum: string;
}

export interface ReadNodeResult {
  document_id: string;
  revision: number;
  node: SSSPNode;
}

export interface ExportResult {
  protocol: "SSSP";
  source_revision: number;
  source_hash: string;
  compiler: string;
  exported_at: string;
  filename: string;
  source_uri: string;
  content: string;
  validation: ValidationReport;
}

export interface CommitResult {
  document_id: string;
  revision: number;
  document_hash: string;
  snapshot_uri: string;
  label: string;
  snapshot_at: string;
  created: boolean;
  validation: ValidationReport;
}

function isSSSPDocument(value: unknown): value is SSSPDocument {
  if (value === null || typeof value !== "object") return false;
  const candidate = value as Partial<SSSPDocument>;
  return (
    candidate.protocol === "SSSP" &&
    candidate.version === "0.1" &&
    typeof candidate.document_id === "string" &&
    typeof candidate.title === "string" &&
    typeof candidate.revision === "number" &&
    Array.isArray(candidate.nodes)
  );
}

export class SSSPStore extends DurableObject<Env> {
  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    ctx.blockConcurrencyWhile(async () => {
      this.migrate();
    });
  }

  private migrate(): void {
    this.ctx.storage.sql.exec(`
      CREATE TABLE IF NOT EXISTS _sql_schema_migrations (
        id INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL
      );
    `);
    const current = this.ctx.storage.sql
      .exec<{ version: number }>(
        "SELECT COALESCE(MAX(id), 0) AS version FROM _sql_schema_migrations",
      )
      .one().version;
    if (current < 1) {
      const now = utcNow();
      this.ctx.storage.sql.exec(`
        CREATE TABLE IF NOT EXISTS documents (
          document_id TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          revision INTEGER NOT NULL,
          canonical_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          document_id TEXT NOT NULL,
          ts TEXT NOT NULL,
          action TEXT NOT NULL,
          actor TEXT NOT NULL,
          node_id TEXT,
          revision INTEGER NOT NULL,
          details_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS audit_document_revision
          ON audit(document_id, revision, id);
        CREATE TABLE IF NOT EXISTS versions (
          document_id TEXT NOT NULL,
          revision INTEGER NOT NULL,
          document_hash TEXT NOT NULL,
          label TEXT NOT NULL,
          snapshot_at TEXT NOT NULL,
          snapshot_json TEXT NOT NULL,
          PRIMARY KEY (document_id, revision, document_hash)
        );
        CREATE INDEX IF NOT EXISTS versions_document_revision
          ON versions(document_id, revision);
      `);
      this.ctx.storage.sql.exec(
        "INSERT INTO _sql_schema_migrations (id, applied_at) VALUES (?, ?)",
        1,
        now,
      );
    }
  }

  private result<T>(operation: () => T): StoreResult<T> {
    try {
      return { ok: true, value: operation() };
    } catch (error) {
      if (error instanceof SSSPError) {
        return {
          ok: false,
          error: { code: error.code, message: error.message, data: error.data },
        };
      }
      const message = error instanceof Error ? error.message : String(error);
      console.error(
        JSON.stringify({ message: "SSSP store operation failed", error: message }),
      );
      return {
        ok: false,
        error: { code: "INTERNAL", message: "SSSP storage operation failed", data: {} },
      };
    }
  }

  private load(documentId: string): SSSPDocument {
    assertDocumentId(documentId);
    const row = this.ctx.storage.sql
      .exec<DocumentRow>(
        "SELECT canonical_json FROM documents WHERE document_id = ?",
        documentId,
      )
      .toArray()[0];
    if (!row) {
      throw new SSSPError("DOCUMENT_NOT_FOUND", `Unknown document: ${documentId}`);
    }
    let parsed: unknown;
    try {
      parsed = JSON.parse(row.canonical_json) as unknown;
    } catch (error) {
      throw new SSSPError(
        "DOCUMENT_CORRUPT",
        `Cannot parse canonical document: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
    if (!isSSSPDocument(parsed)) {
      throw new SSSPError("DOCUMENT_CORRUPT", "Stored canonical document has an invalid shape");
    }
    return parsed;
  }

  private ensureRevision(document: SSSPDocument, expectedRevision?: number): void {
    if (expectedRevision !== undefined && document.revision !== expectedRevision) {
      throw new SSSPError(
        "REVISION_CONFLICT",
        `Expected revision ${expectedRevision}, current revision is ${document.revision}`,
        { expected: expectedRevision, current: document.revision },
      );
    }
  }

  private enforceLiveQuota(document: SSSPDocument): void {
    assertDocumentLimits(document);
    const otherBytes = this.ctx.storage.sql
      .exec<BytesRow>(
        `SELECT COALESCE(SUM(length(CAST(canonical_json AS BLOB))), 0) AS bytes
         FROM documents WHERE document_id <> ?`,
        document.document_id,
      )
      .one().bytes;
    const nextBytes = otherBytes + jsonByteLength(document);
    if (nextBytes > LIMITS.liveDocumentBytes) {
      throw new SSSPError("WORKSPACE_QUOTA", "The anonymous public workspace is full", {
        maximum: LIMITS.liveDocumentBytes,
      });
    }
  }

  private save(document: SSSPDocument): void {
    this.enforceLiveQuota(document);
    this.ctx.storage.sql.exec(
      `UPDATE documents
       SET title = ?, revision = ?, canonical_json = ?, updated_at = ?
       WHERE document_id = ?`,
      document.title,
      document.revision,
      canonicalJson(document),
      document.updated_at,
      document.document_id,
    );
  }

  private audit(
    document: SSSPDocument,
    action: string,
    actor: string,
    details: Record<string, unknown> = {},
    nodeId?: string,
  ): void {
    this.ctx.storage.sql.exec(
      `INSERT INTO audit
       (document_id, ts, action, actor, node_id, revision, details_json)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      document.document_id,
      utcNow(),
      action,
      actor,
      nodeId ?? null,
      document.revision,
      canonicalJson(details),
    );
    this.ctx.storage.sql.exec(
      `DELETE FROM audit
       WHERE id NOT IN (SELECT id FROM audit ORDER BY id DESC LIMIT ?)`,
      LIMITS.auditRows,
    );
  }

  async createDocument(
    documentId: string,
    title: string,
    actor = "anonymous-assistant",
  ): Promise<StoreResult<DocumentSummary>> {
    return this.result(() =>
      this.ctx.storage.transactionSync(() => {
        assertDocumentId(documentId);
        const existing = this.ctx.storage.sql
          .exec<CountRow>("SELECT COUNT(*) AS count FROM documents WHERE document_id = ?", documentId)
          .one().count;
        if (existing > 0) {
          throw new SSSPError("DOCUMENT_EXISTS", `Document already exists: ${documentId}`);
        }
        const count = this.ctx.storage.sql
          .exec<CountRow>("SELECT COUNT(*) AS count FROM documents")
          .one().count;
        if (count >= LIMITS.documents) {
          throw new SSSPError("WORKSPACE_QUOTA", "The anonymous public workspace reached its document limit", {
            maximum: LIMITS.documents,
          });
        }
        const normalizedActor = normalizeDisplayText(
          actor,
          "anonymous-assistant",
          "actor",
          LIMITS.actorLength,
        );
        const document = newDocument(documentId, title);
        this.enforceLiveQuota(document);
        this.ctx.storage.sql.exec(
          `INSERT INTO documents
           (document_id, title, revision, canonical_json, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)`,
          document.document_id,
          document.title,
          document.revision,
          canonicalJson(document),
          document.created_at,
          document.updated_at,
        );
        this.audit(document, "create_document", normalizedActor);
        return summarize(document);
      }),
    );
  }

  async appendNode(
    documentId: string,
    rawNode: Record<string, unknown>,
    expectedRevision?: number,
    actor = "anonymous-assistant",
    reason = "append node",
  ): Promise<StoreResult<AppendResult>> {
    return this.result(() =>
      this.ctx.storage.transactionSync(() => {
        const document = this.load(documentId);
        this.ensureRevision(document, expectedRevision);
        const normalizedActor = normalizeDisplayText(
          actor,
          "anonymous-assistant",
          "actor",
          LIMITS.actorLength,
        );
        const normalizedReason = normalizeDisplayText(
          reason,
          "append node",
          "reason",
          LIMITS.reasonLength,
        );
        const node = normalizeNode(rawNode, normalizedActor, normalizedReason);
        if (document.nodes.some((entry) => entry.id === node.id)) {
          throw new SSSPError("NODE_EXISTS", `Node already exists: ${node.id}`);
        }
        const candidate = structuredClone(document);
        candidate.nodes.push(node);
        candidate.revision += 1;
        candidate.updated_at = utcNow();
        const validation = validateDocument(candidate, true);
        if (validation.status === "FAIL") {
          throw new SSSPError(
            "VALIDATION_FAILED",
            "Candidate document failed validation",
            validation,
          );
        }
        this.save(candidate);
        this.audit(candidate, "append_node", normalizedActor, {}, node.id);
        return { ...summarize(candidate), node, validation };
      }),
    );
  }

  async replaceNode(
    documentId: string,
    nodeId: string,
    replacement: Record<string, unknown>,
    expectedRevision?: number,
    expectedChecksum?: string,
    actor = "anonymous-assistant",
    reason = "replace node",
  ): Promise<StoreResult<ReplaceResult>> {
    return this.result(() =>
      this.ctx.storage.transactionSync(() => {
        const document = this.load(documentId);
        this.ensureRevision(document, expectedRevision);
        const index = document.nodes.findIndex((node) => node.id === nodeId);
        if (index < 0) {
          throw new SSSPError("NODE_NOT_FOUND", `Unknown node: ${nodeId}`);
        }
        const previous = document.nodes[index];
        if (!previous) {
          throw new SSSPError("NODE_NOT_FOUND", `Unknown node: ${nodeId}`);
        }
        if (expectedChecksum !== undefined && previous.checksum !== expectedChecksum) {
          throw new SSSPError("CHECKSUM_CONFLICT", "Node checksum differs from expected value", {
            expected: expectedChecksum,
            current: previous.checksum,
          });
        }
        const normalizedActor = normalizeDisplayText(
          actor,
          "anonymous-assistant",
          "actor",
          LIMITS.actorLength,
        );
        const normalizedReason = normalizeDisplayText(
          reason,
          "replace node",
          "reason",
          LIMITS.reasonLength,
        );
        const node = normalizeNode(
          { ...replacement, id: nodeId },
          normalizedActor,
          normalizedReason,
          previous.created_at,
        );
        const candidate = structuredClone(document);
        candidate.nodes[index] = node;
        candidate.revision += 1;
        candidate.updated_at = utcNow();
        const validation = validateDocument(candidate, true);
        if (validation.status === "FAIL") {
          throw new SSSPError(
            "VALIDATION_FAILED",
            "Candidate document failed validation",
            validation,
          );
        }
        this.save(candidate);
        this.audit(
          candidate,
          "replace_node",
          normalizedActor,
          { previous_checksum: previous.checksum },
          nodeId,
        );
        return {
          ...summarize(candidate),
          node,
          previous_checksum: previous.checksum,
          validation,
        };
      }),
    );
  }

  async readNode(documentId: string, nodeId: string): Promise<StoreResult<ReadNodeResult>> {
    return this.result(() => {
      const document = this.load(documentId);
      const node = document.nodes.find((entry) => entry.id === nodeId);
      if (!node) {
        throw new SSSPError("NODE_NOT_FOUND", `Unknown node: ${nodeId}`);
      }
      return { document_id: documentId, revision: document.revision, node };
    });
  }

  async validateDocument(documentId: string): Promise<StoreResult<ValidationReport>> {
    return this.result(() => validateDocument(this.load(documentId), true));
  }

  async exportDocument(documentId: string, format = "markdown"): Promise<StoreResult<ExportResult>> {
    return this.result(() => {
      if (format !== "markdown") {
        throw new SSSPError("UNSUPPORTED_EXPORT", "SSSP currently supports only Markdown export");
      }
      const document = this.load(documentId);
      const validation = validateDocument(document, true);
      if (validation.status === "FAIL") {
        throw new SSSPError(
          "VALIDATION_FAILED",
          "Cannot export invalid canonical document",
          validation,
        );
      }
      return {
        protocol: "SSSP",
        source_revision: document.revision,
        source_hash: documentHash(document),
        compiler: "sssp-markdown-exporter/0.3",
        exported_at: utcNow(),
        filename: `${documentId}_r${document.revision}.md`,
        source_uri: `sssp://${documentId}/revisions/${document.revision}`,
        content: exportMarkdown(document),
        validation,
      };
    });
  }

  async commitVersion(
    documentId: string,
    label = "snapshot",
  ): Promise<StoreResult<CommitResult>> {
    return this.result(() =>
      this.ctx.storage.transactionSync(() => {
        const document = this.load(documentId);
        const validation = validateDocument(document, true);
        if (validation.status === "FAIL") {
          throw new SSSPError(
            "VALIDATION_FAILED",
            "Cannot snapshot invalid canonical document",
            validation,
          );
        }
        const normalizedLabel = normalizeDisplayText(
          label,
          "snapshot",
          "label",
          LIMITS.labelLength,
        );
        const hash = documentHash(document);
        const existing = this.ctx.storage.sql
          .exec<SnapshotRow>(
            `SELECT label, snapshot_at FROM versions
             WHERE document_id = ? AND revision = ? AND document_hash = ?`,
            documentId,
            document.revision,
            hash,
          )
          .toArray()[0];
        const snapshotUri = `sssp://${documentId}/versions/r${String(document.revision).padStart(6, "0")}-${hash.slice(7, 19)}`;
        if (existing) {
          return {
            document_id: documentId,
            revision: document.revision,
            document_hash: hash,
            snapshot_uri: snapshotUri,
            label: existing.label,
            snapshot_at: existing.snapshot_at,
            created: false,
            validation,
          };
        }

        const perDocument = this.ctx.storage.sql
          .exec<CountRow>(
            "SELECT COUNT(*) AS count FROM versions WHERE document_id = ?",
            documentId,
          )
          .one().count;
        if (perDocument >= LIMITS.snapshotsPerDocument) {
          throw new SSSPError("SNAPSHOT_QUOTA", "Document reached its snapshot limit", {
            maximum: LIMITS.snapshotsPerDocument,
          });
        }
        const snapshotJson = canonicalJson(document);
        const storedBytes = this.ctx.storage.sql
          .exec<BytesRow>(
            "SELECT COALESCE(SUM(length(CAST(snapshot_json AS BLOB))), 0) AS bytes FROM versions",
          )
          .one().bytes;
        if (storedBytes + new TextEncoder().encode(snapshotJson).byteLength > LIMITS.snapshotBytes) {
          throw new SSSPError("SNAPSHOT_QUOTA", "The anonymous public workspace snapshot quota is full", {
            maximum: LIMITS.snapshotBytes,
          });
        }
        const snapshotAt = utcNow();
        this.ctx.storage.sql.exec(
          `INSERT INTO versions
           (document_id, revision, document_hash, label, snapshot_at, snapshot_json)
           VALUES (?, ?, ?, ?, ?, ?)`,
          documentId,
          document.revision,
          hash,
          normalizedLabel,
          snapshotAt,
          snapshotJson,
        );
        this.audit(document, "commit_version", "anonymous-assistant", {
          label: normalizedLabel,
          snapshot_uri: snapshotUri,
        });
        return {
          document_id: documentId,
          revision: document.revision,
          document_hash: hash,
          snapshot_uri: snapshotUri,
          label: normalizedLabel,
          snapshot_at: snapshotAt,
          created: true,
          validation,
        };
      }),
    );
  }
}
