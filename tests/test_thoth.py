from __future__ import annotations

import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools import thoth


class ThothRoutingTests(unittest.TestCase):
    def request(self, intent: str, style: str | None = None) -> dict:
        value = {
            "protocol": "QSOL-THOTH/ROUTE-REQUEST/1",
            "intent": intent,
        }
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

    def test_routing_schemas_are_semantically_validated(self):
        request_schema = thoth.load_json(thoth.REQUEST_SCHEMA_PATH)
        bad_request = copy.deepcopy(request_schema)
        bad_request["properties"]["protocol"]["const"] = "BROKEN/REQUEST/1"
        with self.assertRaises(thoth.ThothError):
            thoth.validate_request_schema(bad_request)

        decision_schema = thoth.load_json(thoth.DECISION_SCHEMA_PATH)
        bad_decision = copy.deepcopy(decision_schema)
        bad_decision["required"].remove("implementation_sha256")
        with self.assertRaises(thoth.ThothError):
            thoth.validate_decision_schema(bad_decision)

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

    def test_alias_resolution_is_exact_and_canonical(self):
        decision = thoth.route_request(self.request("code_review"))
        self.assertEqual(decision["canonical_intent"], "software_review")
        self.assertEqual(decision["style"], "technical")

    def test_explicit_style_override_adds_receiver_support_only(self):
        decision = thoth.route_request(
            self.request("software_review", "australian_humour")
        )
        self.assertEqual(decision["canonical_intent"], "software_review")
        self.assertEqual(decision["style"], "australian_humour")
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

    def test_decision_receipt_includes_availability_boundary(self):
        decision = thoth.route_request(self.request("general"))
        self.assertIn(
            "ROUTE_DECISION != CAPSULE_AVAILABILITY",
            decision["boundaries"],
        )

    def test_decision_boundaries_are_not_shared_mutable_state(self):
        request = self.request("research")
        baseline = thoth.route_request(request)
        mutated = thoth.route_request(request)
        mutated["boundaries"].append("MUTATED BY CALLER")
        after = thoth.route_request(request)
        self.assertNotIn("MUTATED BY CALLER", after["boundaries"])
        self.assertEqual(baseline["decision_sha256"], after["decision_sha256"])

    def test_new_positive_concap_role_versions_are_permitted(self):
        registry = thoth.load_json(thoth.REGISTRY_PATH)
        revised = copy.deepcopy(registry)
        revised["capsules"][0]["id"] = "concap.identity.core/2"
        order_by_id, known = thoth.validate_registry(revised)
        self.assertIn("concap.identity.core/2", known)
        self.assertEqual(order_by_id["concap.identity.core/2"], 10)

    def test_zero_concap_role_version_is_rejected(self):
        registry = thoth.load_json(thoth.REGISTRY_PATH)
        revised = copy.deepcopy(registry)
        revised["capsules"][0]["id"] = "concap.identity.core/0"
        with self.assertRaises(thoth.ThothError):
            thoth.validate_registry(revised)

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
        self.assertIn("FAIL: cannot load", proc.stderr)
        self.assertIn(str(path), proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_unknown_intent_fails_closed(self):
        with self.assertRaises(thoth.ThothError):
            thoth.route_request(self.request("i_reckon_this_is_close_enough"))

    def test_unknown_style_fails_closed(self):
        with self.assertRaises(thoth.ThothError):
            thoth.route_request(self.request("general", "surprise_pirate"))

    def test_same_request_is_byte_stable(self):
        request = self.request("formal_claim")
        first = thoth.canonical_bytes(thoth.route_request(request))
        second = thoth.canonical_bytes(thoth.route_request(request))
        self.assertEqual(first, second)

    def test_decision_hash_is_acyclic_and_recomputable(self):
        decision = thoth.route_request(self.request("research"))
        claimed = decision.pop("decision_sha256")
        self.assertEqual(claimed, thoth.digest_bytes(thoth.canonical_bytes(decision)))

    def test_request_hash_binds_explicit_style(self):
        technical = thoth.route_request(self.request("software_review"))
        funny = thoth.route_request(
            self.request("software_review", "australian_humour")
        )
        self.assertNotEqual(technical["request_sha256"], funny["request_sha256"])
        self.assertNotEqual(technical["decision_sha256"], funny["decision_sha256"])


if __name__ == "__main__":
    unittest.main()
