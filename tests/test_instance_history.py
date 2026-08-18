from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import instance_history as history
from deterministic_contract import ContractError

EXAMPLE = ROOT / "examples" / "instances" / "synthetic-instance-history.json"
SCHEMA = ROOT / "schema" / "concap-instance-history.schema.json"


def rehash(value: dict) -> dict:
    predecessor = None
    for index, snapshot in enumerate(value["snapshots"]):
        snapshot["sequence"] = index + 1
        snapshot["predecessor_snapshot_id"] = predecessor
        snapshot["snapshot_id"] = history.digest(history.snapshot_body(snapshot))
        predecessor = snapshot["snapshot_id"]
    value["history_id"] = history.digest(history.history_body(value))
    return value


class InstanceHistoryTests(unittest.TestCase):
    def setUp(self):
        self.value = history.load_json(EXAMPLE, history.PREFIX)

    def test_synthetic_history_validates_without_claiming_real_execution(self):
        report = history.validation_report(self.value)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["record_class"], "synthetic-conformance")
        self.assertEqual(report["snapshot_count"], 2)
        counts = {item["role_id"]: item["accepted_instances"] for item in report["role_history_counts"]}
        self.assertEqual(counts["concap.identity.core/1"], 2)
        self.assertIn("INSTANCE_HISTORY != CAPSULE_BYTES", report["boundaries"])

    def test_snapshot_and_history_hashes_are_acyclic(self):
        checked = history.validate_history(self.value)
        for snapshot in checked["snapshots"]:
            self.assertEqual(snapshot["snapshot_id"], history.digest(history.snapshot_body(snapshot)))
        self.assertEqual(checked["history_id"], history.digest(history.history_body(checked)))

    def test_historical_instances_of_same_role_are_preserved(self):
        checked = history.validate_history(self.value)
        identities = [
            next(item for item in snapshot["instances"] if item["role_id"] == "concap.identity.core/1")["capsule_sha256"]
            for snapshot in checked["snapshots"]
        ]
        self.assertEqual(len(identities), 2)
        self.assertNotEqual(identities[0], identities[1])

    def test_append_only_extension_passes(self):
        base = copy.deepcopy(self.value)
        base["snapshots"] = base["snapshots"][:1]
        rehash(base)
        report = history.check_append_only(base, self.value)
        self.assertEqual(report["appended_snapshot_count"], 1)

    def test_valid_rewrite_of_accepted_prefix_is_rejected(self):
        candidate = copy.deepcopy(self.value)
        candidate["snapshots"][0]["source_commit"] = "f" * 40
        rehash(candidate)
        with self.assertRaisesRegex(ContractError, "E_INSTANCE_APPEND_MUTATION"):
            history.check_append_only(self.value, candidate)

    def test_truncation_is_rejected(self):
        candidate = copy.deepcopy(self.value)
        candidate["snapshots"] = candidate["snapshots"][:1]
        rehash(candidate)
        with self.assertRaisesRegex(ContractError, "E_INSTANCE_APPEND_TRUNCATION"):
            history.check_append_only(self.value, candidate)

    def test_false_fixed_point_claim_is_rejected(self):
        changed = copy.deepcopy(self.value)
        changed["snapshots"][0]["instances"][0]["fixed_point_verified"] = False
        rehash(changed)
        with self.assertRaisesRegex(ContractError, "E_INSTANCE_FIXED_POINT"):
            history.validate_history(changed)

    def test_unregistered_role_is_rejected(self):
        changed = copy.deepcopy(self.value)
        changed["snapshots"][0]["instances"][0]["role_id"] = "concap.not.registered/1"
        rehash(changed)
        with self.assertRaisesRegex(ContractError, "E_INSTANCE_UNKNOWN_ROLE"):
            history.validate_history(changed)

    def test_capsule_metadata_conflict_is_rejected(self):
        changed = copy.deepcopy(self.value)
        second = changed["snapshots"][0]["instances"][1]
        second["capsule_name"] = "identity.dat"
        rehash(changed)
        with self.assertRaisesRegex(ContractError, "E_INSTANCE_CAPSULE_CONFLICT"):
            history.validate_history(changed)

    def test_schema_is_closed_and_marks_synthetic_records(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("record_class", schema["required"])
        self.assertEqual(
            schema["properties"]["record_class"]["enum"],
            ["accepted-private-metadata", "synthetic-conformance"],
        )
        self.assertFalse(schema["$defs"]["snapshot"]["additionalProperties"])
        self.assertFalse(schema["$defs"]["instance"]["additionalProperties"])

    def test_duplicate_json_members_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text('{"protocol":"x","protocol":"y"}', encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "E_INSTANCE_JSON_DUPLICATE"):
                history.load_json(path, history.PREFIX)


if __name__ == "__main__":
    unittest.main()
