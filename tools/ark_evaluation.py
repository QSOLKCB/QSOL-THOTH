#!/usr/bin/env python3
"""Deterministic THOTH-to-ARK evaluation receipt builder.

All semantic judgements arrive as explicit observations. This tool validates,
counts and hashes them; it does not infer style quality, factual truth or
historical truth from model output.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from deterministic_contract import (
    ContractError,
    canonical_bytes,
    digest,
    exact_keys,
    load_json,
    require,
    require_concap,
    require_sha256,
    require_token,
)

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "ai" / "ark-evaluation-policy.json"
REGISTRY_PATH = ROOT / "ai" / "concap-registry.json"

POLICY_PROTOCOL = "QSOL-THOTH/ARK-EVALUATION-POLICY/1"
OBSERVATION_PROTOCOL = "QSOL-ARK/THOTH-EVALUATION-OBSERVATION/1"
RECEIPT_PROTOCOL = "QSOL-ARK/THOTH-EVALUATION-RECEIPT/1"
VALIDATION_PROTOCOL = "QSOL-THOTH/ARK-EVALUATION-POLICY-VALIDATION/1"
PREFIX = "ARK_EVAL"

DIMENSIONS = (
    ("route_sufficiency", 10, "selected_required_roles_over_declared_required_roles"),
    ("route_minimality", 20, "selected_justified_roles_over_all_selected_roles"),
    ("style_fidelity", 30, "passed_over_assessed_style_obligations"),
    ("factual_accuracy", 40, "correct_over_assessed_claims"),
    ("historical_reconstruction_coverage", 50, "covered_over_assessed_retention_obligations"),
)

TRANSPORTS = (
    "local-directory",
    "archive",
    "static-http",
    "capability-relay",
)

NEGATIVE_CHECKS = (
    "style_leakage",
    "unsupported_historical_interpolation",
    "accidental_private_source_dependency",
)

BOUNDARIES = (
    "STYLE_FIDELITY != FACTUAL_ACCURACY != PHYSICAL_TRUTH",
    "ROUTE_SUFFICIENCY != ROUTE_MINIMALITY",
    "HISTORICAL_COVERAGE != HISTORICAL_TRUTH",
    "TRANSPORT_EQUIVALENCE != AUTHORITY",
    "CLEAN_ROOM_SUCCESS != PRIVATE_SOURCE_ACCESS",
    "MEASURED_OBSERVATION != AUTOMATIC_TRUTH",
    "AGGREGATE_SCORE = FORBIDDEN",
)


def registry_role_order() -> dict[str, int]:
    registry = load_json(REGISTRY_PATH, PREFIX)
    capsules = registry.get("capsules")
    require(isinstance(capsules, list), "E_ARK_EVAL_REGISTRY", "registry capsules must be an array")
    roles: dict[str, int] = {}
    orders: set[int] = set()
    for index, item in enumerate(capsules):
        require(isinstance(item, dict), "E_ARK_EVAL_REGISTRY", f"registry capsules[{index}] must be an object")
        role_id = require_concap(item.get("id"), f"registry capsules[{index}].id", PREFIX)
        require(role_id not in roles, "E_ARK_EVAL_REGISTRY", f"duplicate registry role: {role_id}")
        order = item.get("order")
        require(
            isinstance(order, int) and not isinstance(order, bool) and order > 0,
            "E_ARK_EVAL_REGISTRY",
            f"registry capsules[{index}].order must be a positive integer",
        )
        require(order not in orders, "E_ARK_EVAL_REGISTRY", f"duplicate registry order: {order}")
        roles[role_id] = order
        orders.add(order)
    return roles


def validate_policy(policy: Any) -> dict[str, Any]:
    value = exact_keys(
        policy,
        {
            "protocol",
            "schema_version",
            "authority",
            "dimensions",
            "transport_profiles",
            "clean_room_requirements",
            "negative_space_checks",
            "aggregation",
            "boundaries",
        },
        "ARK evaluation policy",
        PREFIX,
    )
    require(value["protocol"] == POLICY_PROTOCOL, "E_ARK_EVAL_POLICY_PROTOCOL", "unexpected ARK evaluation policy protocol")
    require(value["schema_version"] == "1.0.0", "E_ARK_EVAL_POLICY_VERSION", "unsupported ARK evaluation policy version")
    require(value["authority"] == "measurement-contract-only", "E_ARK_EVAL_POLICY_AUTHORITY", "evaluation policy cannot claim truth authority")
    dimensions = value["dimensions"]
    require(isinstance(dimensions, list) and len(dimensions) == len(DIMENSIONS), "E_ARK_EVAL_POLICY_DIMENSIONS", "dimension count drift")
    observed_dimensions: list[tuple[Any, Any, Any]] = []
    for index, item in enumerate(dimensions):
        item = exact_keys(item, {"id", "order", "measurement"}, f"dimensions[{index}]", PREFIX)
        observed_dimensions.append((item["id"], item["order"], item["measurement"]))
    require(tuple(observed_dimensions) == DIMENSIONS, "E_ARK_EVAL_POLICY_DIMENSIONS", "dimension semantics or ordering drift")
    require(value["transport_profiles"] == list(TRANSPORTS), "E_ARK_EVAL_POLICY_TRANSPORTS", "transport profile set or ordering drift")
    clean = exact_keys(
        value["clean_room_requirements"],
        {
            "portable_inputs_only",
            "private_source_repository_access",
            "private_context_connector_access",
            "hidden_provider_memory_dependency",
        },
        "clean_room_requirements",
        PREFIX,
    )
    require(clean["portable_inputs_only"] is True, "E_ARK_EVAL_POLICY_CLEAN_ROOM", "portable inputs must be required")
    require(clean["private_source_repository_access"] is False, "E_ARK_EVAL_POLICY_CLEAN_ROOM", "private repository access must be forbidden")
    require(clean["private_context_connector_access"] is False, "E_ARK_EVAL_POLICY_CLEAN_ROOM", "private context connector access must be forbidden")
    require(clean["hidden_provider_memory_dependency"] is False, "E_ARK_EVAL_POLICY_CLEAN_ROOM", "hidden provider memory dependency must be forbidden")
    require(value["negative_space_checks"] == list(NEGATIVE_CHECKS), "E_ARK_EVAL_POLICY_NEGATIVE", "negative-space check set or ordering drift")
    require(value["aggregation"] == "forbidden-keep-dimensions-separate", "E_ARK_EVAL_POLICY_AGGREGATION", "dimension aggregation is forbidden")
    require(value["boundaries"] == list(BOUNDARIES), "E_ARK_EVAL_POLICY_BOUNDARIES", "evaluation boundary set drift")
    return value


def policy_validation_report(policy: dict[str, Any]) -> dict[str, Any]:
    checked = validate_policy(policy)
    return {
        "protocol": VALIDATION_PROTOCOL,
        "status": "ok",
        "policy_sha256": digest(checked),
        "dimension_ids": [item[0] for item in DIMENSIONS],
        "transport_profiles": list(TRANSPORTS),
        "aggregation": "none",
        "boundaries": list(BOUNDARIES),
    }


def validate_outcomes(
    value: Any,
    where: str,
    item_key: str,
    allowed: set[str],
) -> list[dict[str, Any]]:
    container = exact_keys(value, {item_key}, where, PREFIX)
    observations = container[item_key]
    require(isinstance(observations, list) and observations, "E_ARK_EVAL_OBSERVATIONS", f"{where}.{item_key} must be non-empty")
    ids: list[str] = []
    out: list[dict[str, Any]] = []
    for index, item in enumerate(observations):
        item = exact_keys(item, {"id", "outcome"}, f"{where}.{item_key}[{index}]", PREFIX)
        observation_id = require_token(item["id"], f"{where}.{item_key}[{index}].id", PREFIX)
        outcome = item["outcome"]
        require(isinstance(outcome, str), "E_ARK_EVAL_OUTCOME", f"{where}.{item_key}[{index}].outcome must be a string")
        require(outcome in allowed, "E_ARK_EVAL_OUTCOME", f"{where}.{item_key}[{index}] has unknown outcome")
        ids.append(observation_id)
        out.append(item)
    require(len(ids) == len(set(ids)), "E_ARK_EVAL_DUPLICATE", f"{where}.{item_key} ids must be unique")
    require(ids == sorted(ids, key=lambda item: item.encode("utf-8")), "E_ARK_EVAL_ORDER", f"{where}.{item_key} must be UTF-8 sorted by id")
    return out


def validate_route(value: Any, role_order: dict[str, int]) -> dict[str, Any]:
    route = exact_keys(value, {"selected_role_ids", "required_role_ids", "justified_role_ids"}, "route", PREFIX)
    for key in ("selected_role_ids", "required_role_ids", "justified_role_ids"):
        roles = route[key]
        require(isinstance(roles, list) and roles, "E_ARK_EVAL_ARRAY", f"route.{key} must be a non-empty array")
        checked = [require_concap(role_id, f"route.{key}[{index}]", PREFIX) for index, role_id in enumerate(roles)]
        require(len(checked) == len(set(checked)), "E_ARK_EVAL_DUPLICATE", f"route.{key} must contain unique entries")
        unknown = sorted(set(checked) - set(role_order), key=lambda item: item.encode("utf-8"))
        require(not unknown, "E_ARK_EVAL_UNKNOWN_ROLE", f"route.{key} contains unregistered roles: {unknown}")
        expected = sorted(checked, key=lambda item: (role_order[item], item.encode("utf-8")))
        require(checked == expected, "E_ARK_EVAL_ORDER", f"route.{key} must follow canonical registry order")
    required = set(route["required_role_ids"])
    justified = set(route["justified_role_ids"])
    require(required <= justified, "E_ARK_EVAL_ROUTE_JUSTIFICATION", "every required role must also be justified")
    return route


def validate_transport_object(value: Any, where: str) -> dict[str, Any]:
    item = exact_keys(value, {"object_id", "size_bytes", "bytes_sha256"}, where, PREFIX)
    object_id = require_sha256(item["object_id"], f"{where}.object_id", PREFIX)
    byte_hash = require_sha256(item["bytes_sha256"], f"{where}.bytes_sha256", PREFIX)
    require(object_id == byte_hash, "E_ARK_EVAL_OBJECT_IDENTITY", f"{where}: object identity must equal exact byte hash")
    size = item["size_bytes"]
    require(isinstance(size, int) and not isinstance(size, bool) and size >= 0, "E_ARK_EVAL_OBJECT_SIZE", f"{where}.size_bytes must be non-negative")
    return item


def validate_transports(value: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    require(isinstance(value, list) and len(value) == len(TRANSPORTS), "E_ARK_EVAL_TRANSPORTS", "transport observation count drift")
    profiles: list[dict[str, Any]] = []
    reference: list[dict[str, Any]] | None = None
    observed_ids: list[str] = []
    for index, item in enumerate(value):
        item = exact_keys(item, {"id", "objects"}, f"transports[{index}]", PREFIX)
        require(item["id"] == TRANSPORTS[index], "E_ARK_EVAL_TRANSPORTS", f"transports[{index}].id or ordering drift")
        objects = item["objects"]
        require(isinstance(objects, list) and objects, "E_ARK_EVAL_TRANSPORT_OBJECTS", f"transports[{index}].objects must be non-empty")
        checked_objects = [
            validate_transport_object(obj, f"transports[{index}].objects[{object_index}]")
            for object_index, obj in enumerate(objects)
        ]
        ids = [obj["object_id"] for obj in checked_objects]
        require(len(ids) == len(set(ids)), "E_ARK_EVAL_DUPLICATE", f"transports[{index}].objects contains duplicates")
        require(ids == sorted(ids, key=lambda item: item.encode("utf-8")), "E_ARK_EVAL_ORDER", f"transports[{index}].objects must be UTF-8 sorted")
        if reference is None:
            reference = checked_objects
        else:
            require(canonical_bytes(reference) == canonical_bytes(checked_objects), "E_ARK_EVAL_TRANSPORT_MISMATCH", f"{item['id']} delivered non-identical object observations")
        observed_ids.append(item["id"])
        profiles.append(item)
    require(observed_ids == list(TRANSPORTS), "E_ARK_EVAL_TRANSPORTS", "required transport profiles missing")
    require(reference is not None, "E_ARK_EVAL_TRANSPORT_OBJECTS", "transport observations must contain objects")
    return profiles, reference


def validate_observation(observation: Any, policy: dict[str, Any]) -> dict[str, Any]:
    value = exact_keys(
        observation,
        {
            "protocol",
            "schema_version",
            "trial_id",
            "assessment_authority",
            "route",
            "style_fidelity",
            "factual_accuracy",
            "historical_reconstruction",
            "clean_room",
            "transports",
            "negative_space",
            "boundaries",
        },
        "evaluation observation",
        PREFIX,
    )
    require(value["protocol"] == OBSERVATION_PROTOCOL, "E_ARK_EVAL_PROTOCOL", "unexpected evaluation observation protocol")
    require(value["schema_version"] == "1.0.0", "E_ARK_EVAL_VERSION", "unsupported evaluation observation version")
    require_token(value["trial_id"], "trial_id", PREFIX)
    require(
        value["assessment_authority"] == "explicit-observations-not-automatic-truth",
        "E_ARK_EVAL_AUTHORITY",
        "evaluation observations cannot claim automatic truth",
    )
    validate_route(value["route"], registry_role_order())
    style = validate_outcomes(value["style_fidelity"], "style_fidelity", "obligations", {"pass", "fail", "not_observed"})
    facts = validate_outcomes(value["factual_accuracy"], "factual_accuracy", "claims", {"correct", "incorrect", "unverified"})
    historical = validate_outcomes(value["historical_reconstruction"], "historical_reconstruction", "obligations", {"covered", "missed", "unverified"})
    require(any(item["outcome"] in {"pass", "fail"} for item in style), "E_ARK_EVAL_UNASSESSED", "style_fidelity has no assessed obligations")
    require(any(item["outcome"] in {"correct", "incorrect"} for item in facts), "E_ARK_EVAL_UNASSESSED", "factual_accuracy has no assessed claims")
    require(any(item["outcome"] in {"covered", "missed"} for item in historical), "E_ARK_EVAL_UNASSESSED", "historical reconstruction has no assessed obligations")

    clean = exact_keys(
        value["clean_room"],
        {
            "portable_inputs_only",
            "private_source_repository_access",
            "private_context_connector_access",
            "hidden_provider_memory_dependency",
        },
        "clean_room",
        PREFIX,
    )
    for key, expected in policy["clean_room_requirements"].items():
        require(clean[key] is expected, "E_ARK_EVAL_CLEAN_ROOM", f"clean_room.{key} violates the clean-room contract")
    validate_transports(value["transports"])
    negative = exact_keys(value["negative_space"], set(NEGATIVE_CHECKS), "negative_space", PREFIX)
    for check in NEGATIVE_CHECKS:
        require(negative[check] is False, "E_ARK_EVAL_NEGATIVE_SPACE", f"negative-space violation: {check}")
    require(value["boundaries"] == list(BOUNDARIES), "E_ARK_EVAL_BOUNDARIES", "evaluation observation boundary set drift")
    return value


def fraction(numerator: int, denominator: int) -> dict[str, int]:
    require(denominator > 0, "E_ARK_EVAL_DENOMINATOR", "measurement denominator must be positive")
    return {"numerator": numerator, "denominator": denominator}


def count_outcomes(items: list[dict[str, Any]], outcomes: tuple[str, ...]) -> dict[str, int]:
    return {outcome: sum(1 for item in items if item["outcome"] == outcome) for outcome in outcomes}


def evaluate(observation: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    checked_policy = validate_policy(policy)
    checked = validate_observation(observation, checked_policy)
    selected = set(checked["route"]["selected_role_ids"])
    required = set(checked["route"]["required_role_ids"])
    justified = set(checked["route"]["justified_role_ids"])
    role_order = registry_role_order()
    missing = sorted(required - selected, key=lambda item: (role_order[item], item.encode("utf-8")))
    unjustified = sorted(selected - justified, key=lambda item: (role_order[item], item.encode("utf-8")))

    style_items = checked["style_fidelity"]["obligations"]
    style_counts = count_outcomes(style_items, ("pass", "fail", "not_observed"))
    fact_items = checked["factual_accuracy"]["claims"]
    fact_counts = count_outcomes(fact_items, ("correct", "incorrect", "unverified"))
    history_items = checked["historical_reconstruction"]["obligations"]
    history_counts = count_outcomes(history_items, ("covered", "missed", "unverified"))
    _, reference_objects = validate_transports(checked["transports"])

    body = {
        "protocol": RECEIPT_PROTOCOL,
        "trial_id": checked["trial_id"],
        "policy_sha256": digest(checked_policy),
        "observation_sha256": digest(checked),
        "metrics": {
            "route_sufficiency": {
                "fraction": fraction(len(required & selected), len(required)),
                "missing_required_roles": missing,
            },
            "route_minimality": {
                "fraction": fraction(len(selected & justified), len(selected)),
                "unjustified_selected_roles": unjustified,
            },
            "style_fidelity": {
                "fraction": fraction(style_counts["pass"], style_counts["pass"] + style_counts["fail"]),
                "counts": style_counts,
            },
            "factual_accuracy": {
                "fraction": fraction(fact_counts["correct"], fact_counts["correct"] + fact_counts["incorrect"]),
                "counts": fact_counts,
            },
            "historical_reconstruction_coverage": {
                "fraction": fraction(history_counts["covered"], history_counts["covered"] + history_counts["missed"]),
                "counts": history_counts,
            },
        },
        "transport_equivalence": {
            "status": "byte-identical",
            "profiles": list(TRANSPORTS),
            "object_count": len(reference_objects),
            "object_set_sha256": digest(reference_objects),
        },
        "clean_room_status": "pass",
        "negative_space_status": "pass",
        "aggregation": "none",
        "boundaries": list(BOUNDARIES),
    }
    return {**body, "evaluation_sha256": digest(body)}


def emit(value: Any) -> None:
    sys.stdout.buffer.write(canonical_bytes(value) + b"\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and receipt THOTH-to-ARK evaluation observations")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-policy", help="validate the canonical evaluation policy")
    evaluate_parser = sub.add_parser("evaluate", help="evaluate one explicit observation report")
    evaluate_parser.add_argument("--observation", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        policy = load_json(POLICY_PATH, PREFIX)
        if args.command == "validate-policy":
            emit(policy_validation_report(policy))
        else:
            emit(evaluate(load_json(args.observation, PREFIX), policy))
    except ContractError as exc:
        print(f"{exc.code}: {exc.detail}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
