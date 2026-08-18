#!/usr/bin/env python3
"""Deterministic public router for QSOL-CONCAP.

Standard-library only. Canonical routing uses explicit ASCII tokens, declared
aliases, a finite ESS-style state machine, and SHA-256 receipts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r"^[a-z0-9_.-]+$")
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")

REGISTRY_PATH = ROOT / "ai" / "concap-registry.json"
STYLE_PATH = ROOT / "ai" / "ess-style-machine.json"
ROUTER_PATH = ROOT / "ai" / "router.json"
REQUEST_SCHEMA_PATH = ROOT / "schema" / "route-request.schema.json"
DECISION_SCHEMA_PATH = ROOT / "schema" / "route-decision.schema.json"
IMPLEMENTATION_PATH = ROOT / "tools" / "thoth.py"

DECISION_BOUNDARIES = [
    "ROUTING != FACTUAL_AUTHORITY",
    "STYLE_SWITCH != EPISTEMIC_SWITCH",
    "STYLE_SUPPORT != EVIDENCE",
    "CONCAP_ID != CAPSULE_BYTES",
    "SELECTED != LOADED",
    "LOADED != TRUE",
]


class ThothError(Exception):
    pass


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ThothError(f"duplicate JSON object member: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ThothError(f"refusing symlinked contract: {path.relative_to(ROOT)}")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ThothError(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise ThothError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ThothError(message)


def exact_keys(value: dict[str, Any], allowed: set[str], where: str) -> None:
    extra = sorted(set(value) - allowed)
    missing = sorted(allowed - set(value))
    require(not extra, f"{where}: unsupported fields: {extra}")
    require(not missing, f"{where}: missing fields: {missing}")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def configuration_digest() -> str:
    digest = hashlib.sha256()
    for path in sorted(
        [REGISTRY_PATH, STYLE_PATH, ROUTER_PATH, REQUEST_SCHEMA_PATH, DECISION_SCHEMA_PATH],
        key=lambda item: item.relative_to(ROOT).as_posix(),
    ):
        rel = path.relative_to(ROOT).as_posix().encode("utf-8")
        data = path.read_bytes()
        digest.update(rel)
        digest.update(b"\0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\0")
        digest.update(data)
    return "sha256:" + digest.hexdigest()


def validate_registry(registry: dict[str, Any]) -> tuple[dict[str, int], set[str]]:
    exact_keys(
        registry,
        {"protocol", "schema_version", "namespace", "expansion", "authority", "capsules", "boundaries"},
        "CONCAP registry",
    )
    require(registry["protocol"] == "QSOL-THOTH/CONCAP-REGISTRY/1", "unexpected CONCAP registry protocol")
    require(registry["namespace"] == "CONCAP", "registry namespace must be CONCAP")
    require(registry["expansion"] == "CONtext CAPsules", "CONCAP expansion drift detected")
    require(registry["authority"] == "semantic-routing-only", "registry authority drift detected")
    capsules = registry["capsules"]
    require(isinstance(capsules, list) and capsules, "registry capsules must be a non-empty array")

    order_by_id: dict[str, int] = {}
    orders: set[int] = set()
    for index, item in enumerate(capsules):
        require(isinstance(item, dict), f"registry capsule {index} must be an object")
        exact_keys(
            item,
            {"id", "order", "role", "default_privacy", "epistemic_authority", "style_authority"},
            f"registry capsule {index}",
        )
        capsule_id = item["id"]
        order = item["order"]
        require(isinstance(capsule_id, str) and capsule_id.startswith("concap.") and capsule_id.endswith("/1"), f"invalid CONCAP id: {capsule_id!r}")
        require(capsule_id not in order_by_id, f"duplicate CONCAP id: {capsule_id}")
        require(isinstance(order, int) and not isinstance(order, bool) and order > 0, f"invalid CONCAP order for {capsule_id}")
        require(order not in orders, f"duplicate CONCAP order: {order}")
        require(item["epistemic_authority"] == "none-by-routing", f"{capsule_id}: routing must not grant epistemic authority")
        order_by_id[capsule_id] = order
        orders.add(order)

    boundaries = registry["boundaries"]
    require(isinstance(boundaries, list), "registry boundaries must be an array")
    require("CONCAP_ID != CAPSULE_BYTES" in boundaries, "registry missing byte-identity boundary")
    return order_by_id, set(order_by_id)


def validate_style_machine(style_machine: dict[str, Any], known_capsules: set[str]) -> set[str]:
    exact_keys(
        style_machine,
        {"protocol", "schema_version", "selection", "states", "transition_contract", "boundaries"},
        "ESS style machine",
    )
    require(style_machine["protocol"] == "QSOL-THOTH/ESS-STYLE/1", "unexpected ESS style protocol")
    selection = style_machine["selection"]
    require(isinstance(selection, dict), "ESS selection must be an object")
    exact_keys(
        selection,
        {"explicit_declared_style_wins", "otherwise_use_route_default", "unknown_style_policy", "tie_break"},
        "ESS selection",
    )
    require(selection["explicit_declared_style_wins"] is True, "explicit declared style must win")
    require(selection["otherwise_use_route_default"] is True, "route default style fallback required")
    require(selection["unknown_style_policy"] == "fail_closed", "unknown style policy must fail closed")

    states = style_machine["states"]
    require(isinstance(states, list) and states, "ESS states must be a non-empty array")
    style_ids: set[str] = set()
    orders: set[int] = set()
    for index, state in enumerate(states):
        require(isinstance(state, dict), f"ESS state {index} must be an object")
        exact_keys(state, {"id", "order", "receiver_role", "support_concaps"}, f"ESS state {index}")
        style_id = state["id"]
        order = state["order"]
        require(isinstance(style_id, str) and TOKEN.fullmatch(style_id), f"invalid ESS style id: {style_id!r}")
        require(style_id not in style_ids, f"duplicate ESS style id: {style_id}")
        require(isinstance(order, int) and not isinstance(order, bool) and order > 0, f"invalid ESS style order: {style_id}")
        require(order not in orders, f"duplicate ESS style order: {order}")
        support = state["support_concaps"]
        require(isinstance(support, list), f"{style_id}: support_concaps must be an array")
        require(len(support) == len(set(support)), f"{style_id}: duplicate support CONCAP")
        for capsule_id in support:
            require(capsule_id in known_capsules, f"{style_id}: unknown support CONCAP {capsule_id}")
        style_ids.add(style_id)
        orders.add(order)

    boundaries = style_machine["boundaries"]
    require(isinstance(boundaries, list), "ESS boundaries must be an array")
    require("STYLE_SWITCH != EPISTEMIC_SWITCH" in boundaries, "ESS machine missing epistemic boundary")
    require("STYLE_SUPPORT != EVIDENCE" in boundaries, "ESS machine missing evidence boundary")
    return style_ids


def validate_router(router: dict[str, Any], known_capsules: set[str], style_ids: set[str]) -> dict[str, dict[str, Any]]:
    exact_keys(
        router,
        {"protocol", "schema_version", "unknown_intent_policy", "intent_token_pattern", "routes", "selection_contract", "boundaries"},
        "router",
    )
    require(router["protocol"] == "QSOL-THOTH/ROUTER/1", "unexpected router protocol")
    require(router["unknown_intent_policy"] == "fail_closed", "unknown intent policy must fail closed")
    require(router["intent_token_pattern"] == "^[a-z0-9_.-]+$", "intent token grammar drift detected")

    routes = router["routes"]
    require(isinstance(routes, list) and routes, "router routes must be a non-empty array")
    token_map: dict[str, dict[str, Any]] = {}
    canonical_intents: set[str] = set()
    route_orders: set[int] = set()
    for index, route in enumerate(routes):
        require(isinstance(route, dict), f"route {index} must be an object")
        exact_keys(route, {"intent", "aliases", "order", "default_style", "concaps"}, f"route {index}")
        intent = route["intent"]
        aliases = route["aliases"]
        order = route["order"]
        default_style = route["default_style"]
        concaps = route["concaps"]

        require(isinstance(intent, str) and TOKEN.fullmatch(intent), f"invalid route intent: {intent!r}")
        require(intent not in canonical_intents, f"duplicate canonical intent: {intent}")
        require(isinstance(order, int) and not isinstance(order, bool) and order > 0, f"invalid route order: {intent}")
        require(order not in route_orders, f"duplicate route order: {order}")
        require(default_style in style_ids, f"{intent}: unknown default style {default_style}")
        require(isinstance(aliases, list), f"{intent}: aliases must be an array")
        require(isinstance(concaps, list) and concaps, f"{intent}: concaps must be a non-empty array")
        require(len(concaps) == len(set(concaps)), f"{intent}: duplicate CONCAP")
        for capsule_id in concaps:
            require(capsule_id in known_capsules, f"{intent}: unknown CONCAP {capsule_id}")

        canonical_intents.add(intent)
        route_orders.add(order)
        for token in [intent, *aliases]:
            require(isinstance(token, str) and TOKEN.fullmatch(token), f"{intent}: invalid alias token {token!r}")
            require(token not in token_map, f"ambiguous route token: {token}")
            token_map[token] = route

    boundaries = router["boundaries"]
    require(isinstance(boundaries, list), "router boundaries must be an array")
    require("ROUTING != FACTUAL_AUTHORITY" in boundaries, "router missing factual-authority boundary")
    return token_map


def load_and_validate() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, int], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    registry = load_json(REGISTRY_PATH)
    style_machine = load_json(STYLE_PATH)
    router = load_json(ROUTER_PATH)
    load_json(REQUEST_SCHEMA_PATH)
    load_json(DECISION_SCHEMA_PATH)

    order_by_id, known_capsules = validate_registry(registry)
    style_ids = validate_style_machine(style_machine, known_capsules)
    token_map = validate_router(router, known_capsules, style_ids)
    states_by_id = {state["id"]: state for state in style_machine["states"]}
    return registry, style_machine, router, order_by_id, token_map, states_by_id


def validate_request(request: dict[str, Any]) -> None:
    allowed = {"protocol", "intent", "style"}
    extra = sorted(set(request) - allowed)
    require(not extra, f"route request has unsupported fields: {extra}")
    require(set(request) >= {"protocol", "intent"}, "route request requires protocol and intent")
    require(request["protocol"] == "QSOL-THOTH/ROUTE-REQUEST/1", "unexpected route request protocol")
    intent = request["intent"]
    require(isinstance(intent, str) and TOKEN.fullmatch(intent), "route request intent must be an exact ASCII token")
    if "style" in request:
        style = request["style"]
        require(isinstance(style, str) and TOKEN.fullmatch(style), "route request style must be an exact ASCII token")


def route_request(request: dict[str, Any]) -> dict[str, Any]:
    _, _, _, order_by_id, token_map, states_by_id = load_and_validate()
    validate_request(request)

    token = request["intent"]
    route = token_map.get(token)
    require(route is not None, f"unknown intent: {token}")

    style_id = request.get("style", route["default_style"])
    require(style_id in states_by_id, f"unknown style: {style_id}")
    state = states_by_id[style_id]

    selected = set(route["concaps"])
    selected.update(state["support_concaps"])
    ordered = sorted(selected, key=lambda capsule_id: (order_by_id[capsule_id], capsule_id.encode("utf-8")))

    request_sha = digest_bytes(canonical_bytes(request))
    config_sha = configuration_digest()
    implementation_sha = digest_file(IMPLEMENTATION_PATH)

    base = {
        "protocol": "QSOL-THOTH/ROUTE-DECISION/1",
        "canonical_intent": route["intent"],
        "style": style_id,
        "concaps": ordered,
        "request_sha256": request_sha,
        "configuration_sha256": config_sha,
        "implementation_sha256": implementation_sha,
        "boundaries": DECISION_BOUNDARIES,
    }
    return {**base, "decision_sha256": digest_bytes(canonical_bytes(base))}


def command_validate() -> int:
    registry, style_machine, router, _, _, _ = load_and_validate()
    report = {
        "protocol": "QSOL-THOTH/VALIDATION-REPORT/1",
        "configuration_sha256": configuration_digest(),
        "implementation_sha256": digest_file(IMPLEMENTATION_PATH),
        "concap_count": len(registry["capsules"]),
        "style_count": len(style_machine["states"]),
        "route_count": len(router["routes"]),
        "status": "ok",
    }
    print(canonical_bytes(report).decode("utf-8"))
    return 0


def command_route(args: argparse.Namespace) -> int:
    if args.request:
        request_path = Path(args.request)
        if request_path.is_symlink():
            raise ThothError("route request file must not be a symlink")
        request = load_json(request_path.resolve())
        require(args.intent is None and args.style is None, "--request cannot be combined with --intent or --style")
    else:
        require(args.intent is not None, "route requires --intent or --request")
        request = {
            "protocol": "QSOL-THOTH/ROUTE-REQUEST/1",
            "intent": args.intent,
        }
        if args.style is not None:
            request["style"] = args.style

    print(canonical_bytes(route_request(request)).decode("utf-8"))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="thoth")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="validate public THOTH contracts")
    route = sub.add_parser("route", help="emit a deterministic CONCAP route decision")
    route.add_argument("--intent")
    route.add_argument("--style")
    route.add_argument("--request")
    args = parser.parse_args()

    try:
        if args.command == "validate":
            return command_validate()
        if args.command == "route":
            return command_route(args)
        raise ThothError(f"unsupported command: {args.command}")
    except ThothError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
