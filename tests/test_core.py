import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from sssp_core import SSSPError, SSSPStore


def main():
    td = tempfile.mkdtemp(prefix="sssp-core-test-")
    try:
        s = SSSPStore(td)
        created = s.create_document("paper-test", "測試論文")
        assert created["revision"] == 0
        r1 = s.append_node("paper-test", {"id":"p1","type":"paragraph","content":"這是一段正文。"}, expected_revision=0)
        assert r1["revision"] == 1
        r2 = s.append_node("paper-test", {"id":"eq1","type":"math_block","latex":r"\forall x\in X,\; P(x)\Rightarrow Q(x)"}, expected_revision=1)
        assert r2["revision"] == 2
        assert r2["validation"]["status"] in {"PASS","WARN"}
        node = s.read_node("paper-test", "eq1")["node"]
        r3 = s.replace_node("paper-test", "eq1", {"type":"math_block","latex":r"\boxed{\forall x\in X,\;P(x)}"}, expected_revision=2, expected_checksum=node["checksum"])
        assert r3["revision"] == 3
        try:
            s.replace_node("paper-test", "eq1", {"type":"math_block","latex":"x"}, expected_revision=2)
            raise AssertionError("revision conflict was not detected")
        except SSSPError as e:
            assert e.code == "REVISION_CONFLICT"
        v = s.validate_document("paper-test")
        assert v["status"] in {"PASS","WARN"}
        ex = s.export_document("paper-test")
        assert Path(ex["path"]).exists()
        snap = s.commit_version("paper-test", "test")
        assert Path(snap["snapshot"]).exists()
        print(json.dumps({"ok": True, "validation": v["status"], "export": ex["path"], "snapshot": snap["snapshot"]}, ensure_ascii=False, indent=2))
    finally:
        shutil.rmtree(td, ignore_errors=True)

if __name__ == "__main__":
    main()
