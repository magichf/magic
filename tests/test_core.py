import json
import tempfile
import unittest
from pathlib import Path

from iac.core import (
    initialize, append_event, verify_store, export_verified, IntegrityError
)


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "store"
        initialize(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_empty_store_verifies(self):
        self.assertTrue(verify_store(self.root)["valid"])

    def test_append_and_checkpoint(self):
        append_event(self.root, "checkpoint", {"task": "portability"})
        self.assertEqual(verify_store(self.root)["events"], 1)

    def test_payload_tampering_is_detected(self):
        append_event(self.root, "note", {"value": 1})
        path = self.root / "events.jsonl"
        event = json.loads(path.read_text(encoding="utf-8"))
        event["payload"]["value"] = 2
        path.write_text(json.dumps(event) + "\n", encoding="utf-8")
        with self.assertRaises(IntegrityError):
            verify_store(self.root)

    def test_deleted_event_is_detected_by_checkpoint(self):
        append_event(self.root, "note", {"value": 1})
        (self.root / "events.jsonl").write_text("", encoding="utf-8")
        with self.assertRaises(IntegrityError):
            verify_store(self.root)

    def test_corrupt_state_is_rejected(self):
        (self.root / "state.json").write_text("{broken", encoding="utf-8")
        with self.assertRaises(IntegrityError):
            verify_store(self.root)

    def test_export_is_independently_verified(self):
        append_event(self.root, "checkpoint", {"n": 1})
        destination = Path(self.temp.name) / "portable-copy"
        self.assertEqual(verify_store(self.root), export_verified(self.root, destination))

    def test_initializer_refuses_overwrite(self):
        with self.assertRaises(FileExistsError):
            initialize(self.root)


if __name__ == "__main__":
    unittest.main()
