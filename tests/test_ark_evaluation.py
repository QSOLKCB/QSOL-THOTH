from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import ark_evaluation as evaluation
import concap_resolver as resolver
import thoth
from deterministic_contract import ContractError

POLICY = ROOT / "ai" / "ark-evaluation-policy.json"
OBSERVATION = ROOT / "examples" / "evaluation" / "synthetic-clean-room-observation.json"
OBJECT = ROOT / "examples" / "evaluation" / "objects" / "synthetic-portable-object.dat"


class ArkEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.policy = evaluation.load_json(POLICY, evaluation.PREFIX)
        self.observation = evaluation.load_json(OBSERVATION, evaluation.PREFIX)

    def test_policy_validates_without_aggregation(self):
        report = evaluation.policy_validation_report(self.policy)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["aggregation"], "none")
        self.assertEqual(report["dimension_ids"], [item[0] for item in evaluation.DIMENSIONS])

    def test_dimensions_are_measured_separately(self):
        receipt = evaluation.evaluate(self.observation, self.policy)
        self.assertEqual(
            set(receipt["metrics"]),
            {
                "route_sufficiency",
                "route_minimality",
                "style_fidelity",
                "factual_accuracy",
                "historical_reconstruction_coverage",
            },
        )
        self.assertNotIn("score", receipt)
        self.assertNotIn("overall", receipt)
        self.assertEqual(receipt["aggregation"], "none")
        self.assertIn("STYLE_FIDELITY != FACTUAL_ACCURACY != PHYSICAL_TRUTH", receipt["boundaries"])

    def test_receipt_is_deterministic_and_acyclic(self):
        first = evaluation.evaluate(self.observation, self.policy)
        second = evaluation.evaluate(self.observation, self.policy)
        self.assertEqual(evaluation.canonical_bytes(first), evaluation.canonical_bytes(second))
        body = dict(first)
        claimed = body.pop("evaluation_sha256")
        self.assertEqual(claimed, evaluation.digest(body))

    def test_route_sufficiency_and_minimality_do_not_collapse(self):
        changed = copy.deepcopy(self.observation)
        changed["route"]["selected_role_ids"] = ["concap.workstyle.engineering/1"]
        receipt = evaluation.evaluate(changed, self.policy)
        self.assertEqual(receipt["metrics"]["route_sufficiency"]["fraction"], {"numerator": 1, "denominator": 2})
        self.assertEqual(receipt["metrics"]["route_minimality"]["fraction"], {"numerator": 1, "denominator": 1})

        changed = copy.deepcopy(self.observation)
        changed["route"]["selected_role_ids"] = [
            "concap.culture.core/1",
            "concap.identity.core/1",
            "concap.workstyle.engineering/1",
        ]
        receipt = evaluation.evaluate(changed, self.policy)
        self.assertEqual(receipt["metrics"]["route_sufficiency"]["fraction"], {"numerator": 2, "denominator": 2})
        self.assertEqual(receipt["metrics"]["route_minimality"]["fraction"], {"numerator": 2, "denominator": 3})
        self.assertEqual(receipt["metrics"]["route_minimality"]["unjustified_selected_roles"], ["concap.culture.core/1"])

    def test_four_transports_require_byte_identical_observations(self):
        receipt = evaluation.evaluate(self.observation, self.policy)
        self.assertEqual(receipt["transport_equivalence"]["status"], "byte-identical")
        self.assertEqual(receipt["transport_equivalence"]["profiles"], list(evaluation.TRANSPORTS))
        changed = copy.deepcopy(self.observation)
        changed["transports"][2]["objects"][0]["size_bytes"] += 1
        with self.assertRaisesRegex(ContractError, "E_ARK_EVAL_TRANSPORT_MISMATCH"):
            evaluation.evaluate(changed, self.policy)

    def test_clean_room_private_dependencies_fail_closed(self):
        for key in (
            "private_source_repository_access",
            "private_context_connector_access",
            "hidden_provider_memory_dependency",
        ):
            with self.subTest(key=key):
                changed = copy.deepcopy(self.observation)
                changed["clean_room"][key] = True
                with self.assertRaisesRegex(ContractError, "E_ARK_EVAL_CLEAN_ROOM"):
                    evaluation.evaluate(changed, self.policy)

    def test_negative_space_violations_fail_closed(self):
        for check in evaluation.NEGATIVE_CHECKS:
            with self.subTest(check=check):
                changed = copy.deepcopy(self.observation)
                changed["negative_space"][check] = True
                with self.assertRaisesRegex(ContractError, "E_ARK_EVAL_NEGATIVE_SPACE"):
                    evaluation.evaluate(changed, self.policy)

    def test_unassessed_dimensions_are_rejected(self):
        changed = copy.deepcopy(self.observation)
        for item in changed["factual_accuracy"]["claims"]:
            item["outcome"] = "unverified"
        with self.assertRaisesRegex(ContractError, "E_ARK_EVAL_UNASSESSED"):
            evaluation.evaluate(changed, self.policy)

    def test_synthetic_object_receipt_matches_actual_public_bytes(self):
        payload = OBJECT.read_bytes()
        object_id = "sha256:" + hashlib.sha256(payload).hexdigest()
        first = self.observation["transports"][0]["objects"][0]
        self.assertEqual(first["object_id"], object_id)
        self.assertEqual(first["bytes_sha256"], object_id)
        self.assertEqual(first["size_bytes"], len(payload))

    def test_clean_room_resolution_needs_no_source_repository(self):
        decision = thoth.route_request({"protocol": "QSOL-THOTH/ROUTE-REQUEST/1", "intent": "general"})
        self.assertEqual(decision["concaps"], self.observation["route"]["selected_role_ids"])
        obj = self.observation["transports"][0]["objects"][0]
        index_body = {
            "protocol": resolver.OBJECT_INDEX_PROTOCOL,
            "schema_version": "1.0.0",
            "bundle_id": "synthetic_clean_room",
            "bundle_class": "PUBLIC",
            "export_spec_sha256": "sha256:" + "1" * 64,
            "projection_sha256": "sha256:" + "2" * 64,
            "objects": [
                {
                    "object_id": obj["object_id"],
                    "size_bytes": obj["size_bytes"],
                    "media_type": "application/vnd.qsol.restore-dat",
                    "container": "qsol-restore-dat/1",
                    "path": resolver.object_path_for(obj["object_id"]),
                }
            ],
            "role_bindings": [
                {"role_id": role_id, "object_id": obj["object_id"]}
                for role_id in decision["concaps"]
            ],
            "boundaries": list(resolver.INDEX_BOUNDARIES),
        }
        index = {**index_body, "index_id": resolver.digest(index_body)}
        bindings = resolver.load_json(ROOT / "ai" / "concap-source-bindings.json")
        resolution = resolver.resolve(decision, index, bindings)
        self.assertEqual([item["object_id"] for item in resolution["objects_to_fetch"]], [obj["object_id"]])
        payload = {key: value for key, value in resolution.items() if key != "boundaries"}
        self.assertNotIn("source", json.dumps(payload).lower())

    def test_schemas_are_closed_and_receipt_has_no_aggregate_score(self):
        for name in (
            "ark-evaluation-policy.schema.json",
            "ark-evaluation-observation.schema.json",
            "ark-evaluation-receipt.schema.json",
        ):
            schema = json.loads((ROOT / "schema" / name).read_text(encoding="utf-8"))
            self.assertFalse(schema["additionalProperties"], name)
        receipt_schema = json.loads((ROOT / "schema" / "ark-evaluation-receipt.schema.json").read_text(encoding="utf-8"))
        self.assertNotIn("score", receipt_schema["properties"])
        self.assertNotIn("overall", receipt_schema["properties"])


if __name__ == "__main__":
    unittest.main()
