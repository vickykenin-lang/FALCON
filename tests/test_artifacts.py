import tempfile, unittest
from dataclasses import replace
from artifacts.store import ArtifactStore

class ArtifactStoreTests(unittest.TestCase):
    def test_round_trip_and_content_addressing(self):
        with tempfile.TemporaryDirectory() as d:
            store=ArtifactStore(d); ref=store.put_text("Falcon evidence","execution")
            self.assertEqual(store.get_text(ref),"Falcon evidence")
            self.assertTrue(ref.uri.endswith(ref.sha256)); self.assertEqual(ref.size_bytes,len(b"Falcon evidence"))
    def test_rejects_malformed_digest_uri(self):
        with tempfile.TemporaryDirectory() as d:
            store=ArtifactStore(d); ref=store.put_text("x","execution")
            with self.assertRaisesRegex(ValueError,"invalid_artifact_digest"):
                store.get_bytes(replace(ref,uri="artifact://sha256/../../escape"))
    def test_rejects_reference_digest_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            store=ArtifactStore(d); ref=store.put_text("x","execution")
            with self.assertRaisesRegex(ValueError,"artifact_reference_mismatch"):
                store.get_bytes(replace(ref,sha256="0"*64))
    def test_rejects_bad_metadata_and_data_types(self):
        with tempfile.TemporaryDirectory() as d:
            store=ArtifactStore(d)
            with self.assertRaisesRegex(ValueError,"owner_module_required"): store.put_bytes(b"x","")
            with self.assertRaisesRegex(ValueError,"media_type_required"): store.put_bytes(b"x","execution","")
            with self.assertRaisesRegex(TypeError,"artifact_data_must_be_bytes"): store.put_bytes("x","execution")
    def test_detects_tampered_content(self):
        with tempfile.TemporaryDirectory() as d:
            store=ArtifactStore(d); ref=store.put_text("original","execution")
            path=store.backend._path(ref.sha256); path.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError,"artifact_integrity_failure"): store.get_bytes(ref)
if __name__=="__main__": unittest.main()
