from __future__ import annotations

import unittest

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
