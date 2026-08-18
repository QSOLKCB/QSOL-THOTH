from __future__ import annotations

import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools import thoth


class ThothConformanceTests(unittest.TestCase):
    def request(self, intent: str, style: str | None = None) -> dict:
        value = {"protocol": "QSOL-THOTH/ROUTE-REQUEST/1", "intent": intent}
        if style is not None:
            value["style"] = style
        return value

    def test_public_contracts_validate(self):
        registry, styles, router, _, token_map, states = thoth.load_and_validate()
        self.assertEqual(registry["protocol"], "QSOL-THOTH/CONCAP-REGISTRY/1")
        self.assertEqual(styles["protocol"], "QSOL-THOTH/ESS-STYLE/1")
        self.assertEqual(router["protocol"], "QSOL-THOTH/ROUTER/1")
        self.assertIn("comedy", token_map)
        self.assertIn("australian_humour", states)

    def test_machine_readable_schemas_validate_semantics(self):
        thoth.validate_registry_schema(thoth.load_json(thoth.REGISTRY_SCHEMA_PATH))
        thoth.validate_compatibility_schema(thoth.load_json(thoth.COMPATIBILITY_SCHEMA_PATH))
        thoth.validate_style_schema(thoth.load_json(thoth.STYLE_SCHEMA_PATH))
        thoth.validate_router_schema(thoth.load_json(thoth.ROUTER_SCHEMA_PATH))
        thoth.validate_request_schema(thoth.load_json(thoth.REQUEST_SCHEMA_PATH))
        thoth.validate_decision_schema(thoth.load_json(thoth.DECISION_SCHEMA_PATH))

    def test_schema_drift_fails_closed(self):
        schema = thoth.load_json(thoth.REGISTRY_SCHEMA_PATH)
        bad = copy.deepcopy(schema)
        bad["properties"]["namespace"]["const"] = "NOT_CONCAP"
        with self.assertRaises(thoth.ThothError) as caught:
            thoth.validate_registry_schema(bad)
        self.assertEqual(caught.exception.code, "E_SCHEMA_SEMANTICS")

    def test_compatibility_policy_disables_implicit_substitution(self):
        policy = thoth.load_json(thoth.COMPATIBILITY_PATH)
        thoth.validate_compatibility_policy(policy)
        self.assertFalse(policy["role_versioning"]["implicit_version_substitution"])
        self.assertFalse(policy["role_versioning"]["new_version_backward_compatible_by_default"])

    def test_new_positive_concap_role_versions_are_permitted(self):
        registry = thoth.load_json(thoth.REGISTRY_PATH)
        revised = copy.deepcopy(registry)
        revised["capsules"][0]["id"] = "concap.identity.core/2"
        order_by_id, known = thoth.validate_registry(revised)
        self.assertIn("concap.identity.core/2", known)
        self.assertEqual(order_by_id["concap.identity.core/2"], 10)

    def test_comedy_route_selects_minimum_cultural_set(self):
        decision = thoth.route_request(self.request("comedy"))
        self.assertEqual(decision["canonical_intent"], "comedy")
        self.assertEqual(decision["style"], "australian_humour")
        self.assertEqual(
            decision["concaps"],
            [
                "concap.culture.core/1",
                "concap.culture.au-humour/1",
                "concap.culture.comedy/1",
            ],
        )

    def test_explicit_australian_humour_style_does_not_remove_engineering_context(self):
        decision = thoth.route_request(self.request("software_review", "australian_humour"))
        self.assertEqual(
            decision["concaps"],
            [
                "concap.identity.core/1",
                "concap.workstyle.engineering/1",
                "concap.receipts/1",
                "concap.culture.core/1",
                "concap.culture.au-humour/1",
                "concap.culture.comedy/1",
            ],
        )
        self.assertIn("STYLE_SUPPORT != EVIDENCE", decision["boundaries"])
        self.assertIn("ROUTING != FACTUAL_AUTHORITY", decision["boundaries"])

    def test_decision_boundaries_are_not_shared_mutable_state(self):
        request = self.request("research")
        baseline = thoth.route_request(request)
        mutated = thoth.route_request(request)
        mutated["boundaries"].append("MUTATED")
        after = thoth.route_request(request)
        self.assertEqual(baseline["decision_sha256"], after["decision_sha256"])
        self.assertNotIn("MUTATED", after["boundaries"])

    def test_decision_hash_is_acyclic_and_recomputable(self):
        decision = thoth.route_request(self.request("research"))
        claimed = decision.pop("decision_sha256")
        self.assertEqual(claimed, thoth.digest_bytes(thoth.canonical_bytes(decision)))

    def test_same_request_is_byte_stable(self):
        request = self.request("formal_claim")
        first = thoth.canonical_bytes(thoth.route_request(request))
        second = thoth.canonical_bytes(thoth.route_request(request))
        self.assertEqual(first, second)

    def test_positive_known_answer_vectors_are_frozen(self):
        for vector in thoth.load_positive_vectors():
            actual = thoth.route_request(vector["request"])
            self.assertEqual(
                thoth.canonical_bytes(actual),
                thoth.canonical_bytes(vector["expected_decision"]),
                vector["id"],
            )

    def test_negative_vectors_return_declared_error_codes(self):
        for vector in thoth.load_negative_vectors():
            self.assertEqual(
                thoth.exercise_negative_vector(vector),
                vector["expected_error"],
                vector["id"],
            )

    def test_full_conformance_suite_passes(self):
        report = thoth.run_conformance()
        self.assertEqual(report["status"], "ok")
        self.assertGreaterEqual(report["positive_vectors"], 6)
        self.assertGreaterEqual(report["negative_vectors"], 7)

    def test_duplicate_json_member_has_stable_error_code(self):
        fixture = thoth.ROOT / "vectors/negative/fixtures/duplicate-json-member.request.json"
        with self.assertRaises(thoth.ThothError) as caught:
            thoth.load_json(fixture)
        self.assertEqual(caught.exception.code, "E_JSON_DUPLICATE_MEMBER")

    def test_unknown_route_errors_are_stable(self):
        with self.assertRaises(thoth.ThothError) as caught:
            thoth.route_request(self.request("not_a_route"))
        self.assertEqual(caught.exception.code, "E_ROUTE_UNKNOWN_INTENT")
        with self.assertRaises(thoth.ThothError) as caught:
            thoth.route_request(self.request("general", "surprise_pirate"))
        self.assertEqual(caught.exception.code, "E_ROUTE_UNKNOWN_STYLE")

    def test_external_malformed_request_reports_clean_cli_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad-request.json"
            path.write_text("{ definitely-not-json", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(thoth.IMPLEMENTATION_PATH), "route", "--request", str(path)],
                cwd=thoth.ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("FAIL: E_JSON_LOAD:", proc.stderr)
        self.assertIn(str(path), proc.stderr)


if __name__ == "__main__":
    unittest.main()
