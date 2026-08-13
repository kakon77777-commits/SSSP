import { McpServer, type CallToolResult } from "@modelcontextprotocol/server";
import { z } from "zod";

import { LIMITS } from "./core";
import { NODE_TYPES, SERVICE_VERSION, type StoreErrorPayload, type StoreResult } from "./protocol";

const documentIdSchema = z
  .string()
  .regex(/^[A-Za-z0-9._-]{1,128}$/)
  .describe("Stable SSSP document ID; 1-128 ASCII letters, digits, dot, underscore, or hyphen.");
const nodeIdSchema = z
  .string()
  .regex(/^[A-Za-z0-9._-]{1,128}$/)
  .describe("Stable node ID; 1-128 ASCII letters, digits, dot, underscore, or hyphen.");
const checksumSchema = z.string().regex(/^sha256:[0-9a-f]{64}$/);
const actorSchema = z
  .string()
  .min(1)
  .max(LIMITS.actorLength)
  .optional()
  .describe("Optional, unverified provenance display label. This public server does not authenticate it.");
const reasonSchema = z.string().min(1).max(LIMITS.reasonLength).optional();

const nodeInputSchema = z.looseObject({
  id: nodeIdSchema,
  type: z.enum(NODE_TYPES),
  content: z.string().max(LIMITS.nodeTextLength).optional(),
  latex: z.string().max(LIMITS.mathTextLength).optional(),
  level: z.number().int().min(1).max(6).optional(),
  label: z.string().max(1_000).optional(),
  language: z.string().max(64).optional(),
  claim: z.record(z.string(), z.unknown()).optional(),
});

const nodeOutputSchema = z.looseObject({
  id: nodeIdSchema,
  type: z.enum(NODE_TYPES),
  content: z.string().optional(),
  latex: z.string().optional(),
  created_at: z.string(),
  updated_at: z.string(),
  provenance: z.object({ actor: z.string(), reason: z.string() }),
  checksum: checksumSchema,
});

const issueSchema = z.object({
  level: z.enum(["FAIL", "WARN"]),
  code: z.string(),
  message: z.string(),
  node_id: z.string().optional(),
});

const validationSchema = z.object({
  status: z.enum(["PASS", "WARN", "FAIL"]),
  issue_count: z.number().int().nonnegative(),
  issues: z.array(issueSchema),
  render_math_checked: z.number().int().nonnegative(),
  render_notes: z.array(z.string()),
  document_hash: checksumSchema,
});

const summarySchema = z.object({
  document_id: documentIdSchema,
  title: z.string(),
  revision: z.number().int().nonnegative(),
  node_count: z.number().int().nonnegative(),
  document_hash: checksumSchema,
});

const appendOutputSchema = summarySchema.extend({
  node: nodeOutputSchema,
  validation: validationSchema,
});

const replaceOutputSchema = appendOutputSchema.extend({
  previous_checksum: checksumSchema,
});

const PUBLIC_WARNING =
  "This is a shared, unauthenticated public research instance. Never store secrets, personal data, private drafts, credentials, or confidential material. Anyone who knows a document_id can attempt to read or change its nodes.";

function renderJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function toolSuccess<T extends object>(value: T): CallToolResult {
  return {
    content: [{ type: "text", text: renderJson(value) }],
    structuredContent: value,
  };
}

function toolError(error: StoreErrorPayload): CallToolResult {
  return {
    content: [{ type: "text", text: renderJson(error) }],
    isError: true,
  };
}

function toolResult<T extends object>(result: StoreResult<T>): CallToolResult {
  return result.ok ? toolSuccess(result.value) : toolError(result.error);
}

const writeAnnotations = {
  readOnlyHint: false,
  destructiveHint: false,
  idempotentHint: false,
  openWorldHint: false,
} as const;

const readAnnotations = {
  readOnlyHint: true,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: false,
} as const;

export function createSSSPServer(env: Env): McpServer {
  const server = new McpServer(
    {
      name: "sssp-mcp",
      title: "SSSP Scholarly Source Server",
      version: SERVICE_VERSION,
    },
    {
      instructions:
        `Use these tools to maintain canonical Structured Scholarly Source Protocol documents. ` +
        `Rendered chat or Markdown is never the source of truth. ${PUBLIC_WARNING}`,
    },
  );
  const store = env.SSSP_STORE.getByName("public-v1");

  server.registerTool(
    "sssp.create_document",
    {
      title: "Create SSSP Document",
      description: `Create a canonical document in the shared public SSSP workspace. ${PUBLIC_WARNING}`,
      inputSchema: z.object({
        document_id: documentIdSchema,
        title: z.string().min(1).max(LIMITS.titleLength),
        actor: actorSchema,
      }),
      outputSchema: summarySchema,
      annotations: writeAnnotations,
    },
    async ({ document_id, title, actor }) =>
      toolResult(await store.createDocument(document_id, title, actor)),
  );

  server.registerTool(
    "sssp.append_node",
    {
      title: "Append SSSP Node",
      description:
        "Append one typed canonical node, run structural and MathJax validation, and commit atomically to the shared public workspace.",
      inputSchema: z.object({
        document_id: documentIdSchema,
        node: nodeInputSchema,
        expected_revision: z.number().int().nonnegative().optional(),
        actor: actorSchema,
        reason: reasonSchema,
      }),
      outputSchema: appendOutputSchema,
      annotations: writeAnnotations,
    },
    async ({ document_id, node, expected_revision, actor, reason }) =>
      toolResult(
        await store.appendNode(document_id, node, expected_revision, actor, reason),
      ),
  );

  server.registerTool(
    "sssp.replace_node",
    {
      title: "Replace SSSP Node",
      description:
        "Replace one canonical node with revision and checksum conflict protection. This changes existing public workspace content.",
      inputSchema: z.object({
        document_id: documentIdSchema,
        node_id: nodeIdSchema,
        replacement: nodeInputSchema.omit({ id: true }),
        expected_revision: z.number().int().nonnegative().optional(),
        expected_checksum: checksumSchema.optional(),
        actor: actorSchema,
        reason: reasonSchema,
      }),
      outputSchema: replaceOutputSchema,
      annotations: { ...writeAnnotations, destructiveHint: true },
    },
    async ({
      document_id,
      node_id,
      replacement,
      expected_revision,
      expected_checksum,
      actor,
      reason,
    }) =>
      toolResult(
        await store.replaceNode(
          document_id,
          node_id,
          replacement,
          expected_revision,
          expected_checksum,
          actor,
          reason,
        ),
      ),
  );

  server.registerTool(
    "sssp.read_node",
    {
      title: "Read SSSP Node",
      description:
        "Read one canonical node by document_id and node_id without using a rendered export.",
      inputSchema: z.object({ document_id: documentIdSchema, node_id: nodeIdSchema }),
      outputSchema: z.object({
        document_id: documentIdSchema,
        revision: z.number().int().nonnegative(),
        node: nodeOutputSchema,
      }),
      annotations: readAnnotations,
    },
    async ({ document_id, node_id }) => toolResult(await store.readNode(document_id, node_id)),
  );

  server.registerTool(
    "sssp.validate_document",
    {
      title: "Validate SSSP Document",
      description:
        "Run structural, Unicode, checksum, and MathJax render validation against canonical source.",
      inputSchema: z.object({ document_id: documentIdSchema }),
      outputSchema: validationSchema,
      annotations: readAnnotations,
    },
    async ({ document_id }) => toolResult(await store.validateDocument(document_id)),
  );

  server.registerTool(
    "sssp.export_document",
    {
      title: "Export SSSP Document",
      description:
        "Compile canonical SSSP source into a derived Markdown view. This does not mutate canonical source.",
      inputSchema: z.object({
        document_id: documentIdSchema,
        format: z.literal("markdown").optional(),
      }),
      outputSchema: z.object({
        protocol: z.literal("SSSP"),
        source_revision: z.number().int().nonnegative(),
        source_hash: checksumSchema,
        compiler: z.string(),
        exported_at: z.string(),
        filename: z.string(),
        source_uri: z.string(),
        content: z.string(),
        validation: validationSchema,
      }),
      annotations: readAnnotations,
    },
    async ({ document_id, format }) =>
      toolResult(await store.exportDocument(document_id, format)),
  );

  server.registerTool(
    "sssp.commit_version",
    {
      title: "Commit SSSP Version",
      description:
        "Create an immutable validated snapshot of the canonical document in the shared public workspace.",
      inputSchema: z.object({
        document_id: documentIdSchema,
        label: z.string().min(1).max(LIMITS.labelLength).optional(),
      }),
      outputSchema: z.object({
        document_id: documentIdSchema,
        revision: z.number().int().nonnegative(),
        document_hash: checksumSchema,
        snapshot_uri: z.string(),
        label: z.string(),
        snapshot_at: z.string(),
        created: z.boolean(),
        validation: validationSchema,
      }),
      annotations: writeAnnotations,
    },
    async ({ document_id, label }) => toolResult(await store.commitVersion(document_id, label)),
  );

  return server;
}
