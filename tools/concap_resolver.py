#!/usr/bin/env python3
"""Transport-neutral CONCAP resolver for QSOL-THOTH.

The resolver maps a verified THOTH route decision onto a caller-supplied
portable object index. It never queries private repositories or network state.
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
BINDINGS_PATH = ROOT / "ai" / "concap-source-bindings.json"

TOKEN = re.compile(r"^[a-z0-9_.-]+$")
CONCAP_ID = re.compile(r"^concap\.[a-z0-9_.-]+/[1-9][0-9]*$")
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")

BINDING_PROTOCOL = "QSOL-THOTH/CONCAP-SOURCE-BINDINGS/1"
OBJECT_INDEX_PROTOCOL = "QSOL-CONCAP/OBJECT-INDEX/1"
ROUTE_DECISION_PROTOCOL = "QSOL-THOTH/ROUTE-DECISION/1"
RESOLUTION_PROTOCOL = "QSOL-THOTH/RESOLUTION-RECEIPT/1"

BINDING_BOUNDARIES = (
    "SOURCE_BINDING != PRIVATE_SOURCE_PATH",
    "RESOLUTION != TRANSPORT",
    "OBJECT_IDENTITY != TRANSPORT_LOCATION",
    "RESOLUTION != FACTUAL_AUTHORITY",
    "MODEL_CAN_LOAD_OBJECT != MODEL_CAN_ACCESS_SOURCE_REPOSITORY",
    "SELECTED != LOADED",
)

INDEX_BOUNDARIES = (
    "PRIVATE_SOURCE != PORTABLE_BUNDLE",
    "BUNDLE_OBJECT != CANONICAL_SOURCE",
    "OBJECT_IDENTITY != TRANSPORT_LOCATION",
    "MODEL_CAN_LOAD_OBJECT != MODEL_CAN_ACCESS_SOURCE_REPOSITORY",
    "QSOL-RESTORE-DAT/1 != ENCRYPTION",
)

RECEIPT_BOUNDARIES = (
    "ROUTE_DECISION != CAPSULE_AVAILABILITY",
    "RESOLUTION != TRANSPORT",
    "RESOLUTION != FACTUAL_AUTHORITY",
    "OBJECT_IDENTITY != TRANSPORT_LOCATION",
    "RESOLVED != LOADED",
    "LOADED != TRUE",
    "MODEL_CAN_LOAD_OBJECT != MODEL_CAN_ACCESS_SOURCE_REPOSITORY",
)


class ResolverError(Exception):
    """Stable machine error plus human diagnostic."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def fail(code: str, detail: str) -> None:
    raise ResolverError(code, detail)


def require(condition: bool, code: str, detail: str) -> None:
    if not condition:
        fail(code, detail)


def reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            fail("E_RESOLVE_JSON_DUPLICATE", f"duplicate JSON object member: {key}")
        out[key] = value
    return out


def load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        fail("E_RESOLVE_SYMLINK", f"refusing symlink input: {path}")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_pairs,
        )
    except ResolverError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail("E_RESOLVE_JSON_LOAD", f"cannot load {path}: {exc}")
    require(isinstance(value, dict), "E_RESOLVE_JSON_TOPLEVEL", f"{path} must contain an object")
    return value


def exact_keys(value: dict[str, Any], expected: set[str], where: str) -> None:
    extra = sorted(set(value) - expected)
    missing = sorted(expected - set(value))
    require(not extra, "E_RESOLVE_FIELDS", f"{where}: unsupported fields: {extra}")
    require(not missing, "E_RESOLVE_FIELDS", f"{where}: missing fields: {missing}")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def require_sha(value: Any, where: str) -> str:
    require(
        isinstance(value, str) and SHA256.fullmatch(value) is not None,
        "E_RESOLVE_SHA256",
        f"{where} must be sha256:<64-lower-hex>",
    )
    return value


def require_token(value: Any, where: str) -> str:
    require(
        isinstance(value, str) and TOKEN.fullmatch(value) is not None,
        "E_RESOLVE_TOKEN",
        f"{where} must be a canonical token",
    )
    return value


def require_role(value: Any, where: str) -> str:
    require(
        isinstance(value, str) and CONCAP_ID.fullmatch(value) is not None,
        "E_RESOLVE_ROLE",
        f"{where} must be a versioned CONCAP id",
    )
    return value


def require_boundaries(value: Any, mandatory: tuple[str, ...], where: str) -> list[str]:
    require(isinstance(value, list), "E_RESOLVE_BOUNDARIES", f"{where} must be an array")
    require(
        all(isinstance(item, str) and item for item in value),
        "E_RESOLVE_BOUNDARIES",
        f"{where} must contain non-empty strings",
    )
    require(
        len(value) == len(set(value)),
        "E_RESOLVE_BOUNDARIES",
        f"{where} must not contain duplicates",
    )
    for boundary in mandatory:
        require(
            boundary in value,
            "E_RESOLVE_BOUNDARIES",
            f"{where} missing boundary: {boundary}",
        )
    return value


def validate_bindings(value: dict[str, Any]) -> dict[str, dict[str, Any]]:
    exact_keys(
        value,
        {"protocol", "schema_version", "authority", "roles", "boundaries"},
        "source bindings",
    )
    require(
        value["protocol"] == BINDING_PROTOCOL,
        "E_BINDING_PROTOCOL",
        "unexpected source-binding protocol",
    )
    require(
        value["schema_version"] == "1.0.0",
        "E_BINDING_VERSION",
        "unsupported source-binding schema version",
    )
    require(
        value["authority"] == "resolution-metadata-only",
        "E_BINDING_AUTHORITY",
        "source bindings must not claim authority",
    )
    require_boundaries(value["boundaries"], BINDING_BOUNDARIES, "source-binding boundaries")
    roles = value["roles"]
    require(isinstance(roles, list) and roles, "E_BINDING_ROLES", "roles must be a non-empty array")
    out: dict[str, dict[str, Any]] = {}
    last: bytes | None = None
    for index, item in enumerate(roles):
        require(isinstance(item, dict), "E_BINDING_ROLE", f"roles[{index}] must be an object")
        exact_keys(
            item,
            {
                "role_id",
                "source_class",
                "load_requirement",
                "delivery",
                "style_support_only",
                "factual_authority",
            },
            f"roles[{index}]",
        )
        role_id = require_role(item["role_id"], f"roles[{index}].role_id")
        encoded = role_id.encode("utf-8")
        require(
            last is None or last < encoded,
            "E_BINDING_ORDER",
            "roles must be strictly UTF-8 sorted by role_id",
        )
        last = encoded
        require(role_id not in out, "E_BINDING_DUPLICATE_ROLE", f"duplicate role: {role_id}")
        require_token(item["source_class"], f"{role_id}.source_class")
        require(
            item["load_requirement"] in {"required", "best_effort"},
            "E_BINDING_REQUIREMENT",
            f"{role_id}: invalid load_requirement",
        )
        require(
            item["delivery"] == "portable_object",
            "E_BINDING_DELIVERY",
            f"{role_id}: unsupported delivery mode",
        )
        require(
            type(item["style_support_only"]) is bool,
            "E_BINDING_STYLE",
            f"{role_id}: style_support_only must be boolean",
        )
        require(
            item["factual_authority"] == "none-by-resolution",
            "E_BINDING_AUTHORITY",
            f"{role_id}: resolution cannot grant authority",
        )
        if item["style_support_only"]:
            require(
                item["load_requirement"] == "best_effort",
                "E_BINDING_STYLE",
                f"{role_id}: style support must be best_effort",
            )
        out[role_id] = item
    return out


def object_path_for(object_id: str) -> str:
    hex_digest = object_id.split(":", 1)[1]
    return f"objects/sha256/{hex_digest[:2]}/{hex_digest}.dat"


def validate_object_index(
    value: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    exact_keys(
        value,
        {
            "protocol",
            "schema_version",
            "index_id",
            "bundle_id",
            "bundle_class",
            "export_spec_sha256",
            "projection_sha256",
            "objects",
            "role_bindings",
            "boundaries",
        },
        "object index",
    )
    require(
        value["protocol"] == OBJECT_INDEX_PROTOCOL,
        "E_INDEX_PROTOCOL",
        "unexpected object-index protocol",
    )
    require(
        value["schema_version"] == "1.0.0",
        "E_INDEX_VERSION",
        "unsupported object-index schema version",
    )
    require_token(value["bundle_id"], "object index bundle_id")
    require(
        value["bundle_class"] in {"PUBLIC", "INTERNAL", "RESTRICTED"},
        "E_INDEX_CLASS",
        "invalid bundle_class",
    )
    require_sha(value["export_spec_sha256"], "object index export_spec_sha256")
    require_sha(value["projection_sha256"], "object index projection_sha256")
    require_sha(value["index_id"], "object index index_id")
    require_boundaries(value["boundaries"], INDEX_BOUNDARIES, "object-index boundaries")
    body = dict(value)
    claimed = body.pop("index_id")
    require(claimed == digest(body), "E_INDEX_HASH", "object index identity mismatch")

    objects_value = value["objects"]
    require(
        isinstance(objects_value, list) and objects_value,
        "E_INDEX_OBJECTS",
        "objects must be a non-empty array",
    )
    objects: dict[str, dict[str, Any]] = {}
    last_object: bytes | None = None
    for index, item in enumerate(objects_value):
        require(isinstance(item, dict), "E_INDEX_OBJECT", f"objects[{index}] must be an object")
        exact_keys(
            item,
            {"object_id", "size_bytes", "media_type", "container", "path"},
            f"objects[{index}]",
        )
        object_id = require_sha(item["object_id"], f"objects[{index}].object_id")
        encoded = object_id.encode("utf-8")
        require(
            last_object is None or last_object < encoded,
            "E_INDEX_ORDER",
            "objects must be strictly UTF-8 sorted by object_id",
        )
        last_object = encoded
        require(
            object_id not in objects,
            "E_INDEX_DUPLICATE_OBJECT",
            f"duplicate object: {object_id}",
        )
        require(
            isinstance(item["size_bytes"], int)
            and not isinstance(item["size_bytes"], bool)
            and item["size_bytes"] >= 0,
            "E_INDEX_OBJECT",
            f"{object_id}: invalid size_bytes",
        )
        require(
            item["media_type"] == "application/vnd.qsol.restore-dat",
            "E_INDEX_OBJECT",
            f"{object_id}: media_type drift",
        )
        require(
            item["container"] == "qsol-restore-dat/1",
            "E_INDEX_OBJECT",
            f"{object_id}: container drift",
        )
        require(
            item["path"] == object_path_for(object_id),
            "E_INDEX_PATH",
            f"{object_id}: path must be content-address derived",
        )
        objects[object_id] = item

    bindings_value = value["role_bindings"]
    require(
        isinstance(bindings_value, list) and bindings_value,
        "E_INDEX_BINDINGS",
        "role_bindings must be a non-empty array",
    )
    role_bindings: dict[str, str] = {}
    last_role: bytes | None = None
    for index, item in enumerate(bindings_value):
        require(
            isinstance(item, dict),
            "E_INDEX_BINDING",
            f"role_bindings[{index}] must be an object",
        )
        exact_keys(item, {"role_id", "object_id"}, f"role_bindings[{index}]")
        role_id = require_role(item["role_id"], f"role_bindings[{index}].role_id")
        object_id = require_sha(item["object_id"], f"role_bindings[{index}].object_id")
        encoded = role_id.encode("utf-8")
        require(
            last_role is None or last_role < encoded,
            "E_INDEX_ORDER",
            "role_bindings must be strictly UTF-8 sorted by role_id",
        )
        last_role = encoded
        require(
            role_id not in role_bindings,
            "E_INDEX_DUPLICATE_ROLE",
            f"duplicate role binding: {role_id}",
        )
        require(
            object_id in objects,
            "E_INDEX_UNKNOWN_OBJECT",
            f"{role_id}: object not declared: {object_id}",
        )
        role_bindings[role_id] = object_id
    return objects, role_bindings


def validate_route_decision(value: dict[str, Any]) -> list[str]:
    expected = {
        "protocol",
        "canonical_intent",
        "style",
        "concaps",
        "request_sha256",
        "configuration_sha256",
        "implementation_sha256",
        "decision_sha256",
        "boundaries",
    }
    exact_keys(value, expected, "route decision")
    require(
        value["protocol"] == ROUTE_DECISION_PROTOCOL,
        "E_DECISION_PROTOCOL",
        "unexpected route-decision protocol",
    )
    require_token(value["canonical_intent"], "route decision canonical_intent")
    require_token(value["style"], "route decision style")
    for field in (
        "request_sha256",
        "configuration_sha256",
        "implementation_sha256",
        "decision_sha256",
    ):
        require_sha(value[field], f"route decision {field}")
    concaps = value["concaps"]
    require(
        isinstance(concaps, list) and concaps,
        "E_DECISION_ROLES",
        "route decision concaps must be non-empty",
    )
    require(
        len(concaps) == len(set(concaps)),
        "E_DECISION_ROLES",
        "route decision concaps must be unique",
    )
    for role_id in concaps:
        require_role(role_id, "route decision concap")
    require_boundaries(
        value["boundaries"],
        ("ROUTING != FACTUAL_AUTHORITY",),
        "route-decision boundaries",
    )
    body = dict(value)
    claimed = body.pop("decision_sha256")
    require(claimed == digest(body), "E_DECISION_HASH", "route decision identity mismatch")
    return concaps


def resolve(
    decision: dict[str, Any],
    index: dict[str, Any],
    bindings: dict[str, Any],
) -> dict[str, Any]:
    selected_roles = validate_route_decision(decision)
    public_roles = validate_bindings(bindings)
    objects, available_roles = validate_object_index(index)

    resolved_roles: list[dict[str, str]] = []
    missing_best_effort: list[str] = []
    required_missing: list[str] = []

    for role_id in selected_roles:
        require(
            role_id in public_roles,
            "E_RESOLVE_UNBOUND_ROLE",
            f"no public source binding for {role_id}",
        )
        object_id = available_roles.get(role_id)
        if object_id is None:
            if public_roles[role_id]["load_requirement"] == "required":
                required_missing.append(role_id)
            else:
                missing_best_effort.append(role_id)
            continue
        resolved_roles.append({"role_id": role_id, "object_id": object_id})

    require(
        not required_missing,
        "E_RESOLVE_REQUIRED_ROLE_UNAVAILABLE",
        f"required roles unavailable: {required_missing}",
    )

    fetch_ids = sorted(
        {item["object_id"] for item in resolved_roles},
        key=lambda value: value.encode("utf-8"),
    )
    objects_to_fetch = [objects[object_id] for object_id in fetch_ids]
    base = {
        "protocol": RESOLUTION_PROTOCOL,
        "route_decision_sha256": decision["decision_sha256"],
        "binding_configuration_sha256": digest(bindings),
        "object_index_id": index["index_id"],
        "resolved_roles": resolved_roles,
        "objects_to_fetch": objects_to_fetch,
        "missing_best_effort": missing_best_effort,
        "boundaries": list(RECEIPT_BOUNDARIES),
    }
    return {**base, "resolution_sha256": digest(base)}


def emit(value: Any) -> None:
    sys.stdout.buffer.write(canonical_bytes(value) + b"\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resolve THOTH CONCAP roles against a portable object index"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser(
        "validate-bindings",
        help="validate public source-binding metadata",
    )
    validate.add_argument("--bindings", default=str(BINDINGS_PATH))

    resolve_parser = sub.add_parser(
        "resolve",
        help="resolve a route decision against an object index",
    )
    resolve_parser.add_argument("--decision", required=True)
    resolve_parser.add_argument("--index", required=True)
    resolve_parser.add_argument("--bindings", default=str(BINDINGS_PATH))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        bindings = load_json(Path(args.bindings))
        if args.command == "validate-bindings":
            roles = validate_bindings(bindings)
            emit(
                {
                    "protocol": "QSOL-THOTH/SOURCE-BINDING-VALIDATION/1",
                    "status": "ok",
                    "role_count": len(roles),
                    "binding_configuration_sha256": digest(bindings),
                }
            )
            return 0
        decision = load_json(Path(args.decision))
        index = load_json(Path(args.index))
        emit(resolve(decision, index, bindings))
        return 0
    except ResolverError as exc:
        print(f"THOTH resolver error: {exc.code}: {exc.detail}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
