#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))
from sssp_core import SSSPStore

store = SSSPStore(ROOT / 'data')
doc_id = 'demo-paper'
try:
    store.create_document(doc_id, 'SSSP Demo：Source First 學術文件', actor='demo')
except Exception:
    pass
doc = store.load(doc_id)
if not doc['nodes']:
    store.append_node(doc_id, {'id':'h1','type':'heading','level':2,'content':'核心命題'}, expected_revision=0, actor='demo')
    store.append_node(doc_id, {'id':'p1','type':'paragraph','content':'渲染結果只是衍生 view；canonical source 由 typed nodes 保存。'}, expected_revision=1, actor='demo')
    store.append_node(doc_id, {'id':'eq1','type':'math_block','latex':r'\boxed{\text{Canonical Source}\rightarrow\text{Validation}\rightarrow\text{Rendered View}}'}, expected_revision=2, actor='demo')
store.export_document(doc_id)
store.commit_version(doc_id, 'demo-ready')
print(store.summary(store.load(doc_id)))
