#!/usr/bin/env python3
"""Deterministic minimum-sufficient historical reconstruction planner.

This tool minimizes a declared semantic reconstruction basis. It does not
claim to recover omitted source bytes or to establish historical truth.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

TOKEN = re.compile(r"^[a-z0-9_.-]+$")
SEMVER = re.compile(r"^[1-9][0-9]*\.[0-9]+\.[0-9]+$")

PLAN_BOUNDARIES = [
    "MINIMUM_SUFFICIENT != COMPLETE_HISTORY",
    "SEMANTIC_RECONSTRUCTION != VERBATIM_SOURCE",
    "COVERED_CLAIM != PROVEN_TRUE",
    "HISTORICAL_SUMMARY != PRIMARY_EVIDENCE",
    "COMPRESSION != OMISSION_AUTHORITY",
]


class HistoryError(Exception):
    """Stable machine error code plus human diagnostic."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def fail(code: str, detail: str) -> None:
    raise HistoryError(code, detail)


def require(condition: bool, code: str, detail: str) -> None:
    if not condition:
        fail(code, detail)


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            fail("E_HISTORY_JSON_DUPLICATE", f"duplicate JSON object member: {key}")
        out[key] = value
    return out


def load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        fail("E_HISTORY_SYMLINK", f"refusing symlink input: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_pairs)
    except HistoryError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail("E_HISTORY_JSON_LOAD", f"cannot load {path}: {exc}")
    require(isinstance(value, dict), "E_HISTORY_JSON_TOPLEVEL", "top level must be an object")
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def exact_keys(value: dict[str, Any], expected: set[str], where: str) -> None:
    extra = sorted(set(value) - expected)
    missing = sorted(expected - set(value))
    require(not extra, "E_HISTORY_FIELDS", f"{where}: unsupported fields: {extra}")
    require(not missing, "E_HISTORY_FIELDS", f"{where}: missing fields: {missing}")


def validate_boundaries(value: Any, code: str, where: str) -> None:
    require(isinstance(value, list) and len(value) == len(set(value)), code, f"{where} must be a unique array")
    for boundary in PLAN_BOUNDARIES:
        require(boundary in value, code, f"missing boundary: {boundary}")


def validate_policy(policy: dict[str, Any]) -> None:
    exact_keys(policy, {"protocol", "schema_version", "objective", "max_search_nodes", "tie_break", "boundaries"}, "policy")
    require(policy["protocol"] == "QSOL-THOTH/HISTORY-RECONSTRUCTION-POLICY/1", "E_HISTORY_POLICY_PROTOCOL", "unexpected policy protocol")
    require(isinstance(policy["schema_version"], str) and SEMVER.fullmatch(policy["schema_version"]), "E_HISTORY_POLICY_VERSION", "invalid policy schema_version")
    objective = policy["objective"]
    require(isinstance(objective, dict), "E_HISTORY_POLICY", "objective must be an object")
    exact_keys(objective, {"coverage", "cost", "dependencies", "algorithm"}, "policy.objective")
    require(objective["coverage"] == "all_retention_obligations", "E_HISTORY_POLICY", "coverage objective drift")
    require(objective["cost"] == "canonical_record_bytes", "E_HISTORY_POLICY", "cost objective drift")
    require(objective["dependencies"] == "transitive_closure", "E_HISTORY_POLICY", "dependency objective drift")
    require(objective["algorithm"] == "exact_branch_and_bound", "E_HISTORY_POLICY", "algorithm drift")
    require(isinstance(policy["max_search_nodes"], int) and not isinstance(policy["max_search_nodes"], bool) and policy["max_search_nodes"] > 0, "E_HISTORY_POLICY", "max_search_nodes must be positive")
    require(policy["tie_break"] == "total_bytes_then_record_count_then_utf8_ids", "E_HISTORY_POLICY", "tie-break drift")
    validate_boundaries(policy["boundaries"], "E_HISTORY_POLICY", "policy boundaries")


def validate_record(record: dict[str, Any], index: int | str) -> None:
    require(isinstance(record, dict), "E_HISTORY_RECORD", f"record {index} must be object")
    exact_keys(record, {"id", "order", "kind", "summary", "claims", "requires"}, f"record {index}")
    record_id = record["id"]
    require(isinstance(record_id, str) and TOKEN.fullmatch(record_id), "E_HISTORY_RECORD_ID", f"invalid record id: {record_id!r}")
    order = record["order"]
    require(isinstance(order, int) and not isinstance(order, bool) and order > 0, "E_HISTORY_RECORD_ORDER", f"invalid order for {record_id}")
    require(record["kind"] in {"detail", "bridge", "anchor"}, "E_HISTORY_RECORD_KIND", f"invalid kind for {record_id}")
    require(isinstance(record["summary"], str) and record["summary"], "E_HISTORY_RECORD_SUMMARY", f"summary missing for {record_id}")
    for field in ("claims", "requires"):
        values = record[field]
        require(isinstance(values, list) and len(values) == len(set(values)), "E_HISTORY_RECORD", f"{record_id}.{field} must be a unique array")
    require(bool(record["claims"]), "E_HISTORY_RECORD", f"{record_id}.claims must be non-empty")
    for claim in record["claims"]:
        require(isinstance(claim, str) and TOKEN.fullmatch(claim), "E_HISTORY_RECORD", f"{record_id}: invalid claim {claim!r}")
    for dependency in record["requires"]:
        require(isinstance(dependency, str) and TOKEN.fullmatch(dependency), "E_HISTORY_RECORD", f"{record_id}: invalid dependency {dependency!r}")


def validate_dataset(dataset: dict[str, Any]) -> None:
    exact_keys(dataset, {"protocol", "schema_version", "id", "authority", "retention_obligations", "records", "boundaries"}, "dataset")
    require(dataset["protocol"] == "QSOL-THOTH/HISTORY-DATASET/1", "E_HISTORY_DATASET_PROTOCOL", "unexpected dataset protocol")
    require(isinstance(dataset["schema_version"], str) and SEMVER.fullmatch(dataset["schema_version"]), "E_HISTORY_DATASET_VERSION", "invalid dataset schema_version")
    require(isinstance(dataset["id"], str) and TOKEN.fullmatch(dataset["id"]), "E_HISTORY_DATASET_ID", "invalid dataset id")
    require(dataset["authority"] == "demonstration-only", "E_HISTORY_AUTHORITY", "demo dataset must not claim factual authority")
    obligations = dataset["retention_obligations"]
    require(isinstance(obligations, list) and obligations, "E_HISTORY_OBLIGATIONS", "retention_obligations must be non-empty")
    require(len(obligations) == len(set(obligations)), "E_HISTORY_OBLIGATIONS", "duplicate retention obligation")
    for claim in obligations:
        require(isinstance(claim, str) and TOKEN.fullmatch(claim), "E_HISTORY_OBLIGATIONS", f"invalid obligation: {claim!r}")
    records = dataset["records"]
    require(isinstance(records, list) and records, "E_HISTORY_RECORDS", "records must be non-empty")
    ids: set[str] = set()
    orders: set[int] = set()
    for index, record in enumerate(records):
        validate_record(record, index)
        require(record["id"] not in ids, "E_HISTORY_RECORD_ID", f"duplicate record id: {record['id']}")
        require(record["order"] not in orders, "E_HISTORY_RECORD_ORDER", f"duplicate record order: {record['order']}")
        ids.add(record["id"])
        orders.add(record["order"])
    for record in records:
        for dependency in record["requires"]:
            require(dependency in ids, "E_HISTORY_DEPENDENCY", f"{record['id']}: unknown dependency {dependency}")
    validate_boundaries(dataset["boundaries"], "E_HISTORY_BOUNDARIES", "dataset boundaries")


def record_sort_key(record: dict[str, Any]) -> tuple[int, bytes]:
    return (record["order"], record["id"].encode("utf-8"))


def _validate_dependency_closure(records: dict[str, dict[str, Any]]) -> None:
    complete: set[str] = set()
    def visit(record_id: str, stack: tuple[str, ...]) -> None:
        if record_id in complete:
            return
        require(record_id not in stack, "E_HISTORY_DEPENDENCY_CYCLE", f"dependency cycle at {record_id}")
        for dependency in records[record_id]["requires"]:
            require(dependency in records, "E_HISTORY_DEPENDENCY", f"{record_id}: missing dependency {dependency}")
            visit(dependency, stack + (record_id,))
        complete.add(record_id)
    for record_id in sorted(records, key=lambda value: value.encode("utf-8")):
        visit(record_id, ())


def make_basis(dataset: dict[str, Any], policy: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    records = {record["id"]: record for record in dataset["records"]}
    selected = [records[record_id] for record_id in plan["selected_records"]]
    base = {
        "protocol": "QSOL-THOTH/HISTORY-BASIS/1",
        "dataset_id": dataset["id"],
        "dataset_sha256": plan["dataset_sha256"],
        "policy_sha256": plan["policy_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "retention_obligations": list(plan["retention_obligations"]),
        "records": selected,
        "boundaries": list(PLAN_BOUNDARIES),
    }
    return {**base, "basis_sha256": digest(base)}


def validate_basis(basis: dict[str, Any]) -> None:
    exact_keys(basis, {"protocol", "dataset_id", "dataset_sha256", "policy_sha256", "plan_sha256", "retention_obligations", "records", "boundaries", "basis_sha256"}, "basis")
    require(basis["protocol"] == "QSOL-THOTH/HISTORY-BASIS/1", "E_HISTORY_BASIS_PROTOCOL", "unexpected basis protocol")
    require(isinstance(basis["dataset_id"], str) and TOKEN.fullmatch(basis["dataset_id"]), "E_HISTORY_BASIS", "invalid basis dataset id")
    for field in ("dataset_sha256", "policy_sha256", "plan_sha256", "basis_sha256"):
        value = basis[field]
        require(isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value), "E_HISTORY_BASIS", f"invalid {field}")
    obligations = basis["retention_obligations"]
    require(isinstance(obligations, list) and obligations and len(obligations) == len(set(obligations)), "E_HISTORY_BASIS", "basis obligations must be unique and non-empty")
    records_list = basis["records"]
    require(isinstance(records_list, list) and records_list, "E_HISTORY_BASIS", "basis records must be non-empty")
    records: dict[str, dict[str, Any]] = {}
    orders: set[int] = set()
    for index, record in enumerate(records_list):
        validate_record(record, f"basis[{index}]")
        require(record["id"] not in records, "E_HISTORY_BASIS", f"duplicate basis record: {record['id']}")
        require(record["order"] not in orders, "E_HISTORY_BASIS", f"duplicate basis order: {record['order']}")
        records[record["id"]] = record
        orders.add(record["order"])
    _validate_dependency_closure(records)
    covered: set[str] = set()
    for record in records.values():
        covered.update(record["claims"])
    require(set(obligations) <= covered, "E_HISTORY_BASIS_COVERAGE", "basis does not cover all retention obligations")
    validate_boundaries(basis["boundaries"], "E_HISTORY_BASIS", "basis boundaries")
    body = dict(basis)
    claimed = body.pop("basis_sha256")
    require(claimed == digest(body), "E_HISTORY_BASIS_HASH", "basis SHA-256 mismatch")


def plan_minimum(dataset: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    validate_dataset(dataset)
    validate_policy(policy)
    records = {record["id"]: record for record in dataset["records"]}
    _validate_dependency_closure(records)
    ordered_ids = [record["id"] for record in sorted(dataset["records"], key=record_sort_key)]
    record_bytes = {record_id: len(canonical_bytes(records[record_id])) for record_id in records}
    closure_cache: dict[str, frozenset[str]] = {}
    def dependency_closure(record_id: str) -> frozenset[str]:
        if record_id in closure_cache:
            return closure_cache[record_id]
        out = {record_id}
        for dependency in records[record_id]["requires"]:
            out.update(dependency_closure(dependency))
        frozen = frozenset(out)
        closure_cache[record_id] = frozen
        return frozen
    closure_claims: dict[str, frozenset[str]] = {}
    for record_id in ordered_ids:
        claims: set[str] = set()
        for member in dependency_closure(record_id):
            claims.update(records[member]["claims"])
        closure_claims[record_id] = frozenset(claims)
    obligations = frozenset(dataset["retention_obligations"])
    coverers: dict[str, list[str]] = {}
    for claim in sorted(obligations, key=lambda value: value.encode("utf-8")):
        choices = [record_id for record_id in ordered_ids if claim in closure_claims[record_id]]
        require(bool(choices), "E_HISTORY_UNSATISFIABLE", f"no record covers obligation: {claim}")
        coverers[claim] = choices
    max_nodes = policy["max_search_nodes"]
    search_nodes = 0
    best_selected: frozenset[str] | None = None
    best_key: tuple[int, int, tuple[bytes, ...]] | None = None
    visited: set[frozenset[str]] = set()
    def selection_cost(selected: frozenset[str]) -> int:
        return sum(record_bytes[record_id] for record_id in selected)
    def selection_key(selected: frozenset[str]) -> tuple[int, int, tuple[bytes, ...]]:
        return (selection_cost(selected), len(selected), tuple(sorted(record_id.encode("utf-8") for record_id in selected)))
    def covered_claims(selected: frozenset[str]) -> frozenset[str]:
        claims: set[str] = set()
        for record_id in selected:
            claims.update(records[record_id]["claims"])
        return frozenset(claims)
    def dfs(selected: frozenset[str]) -> None:
        nonlocal search_nodes, best_selected, best_key
        if selected in visited:
            return
        visited.add(selected)
        search_nodes += 1
        require(search_nodes <= max_nodes, "E_HISTORY_SEARCH_LIMIT", f"search node limit exceeded: {max_nodes}")
        key = selection_key(selected)
        if best_key is not None and key[0] > best_key[0]:
            return
        missing = obligations - covered_claims(selected)
        if not missing:
            if best_key is None or key < best_key:
                best_key = key
                best_selected = selected
            return
        claim = min(missing, key=lambda value: value.encode("utf-8"))
        choices = []
        for record_id in coverers[claim]:
            expanded = frozenset(set(selected) | set(dependency_closure(record_id)))
            if expanded == selected:
                continue
            increment = selection_cost(expanded) - selection_cost(selected)
            choices.append((increment, records[record_id]["order"], record_id.encode("utf-8"), expanded))
        choices.sort(key=lambda item: (item[0], item[1], item[2]))
        for _, _, _, expanded in choices:
            if best_key is not None and selection_cost(expanded) > best_key[0]:
                continue
            dfs(expanded)
    dfs(frozenset())
    require(best_selected is not None and best_key is not None, "E_HISTORY_UNSATISFIABLE", "no satisfying historical basis exists")
    selected_ordered = [record_id for record_id in ordered_ids if record_id in best_selected]
    covered = sorted(obligations & covered_claims(best_selected), key=lambda value: value.encode("utf-8"))
    candidate_bytes = sum(record_bytes.values())
    selected_bytes = sum(record_bytes[record_id] for record_id in best_selected)
    preliminary = {
        "protocol": "QSOL-THOTH/HISTORY-PLAN/1",
        "dataset_id": dataset["id"],
        "dataset_sha256": digest(dataset),
        "policy_sha256": digest(policy),
        "candidate_record_count": len(records),
        "candidate_record_bytes": candidate_bytes,
        "canonical_dataset_bytes": len(canonical_bytes(dataset)),
        "retention_obligations": sorted(obligations, key=lambda value: value.encode("utf-8")),
        "selected_records": selected_ordered,
        "selected_record_count": len(selected_ordered),
        "selected_record_bytes": selected_bytes,
        "covered_obligations": covered,
        "record_retention_ratio": {"numerator": selected_bytes, "denominator": candidate_bytes},
        "search_nodes": search_nodes,
        "boundaries": list(PLAN_BOUNDARIES),
    }
    provisional_plan = {**preliminary, "plan_sha256": "sha256:" + ("0" * 64)}
    provisional_basis = make_basis(dataset, policy, provisional_plan)
    validate_basis(provisional_basis)
    basis_bytes = len(canonical_bytes(provisional_basis))
    plan_body = dict(preliminary)
    plan_body["self_contained_basis_bytes"] = basis_bytes
    plan_body["self_contained_retention_ratio"] = {"numerator": basis_bytes, "denominator": len(canonical_bytes(dataset))}
    return {**plan_body, "plan_sha256": digest(plan_body)}


def build_basis(dataset: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    plan = plan_minimum(dataset, policy)
    basis = make_basis(dataset, policy, plan)
    validate_basis(basis)
    return basis


def reconstruct_basis(basis: dict[str, Any]) -> dict[str, Any]:
    validate_basis(basis)
    records = sorted(basis["records"], key=record_sort_key)
    selected = [{"id": record["id"], "order": record["order"], "summary": record["summary"], "claims": list(record["claims"])} for record in records]
    base = {
        "protocol": "QSOL-THOTH/HISTORY-RECONSTRUCTION/1",
        "dataset_id": basis["dataset_id"],
        "basis_sha256": basis["basis_sha256"],
        "retention_obligations": list(basis["retention_obligations"]),
        "records": selected,
        "boundaries": list(PLAN_BOUNDARIES),
    }
    return {**base, "reconstruction_sha256": digest(base)}


def main() -> int:
    parser = argparse.ArgumentParser(prog="history-minset")
    sub = parser.add_subparsers(dest="command", required=True)
    plan_parser = sub.add_parser("plan", help="calculate the exact minimum semantic basis")
    plan_parser.add_argument("--dataset", required=True)
    plan_parser.add_argument("--policy", default="ai/history-reconstruction-policy.json")
    pack_parser = sub.add_parser("pack", help="emit a self-contained reconstruction basis")
    pack_parser.add_argument("--dataset", required=True)
    pack_parser.add_argument("--policy", default="ai/history-reconstruction-policy.json")
    reconstruct_parser = sub.add_parser("reconstruct", help="reconstruct from a self-contained basis only")
    reconstruct_parser.add_argument("--basis", required=True)
    args = parser.parse_args()
    try:
        if args.command in {"plan", "pack"}:
            dataset = load_json(Path(args.dataset))
            policy = load_json(Path(args.policy))
            output = plan_minimum(dataset, policy) if args.command == "plan" else build_basis(dataset, policy)
        else:
            output = reconstruct_basis(load_json(Path(args.basis)))
        print(canonical_bytes(output).decode("utf-8"))
        return 0
    except HistoryError as exc:
        print(f"FAIL: {exc.code}: {exc.detail}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
