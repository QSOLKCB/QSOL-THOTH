#!/usr/bin/env python3
"""Small standard-library helpers for deterministic THOTH side contracts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

TOKEN = re.compile(r"^[a-z0-9_.-]+$")
CONCAP_ID = re.compile(r"^concap\.[a-z0-9_.-]+/[1-9][0-9]*$")
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
GIT_SHA1 = re.compile(r"^[0-9a-f]{40}$")


class ContractError(Exception):
    """Stable machine error code plus a human diagnostic."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def fail(code: str, detail: str) -> None:
    raise ContractError(code, detail)


def require(condition: bool, code: str, detail: str) -> None:
    if not condition:
        fail(code, detail)


def _reject_duplicate_pairs(prefix: str):
    def reject(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                fail(f"E_{prefix}_JSON_DUPLICATE", f"duplicate JSON object member: {key}")
            out[key] = value
        return out

    return reject


def _reject_constant(prefix: str):
    def reject(value: str) -> None:
        fail(f"E_{prefix}_JSON_CONSTANT", f"non-finite JSON number is forbidden: {value}")

    return reject


def load_json(path: Path, prefix: str) -> dict[str, Any]:
    require(not path.is_symlink(), f"E_{prefix}_SYMLINK", f"refusing symlink input: {path}")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs(prefix),
            parse_constant=_reject_constant(prefix),
        )
    except ContractError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"E_{prefix}_JSON_LOAD", f"cannot load {path}: {exc}")
    require(isinstance(value, dict), f"E_{prefix}_JSON_TOPLEVEL", f"{path} must contain an object")
    return value


def exact_keys(value: Any, expected: set[str], where: str, prefix: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"E_{prefix}_OBJECT", f"{where} must be an object")
    extra = sorted(set(value) - expected)
    missing = sorted(expected - set(value))
    require(not extra, f"E_{prefix}_FIELDS", f"{where}: unsupported fields: {extra}")
    require(not missing, f"E_{prefix}_FIELDS", f"{where}: missing fields: {missing}")
    return value


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        fail("E_CANONICAL_JSON", f"value is not canonical JSON: {exc}")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def require_token(value: Any, where: str, prefix: str) -> str:
    require(
        isinstance(value, str) and TOKEN.fullmatch(value) is not None,
        f"E_{prefix}_TOKEN",
        f"{where} must be a canonical token",
    )
    return value


def require_concap(value: Any, where: str, prefix: str) -> str:
    require(
        isinstance(value, str) and CONCAP_ID.fullmatch(value) is not None,
        f"E_{prefix}_CONCAP",
        f"{where} must be a versioned CONCAP id",
    )
    return value


def require_sha256(value: Any, where: str, prefix: str) -> str:
    require(
        isinstance(value, str) and SHA256.fullmatch(value) is not None,
        f"E_{prefix}_SHA256",
        f"{where} must be sha256:<64-lower-hex>",
    )
    return value


def require_git_sha1(value: Any, where: str, prefix: str) -> str:
    require(
        isinstance(value, str) and GIT_SHA1.fullmatch(value) is not None,
        f"E_{prefix}_GIT_SHA1",
        f"{where} must be a 40-character lower-hex Git commit id",
    )
    return value


def require_sorted_unique_strings(
    value: Any,
    where: str,
    prefix: str,
    *,
    non_empty: bool = False,
    kind: str = "token",
) -> list[str]:
    require(isinstance(value, list), f"E_{prefix}_ARRAY", f"{where} must be an array")
    if non_empty:
        require(bool(value), f"E_{prefix}_ARRAY", f"{where} must be non-empty")
    checked: list[str] = []
    for index, item in enumerate(value):
        if kind == "token":
            checked.append(require_token(item, f"{where}[{index}]", prefix))
        elif kind == "concap":
            checked.append(require_concap(item, f"{where}[{index}]", prefix))
        else:
            require(isinstance(item, str) and bool(item), f"E_{prefix}_STRING", f"{where}[{index}] must be a non-empty string")
            checked.append(item)
    require(len(checked) == len(set(checked)), f"E_{prefix}_DUPLICATE", f"{where} must contain unique entries")
    expected = sorted(checked, key=lambda item: item.encode("utf-8"))
    require(checked == expected, f"E_{prefix}_ORDER", f"{where} must be strictly UTF-8 sorted")
    return checked
