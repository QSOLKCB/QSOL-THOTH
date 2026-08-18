#!/usr/bin/env python3
"""Validate private CONCAP instance history without reading capsule payloads.

The public contract accepts caller-supplied private metadata. It proves
identity/ordering invariants only; it never claims that a referenced capsule
exists, was verified, or is factually authoritative unless the supplied
accepted receipt says so.
"""

from __future__ import annotations

import argparse
import json
import re
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
    require_git_sha1,
    require_sha256,
    require_token,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "ai" / "concap-registry.json"

PROTOCOL = "QSOL-CAPSULES/CONCAP-INSTANCE-HISTORY/1"
VALIDATION_PROTOCOL = "QSOL-THOTH/INSTANCE-HISTORY-VALIDATION/1"
APPEND_PROTOCOL = "QSOL-THOTH/INSTANCE-HISTORY-APPEND-CHECK/1"
PREFIX = "INSTANCE"
CAPSULE_NAME = re.compile(r"^[a-z0-9][a-z0-9_.-]*\.dat$")

BOUNDARIES = (
    "INSTANCE_HISTORY != CAPSULE_BYTES",
    "ACCEPTED_METADATA != FACTUAL_AUTHORITY",
    "CAPSULE_PRESENT != CAPSULE_VERIFIED",
    "SNAPSHOT_APPEND_ONLY != SOURCE_IMMUTABLE",
    "HISTORICAL_INSTANCE != CURRENT_INSTANCE",
    "MODEL_CAN_LOAD_EXPORT != MODEL_CAN_ACCESS_CAPSULE_REPOSITORY",
)


def known_roles() -> set[str]:
    registry = load_json(REGISTRY_PATH, PREFIX)
    capsules = registry.get("capsules")
    require(isinstance(capsules, list), "E_INSTANCE_REGISTRY", "registry capsules must be an array")
    roles: set[str] = set()
    for index, item in enumerate(capsules):
        require(isinstance(item, dict), "E_INSTANCE_REGISTRY", f"registry capsules[{index}] must be an object")
        role_id = require_concap(item.get("id"), f"registry capsules[{index}].id", PREFIX)
        require(role_id not in roles, "E_INSTANCE_REGISTRY", f"duplicate registry role: {role_id}")
        roles.add(role_id)
    return roles


def snapshot_body(snapshot: dict[str, Any]) -> dict[str, Any]:
    body = dict(snapshot)
    body.pop("snapshot_id", None)
    return body


def history_body(history: dict[str, Any]) -> dict[str, Any]:
    body = dict(history)
    body.pop("history_id", None)
    return body


def validate_instance(instance: Any, where: str, roles: set[str]) -> dict[str, Any]:
    value = exact_keys(
        instance,
        {
            "role_id",
            "capsule_name",
            "capsule_sha256",
            "size_bytes",
            "container",
            "fixed_point_verified",
        },
        where,
        PREFIX,
    )
    role_id = require_concap(value["role_id"], f"{where}.role_id", PREFIX)
    require(role_id in roles, "E_INSTANCE_UNKNOWN_ROLE", f"{where}: role is not in the public registry: {role_id}")
    name = value["capsule_name"]
    require(
        isinstance(name, str) and CAPSULE_NAME.fullmatch(name) is not None,
        "E_INSTANCE_CAPSULE_NAME",
        f"{where}.capsule_name must be a basename ending in .dat",
    )
    require_sha256(value["capsule_sha256"], f"{where}.capsule_sha256", PREFIX)
    size = value["size_bytes"]
    require(isinstance(size, int) and not isinstance(size, bool) and size > 0, "E_INSTANCE_SIZE", f"{where}.size_bytes must be positive")
    require(value["container"] == "qsol-restore-dat/1", "E_INSTANCE_CONTAINER", f"{where}.container drift")
    require(value["fixed_point_verified"] is True, "E_INSTANCE_FIXED_POINT", f"{where} is not fixed-point verified")
    return value


def validate_snapshot(
    snapshot: Any,
    index: int,
    expected_predecessor: str | None,
    roles: set[str],
    capsule_sizes_by_hash: dict[str, int],
) -> dict[str, Any]:
    where = f"snapshots[{index}]"
    value = exact_keys(
        snapshot,
        {
            "snapshot_id",
            "sequence",
            "predecessor_snapshot_id",
            "acceptance_status",
            "source_commit",
            "source_projection_sha256",
            "generator_commit",
            "policy_sha256",
            "verification_receipt_sha256",
            "instances",
        },
        where,
        PREFIX,
    )
    sequence = value["sequence"]
    require(
        isinstance(sequence, int) and not isinstance(sequence, bool) and sequence == index + 1,
        "E_INSTANCE_SEQUENCE",
        f"{where}.sequence must be {index + 1}",
    )
    predecessor = value["predecessor_snapshot_id"]
    if expected_predecessor is None:
        require(predecessor is None, "E_INSTANCE_CHAIN", f"{where} first predecessor must be null")
    else:
        require_sha256(predecessor, f"{where}.predecessor_snapshot_id", PREFIX)
        require(predecessor == expected_predecessor, "E_INSTANCE_CHAIN", f"{where} predecessor does not match prior snapshot")
    require(value["acceptance_status"] == "accepted", "E_INSTANCE_ACCEPTANCE", f"{where} is not accepted")
    require_git_sha1(value["source_commit"], f"{where}.source_commit", PREFIX)
    require_sha256(value["source_projection_sha256"], f"{where}.source_projection_sha256", PREFIX)
    require_git_sha1(value["generator_commit"], f"{where}.generator_commit", PREFIX)
    require_sha256(value["policy_sha256"], f"{where}.policy_sha256", PREFIX)
    require_sha256(value["verification_receipt_sha256"], f"{where}.verification_receipt_sha256", PREFIX)

    instances = value["instances"]
    require(isinstance(instances, list) and instances, "E_INSTANCE_INSTANCES", f"{where}.instances must be non-empty")
    seen_roles: set[str] = set()
    capsule_metadata: dict[str, tuple[str, int]] = {}
    ordered_roles: list[str] = []
    for instance_index, instance in enumerate(instances):
        item = validate_instance(instance, f"{where}.instances[{instance_index}]", roles)
        role_id = item["role_id"]
        require(role_id not in seen_roles, "E_INSTANCE_DUPLICATE_ROLE", f"{where}: duplicate role {role_id}")
        seen_roles.add(role_id)
        ordered_roles.append(role_id)
        capsule_sha256 = item["capsule_sha256"]
        size_bytes = item["size_bytes"]
        prior_size = capsule_sizes_by_hash.get(capsule_sha256)
        require(
            prior_size is None or prior_size == size_bytes,
            "E_INSTANCE_CAPSULE_CONFLICT",
            f"{where}: conflicting size metadata for {capsule_sha256}",
        )
        capsule_sizes_by_hash[capsule_sha256] = size_bytes
        metadata = (capsule_sha256, size_bytes)
        prior = capsule_metadata.get(item["capsule_name"])
        require(prior is None or prior == metadata, "E_INSTANCE_CAPSULE_CONFLICT", f"{where}: conflicting metadata for {item['capsule_name']}")
        capsule_metadata[item["capsule_name"]] = metadata
    require(
        ordered_roles == sorted(ordered_roles, key=lambda item: item.encode("utf-8")),
        "E_INSTANCE_ORDER",
        f"{where}.instances must be strictly UTF-8 sorted by role_id",
    )

    claimed = require_sha256(value["snapshot_id"], f"{where}.snapshot_id", PREFIX)
    require(claimed == digest(snapshot_body(value)), "E_INSTANCE_SNAPSHOT_HASH", f"{where}.snapshot_id mismatch")
    return value


def validate_history(history: Any) -> dict[str, Any]:
    value = exact_keys(
        history,
        {"protocol", "schema_version", "record_class", "authority", "history_id", "snapshots", "boundaries"},
        "instance history",
        PREFIX,
    )
    require(value["protocol"] == PROTOCOL, "E_INSTANCE_PROTOCOL", "unexpected instance-history protocol")
    require(value["schema_version"] == "1.0.0", "E_INSTANCE_VERSION", "unsupported instance-history version")
    record_class = value["record_class"]
    require(
        isinstance(record_class, str)
        and record_class in {"accepted-private-metadata", "synthetic-conformance"},
        "E_INSTANCE_RECORD_CLASS",
        "unknown instance-history record_class",
    )
    require(value["authority"] == "private-instance-metadata-only", "E_INSTANCE_AUTHORITY", "instance history cannot claim source authority")
    require(value["boundaries"] == list(BOUNDARIES), "E_INSTANCE_BOUNDARIES", "instance-history boundary set drift")
    snapshots = value["snapshots"]
    require(isinstance(snapshots, list) and snapshots, "E_INSTANCE_SNAPSHOTS", "snapshots must be a non-empty array")
    roles = known_roles()
    predecessor: str | None = None
    seen_snapshots: set[str] = set()
    capsule_sizes_by_hash: dict[str, int] = {}
    for index, snapshot in enumerate(snapshots):
        checked = validate_snapshot(snapshot, index, predecessor, roles, capsule_sizes_by_hash)
        snapshot_id = checked["snapshot_id"]
        require(snapshot_id not in seen_snapshots, "E_INSTANCE_DUPLICATE_SNAPSHOT", f"duplicate snapshot: {snapshot_id}")
        seen_snapshots.add(snapshot_id)
        predecessor = snapshot_id
    claimed = require_sha256(value["history_id"], "instance history.history_id", PREFIX)
    require(claimed == digest(history_body(value)), "E_INSTANCE_HISTORY_HASH", "instance history identity mismatch")
    return value


def validation_report(history: dict[str, Any]) -> dict[str, Any]:
    checked = validate_history(history)
    role_versions: dict[str, int] = {}
    for snapshot in checked["snapshots"]:
        for instance in snapshot["instances"]:
            role_versions[instance["role_id"]] = role_versions.get(instance["role_id"], 0) + 1
    return {
        "protocol": VALIDATION_PROTOCOL,
        "status": "ok",
        "record_class": checked["record_class"],
        "history_id": checked["history_id"],
        "snapshot_count": len(checked["snapshots"]),
        "role_history_counts": [
            {"role_id": role_id, "accepted_instances": role_versions[role_id]}
            for role_id in sorted(role_versions, key=lambda item: item.encode("utf-8"))
        ],
        "latest_snapshot_id": checked["snapshots"][-1]["snapshot_id"],
        "boundaries": list(BOUNDARIES),
    }


def check_append_only(base: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    old = validate_history(base)
    new = validate_history(candidate)
    require(
        new["record_class"] == old["record_class"],
        "E_INSTANCE_APPEND_RECORD_CLASS",
        "candidate history changes the accepted record_class",
    )
    old_snapshots = old["snapshots"]
    new_snapshots = new["snapshots"]
    require(len(new_snapshots) >= len(old_snapshots), "E_INSTANCE_APPEND_TRUNCATION", "candidate history truncates accepted snapshots")
    for index, old_snapshot in enumerate(old_snapshots):
        require(
            canonical_bytes(old_snapshot) == canonical_bytes(new_snapshots[index]),
            "E_INSTANCE_APPEND_MUTATION",
            f"candidate mutates accepted snapshot at sequence {index + 1}",
        )
    return {
        "protocol": APPEND_PROTOCOL,
        "status": "ok",
        "base_history_id": old["history_id"],
        "candidate_history_id": new["history_id"],
        "base_snapshot_count": len(old_snapshots),
        "candidate_snapshot_count": len(new_snapshots),
        "appended_snapshot_count": len(new_snapshots) - len(old_snapshots),
        "boundaries": list(BOUNDARIES),
    }


def emit(value: Any) -> None:
    sys.stdout.buffer.write(canonical_bytes(value) + b"\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate immutable private CONCAP instance-history metadata")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="validate one instance history")
    validate.add_argument("--history", type=Path, required=True)
    append = sub.add_parser("check-append-only", help="prove that a candidate preserves the accepted history prefix")
    append.add_argument("--base", type=Path, required=True)
    append.add_argument("--candidate", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "validate":
            emit(validation_report(load_json(args.history, PREFIX)))
        else:
            emit(check_append_only(load_json(args.base, PREFIX), load_json(args.candidate, PREFIX)))
    except ContractError as exc:
        print(f"{exc.code}: {exc.detail}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
