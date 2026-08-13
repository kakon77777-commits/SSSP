import { describe, expect, it } from "vitest";

import {
  createDocument,
  exportMarkdown,
  normalizeNode,
  validateDocument,
} from "../src/worker/core";

describe("Cloudflare SSSP canonical core", () => {
  it("accepts a valid MathJax node and exports from canonical source", () => {
    const document = createDocument("worker-paper", "Worker paper");
    document.nodes.push(
      normalizeNode(
        { id: "eq-1", type: "math_block", latex: String.raw`\forall x\in X,\;P(x)` },
        "test",
        "valid equation",
      ),
    );
    document.revision = 1;

    const report = validateDocument(document, true);
    expect(report.status).toBe("PASS");
    expect(report.render_math_checked).toBe(1);
    expect(exportMarkdown(document)).toContain(String.raw`\forall x\in X,\;P(x)`);
    expect(exportMarkdown(document)).toContain("SSSP source revision: 1");
  });

  it("rejects invisible and structurally damaged canonical source", () => {
    const document = createDocument("damaged-paper", "Damaged paper");
    document.nodes.push(
      normalizeNode(
        { id: "pua", type: "paragraph", content: "Run\uE020" },
        "test",
        "damage fixture",
      ),
      normalizeNode(
        { id: "brace", type: "math_block", latex: String.raw`\boxed{\forall x` },
        "test",
        "damage fixture",
      ),
    );
    document.revision = 2;

    const report = validateDocument(document, false);
    expect(report.status).toBe("FAIL");
    expect(report.issues.map((entry) => entry.code)).toEqual(
      expect.arrayContaining(["PUA_CHAR", "UNBALANCED_BRACES"]),
    );
  });
});
