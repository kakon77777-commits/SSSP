import copy
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from sssp_core import node_checksum, validate_document_obj, utc_now


def doc_with(node):
    n = copy.deepcopy(node)
    now = utc_now()
    n.setdefault("created_at", now)
    n.setdefault("updated_at", now)
    n.setdefault("provenance", {"actor":"fixture","reason":"damage regression"})
    n["checksum"] = node_checksum(n)
    return {
        "protocol":"SSSP", "version":"0.1", "document_id":"fixture", "title":"fixture", "revision":0,
        "created_at":now, "updated_at":now, "nodes":[n],
        "semantic_ledger":{"terms":{},"deprecated_terms":{},"symbols":{}}, "claim_ledger":{}
    }


def codes(report):
    return {x["code"] for x in report["issues"]}


def main():
    # I: \b decoded to actual backspace, leaving 'oxed'.
    r = validate_document_obj(doc_with({"id":"i1","type":"math_block","latex":"\x08oxed{x}"}), render_math=False)
    assert r["status"] == "FAIL" and "CONTROL_CHAR" in codes(r)

    # J: PUA marker from rendered DOM.
    r = validate_document_obj(doc_with({"id":"j1","type":"paragraph","content":"Run0\ue020"}), render_math=False)
    assert r["status"] == "FAIL" and "PUA_CHAR" in codes(r)

    # J: zero-width marker indicating flattened subscript.
    r = validate_document_obj(doc_with({"id":"j2","type":"paragraph","content":"Run\u200b0"}), render_math=False)
    assert r["status"] == "FAIL" and "ZERO_WIDTH" in codes(r)

    # Structural brace corruption.
    r = validate_document_obj(doc_with({"id":"h1","type":"math_block","latex":r"\boxed{\forall x"}), render_math=False)
    assert r["status"] == "FAIL" and "UNBALANCED_BRACES" in codes(r)

    # Canonical math should not contain markdown delimiter.
    r = validate_document_obj(doc_with({"id":"d1","type":"math_block","latex":"$x+y$"}), render_math=False)
    assert r["status"] == "WARN" and "MATH_DELIMITER_IN_CANONICAL" in codes(r)

    # Silent \n corruption signature: a normal newline + 'eg'.
    r = validate_document_obj(doc_with({"id":"i2","type":"math_block","latex":r"P(x)\\Rightarrow\neg P(x)\neg P(x)"}), render_math=False)
    # sanity: legitimate source shouldn't be flagged
    assert "ESCAPE_CORRUPTION_RISK" not in codes(r)
    r = validate_document_obj(doc_with({"id":"i3","type":"math_block","latex":"P(x)\\Rightarrow\n  eg P(x)"}), render_math=False)
    assert "ESCAPE_CORRUPTION_RISK" in codes(r)

    print("damage regression fixtures: PASS")

if __name__ == "__main__":
    main()
