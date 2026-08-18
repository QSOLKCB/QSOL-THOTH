#!/usr/bin/env python3
"""Deterministic public router and conformance runner for QSOL-CONCAP.

Standard-library only. Canonical routing uses explicit ASCII tokens, declared
aliases, a finite ESS-style state machine, frozen known-answer vectors, and
SHA-256 receipts.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r"^[a-z0-9_.-]+$")
CONCAP_ID = re.compile(r"^concap\.[a-z0-9_.-]+/[1-9][0-9]*$")
SEMVER = re.compile(r"^[1-9][0-9]*\.[0-9]+\.[0-9]+$")
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")

REGISTRY_PATH = ROOT / "ai" / "concap-registry.json"
COMPATIBILITY_PATH = ROOT / "ai" / "concap-compatibility.json"
STYLE_PATH = ROOT / "ai" / "ess-style-machine.json"
ROUTER_PATH = ROOT / "ai" / "router.json"

REGISTRY_SCHEMA_PATH = ROOT / "schema" / "concap-registry.schema.json"
COMPATIBILITY_SCHEMA_PATH = ROOT / "schema" / "concap-compatibility.schema.json"
STYLE_SCHEMA_PATH = ROOT / "schema" / "ess-style-machine.schema.json"
ROUTER_SCHEMA_PATH = ROOT / "schema" / "router.schema.json"
REQUEST_SCHEMA_PATH = ROOT / "schema" / "route-request.schema.json"
DECISION_SCHEMA_PATH = ROOT / "schema" / "route-decision.schema.json"

IMPLEMENTATION_PATH = ROOT / "tools" / "thoth.py"
POSITIVE_VECTOR_DIR = ROOT / "vectors" / "positive"
NEGATIVE_VECTOR_DIR = ROOT / "vectors" / "negative"

CONFIGURATION_PATHS = (
    REGISTRY_PATH,
    COMPATIBILITY_PATH,
    STYLE_PATH,
    ROUTER_PATH,
    REGISTRY_SCHEMA_PATH,
    COMPATIBILITY_SCHEMA_PATH,
    STYLE_SCHEMA_PATH,
    ROUTER_SCHEMA_PATH,
    REQUEST_SCHEMA_PATH,
    DECISION_SCHEMA_PATH,
)

DECISION_BOUNDARIES = (
    "ROUTING != FACTUAL_AUTHORITY",
    "STYLE_SWITCH != EPISTEMIC_SWITCH",
    "STYLE_SUPPORT != EVIDENCE",
    "CONCAP_ID != CAPSULE_BYTES",
    "ROUTE_DECISION != CAPSULE_AVAILABILITY",
    "SELECTED != LOADED",
    "LOADED != TRUE",
)

JSON_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"


class ThothError(Exception):
    """Stable machine-readable error plus human diagnostic."""

    def __init__(self, code: str, detail: str):
        if not TOKEN.fullmatch(code.lower().replace("-", "_")):
            raise ValueError(f"invalid THOTH error code: {code}")
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def fail(code: str, detail: str) -> None:
    raise ThothError(code, detail)


def require(condition: bool, code: str, detail: str) -> None:
    if not condition:
        fail(code, detail)


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail("E_JSON_DUPLICATE_MEMBER", f"duplicate JSON object member: {key}")
        result[key] = value
    return result


def path_label(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    label = path_label(path)
    if path.is_symlink():
        fail("E_IO_SYMLINK", f"refusing symlinked JSON input: {label}")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except ThothError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail("E_JSON_LOAD", f"cannot load {label}: {exc}")
    if not isinstance(value, dict):
        fail("E_JSON_TOPLEVEL", f"{label} must contain a JSON object")
    return value


def exact_keys(value: dict[str, Any], allowed: set[str], where: str, code: str = "E_CONTRACT_FIELDS") -> None:
    extra = sorted(set(value) - allowed)
    missing = sorted(allowed - set(value))
    require(not extra, code, f"{where}: unsupported fields: {extra}")
    require(not missing, code, f"{where}: missing fields: {missing}")


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


def digest_paths(paths: list[Path] | tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(ROOT).as_posix()):
        rel = path.relative_to(ROOT).as_posix().encode("utf-8")
        data = path.read_bytes()
        digest.update(rel)
        digest.update(b"\0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\0")
        digest.update(data)
    return "sha256:" + digest.hexdigest()


def configuration_digest() -> str:
    return digest_paths(CONFIGURATION_PATHS)


def vector_suite_digest() -> str:
    paths = [p for p in ROOT.joinpath("vectors").rglob("*") if p.is_file()]
    return digest_paths(paths)


def validate_schema_header(schema: dict[str, Any], where: str) -> dict[str, Any]:
    required_top = {"$schema", "$id", "title", "type", "additionalProperties", "required", "properties"}
    exact_keys(schema, required_top, where, "E_SCHEMA_SHAPE")
    require(schema["$schema"] == JSON_SCHEMA_DRAFT, "E_SCHEMA_DRAFT", f"{where}: unexpected JSON Schema draft")
    require(isinstance(schema["$id"], str) and schema["$id"], "E_SCHEMA_SHAPE", f"{where}: $id must be non-empty")
    require(isinstance(schema["title"], str) and schema["title"], "E_SCHEMA_SHAPE", f"{where}: title must be non-empty")
    require(schema["type"] == "object", "E_SCHEMA_SHAPE", f"{where}: top-level type must be object")
    require(schema["additionalProperties"] is False, "E_SCHEMA_SHAPE", f"{where}: additionalProperties must be false")
    required = schema["required"]
    require(isinstance(required, list), "E_SCHEMA_SHAPE", f"{where}: required must be an array")
    require(len(required) == len(set(required)), "E_SCHEMA_SHAPE", f"{where}: duplicate required field")
    properties = schema["properties"]
    require(isinstance(properties, dict), "E_SCHEMA_SHAPE", f"{where}: properties must be an object")
    return properties


def schema_const(properties: dict[str, Any], field: str, expected: Any, where: str) -> None:
    prop = properties.get(field)
    require(isinstance(prop, dict), "E_SCHEMA_SHAPE", f"{where}.{field}: property must be an object")
    require(prop == {"const": expected}, "E_SCHEMA_SEMANTICS", f"{where}.{field}: const drift detected")


def schema_pattern(properties: dict[str, Any], field: str, expected: str, where: str) -> None:
    prop = properties.get(field)
    require(isinstance(prop, dict), "E_SCHEMA_SHAPE", f"{where}.{field}: property must be an object")
    require(prop.get("type") == "string", "E_SCHEMA_SEMANTICS", f"{where}.{field}: type must be string")
    require(prop.get("pattern") == expected, "E_SCHEMA_SEMANTICS", f"{where}.{field}: pattern drift detected")


def validate_request_schema(schema: dict[str, Any]) -> None:
    where = "route request schema"
    properties = validate_schema_header(schema, where)
    require(set(schema["required"]) == {"protocol", "intent"}, "E_SCHEMA_SEMANTICS", f"{where}: required fields drift detected")
    exact_keys(properties, {"protocol", "intent", "style"}, f"{where}.properties", "E_SCHEMA_SHAPE")
    schema_const(properties, "protocol", "QSOL-THOTH/ROUTE-REQUEST/1", where)
    schema_pattern(properties, "intent", "^[a-z0-9_.-]+$", where)
    schema_pattern(properties, "style", "^[a-z0-9_.-]+$", where)


def validate_decision_schema(schema: dict[str, Any]) -> None:
    where = "route decision schema"
    properties = validate_schema_header(schema, where)
    required = {
        "protocol", "canonical_intent", "style", "concaps",
        "request_sha256", "configuration_sha256", "implementation_sha256",
        "decision_sha256", "boundaries",
    }
    require(set(schema["required"]) == required, "E_SCHEMA_SEMANTICS", f"{where}: required fields drift detected")
    exact_keys(properties, required, f"{where}.properties", "E_SCHEMA_SHAPE")
    schema_const(properties, "protocol", "QSOL-THOTH/ROUTE-DECISION/1", where)
    schema_pattern(properties, "canonical_intent", "^[a-z0-9_.-]+$", where)
    schema_pattern(properties, "style", "^[a-z0-9_.-]+$", where)
    for field in ("request_sha256", "configuration_sha256", "implementation_sha256", "decision_sha256"):
        schema_pattern(properties, field, "^sha256:[0-9a-f]{64}$", where)
    for field in ("concaps", "boundaries"):
        prop = properties[field]
        require(isinstance(prop, dict) and prop.get("type") == "array", "E_SCHEMA_SEMANTICS", f"{where}.{field}: type must be array")
        require(prop.get("uniqueItems") is True, "E_SCHEMA_SEMANTICS", f"{where}.{field}: uniqueItems must be true")
        require(
            prop.get("items") == {"type":"string", "minLength":1},
            "E_SCHEMA_SEMANTICS",
            f"{where}.{field}: items must be non-empty strings",
        )


def validate_registry_schema(schema: dict[str, Any]) -> None:
    where = "CONCAP registry schema"
    properties = validate_schema_header(schema, where)
    required = {"protocol","schema_version","namespace","expansion","authority","capsules","boundaries"}
    require(set(schema["required"]) == required, "E_SCHEMA_SEMANTICS", f"{where}: required fields drift detected")
    exact_keys(properties, required, f"{where}.properties", "E_SCHEMA_SHAPE")
    schema_const(properties, "protocol", "QSOL-THOTH/CONCAP-REGISTRY/1", where)
    schema_const(properties, "namespace", "CONCAP", where)
    schema_const(properties, "expansion", "CONtext CAPsules", where)
    schema_const(properties, "authority", "semantic-routing-only", where)
    schema_pattern(properties, "schema_version", "^[1-9][0-9]*\\.[0-9]+\\.[0-9]+$", where)
    capsules = properties["capsules"]
    require(isinstance(capsules, dict) and capsules.get("type") == "array", "E_SCHEMA_SEMANTICS", f"{where}.capsules must be array")
    item_props = capsules.get("items", {}).get("properties", {})
    schema_pattern(item_props, "id", "^concap\\.[a-z0-9_.-]+/[1-9][0-9]*$", f"{where}.capsules.items")
    schema_const(item_props, "default_privacy", "RESTRICTED", f"{where}.capsules.items")
    schema_const(item_props, "epistemic_authority", "none-by-routing", f"{where}.capsules.items")


def validate_style_schema(schema: dict[str, Any]) -> None:
    where = "ESS style schema"
    properties = validate_schema_header(schema, where)
    required = {"protocol","schema_version","selection","states","transition_contract","boundaries"}
    require(set(schema["required"]) == required, "E_SCHEMA_SEMANTICS", f"{where}: required fields drift detected")
    exact_keys(properties, required, f"{where}.properties", "E_SCHEMA_SHAPE")
    schema_const(properties, "protocol", "QSOL-THOTH/ESS-STYLE/1", where)
    states = properties["states"]
    require(isinstance(states, dict) and states.get("type") == "array", "E_SCHEMA_SEMANTICS", f"{where}.states must be array")
    item_props = states.get("items", {}).get("properties", {})
    schema_pattern(item_props, "id", "^[a-z0-9_.-]+$", f"{where}.states.items")
    support = item_props.get("support_concaps", {})
    require(support.get("uniqueItems") is True, "E_SCHEMA_SEMANTICS", f"{where}: support_concaps must be unique")


def validate_router_schema(schema: dict[str, Any]) -> None:
    where = "router schema"
    properties = validate_schema_header(schema, where)
    required = {"protocol","schema_version","unknown_intent_policy","intent_token_pattern","routes","selection_contract","boundaries"}
    require(set(schema["required"]) == required, "E_SCHEMA_SEMANTICS", f"{where}: required fields drift detected")
    exact_keys(properties, required, f"{where}.properties", "E_SCHEMA_SHAPE")
    schema_const(properties, "protocol", "QSOL-THOTH/ROUTER/1", where)
    schema_const(properties, "unknown_intent_policy", "fail_closed", where)
    schema_const(properties, "intent_token_pattern", "^[a-z0-9_.-]+$", where)
    routes = properties["routes"]
    require(isinstance(routes, dict) and routes.get("type") == "array", "E_SCHEMA_SEMANTICS", f"{where}.routes must be array")
    item_props = routes.get("items", {}).get("properties", {})
    schema_pattern(item_props, "intent", "^[a-z0-9_.-]+$", f"{where}.routes.items")
    aliases = item_props.get("aliases", {})
    require(aliases.get("uniqueItems") is True, "E_SCHEMA_SEMANTICS", f"{where}: aliases must be unique")


def validate_compatibility_schema(schema: dict[str, Any]) -> None:
    where = "CONCAP compatibility schema"
    properties = validate_schema_header(schema, where)
    required = {"protocol","schema_version","role_versioning","allowed_in_place_changes","requires_new_role_version","boundaries"}
    require(set(schema["required"]) == required, "E_SCHEMA_SEMANTICS", f"{where}: required fields drift detected")
    exact_keys(properties, required, f"{where}.properties", "E_SCHEMA_SHAPE")
    schema_const(properties, "protocol", "QSOL-THOTH/CONCAP-COMPATIBILITY/1", where)
    role = properties["role_versioning"]
    require(isinstance(role, dict) and role.get("type") == "object", "E_SCHEMA_SEMANTICS", f"{where}.role_versioning must be object")
    role_props = role.get("properties", {})
    schema_const(role_props, "id_pattern", "^concap\\.[a-z0-9_.-]+/[1-9][0-9]*$", f"{where}.role_versioning")


def validate_instance_against_schema(value: Any, schema: dict[str, Any], where: str) -> None:
    """Validate the JSON-Schema subset used by THOTH, without third-party code."""
    if "const" in schema:
        require(value == schema["const"], "E_SCHEMA_INSTANCE", f"{where}: const mismatch")
    if "enum" in schema:
        require(value in schema["enum"], "E_SCHEMA_INSTANCE", f"{where}: value outside enum")

    expected_type = schema.get("type")
    if expected_type == "object":
        require(isinstance(value, dict), "E_SCHEMA_INSTANCE", f"{where}: expected object")
        required = schema.get("required", [])
        require(all(field in value for field in required), "E_SCHEMA_INSTANCE", f"{where}: missing required field")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            require(set(value) <= set(properties), "E_SCHEMA_INSTANCE", f"{where}: additional property")
        for field, field_value in value.items():
            if field in properties:
                validate_instance_against_schema(field_value, properties[field], f"{where}.{field}")
    elif expected_type == "array":
        require(isinstance(value, list), "E_SCHEMA_INSTANCE", f"{where}: expected array")
        if "minItems" in schema:
            require(len(value) >= schema["minItems"], "E_SCHEMA_INSTANCE", f"{where}: too few items")
        if schema.get("uniqueItems") is True:
            encoded = [canonical_bytes(item) for item in value]
            require(len(encoded) == len(set(encoded)), "E_SCHEMA_INSTANCE", f"{where}: duplicate items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                validate_instance_against_schema(item, item_schema, f"{where}[{index}]")
    elif expected_type == "string":
        require(isinstance(value, str), "E_SCHEMA_INSTANCE", f"{where}: expected string")
        if "minLength" in schema:
            require(len(value) >= schema["minLength"], "E_SCHEMA_INSTANCE", f"{where}: string too short")
        if "pattern" in schema:
            require(re.fullmatch(schema["pattern"], value) is not None, "E_SCHEMA_INSTANCE", f"{where}: pattern mismatch")
    elif expected_type == "integer":
        require(isinstance(value, int) and not isinstance(value, bool), "E_SCHEMA_INSTANCE", f"{where}: expected integer")
        if "minimum" in schema:
            require(value >= schema["minimum"], "E_SCHEMA_INSTANCE", f"{where}: below minimum")
    elif expected_type == "boolean":
        require(isinstance(value, bool), "E_SCHEMA_INSTANCE", f"{where}: expected boolean")


def validate_registry(registry: dict[str, Any]) -> tuple[dict[str, int], set[str]]:
    exact_keys(registry, {"protocol","schema_version","namespace","expansion","authority","capsules","boundaries"}, "CONCAP registry")
    require(registry["protocol"] == "QSOL-THOTH/CONCAP-REGISTRY/1", "E_REGISTRY_PROTOCOL", "unexpected CONCAP registry protocol")
    require(isinstance(registry["schema_version"], str) and SEMVER.fullmatch(registry["schema_version"]), "E_REGISTRY_VERSION", "invalid registry schema_version")
    require(registry["namespace"] == "CONCAP", "E_REGISTRY_NAMESPACE", "registry namespace must be CONCAP")
    require(registry["expansion"] == "CONtext CAPsules", "E_REGISTRY_EXPANSION", "CONCAP expansion drift detected")
    require(registry["authority"] == "semantic-routing-only", "E_REGISTRY_AUTHORITY", "registry authority drift detected")
    capsules = registry["capsules"]
    require(isinstance(capsules, list) and capsules, "E_REGISTRY_CAPSULES", "registry capsules must be a non-empty array")

    order_by_id: dict[str, int] = {}
    orders: set[int] = set()
    for index, item in enumerate(capsules):
        require(isinstance(item, dict), "E_REGISTRY_ITEM", f"registry capsule {index} must be an object")
        exact_keys(item, {"id","order","role","default_privacy","epistemic_authority","style_authority"}, f"registry capsule {index}")
        capsule_id = item["id"]
        order = item["order"]
        require(isinstance(capsule_id, str) and CONCAP_ID.fullmatch(capsule_id), "E_REGISTRY_ROLE_ID", f"invalid CONCAP id: {capsule_id!r}")
        require(capsule_id not in order_by_id, "E_REGISTRY_DUPLICATE_ID", f"duplicate CONCAP id: {capsule_id}")
        require(isinstance(order, int) and not isinstance(order, bool) and order > 0, "E_REGISTRY_ORDER", f"invalid CONCAP order for {capsule_id}")
        require(order not in orders, "E_REGISTRY_DUPLICATE_ORDER", f"duplicate CONCAP order: {order}")
        require(isinstance(item["role"], str) and item["role"], "E_REGISTRY_ROLE", f"{capsule_id}: role must be non-empty")
        require(item["default_privacy"] == "RESTRICTED", "E_REGISTRY_PRIVACY", f"{capsule_id}: default privacy must be RESTRICTED")
        require(item["epistemic_authority"] == "none-by-routing", "E_REGISTRY_AUTHORITY", f"{capsule_id}: routing must not grant epistemic authority")
        require(item["style_authority"] in {"none","receiver-guidance"}, "E_REGISTRY_STYLE_AUTHORITY", f"{capsule_id}: invalid style authority")
        order_by_id[capsule_id] = order
        orders.add(order)

    boundaries = registry["boundaries"]
    require(isinstance(boundaries, list) and len(boundaries) == len(set(boundaries)), "E_REGISTRY_BOUNDARIES", "registry boundaries must be a unique array")
    require("CONCAP_ID != CAPSULE_BYTES" in boundaries, "E_REGISTRY_BOUNDARIES", "registry missing byte-identity boundary")
    return order_by_id, set(order_by_id)


def validate_compatibility_policy(policy: dict[str, Any]) -> None:
    exact_keys(policy, {"protocol","schema_version","role_versioning","allowed_in_place_changes","requires_new_role_version","boundaries"}, "CONCAP compatibility policy")
    require(policy["protocol"] == "QSOL-THOTH/CONCAP-COMPATIBILITY/1", "E_COMPAT_PROTOCOL", "unexpected compatibility protocol")
    require(isinstance(policy["schema_version"], str) and SEMVER.fullmatch(policy["schema_version"]), "E_COMPAT_VERSION", "invalid compatibility schema_version")
    role = policy["role_versioning"]
    require(isinstance(role, dict), "E_COMPAT_POLICY", "role_versioning must be an object")
    exact_keys(role, {"id_pattern","semantic_change_requires_new_version","existing_version_semantics_immutable","new_version_backward_compatible_by_default","implicit_version_substitution","resolver_must_match_exact_declared_role_id"}, "role_versioning")
    require(role["id_pattern"] == r"^concap\.[a-z0-9_.-]+/[1-9][0-9]*$", "E_COMPAT_POLICY", "role id pattern drift detected")
    require(role["semantic_change_requires_new_version"] is True, "E_COMPAT_POLICY", "semantic changes must require a new role version")
    require(role["existing_version_semantics_immutable"] is True, "E_COMPAT_POLICY", "existing role semantics must be immutable")
    require(role["new_version_backward_compatible_by_default"] is False, "E_COMPAT_POLICY", "new versions must not be assumed compatible")
    require(role["implicit_version_substitution"] is False, "E_COMPAT_POLICY", "implicit role-version substitution must remain disabled")
    require(role["resolver_must_match_exact_declared_role_id"] is True, "E_COMPAT_POLICY", "resolver must match exact role id")
    for field in ("allowed_in_place_changes","requires_new_role_version","boundaries"):
        value = policy[field]
        require(isinstance(value, list) and value, "E_COMPAT_POLICY", f"{field} must be a non-empty array")
    require("NEW_ROLE_VERSION != BACKWARD_COMPATIBLE_BY_DEFAULT" in policy["boundaries"], "E_COMPAT_POLICY", "compatibility boundary missing")


def validate_style_machine(style_machine: dict[str, Any], known_capsules: set[str]) -> set[str]:
    exact_keys(style_machine, {"protocol","schema_version","selection","states","transition_contract","boundaries"}, "ESS style machine")
    require(style_machine["protocol"] == "QSOL-THOTH/ESS-STYLE/1", "E_STYLE_PROTOCOL", "unexpected ESS style protocol")
    require(isinstance(style_machine["schema_version"], str) and SEMVER.fullmatch(style_machine["schema_version"]), "E_STYLE_VERSION", "invalid ESS schema_version")
    selection = style_machine["selection"]
    require(isinstance(selection, dict), "E_STYLE_SELECTION", "ESS selection must be an object")
    exact_keys(selection, {"explicit_declared_style_wins","otherwise_use_route_default","unknown_style_policy","tie_break"}, "ESS selection")
    require(selection["explicit_declared_style_wins"] is True, "E_STYLE_SELECTION", "explicit declared style must win")
    require(selection["otherwise_use_route_default"] is True, "E_STYLE_SELECTION", "route default style fallback required")
    require(selection["unknown_style_policy"] == "fail_closed", "E_STYLE_SELECTION", "unknown style policy must fail closed")
    require(selection["tie_break"] == "none-required-exact-token-selection", "E_STYLE_SELECTION", "style tie-break drift detected")

    states = style_machine["states"]
    require(isinstance(states, list) and states, "E_STYLE_STATES", "ESS states must be a non-empty array")
    style_ids: set[str] = set()
    orders: set[int] = set()
    for index, state in enumerate(states):
        require(isinstance(state, dict), "E_STYLE_STATE", f"ESS state {index} must be an object")
        exact_keys(state, {"id","order","receiver_role","support_concaps"}, f"ESS state {index}")
        style_id = state["id"]
        order = state["order"]
        require(isinstance(style_id, str) and TOKEN.fullmatch(style_id), "E_STYLE_ID", f"invalid ESS style id: {style_id!r}")
        require(style_id not in style_ids, "E_STYLE_DUPLICATE_ID", f"duplicate ESS style id: {style_id}")
        require(isinstance(order, int) and not isinstance(order, bool) and order > 0, "E_STYLE_ORDER", f"invalid ESS style order: {style_id}")
        require(order not in orders, "E_STYLE_DUPLICATE_ORDER", f"duplicate ESS style order: {order}")
        require(isinstance(state["receiver_role"], str) and state["receiver_role"], "E_STYLE_ROLE", f"{style_id}: receiver_role must be non-empty")
        support = state["support_concaps"]
        require(isinstance(support, list), "E_STYLE_SUPPORT", f"{style_id}: support_concaps must be an array")
        require(len(support) == len(set(support)), "E_STYLE_DUPLICATE_SUPPORT", f"{style_id}: duplicate support CONCAP")
        for capsule_id in support:
            require(capsule_id in known_capsules, "E_STYLE_UNKNOWN_CONCAP", f"{style_id}: unknown support CONCAP {capsule_id}")
        style_ids.add(style_id)
        orders.add(order)

    transition = style_machine["transition_contract"]
    require(isinstance(transition, dict), "E_STYLE_TRANSITION", "transition_contract must be object")
    require(transition.get("model_inferred_style_switching") is False, "E_STYLE_TRANSITION", "model inferred switching must remain disabled")
    require(transition.get("wall_clock_input") is False, "E_STYLE_TRANSITION", "wall clock input must remain disabled")
    require(transition.get("random_input") is False, "E_STYLE_TRANSITION", "random input must remain disabled")
    require(transition.get("network_input") is False, "E_STYLE_TRANSITION", "network input must remain disabled")
    boundaries = style_machine["boundaries"]
    require(isinstance(boundaries, list), "E_STYLE_BOUNDARIES", "ESS boundaries must be an array")
    require("STYLE_SWITCH != EPISTEMIC_SWITCH" in boundaries, "E_STYLE_BOUNDARIES", "ESS machine missing epistemic boundary")
    require("STYLE_SUPPORT != EVIDENCE" in boundaries, "E_STYLE_BOUNDARIES", "ESS machine missing evidence boundary")
    return style_ids


def validate_router(router: dict[str, Any], known_capsules: set[str], style_ids: set[str]) -> dict[str, dict[str, Any]]:
    exact_keys(router, {"protocol","schema_version","unknown_intent_policy","intent_token_pattern","routes","selection_contract","boundaries"}, "router")
    require(router["protocol"] == "QSOL-THOTH/ROUTER/1", "E_ROUTER_PROTOCOL", "unexpected router protocol")
    require(isinstance(router["schema_version"], str) and SEMVER.fullmatch(router["schema_version"]), "E_ROUTER_VERSION", "invalid router schema_version")
    require(router["unknown_intent_policy"] == "fail_closed", "E_ROUTER_POLICY", "unknown intent policy must fail closed")
    require(router["intent_token_pattern"] == "^[a-z0-9_.-]+$", "E_ROUTER_TOKEN_PATTERN", "intent token grammar drift detected")

    routes = router["routes"]
    require(isinstance(routes, list) and routes, "E_ROUTER_ROUTES", "router routes must be a non-empty array")
    token_map: dict[str, dict[str, Any]] = {}
    canonical_intents: set[str] = set()
    route_orders: set[int] = set()
    for index, route in enumerate(routes):
        require(isinstance(route, dict), "E_ROUTER_ROUTE", f"route {index} must be an object")
        exact_keys(route, {"intent","aliases","order","default_style","concaps"}, f"route {index}")
        intent = route["intent"]
        aliases = route["aliases"]
        order = route["order"]
        default_style = route["default_style"]
        concaps = route["concaps"]

        require(isinstance(intent, str) and TOKEN.fullmatch(intent), "E_ROUTER_INTENT", f"invalid route intent: {intent!r}")
        require(intent not in canonical_intents, "E_ROUTER_DUPLICATE_INTENT", f"duplicate canonical intent: {intent}")
        require(isinstance(order, int) and not isinstance(order, bool) and order > 0, "E_ROUTER_ORDER", f"invalid route order: {intent}")
        require(order not in route_orders, "E_ROUTER_DUPLICATE_ORDER", f"duplicate route order: {order}")
        require(default_style in style_ids, "E_ROUTER_UNKNOWN_STYLE", f"{intent}: unknown default style {default_style}")
        require(isinstance(aliases, list) and len(aliases) == len(set(aliases)), "E_ROUTER_ALIASES", f"{intent}: aliases must be a unique array")
        require(isinstance(concaps, list) and concaps, "E_ROUTER_CONCAPS", f"{intent}: concaps must be a non-empty array")
        require(len(concaps) == len(set(concaps)), "E_ROUTER_DUPLICATE_CONCAP", f"{intent}: duplicate CONCAP")
        for capsule_id in concaps:
            require(capsule_id in known_capsules, "E_ROUTER_UNKNOWN_CONCAP", f"{intent}: unknown CONCAP {capsule_id}")

        canonical_intents.add(intent)
        route_orders.add(order)
        for token in [intent, *aliases]:
            require(isinstance(token, str) and TOKEN.fullmatch(token), "E_ROUTER_TOKEN", f"{intent}: invalid route token {token!r}")
            require(token not in token_map, "E_ROUTER_AMBIGUOUS_TOKEN", f"ambiguous route token: {token}")
            token_map[token] = route

    selection = router["selection_contract"]
    require(isinstance(selection, dict), "E_ROUTER_SELECTION", "selection_contract must be object")
    require(selection.get("canonical_matching") == "exact ASCII token", "E_ROUTER_SELECTION", "canonical matching drift detected")
    require(selection.get("alias_resolution") == "exact declared alias only", "E_ROUTER_SELECTION", "alias resolution drift detected")
    require(selection.get("fuzzy_matching") is False, "E_ROUTER_SELECTION", "fuzzy matching must remain disabled")
    require(selection.get("embedding_matching") is False, "E_ROUTER_SELECTION", "embedding matching must remain disabled")
    require(selection.get("model_guessing") is False, "E_ROUTER_SELECTION", "model guessing must remain disabled")
    boundaries = router["boundaries"]
    require(isinstance(boundaries, list), "E_ROUTER_BOUNDARIES", "router boundaries must be an array")
    require("ROUTING != FACTUAL_AUTHORITY" in boundaries, "E_ROUTER_BOUNDARIES", "router missing factual-authority boundary")
    require("ROUTE_DECISION != CAPSULE_AVAILABILITY" in boundaries, "E_ROUTER_BOUNDARIES", "router missing capsule-availability boundary")
    return token_map


def load_and_validate() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, int], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    registry = load_json(REGISTRY_PATH)
    compatibility = load_json(COMPATIBILITY_PATH)
    style_machine = load_json(STYLE_PATH)
    router = load_json(ROUTER_PATH)

    registry_schema = load_json(REGISTRY_SCHEMA_PATH)
    compatibility_schema = load_json(COMPATIBILITY_SCHEMA_PATH)
    style_schema = load_json(STYLE_SCHEMA_PATH)
    router_schema = load_json(ROUTER_SCHEMA_PATH)
    request_schema = load_json(REQUEST_SCHEMA_PATH)
    decision_schema = load_json(DECISION_SCHEMA_PATH)

    validate_registry_schema(registry_schema)
    validate_compatibility_schema(compatibility_schema)
    validate_style_schema(style_schema)
    validate_router_schema(router_schema)
    validate_request_schema(request_schema)
    validate_decision_schema(decision_schema)

    validate_instance_against_schema(registry, registry_schema, "ai/concap-registry.json")
    validate_instance_against_schema(compatibility, compatibility_schema, "ai/concap-compatibility.json")
    validate_instance_against_schema(style_machine, style_schema, "ai/ess-style-machine.json")
    validate_instance_against_schema(router, router_schema, "ai/router.json")

    order_by_id, known_capsules = validate_registry(registry)
    validate_compatibility_policy(compatibility)
    style_ids = validate_style_machine(style_machine, known_capsules)
    token_map = validate_router(router, known_capsules, style_ids)
    states_by_id = {state["id"]: state for state in style_machine["states"]}
    return registry, style_machine, router, order_by_id, token_map, states_by_id


def validate_request(request: dict[str, Any]) -> None:
    allowed = {"protocol","intent","style"}
    extra = sorted(set(request) - allowed)
    require(not extra, "E_REQUEST_FIELDS", f"route request has unsupported fields: {extra}")
    require(set(request) >= {"protocol","intent"}, "E_REQUEST_FIELDS", "route request requires protocol and intent")
    require(request["protocol"] == "QSOL-THOTH/ROUTE-REQUEST/1", "E_REQUEST_PROTOCOL", "unexpected route request protocol")
    intent = request["intent"]
    require(isinstance(intent, str) and TOKEN.fullmatch(intent), "E_REQUEST_INTENT", "route request intent must be an exact ASCII token")
    if "style" in request:
        style = request["style"]
        require(isinstance(style, str) and TOKEN.fullmatch(style), "E_REQUEST_STYLE", "route request style must be an exact ASCII token")


def route_with_contracts(
    request: dict[str, Any],
    registry: dict[str, Any],
    style_machine: dict[str, Any],
    router: dict[str, Any],
    *,
    config_sha: str,
    implementation_sha: str,
) -> dict[str, Any]:
    order_by_id, known_capsules = validate_registry(registry)
    style_ids = validate_style_machine(style_machine, known_capsules)
    token_map = validate_router(router, known_capsules, style_ids)
    states_by_id = {state["id"]: state for state in style_machine["states"]}
    validate_request(request)

    token = request["intent"]
    route = token_map.get(token)
    require(route is not None, "E_ROUTE_UNKNOWN_INTENT", f"unknown intent: {token}")
    style_id = request.get("style", route["default_style"])
    require(style_id in states_by_id, "E_ROUTE_UNKNOWN_STYLE", f"unknown style: {style_id}")
    state = states_by_id[style_id]

    selected = set(route["concaps"])
    selected.update(state["support_concaps"])
    ordered = sorted(selected, key=lambda capsule_id: (order_by_id[capsule_id], capsule_id.encode("utf-8")))

    base = {
        "protocol":"QSOL-THOTH/ROUTE-DECISION/1",
        "canonical_intent":route["intent"],
        "style":style_id,
        "concaps":ordered,
        "request_sha256":digest_bytes(canonical_bytes(request)),
        "configuration_sha256":config_sha,
        "implementation_sha256":implementation_sha,
        "boundaries":list(DECISION_BOUNDARIES),
    }
    return {**base, "decision_sha256":digest_bytes(canonical_bytes(base))}


def route_request(request: dict[str, Any]) -> dict[str, Any]:
    registry, style_machine, router, _, _, _ = load_and_validate()
    return route_with_contracts(
        request, registry, style_machine, router,
        config_sha=configuration_digest(),
        implementation_sha=digest_file(IMPLEMENTATION_PATH),
    )


def load_positive_vectors() -> list[dict[str, Any]]:
    vectors = []
    for path in sorted(POSITIVE_VECTOR_DIR.glob("*.json")):
        vector = load_json(path)
        exact_keys(vector, {"protocol","id","request","expected_decision"}, path_label(path))
        require(vector["protocol"] == "QSOL-THOTH/POSITIVE-VECTOR/1", "E_VECTOR_PROTOCOL", f"{path_label(path)}: protocol mismatch")
        require(isinstance(vector["id"], str) and TOKEN.fullmatch(vector["id"]), "E_VECTOR_ID", f"{path_label(path)}: invalid id")
        require(isinstance(vector["request"], dict), "E_VECTOR_SHAPE", f"{path_label(path)}: request must be object")
        require(isinstance(vector["expected_decision"], dict), "E_VECTOR_SHAPE", f"{path_label(path)}: expected_decision must be object")
        vectors.append(vector)
    require(bool(vectors), "E_VECTOR_EMPTY", "no positive conformance vectors found")
    return vectors


def exercise_negative_vector(vector: dict[str, Any]) -> str:
    exact_keys(vector, {"protocol","id","case","expected_error","parameters"}, f"negative vector {vector.get('id','?')}")
    require(vector["protocol"] == "QSOL-THOTH/NEGATIVE-VECTOR/1", "E_VECTOR_PROTOCOL", "negative vector protocol mismatch")
    case = vector["case"]
    params = vector["parameters"]
    require(isinstance(params, dict), "E_VECTOR_SHAPE", "negative vector parameters must be object")

    raw_fixture: Path | None = None
    if case == "raw_request_file":
        exact_keys(params, {"fixture"}, f"negative vector {vector.get('id','?')} parameters", "E_VECTOR_SHAPE")
        fixture_name = params.get("fixture")
        require(isinstance(fixture_name, str) and fixture_name, "E_VECTOR_SHAPE", "raw_request_file fixture must be a non-empty string")
        fixture_rel = Path(fixture_name)
        require(not fixture_rel.is_absolute() and ".." not in fixture_rel.parts, "E_VECTOR_SHAPE", "raw_request_file fixture must be repository-relative")
        raw_fixture = ROOT / fixture_rel

    registry = load_json(REGISTRY_PATH)
    style_machine = load_json(STYLE_PATH)
    router = load_json(ROUTER_PATH)

    try:
        if case == "registry_duplicate_id":
            registry = copy.deepcopy(registry)
            registry["capsules"][1]["id"] = registry["capsules"][0]["id"]
            validate_registry(registry)
        elif case == "registry_invalid_version":
            registry = copy.deepcopy(registry)
            registry["capsules"][0]["id"] = "concap.identity.core/0"
            validate_registry(registry)
        elif case == "router_ambiguous_alias":
            _, known = validate_registry(registry)
            styles_known = validate_style_machine(style_machine, known)
            router = copy.deepcopy(router)
            first_route = router["routes"][0]
            first_route["aliases"].append(first_route["intent"])
            validate_router(router, known, styles_known)
        elif case == "style_unknown_support_concap":
            _, known = validate_registry(registry)
            style_machine = copy.deepcopy(style_machine)
            style_machine["states"][0]["support_concaps"].append("concap.does.not.exist/1")
            validate_style_machine(style_machine, known)
        elif case == "request_unknown_intent":
            route_request({"protocol":"QSOL-THOTH/ROUTE-REQUEST/1","intent":params.get("intent","missing_intent")})
        elif case == "request_unknown_style":
            route_request({"protocol":"QSOL-THOTH/ROUTE-REQUEST/1","intent":"general","style":params.get("style","missing_style")})
        elif case == "raw_request_file":
            require(raw_fixture is not None, "E_VECTOR_SHAPE", "raw_request_file fixture was not prepared")
            load_json(raw_fixture)
        else:
            fail("E_VECTOR_CASE", f"unsupported negative vector case: {case}")
    except ThothError as exc:
        return exc.code
    fail("E_VECTOR_DID_NOT_FAIL", f"negative vector unexpectedly succeeded: {vector['id']}")


def load_negative_vectors() -> list[dict[str, Any]]:
    vectors = []
    for path in sorted(NEGATIVE_VECTOR_DIR.glob("*.vector.json")):
        vector = load_json(path)
        vectors.append(vector)
    require(bool(vectors), "E_VECTOR_EMPTY", "no negative conformance vectors found")
    return vectors


def run_conformance() -> dict[str, Any]:
    load_and_validate()
    positive = load_positive_vectors()
    negative = load_negative_vectors()

    for vector in positive:
        actual = route_request(vector["request"])
        expected = vector["expected_decision"]
        require(
            canonical_bytes(actual) == canonical_bytes(expected),
            "E_CONFORMANCE_KNOWN_ANSWER",
            f"positive vector drift: {vector['id']}",
        )
        claimed = actual["decision_sha256"]
        body = dict(actual)
        body.pop("decision_sha256")
        require(claimed == digest_bytes(canonical_bytes(body)), "E_CONFORMANCE_RECEIPT", f"decision hash mismatch: {vector['id']}")

    for vector in negative:
        actual_code = exercise_negative_vector(vector)
        require(actual_code == vector["expected_error"], "E_CONFORMANCE_NEGATIVE", f"{vector['id']}: expected {vector['expected_error']} got {actual_code}")

    return {
        "protocol":"QSOL-THOTH/CONFORMANCE-REPORT/1",
        "configuration_sha256":configuration_digest(),
        "implementation_sha256":digest_file(IMPLEMENTATION_PATH),
        "vector_suite_sha256":vector_suite_digest(),
        "positive_vectors":len(positive),
        "negative_vectors":len(negative),
        "status":"ok",
    }


def command_validate() -> int:
    registry, style_machine, router, _, _, _ = load_and_validate()
    report = {
        "protocol":"QSOL-THOTH/VALIDATION-REPORT/1",
        "configuration_sha256":configuration_digest(),
        "implementation_sha256":digest_file(IMPLEMENTATION_PATH),
        "concap_count":len(registry["capsules"]),
        "style_count":len(style_machine["states"]),
        "route_count":len(router["routes"]),
        "status":"ok",
    }
    print(canonical_bytes(report).decode("utf-8"))
    return 0


def command_route(args: argparse.Namespace) -> int:
    if args.request:
        request_path = Path(args.request)
        if request_path.is_symlink():
            fail("E_IO_SYMLINK", "route request file must not be a symlink")
        request = load_json(request_path.resolve())
        require(args.intent is None and args.style is None, "E_REQUEST_ARGUMENTS", "--request cannot be combined with --intent or --style")
    else:
        require(args.intent is not None, "E_REQUEST_ARGUMENTS", "route requires --intent or --request")
        request = {"protocol":"QSOL-THOTH/ROUTE-REQUEST/1","intent":args.intent}
        if args.style is not None:
            request["style"] = args.style
    print(canonical_bytes(route_request(request)).decode("utf-8"))
    return 0


def command_conformance() -> int:
    print(canonical_bytes(run_conformance()).decode("utf-8"))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="thoth")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="validate public THOTH contracts")
    sub.add_parser("conformance", help="replay frozen positive and negative CONCAP vectors")
    route = sub.add_parser("route", help="emit a deterministic CONCAP route decision")
    route.add_argument("--intent")
    route.add_argument("--style")
    route.add_argument("--request")
    args = parser.parse_args()

    try:
        if args.command == "validate":
            return command_validate()
        if args.command == "conformance":
            return command_conformance()
        if args.command == "route":
            return command_route(args)
        fail("E_COMMAND", f"unsupported command: {args.command}")
    except ThothError as exc:
        print(f"FAIL: {exc.code}: {exc.detail}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
