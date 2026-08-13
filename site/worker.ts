import { createMcpHandler } from "agents/mcp/server";

import { createSSSPServer } from "../src/worker/mcp";
import { SERVICE_VERSION } from "../src/worker/protocol";

export { SSSPStore } from "../src/worker/store";

const PUBLIC_MCP_WARNING =
  "Unauthenticated shared research instance. Do not submit secrets, personal data, private drafts, or confidential material.";
const MAX_MCP_REQUEST_BYTES = 2 * 1024 * 1024;

const SECURITY_HEADERS = {
  "Content-Security-Policy": [
    "default-src 'self'",
    "base-uri 'self'",
    "connect-src 'self'",
    "font-src 'self' https://fonts.gstatic.com",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "img-src 'self' data:",
    "object-src 'none'",
    "script-src 'self'",
    "style-src 'self' https://fonts.googleapis.com",
    "upgrade-insecure-requests",
  ].join("; "),
  "Cross-Origin-Opener-Policy": "same-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
} as const;

const ALLOWED_ORIGIN_HOSTNAMES = [
  "chatgpt.com",
  "www.chatgpt.com",
  "chat.openai.com",
  "platform.openai.com",
  "claude.ai",
  "www.claude.ai",
  "sssp.evemisslab.com",
  "localhost",
  "127.0.0.1",
];

function withSecurityHeaders(response: Response, cacheControl?: string): Response {
  const headers = new Headers(response.headers);
  for (const [name, value] of Object.entries(SECURITY_HEADERS)) {
    headers.set(name, value);
  }
  if (cacheControl) headers.set("Cache-Control", cacheControl);
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

function json(value: unknown, status = 200, cacheControl = "public, max-age=60"): Response {
  return withSecurityHeaders(
    new Response(JSON.stringify(value, null, 2), {
      status,
      headers: { "Content-Type": "application/json; charset=utf-8" },
    }),
    cacheControl,
  );
}

function trustedMcpHostname(hostname: string): boolean {
  return (
    hostname === "sssp.evemisslab.com" ||
    hostname === "localhost" ||
    hostname === "127.0.0.1" ||
    /^sssp-evemisslab\.[a-z0-9-]+\.workers\.dev$/.test(hostname)
  );
}

function canonicalMcpRequest(request: Request): Request {
  const url = new URL(request.url);
  if (url.pathname !== "/mcp/") return request;
  url.pathname = "/mcp";
  return new Request(url, request);
}

async function enforceMcpBodyLimit(request: Request): Promise<Request | Response> {
  if (request.method !== "POST" || request.body === null) return request;

  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > MAX_MCP_REQUEST_BYTES) {
        await reader.cancel("MCP request body exceeds 2 MiB");
        return json({ error: "MCP request body exceeds 2 MiB" }, 413, "no-store");
      }
      chunks.push(value);
    }
  } catch {
    return json({ error: "Unable to read MCP request body" }, 400, "no-store");
  }

  const body = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    body.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return new Request(request, { body });
}

async function handleMcp(
  request: Request,
  env: Env,
  ctx: ExecutionContext,
): Promise<Response> {
  const normalizedRequest = canonicalMcpRequest(request);
  const url = new URL(normalizedRequest.url);
  if (!trustedMcpHostname(url.hostname)) {
    return json({ error: "Untrusted MCP Host header" }, 421, "no-store");
  }

  if (normalizedRequest.method !== "OPTIONS") {
    const contentLength = normalizedRequest.headers.get("content-length");
    if (contentLength !== null) {
      const bytes = Number(contentLength);
      if (!Number.isFinite(bytes) || bytes < 0) {
        return json({ error: "Invalid Content-Length" }, 400, "no-store");
      }
      if (bytes > MAX_MCP_REQUEST_BYTES) {
        return json({ error: "MCP request body exceeds 2 MiB" }, 413, "no-store");
      }
    }
    const { success } = await env.MCP_RATE_LIMITER.limit({ key: "anonymous-public-mcp" });
    if (!success) {
      const response = json(
        { error: "Public MCP request limit exceeded; retry later" },
        429,
        "no-store",
      );
      response.headers.set("Retry-After", "60");
      return response;
    }
  }

  const boundedRequest = await enforceMcpBodyLimit(normalizedRequest);
  if (boundedRequest instanceof Response) return boundedRequest;

  const handler = createMcpHandler(() => createSSSPServer(env), {
    route: "/mcp",
    legacy: "stateless",
    responseMode: "auto",
    allowedHostnames: [url.hostname],
    allowedOriginHostnames: ALLOWED_ORIGIN_HOSTNAMES,
    corsOptions: {
      origin: "*",
      methods: "GET, POST, DELETE, OPTIONS",
      headers:
        "Content-Type, Accept, Authorization, MCP-Protocol-Version, MCP-Session-Id, Last-Event-ID",
      exposeHeaders: "MCP-Session-Id",
      maxAge: 86_400,
    },
    onerror(error) {
      console.error(
        JSON.stringify({
          message: "MCP handler error",
          error: error.message,
          method: normalizedRequest.method,
          path: url.pathname,
        }),
      );
    },
  });
  const response = await handler(boundedRequest, env, ctx);
  return withSecurityHeaders(response, "no-store");
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/mcp" || url.pathname === "/mcp/") {
      return handleMcp(request, env, ctx);
    }

    if (url.pathname === "/healthz") {
      return json({
        ok: true,
        service: "sssp-public-site-and-mcp",
        version: SERVICE_VERSION,
        mode: "public-unauthenticated-mcp",
        transport: "streamable-http",
        storage: "durable-object-sqlite",
      });
    }

    if (url.pathname === "/.well-known/sssp.json") {
      return json({
        protocol: "SSSP",
        title: "Structured Scholarly Source Protocol",
        version: SERVICE_VERSION,
        status: "research-mvp",
        site: "https://sssp.evemisslab.com/",
        repository: "https://github.com/kakon77777-commits/SSSP",
        public_mcp_endpoint: "https://sssp.evemisslab.com/mcp",
        authentication: "none",
        transport: "streamable-http",
        warning: PUBLIC_MCP_WARNING,
      });
    }

    const response = await env.ASSETS.fetch(request);
    return withSecurityHeaders(response);
  },
} satisfies ExportedHandler<Env>;
