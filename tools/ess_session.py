#!/usr/bin/env python3
"""Replay deterministic multi-turn ESS receiver-style sessions."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import thoth
from deterministic_contract import (
    ContractError,
    canonical_bytes,
    digest,
    exact_keys,
    fail,
    load_json,
    require,
    require_token,
)

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "ai" / "ess-session-policy.json"

POLICY_PROTOCOL = "QSOL-THOTH/ESS-SESSION-POLICY/1"
SESSION_PROTOCOL = "QSOL-THOTH/ESS-SESSION/1"
EVENT_RECEIPT_PROTOCOL = "QSOL-THOTH/ESS-TRANSITION-RECEIPT/1"
REPLAY_PROTOCOL = "QSOL-THOTH/ESS-SESSION-REPLAY/1"
VALIDATION_PROTOCOL = "QSOL-THOTH/ESS-SESSION-POLICY-VALIDATION/1"
PREFIX = "ESS_SESSION"

PROFILES = (
    ("immediate", 10, 0, 1),
    ("demonstrated_hysteresis", 20, 1, 2),
)

BOUNDARIES = (
    "STYLE_SWITCH != EPISTEMIC_SWITCH",
    "STYLE_PERSISTENCE != EPISTEMIC_PERSISTENCE",
    "EXPLICIT_STYLE_TRANSITION != MODEL_INFERENCE",
    "ROUTE_DEFAULT != FORCED_SESSION_TRANSITION",
    "HYSTERESIS != AMBIGUITY",
    "DWELL_COUNT != WALL_CLOCK_TIME",
    "REPLAY_RECEIPT != HIDDEN_STATE",
)

OUTCOMES = {
    "initialized_from_route_default",
    "initialized_from_explicit_transition",
    "persisted",
    "pending_confirmation",
    "deferred_by_dwell",
    "transitioned",
    "no_op_current_style",
    "reset",
}


def style_ids() -> set[str]:
    try:
        _, _, _, _, _, states = thoth.load_and_validate()
    except thoth.ThothError as exc:
        fail("E_ESS_SESSION_STYLE_MACHINE", f"{exc.code}: {exc.detail}")
    return set(states)


def validate_policy(policy: Any) -> dict[str, Any]:
    value = exact_keys(
        policy,
        {
            "protocol",
            "schema_version",
            "authority",
            "initialization",
            "persistence",
            "profiles",
            "reset",
            "canonical_inputs",
            "boundaries",
        },
        "ESS session policy",
        PREFIX,
    )
    require(value["protocol"] == POLICY_PROTOCOL, "E_ESS_SESSION_POLICY_PROTOCOL", "unexpected ESS session policy protocol")
    require(value["schema_version"] == "1.0.0", "E_ESS_SESSION_POLICY_VERSION", "unsupported ESS session policy version")
    require(value["authority"] == "receiver-style-only", "E_ESS_SESSION_POLICY_AUTHORITY", "ESS session policy cannot claim epistemic authority")
    require(value["initialization"] == "first-route-default-or-explicit-transition", "E_ESS_SESSION_POLICY_INITIALIZATION", "session initialization drift")
    require(value["persistence"] == "current-style-persists-until-explicit-transition-or-reset", "E_ESS_SESSION_POLICY_PERSISTENCE", "style persistence drift")
    profiles = value["profiles"]
    require(isinstance(profiles, list) and len(profiles) == len(PROFILES), "E_ESS_SESSION_POLICY_PROFILES", "profile count drift")
    observed: list[tuple[Any, Any, Any, Any]] = []
    for index, item in enumerate(profiles):
        item = exact_keys(
            item,
            {"id", "order", "minimum_dwell_routes", "transition_confirmations"},
            f"profiles[{index}]",
            PREFIX,
        )
        for key in ("order", "minimum_dwell_routes", "transition_confirmations"):
            require(isinstance(item[key], int) and not isinstance(item[key], bool), "E_ESS_SESSION_POLICY_PROFILES", f"profiles[{index}].{key} must be integer")
        require(item["minimum_dwell_routes"] >= 0, "E_ESS_SESSION_POLICY_PROFILES", "minimum_dwell_routes cannot be negative")
        require(item["transition_confirmations"] >= 1, "E_ESS_SESSION_POLICY_PROFILES", "transition_confirmations must be positive")
        observed.append((item["id"], item["order"], item["minimum_dwell_routes"], item["transition_confirmations"]))
    require(tuple(observed) == PROFILES, "E_ESS_SESSION_POLICY_PROFILES", "profile semantics or ordering drift")
    require(value["reset"] == "clear-style-next-route-reinitializes", "E_ESS_SESSION_POLICY_RESET", "reset semantics drift")
    inputs = exact_keys(
        value["canonical_inputs"],
        {"model_inferred_transitions", "wall_clock_input", "random_input", "network_input"},
        "canonical_inputs",
        PREFIX,
    )
    for key, actual in inputs.items():
        require(actual is False, "E_ESS_SESSION_POLICY_INPUT", f"canonical input {key} must remain false")
    require(value["boundaries"] == list(BOUNDARIES), "E_ESS_SESSION_POLICY_BOUNDARIES", "ESS session boundary set drift")
    return value


def policy_report(policy: dict[str, Any]) -> dict[str, Any]:
    checked = validate_policy(policy)
    return {
        "protocol": VALIDATION_PROTOCOL,
        "status": "ok",
        "policy_sha256": digest(checked),
        "styles": sorted(style_ids(), key=lambda item: item.encode("utf-8")),
        "profiles": [item[0] for item in PROFILES],
        "boundaries": list(BOUNDARIES),
    }


def validate_event(event: Any, index: int, known_styles: set[str]) -> dict[str, Any]:
    where = f"events[{index}]"
    require(isinstance(event, dict), "E_ESS_SESSION_EVENT", f"{where} must be an object")
    kind = event.get("kind")
    if kind == "route":
        value = exact_keys(event, {"sequence", "event_id", "kind", "request"}, where, PREFIX)
        request = exact_keys(value["request"], {"protocol", "intent"}, f"{where}.request", PREFIX)
        require(request["protocol"] == "QSOL-THOTH/ROUTE-REQUEST/1", "E_ESS_SESSION_ROUTE_PROTOCOL", f"{where}.request protocol drift")
        require_token(request["intent"], f"{where}.request.intent", PREFIX)
    elif kind == "transition":
        value = exact_keys(event, {"sequence", "event_id", "kind", "target_style"}, where, PREFIX)
        target = require_token(value["target_style"], f"{where}.target_style", PREFIX)
        require(target in known_styles, "E_ESS_SESSION_UNKNOWN_STYLE", f"{where}: unknown target style {target}")
    elif kind == "reset":
        value = exact_keys(event, {"sequence", "event_id", "kind"}, where, PREFIX)
    else:
        fail("E_ESS_SESSION_EVENT_KIND", f"{where}: unknown event kind {kind!r}")
    sequence = value["sequence"]
    require(
        isinstance(sequence, int) and not isinstance(sequence, bool) and sequence == index + 1,
        "E_ESS_SESSION_SEQUENCE",
        f"{where}.sequence must be {index + 1}",
    )
    require_token(value["event_id"], f"{where}.event_id", PREFIX)
    return value


def validate_session(session: Any, policy: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    checked_policy = validate_policy(policy)
    value = exact_keys(
        session,
        {"protocol", "schema_version", "session_id", "profile_id", "events", "boundaries"},
        "ESS session",
        PREFIX,
    )
    require(value["protocol"] == SESSION_PROTOCOL, "E_ESS_SESSION_PROTOCOL", "unexpected ESS session protocol")
    require(value["schema_version"] == "1.0.0", "E_ESS_SESSION_VERSION", "unsupported ESS session version")
    require_token(value["session_id"], "session_id", PREFIX)
    profile_id = require_token(value["profile_id"], "profile_id", PREFIX)
    profiles = {item["id"]: item for item in checked_policy["profiles"]}
    require(profile_id in profiles, "E_ESS_SESSION_PROFILE", f"unknown ESS session profile: {profile_id}")
    events = value["events"]
    require(isinstance(events, list) and events, "E_ESS_SESSION_EVENTS", "events must be a non-empty array")
    known_styles = style_ids()
    ids: set[str] = set()
    for index, event in enumerate(events):
        checked = validate_event(event, index, known_styles)
        require(checked["event_id"] not in ids, "E_ESS_SESSION_DUPLICATE_EVENT", f"duplicate event_id: {checked['event_id']}")
        ids.add(checked["event_id"])
    require(value["boundaries"] == list(BOUNDARIES), "E_ESS_SESSION_BOUNDARIES", "ESS session boundary set drift")
    return value, profiles[profile_id]


def route(request: dict[str, Any]) -> dict[str, Any]:
    try:
        return thoth.route_request(request)
    except thoth.ThothError as exc:
        fail("E_ESS_SESSION_ROUTE", f"{exc.code}: {exc.detail}")


def replay(session: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    checked, profile = validate_session(session, policy)
    checked_policy = validate_policy(policy)
    policy_sha = digest(checked_policy)
    current_style: str | None = None
    dwell_routes = 0
    pending_target: str | None = None
    pending_confirmations = 0
    previous_receipt: str | None = None
    receipts: list[dict[str, Any]] = []

    for event in checked["events"]:
        before_style = current_style
        base_style: str | None = None
        base_decision_sha: str | None = None
        effective_decision_sha: str | None = None
        effective_concaps: list[str] = []
        requested_target: str | None = None

        if event["kind"] == "route":
            base_decision = route(event["request"])
            base_style = base_decision["style"]
            base_decision_sha = base_decision["decision_sha256"]
            if current_style is None:
                effective_decision = base_decision
                current_style = base_style
                outcome = "initialized_from_route_default"
            else:
                effective_request = dict(event["request"])
                effective_request["style"] = current_style
                effective_decision = route(effective_request)
                outcome = "persisted"
            effective_decision_sha = effective_decision["decision_sha256"]
            effective_concaps = list(effective_decision["concaps"])
            dwell_routes += 1
            pending_target = None
            pending_confirmations = 0
        elif event["kind"] == "transition":
            requested_target = event["target_style"]
            if current_style is None:
                current_style = requested_target
                dwell_routes = 0
                pending_target = None
                pending_confirmations = 0
                outcome = "initialized_from_explicit_transition"
            elif requested_target == current_style:
                pending_target = None
                pending_confirmations = 0
                outcome = "no_op_current_style"
            elif dwell_routes < profile["minimum_dwell_routes"]:
                pending_target = None
                pending_confirmations = 0
                outcome = "deferred_by_dwell"
            else:
                if pending_target == requested_target:
                    pending_confirmations += 1
                else:
                    pending_target = requested_target
                    pending_confirmations = 1
                if pending_confirmations >= profile["transition_confirmations"]:
                    current_style = requested_target
                    dwell_routes = 0
                    pending_target = None
                    pending_confirmations = 0
                    outcome = "transitioned"
                else:
                    outcome = "pending_confirmation"
        else:
            current_style = None
            dwell_routes = 0
            pending_target = None
            pending_confirmations = 0
            outcome = "reset"

        require(outcome in OUTCOMES, "E_ESS_SESSION_OUTCOME", "internal ESS outcome drift")
        pending = (
            {"target_style": pending_target, "confirmations": pending_confirmations}
            if pending_target is not None
            else None
        )
        receipt_body = {
            "protocol": EVENT_RECEIPT_PROTOCOL,
            "session_id": checked["session_id"],
            "profile_id": checked["profile_id"],
            "sequence": event["sequence"],
            "event_id": event["event_id"],
            "event_kind": event["kind"],
            "event_sha256": digest(event),
            "policy_sha256": policy_sha,
            "previous_receipt_sha256": previous_receipt,
            "before_style": before_style,
            "after_style": current_style,
            "base_route_style": base_style,
            "base_route_decision_sha256": base_decision_sha,
            "effective_route_decision_sha256": effective_decision_sha,
            "effective_concaps": effective_concaps,
            "requested_target_style": requested_target,
            "outcome": outcome,
            "dwell_routes_after": dwell_routes,
            "pending_transition": pending,
            "boundaries": list(BOUNDARIES),
        }
        receipt = {**receipt_body, "receipt_sha256": digest(receipt_body)}
        previous_receipt = receipt["receipt_sha256"]
        receipts.append(receipt)

    body = {
        "protocol": REPLAY_PROTOCOL,
        "session_id": checked["session_id"],
        "profile_id": checked["profile_id"],
        "policy_sha256": policy_sha,
        "session_sha256": digest(checked),
        "receipts": receipts,
        "final_style": current_style,
        "final_receipt_sha256": previous_receipt,
        "boundaries": list(BOUNDARIES),
    }
    return {**body, "replay_sha256": digest(body)}


def emit(value: Any) -> None:
    sys.stdout.buffer.write(canonical_bytes(value) + b"\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Replay deterministic multi-turn ESS receiver-style sessions")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-policy", help="validate the canonical ESS session policy")
    replay_parser = sub.add_parser("replay", help="replay an ESS session event log")
    replay_parser.add_argument("--session", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        policy = load_json(POLICY_PATH, PREFIX)
        if args.command == "validate-policy":
            emit(policy_report(policy))
        else:
            emit(replay(load_json(args.session, PREFIX), policy))
    except ContractError as exc:
        print(f"{exc.code}: {exc.detail}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
