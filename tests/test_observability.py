import json,tempfile,unittest
from pathlib import Path
from observability.trace import JsonlTraceExporter,Tracer

class ObservabilityTests(unittest.TestCase):
    def test_parent_child_trace_continuity(self):
        tracer=Tracer(); root=tracer.start("autonomic","mission"); child=tracer.child(root,"execution","tool")
        self.assertEqual(child.context.trace_id,root.context.trace_id); self.assertEqual(child.context.parent_span_id,root.context.span_id)
    def test_sensitive_attributes_are_not_recorded(self):
        tracer=Tracer(); span=tracer.start("brain",attributes={"mission_id":"m1","chain_of_thought":"never","token":"secret"})
        self.assertEqual(span.attributes,{"mission_id":"m1"})
    def test_finish_is_terminal_once(self):
        tracer=Tracer(); span=tracer.start("execution"); tracer.finish(span,"OK")
        with self.assertRaisesRegex(ValueError,"span_already_finished"): tracer.finish(span,"OK")
    def test_invalid_status_is_rejected(self):
        tracer=Tracer(); span=tracer.start("execution")
        with self.assertRaisesRegex(ValueError,"invalid_terminal_trace_status"): tracer.finish(span,"UNKNOWN")
    def test_jsonl_export_contains_structured_context(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"traces.jsonl"; tracer=Tracer([JsonlTraceExporter(str(path))]); span=tracer.start("governance","authorize",attributes={"capability":"test.execute"}); tracer.finish(span,"OK")
            row=json.loads(path.read_text().strip()); self.assertEqual(row["context"]["component"],"governance"); self.assertEqual(row["status"],"OK"); self.assertEqual(row["context"]["contract_version"],"1.0")
if __name__=="__main__": unittest.main()
