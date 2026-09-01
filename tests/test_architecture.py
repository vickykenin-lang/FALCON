"""Mechanical enforcement of Falcon's replaceable-organ architecture."""
import ast
import unittest
from pathlib import Path

ORGANS={"autonomic","brain","execution","governance","interface","learning","memory","nervous_system","scheduler","senses"}
ROOT=Path(__file__).resolve().parents[1]

class ArchitectureTests(unittest.TestCase):
    def test_organs_do_not_import_other_organ_implementations(self):
        violations=[]
        for organ in ORGANS:
            for path in (ROOT/organ).rglob("*.py"):
                tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
                for node in ast.walk(tree):
                    names=[]
                    if isinstance(node,ast.Import): names=[a.name for a in node.names]
                    elif isinstance(node,ast.ImportFrom) and node.module: names=[node.module]
                    for name in names:
                        target=name.split(".")[0]
                        if target in ORGANS and target!=organ:
                            violations.append(f"{path.relative_to(ROOT)} imports {name}")
        self.assertEqual(violations,[],"Cross-organ implementation imports:\n"+"\n".join(violations))

    def test_composition_root_may_wire_organs(self):
        self.assertTrue((ROOT/"bootstrap.py").exists())

if __name__=="__main__": unittest.main()
