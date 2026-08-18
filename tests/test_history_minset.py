from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import history_minset as history

DATASET_PATH = ROOT / "examples" / "history" / "world-history-scaffold.json"
POLICY_PATH = ROOT / "ai" / "history-reconstruction-policy.json"
BASIS_SCHEMA_PATH = ROOT / "schema" / "history-basis.schema.json"


class HistoricalReconstructionTests(unittest.TestCase):
    def setUp(self):
        self.dataset = history.load_json(DATASET_PATH)
        self.policy = history.load_json(POLICY_PATH)

    def test_demo_minimum_is_frozen(self):
        plan = history.plan_minimum(self.dataset, self.policy)
        self.assertEqual(plan["selected_records"], ["cosmic_anchor","biological_anchor","civilization_anchor","exchange_anchor","industrial_anchor","conflict_anchor","digital_anchor"])
        self.assertEqual(plan["selected_record_count"], 7)
        self.assertEqual(plan["candidate_record_count"], 17)
        self.assertEqual(plan["selected_record_bytes"], 1541)
        self.assertEqual(plan["candidate_record_bytes"], 3397)
        self.assertEqual(plan["self_contained_basis_bytes"], 2426)
        self.assertEqual(plan["canonical_dataset_bytes"], 3986)

    def test_plan_is_byte_stable(self):
        self.assertEqual(history.canonical_bytes(history.plan_minimum(self.dataset, self.policy)), history.canonical_bytes(history.plan_minimum(self.dataset, self.policy)))

    def test_plan_hash_is_acyclic(self):
        plan = history.plan_minimum(self.dataset, self.policy)
        claimed = plan.pop("plan_sha256")
        self.assertEqual(claimed, history.digest(plan))

    def test_basis_is_self_contained_and_reconstructs_without_dataset(self):
        basis = history.build_basis(self.dataset, self.policy)
        history.validate_basis(basis)
        reconstruction = history.reconstruct_basis(basis)
        self.assertEqual(reconstruction["dataset_id"], "world_history_scaffold")
        self.assertEqual(len(reconstruction["records"]), 7)
        covered = set()
        for record in reconstruction["records"]:
            covered.update(record["claims"])
        self.assertTrue(set(reconstruction["retention_obligations"]) <= covered)

    def test_basis_hash_detects_mutation(self):
        basis = history.build_basis(self.dataset, self.policy)
        changed = copy.deepcopy(basis)
        changed["records"][0]["summary"] += " changed"
        with self.assertRaisesRegex(history.HistoryError, "E_HISTORY_BASIS_HASH"):
            history.validate_basis(changed)

    def test_unsatisfied_obligation_fails_closed(self):
        dataset = copy.deepcopy(self.dataset)
        dataset["retention_obligations"].append("not_covered")
        with self.assertRaisesRegex(history.HistoryError, "E_HISTORY_UNSATISFIABLE"):
            history.plan_minimum(dataset, self.policy)

    def test_dependency_cycle_fails_closed(self):
        dataset = copy.deepcopy(self.dataset)
        dataset["records"][0]["requires"] = ["digital_anchor"]
        with self.assertRaisesRegex(history.HistoryError, "E_HISTORY_DEPENDENCY_CYCLE"):
            history.plan_minimum(dataset, self.policy)

    def test_long_dependency_chain_is_iterative(self):
        record_count = 1100
        records = []
        for index in range(record_count):
            record_id = f"r{index:04d}"
            records.append({
                "id": record_id,
                "order": index + 1,
                "kind": "anchor",
                "summary": record_id,
                "claims": [f"c{index:04d}"],
                "requires": [] if index == 0 else [f"r{index - 1:04d}"],
            })
        dataset = {
            "protocol": "QSOL-THOTH/HISTORY-DATASET/1",
            "schema_version": "1.0.0",
            "id": "long_dependency_chain",
            "authority": "demonstration-only",
            "retention_obligations": [f"c{record_count - 1:04d}"],
            "records": records,
            "boundaries": list(history.PLAN_BOUNDARIES),
        }
        plan = history.plan_minimum(dataset, self.policy)
        self.assertEqual(plan["selected_record_count"], record_count)
        self.assertEqual(plan["selected_records"][0], "r0000")
        self.assertEqual(plan["selected_records"][-1], f"r{record_count - 1:04d}")

    def test_unhashable_array_elements_fail_with_stable_errors(self):
        cases = []

        bad_obligation = copy.deepcopy(self.dataset)
        bad_obligation["retention_obligations"] = [{"not": "a-token"}]
        cases.append((history.validate_dataset, bad_obligation, "E_HISTORY_OBLIGATIONS"))

        bad_claim = copy.deepcopy(self.dataset)
        bad_claim["records"][0]["claims"] = [["nested"]]
        cases.append((history.validate_dataset, bad_claim, "E_HISTORY_RECORD"))

        bad_boundary = copy.deepcopy(self.dataset)
        bad_boundary["boundaries"].append({"not": "a-boundary"})
        cases.append((history.validate_dataset, bad_boundary, "E_HISTORY_BOUNDARIES"))

        bad_basis = history.build_basis(self.dataset, self.policy)
        bad_basis["retention_obligations"] = [{"not": "a-token"}]
        cases.append((history.validate_basis, bad_basis, "E_HISTORY_BASIS"))

        for validator, value, code in cases:
            with self.subTest(code=code):
                with self.assertRaisesRegex(history.HistoryError, code):
                    validator(value)

    def test_basis_schema_defines_record_items(self):
        schema = history.load_json(BASIS_SCHEMA_PATH)
        record_schema = schema["properties"]["records"]["items"]
        self.assertEqual(record_schema["type"], "object")
        self.assertFalse(record_schema["additionalProperties"])
        self.assertEqual(
            set(record_schema["required"]),
            {"id", "order", "kind", "summary", "claims", "requires"},
        )
        self.assertEqual(record_schema["properties"]["claims"]["items"]["type"], "string")
        self.assertEqual(record_schema["properties"]["requires"]["items"]["type"], "string")

    def test_search_budget_is_deterministic(self):
        policy = copy.deepcopy(self.policy)
        policy["max_search_nodes"] = 1
        with self.assertRaisesRegex(history.HistoryError, "E_HISTORY_SEARCH_LIMIT"):
            history.plan_minimum(self.dataset, policy)

    def test_duplicate_json_members_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"
            path.write_text('{"protocol":"x","protocol":"y"}', encoding="utf-8")
            with self.assertRaisesRegex(history.HistoryError, "E_HISTORY_JSON_DUPLICATE"):
                history.load_json(path)

    def test_boundaries_disclaim_truth_and_verbatim_recovery(self):
        plan = history.plan_minimum(self.dataset, self.policy)
        self.assertIn("SEMANTIC_RECONSTRUCTION != VERBATIM_SOURCE", plan["boundaries"])
        self.assertIn("COVERED_CLAIM != PROVEN_TRUE", plan["boundaries"])


if __name__ == "__main__":
    unittest.main()
