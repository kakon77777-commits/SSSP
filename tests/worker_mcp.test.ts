import { exports } from "cloudflare:workers";
import { env, evictDurableObject } from "cloudflare:test";
import { describe, expect, it } from "vitest";

interface JsonRpcResponse {
  jsonrpc: "2.0";
  id?: number;
  result?: Record<string, unknown>;
  error?: Record<string, unknown>;
}

async function parseMcpResponse(response: Response): Promise<JsonRpcResponse | undefined> {
  const text = await response.text();
  if (!text) return undefined;
  if (response.headers.get("content-type")?.includes("text/event-stream")) {
    const data = text
      .split(/\r?\n/)
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trim())
      .find((line) => line.length > 0);
    return data ? (JSON.parse(data) as JsonRpcResponse) : undefined;
  }
  return JSON.parse(text) as JsonRpcResponse;
}

async function postMcp(
  payload: Record<string, unknown>,
  protocolVersion?: string,
  origin = "https://chatgpt.com",
): Promise<{ response: Response; body: JsonRpcResponse | undefined }> {
  const headers = new Headers({
    Accept: "application/json, text/event-stream",
    "Content-Type": "application/json",
    Host: "sssp.evemisslab.com",
    Origin: origin,
  });
  if (protocolVersion) headers.set("MCP-Protocol-Version", protocolVersion);
  const response = await exports.default.fetch(
    new Request("https://sssp.evemisslab.com/mcp", {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    }),
  );
  return { response, body: await parseMcpResponse(response) };
}

function toolValue(body: JsonRpcResponse | undefined): Record<string, unknown> {
  const result = body?.result;
  expect(result).toBeDefined();
  expect(result?.isError).not.toBe(true);
  const value = result?.structuredContent;
  expect(value).toBeTypeOf("object");
  return value as Record<string, unknown>;
}

async function callTool(
  id: number,
  name: string,
  args: Record<string, unknown>,
): Promise<JsonRpcResponse | undefined> {
  const { response, body } = await postMcp(
    {
      jsonrpc: "2.0",
      id,
      method: "tools/call",
      params: { name, arguments: args },
    },
    "2025-11-25",
  );
  expect(response.status).toBe(200);
  return body;
}

describe("public Streamable HTTP MCP", () => {
  it("advertises the live unauthenticated endpoint", async () => {
    const health = await exports.default.fetch(
      new Request("https://sssp.evemisslab.com/healthz"),
    );
    expect(health.status).toBe(200);
    await expect(health.json()).resolves.toMatchObject({
      ok: true,
      mode: "public-unauthenticated-mcp",
      storage: "durable-object-sqlite",
    });

    const discovery = await exports.default.fetch(
      new Request("https://sssp.evemisslab.com/.well-known/sssp.json"),
    );
    await expect(discovery.json()).resolves.toMatchObject({
      public_mcp_endpoint: "https://sssp.evemisslab.com/mcp",
      authentication: "none",
      transport: "streamable-http",
    });
  });

  it("persists a canonical workflow across stateless MCP requests", async () => {
    const documentId = `mcp-${crypto.randomUUID()}`;

    const initialized = await postMcp({
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: {
        protocolVersion: "2025-11-25",
        capabilities: {},
        clientInfo: { name: "vitest", version: "1.0" },
      },
    });
    expect(initialized.response.status, JSON.stringify(initialized.body)).toBe(200);
    expect(initialized.body?.result).toMatchObject({ protocolVersion: "2025-11-25" });

    const toolsResponse = await postMcp(
      { jsonrpc: "2.0", id: 2, method: "tools/list", params: {} },
      "2025-11-25",
    );
    const tools = toolsResponse.body?.result?.tools as Array<{ name: string }>;
    expect(tools.map((tool) => tool.name)).toEqual(
      expect.arrayContaining([
        "sssp.create_document",
        "sssp.append_node",
        "sssp.replace_node",
        "sssp.read_node",
        "sssp.validate_document",
        "sssp.export_document",
        "sssp.commit_version",
      ]),
    );

    const created = toolValue(
      await callTool(3, "sssp.create_document", {
        document_id: documentId,
        title: "Persistent MCP paper",
      }),
    );
    expect(created).toMatchObject({ document_id: documentId, revision: 0, node_count: 0 });

    const appended = toolValue(
      await callTool(4, "sssp.append_node", {
        document_id: documentId,
        expected_revision: 0,
        node: {
          id: "eq-1",
          type: "math_block",
          latex: String.raw`\forall x\in X,\;P(x)\Rightarrow Q(x)`,
        },
      }),
    );
    expect(appended).toMatchObject({
      document_id: documentId,
      revision: 1,
      validation: { status: "PASS", render_math_checked: 1 },
    });
    const appendedChecksum = (appended.node as { checksum: string }).checksum;
    expect(appendedChecksum).toMatch(/^sha256:[0-9a-f]{64}$/);

    const validated = toolValue(
      await callTool(5, "sssp.validate_document", { document_id: documentId }),
    );
    expect(validated).toMatchObject({ status: "PASS", render_math_checked: 1 });

    await evictDurableObject(env.SSSP_STORE.getByName("public-v1"));

    const read = toolValue(
      await callTool(6, "sssp.read_node", { document_id: documentId, node_id: "eq-1" }),
    );
    expect(read).toMatchObject({
      document_id: documentId,
      revision: 1,
      node: { id: "eq-1", type: "math_block" },
    });

    const replaced = toolValue(
      await callTool(7, "sssp.replace_node", {
        document_id: documentId,
        node_id: "eq-1",
        expected_revision: 1,
        expected_checksum: appendedChecksum,
        replacement: {
          type: "math_block",
          latex: String.raw`\boxed{\forall x\in X,\;P(x)\Rightarrow Q(x)}`,
        },
      }),
    );
    expect(replaced).toMatchObject({
      document_id: documentId,
      revision: 2,
      previous_checksum: appendedChecksum,
      node: { id: "eq-1", type: "math_block" },
      validation: { status: "PASS", render_math_checked: 1 },
    });

    const exported = toolValue(
      await callTool(8, "sssp.export_document", {
        document_id: documentId,
        format: "markdown",
      }),
    );
    expect(exported.content).toContain("SSSP source revision: 2");
    expect(exported.content).toContain(String.raw`\boxed{\forall x\in X`);
    expect(exported.source_uri).toBe(`sssp://${documentId}/revisions/2`);

    const committed = toolValue(
      await callTool(9, "sssp.commit_version", { document_id: documentId, label: "vitest" }),
    );
    expect(committed).toMatchObject({ document_id: documentId, revision: 2, created: true });

    const committedAgain = toolValue(
      await callTool(10, "sssp.commit_version", { document_id: documentId, label: "ignored" }),
    );
    expect(committedAgain).toMatchObject({
      document_id: documentId,
      revision: 2,
      created: false,
      label: "vitest",
    });
  });

  it("rejects untrusted browser Origins", async () => {
    const { response } = await postMcp(
      { jsonrpc: "2.0", id: 50, method: "tools/list", params: {} },
      "2025-11-25",
      "https://evil.example",
    );
    expect(response.status).toBe(403);
  });

  it("enforces the real body size when Content-Length is misleading", async () => {
    const response = await exports.default.fetch(
      new Request("https://sssp.evemisslab.com/mcp", {
        method: "POST",
        headers: {
          Accept: "application/json, text/event-stream",
          "Content-Length": "1",
          "Content-Type": "application/json",
          Host: "sssp.evemisslab.com",
          Origin: "https://chatgpt.com",
        },
        body: "x".repeat(2 * 1024 * 1024 + 1),
      }),
    );
    expect(response.status).toBe(413);
    await expect(response.json()).resolves.toMatchObject({
      error: "MCP request body exceeds 2 MiB",
    });
  });
});
