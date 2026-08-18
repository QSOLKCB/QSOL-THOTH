from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import ess_session as ess
from deterministic_contract import ContractError

POLICY = ROOT / "ai" / "ess-session-policy.json"
EXAMPLE = ROOT / "examples" / "ess" / "demonstrated-hysteresis.session.json"


def session(events: list[dict], profile: str = "immediate") -> dict:
    return {
        "protocol": ess.SESSION_PROTOCOL,
        "schema_version": "1.0.0",
        "session_id": "unit_test_session",
        "profile_id": profile,
        "events": events,
        "boundaries": list(ess.BOUNDARIES),
    }


def route_event(sequence: int, intent: str) -> dict:
    return {
        "sequence": sequence,
        "event_id": f"event-{sequence:03d}",
        "kind": "route",
        "request": {"protocol": "QSOL-THOTH/ROUTE-REQUEST/1", "intent": intent},
    }


def transition_event(sequence: int, target: str) -> dict:
    return {
        "sequence": sequence,
        "event_id": f"event-{sequence:03d}",
        "kind": "transition",
        "target_style": target,
    }


class EssSessionTests(unittest.TestCase):
    def setUp(self):
        self.policy = ess.load_json(POLICY, ess.PREFIX)
        self.example = ess.load_json(EXAMPLE, ess.PREFIX)

    def test_policy_is_clock_random_network_and_model_inference_free(self):
        report = ess.policy_report(self.policy)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["profiles"], ["immediate", "demonstrated_hysteresis"])
        self.assertEqual(set(report["styles"]), {"neutral", "technical", "formal", "research", "creative", "australian_humour"})
        self.assertTrue(all(value is False for value in self.policy["canonical_inputs"].values()))

    def test_demonstrated_hysteresis_and_dwell_outcomes_are_frozen(self):
        replay = ess.replay(self.example, self.policy)
        self.assertEqual(
            [receipt["outcome"] for receipt in replay["receipts"]],
            [
                "initialized_from_route_default",
                "pending_confirmation",
                "transitioned",
                "deferred_by_dwell",
                "persisted",
                "pending_confirmation",
                "transitioned",
                "persisted",
                "reset",
                "initialized_from_route_default",
            ],
        )
        self.assertEqual(replay["final_style"], "australian_humour")

    def test_persisted_style_rebuilds_route_with_required_style_support(self):
        replay = ess.replay(self.example, self.policy)
        formal_turn = replay["receipts"][4]
        self.assertEqual(formal_turn["base_route_style"], "formal")
        self.assertEqual(formal_turn["after_style"], "australian_humour")
        self.assertNotEqual(formal_turn["base_route_decision_sha256"], formal_turn["effective_route_decision_sha256"])
        self.assertIn("concap.culture.au-humour/1", formal_turn["effective_concaps"])
        self.assertIn("concap.culture.comedy/1", formal_turn["effective_concaps"])
        self.assertIn("concap.research.active/1", formal_turn["effective_concaps"])

    def test_immediate_profile_transitions_without_hysteresis(self):
        value = session([
            route_event(1, "general"),
            transition_event(2, "research"),
            route_event(3, "comedy"),
        ])
        replay = ess.replay(value, self.policy)
        self.assertEqual([item["outcome"] for item in replay["receipts"]], ["initialized_from_route_default", "transitioned", "persisted"])
        self.assertEqual(replay["final_style"], "research")
        self.assertEqual(replay["receipts"][2]["base_route_style"], "australian_humour")
        self.assertEqual(replay["receipts"][2]["after_style"], "research")

    def test_route_event_breaks_consecutive_hysteresis_confirmation(self):
        value = session([
            route_event(1, "general"),
            transition_event(2, "research"),
            route_event(3, "general"),
            transition_event(4, "research"),
        ], profile="demonstrated_hysteresis")
        replay = ess.replay(value, self.policy)
        self.assertEqual(replay["receipts"][1]["outcome"], "pending_confirmation")
        self.assertIsNone(replay["receipts"][2]["pending_transition"])
        self.assertEqual(replay["receipts"][3]["outcome"], "pending_confirmation")
        self.assertNotEqual(replay["final_style"], "research")

    def test_reset_clears_style_and_next_route_reinitializes(self):
        value = session([
            transition_event(1, "formal"),
            {"sequence": 2, "event_id": "event-002", "kind": "reset"},
            route_event(3, "comedy"),
        ])
        replay = ess.replay(value, self.policy)
        self.assertEqual(replay["receipts"][0]["outcome"], "initialized_from_explicit_transition")
        self.assertIsNone(replay["receipts"][1]["after_style"])
        self.assertEqual(replay["receipts"][2]["outcome"], "initialized_from_route_default")
        self.assertEqual(replay["final_style"], "australian_humour")

    def test_replay_and_event_receipts_are_acyclic_and_chained(self):
        replay = ess.replay(self.example, self.policy)
        previous = None
        for receipt in replay["receipts"]:
            self.assertEqual(receipt["previous_receipt_sha256"], previous)
            body = dict(receipt)
            claimed = body.pop("receipt_sha256")
            self.assertEqual(claimed, ess.digest(body))
            previous = claimed
        self.assertEqual(replay["final_receipt_sha256"], previous)
        body = dict(replay)
        claimed = body.pop("replay_sha256")
        self.assertEqual(claimed, ess.digest(body))

    def test_replay_is_byte_stable(self):
        first = ess.replay(self.example, self.policy)
        second = ess.replay(self.example, self.policy)
        self.assertEqual(ess.canonical_bytes(first), ess.canonical_bytes(second))

    def test_unknown_style_and_model_inferred_route_style_fail_closed(self):
        changed = session([transition_event(1, "model_guessed_vibe")])
        with self.assertRaisesRegex(ContractError, "E_ESS_SESSION_UNKNOWN_STYLE"):
            ess.replay(changed, self.policy)

        changed = session([route_event(1, "general")])
        changed["events"][0]["request"]["style"] = "creative"
        with self.assertRaisesRegex(ContractError, "E_ESS_SESSION_FIELDS"):
            ess.replay(changed, self.policy)

    def test_unknown_route_intent_has_stable_session_error(self):
        changed = session([route_event(1, "definitely_not_a_route")])
        with self.assertRaisesRegex(ContractError, "E_ESS_SESSION_ROUTE"):
            ess.replay(changed, self.policy)

    def test_sequence_and_duplicate_event_ids_fail_closed(self):
        changed = session([route_event(1, "general"), route_event(2, "general")])
        changed["events"][1]["sequence"] = 99
        with self.assertRaisesRegex(ContractError, "E_ESS_SESSION_SEQUENCE"):
            ess.replay(changed, self.policy)

        changed = session([route_event(1, "general"), route_event(2, "general")])
        changed["events"][1]["event_id"] = changed["events"][0]["event_id"]
        with self.assertRaisesRegex(ContractError, "E_ESS_SESSION_DUPLICATE_EVENT"):
            ess.replay(changed, self.policy)

    def test_schemas_are_closed_and_receipt_fields_are_explicit(self):
        for name in (
            "ess-session-policy.schema.json",
            "ess-session.schema.json",
            "ess-session-replay.schema.json",
        ):
            schema = json.loads((ROOT / "schema" / name).read_text(encoding="utf-8"))
            self.assertFalse(schema["additionalProperties"], name)
        replay_schema = json.loads((ROOT / "schema" / "ess-session-replay.schema.json").read_text(encoding="utf-8"))
        receipt = replay_schema["$defs"]["eventReceipt"]
        self.assertFalse(receipt["additionalProperties"])
        self.assertIn("previous_receipt_sha256", receipt["required"])
        self.assertIn("effective_route_decision_sha256", receipt["required"])
        self.assertIn("pending_transition", receipt["required"])


if __name__ == "__main__":
    unittest.main()
