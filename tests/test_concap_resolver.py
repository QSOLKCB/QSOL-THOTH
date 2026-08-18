from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import concap_resolver as resolver
import thoth


def route_decision(intent: str = "general", style: str | None = None) -> dict:
    request = {"protocol": "QSOL-THOTH/ROUTE-REQUEST/1", "intent": intent}
    if style is not None:
        request["style"] = style
    return thoth.route_request(request)


def object_index(role_to_object: dict[str, str], boundaries: list[str] | None = None) -> dict:
    object_ids = sorted(set(role_to_object.values()), key=lambda value: value.encode("utf-8"))
    objects = [
        {
            "object_id": object_id,
            "size_bytes": 123,
            "media_type": "application/vnd.qsol.restore-dat",
            "container": "qsol-restore-dat/1",
            "path": resolver.object_path_for(object_id),
        }
        for object_id in object_ids
    ]
    body = {
        "protocol": resolver.OBJECT_INDEX_PROTOCOL,
        "schema_version": "1.0.0",
        "bundle_id": "synthetic_bundle",
        "bundle_class": "RESTRICTED",
        "export_spec_sha256": "sha256:" + "4" * 64,
        "projection_sha256": "sha256:" + "5" * 64,
        "objects": objects,
        "role_bindings": [
            {"role_id": role_id, "object_id": object_id}
            for role_id, object_id in sorted(role_to_object.items(), key=lambda item: item[0].encode("utf-8"))
        ],
        "boundaries": boundaries if boundaries is not None else list(resolver.INDEX_BOUNDARIES),
    }
    return {**body, "index_id": resolver.digest(body)}


class PortableConcapResolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bindings = resolver.load_json(ROOT / "ai" / "concap-source-bindings.json")
        cls.roles = resolver.validate_bindings(cls.bindings)

    def test_every_registry_role_has_a_public_binding(self):
        registry = resolver.load_json(ROOT / "ai" / "concap-registry.json")
        registry_roles = {item["id"] for item in registry["capsules"]}
        self.assertEqual(registry_roles, set(self.roles))

    def test_required_roles_resolve_without_repository_information(self):
        object_id = "sha256:" + "a" * 64
        decision = route_decision("general")
        index = object_index({
            "concap.identity.core/1": object_id,
            "concap.workstyle.engineering/1": object_id,
        })
        receipt = resolver.resolve(decision, index, self.bindings)
        self.assertEqual(len(receipt["resolved_roles"]), 2)
        self.assertEqual(len(receipt["objects_to_fetch"]), 1)
        # Boundary labels are allowed to discuss repositories. Actual source locators are not.
        payload = {key: value for key, value in receipt.items() if key != "boundaries"}
        encoded = resolver.canonical_bytes(payload).decode("utf-8").lower()
        for forbidden in ("github.com/", "api.github.com/", "raw.githubusercontent.com/", "qsolkcb/", "source_ref", "/home/", "/srv/"):
            self.assertNotIn(forbidden, encoded)

    def test_same_object_can_satisfy_multiple_roles(self):
        object_id = "sha256:" + "b" * 64
        decision = route_decision("comedy")
        index = object_index({
            "concap.culture.core/1": object_id,
            "concap.culture.au-humour/1": object_id,
            "concap.culture.comedy/1": object_id,
        })
        receipt = resolver.resolve(decision, index, self.bindings)
        self.assertEqual(len(receipt["resolved_roles"]), 3)
        self.assertEqual([item["object_id"] for item in receipt["objects_to_fetch"]], [object_id])

    def test_best_effort_style_role_can_be_missing(self):
        decision = route_decision("creative")
        index = object_index({"concap.culture.core/1": "sha256:" + "c" * 64})
        receipt = resolver.resolve(decision, index, self.bindings)
        self.assertIn("concap.culture.music/1", receipt["missing_best_effort"])

    def test_required_role_missing_fails_closed(self):
        decision = route_decision("historical_reconstruction")
        index = object_index({"concap.workstyle.engineering/1": "sha256:" + "d" * 64})
        with self.assertRaisesRegex(resolver.ResolverError, "E_RESOLVE_REQUIRED_ROLE_UNAVAILABLE"):
            resolver.resolve(decision, index, self.bindings)

    def test_decision_hash_tamper_is_rejected(self):
        decision = route_decision("general")
        decision["style"] = "technical"
        index = object_index({
            "concap.identity.core/1": "sha256:" + "e" * 64,
            "concap.workstyle.engineering/1": "sha256:" + "e" * 64,
        })
        with self.assertRaisesRegex(resolver.ResolverError, "E_DECISION_HASH"):
            resolver.resolve(decision, index, self.bindings)

    def test_rehashed_semantic_route_forgery_is_rejected(self):
        decision = route_decision("general")
        decision["concaps"] = ["concap.history.timeline/1"]
        body = dict(decision)
        body.pop("decision_sha256")
        decision["decision_sha256"] = resolver.digest(body)
        index = object_index({"concap.history.timeline/1": "sha256:" + "8" * 64})
        with self.assertRaisesRegex(resolver.ResolverError, "E_DECISION_SEMANTICS"):
            resolver.resolve(decision, index, self.bindings)

    def test_unregistered_binding_role_is_rejected(self):
        mutated = json.loads(json.dumps(self.bindings))
        mutated["roles"][0]["role_id"] = "concap.aaa.unregistered/1"
        with self.assertRaisesRegex(resolver.ResolverError, "E_BINDING_UNKNOWN_ROLE"):
            resolver.validate_bindings(mutated)

    def test_non_style_role_cannot_be_best_effort(self):
        mutated = json.loads(json.dumps(self.bindings))
        target = next(item for item in mutated["roles"] if item["role_id"] == "concap.identity.core/1")
        target["load_requirement"] = "best_effort"
        with self.assertRaisesRegex(resolver.ResolverError, "E_BINDING_REQUIREMENT"):
            resolver.validate_bindings(mutated)

    def test_unhashable_decision_role_has_stable_error(self):
        decision = route_decision("general")
        decision["concaps"] = [{"bad": "role"}]
        with self.assertRaisesRegex(resolver.ResolverError, "E_RESOLVE_ROLE"):
            resolver.validate_route_decision(decision)

    def test_extra_boundary_text_is_rejected(self):
        index = object_index({"concap.identity.core/1": "sha256:" + "7" * 64}, list(resolver.INDEX_BOUNDARIES) + ["PRIVATE_PATH=/srv/secret/repo"])
        with self.assertRaisesRegex(resolver.ResolverError, "E_RESOLVE_BOUNDARIES"):
            resolver.validate_object_index(index)

    def test_index_hash_tamper_is_rejected(self):
        index = object_index({"concap.identity.core/1": "sha256:" + "f" * 64})
        index["bundle_id"] = "changed"
        with self.assertRaisesRegex(resolver.ResolverError, "E_INDEX_HASH"):
            resolver.validate_object_index(index)

    def test_transport_url_is_not_accepted_as_object_path(self):
        object_id = "sha256:" + "a" * 64
        index = object_index({"concap.identity.core/1": object_id})
        index["objects"][0]["path"] = "https://example.invalid/object.dat"
        body = dict(index); body.pop("index_id")
        index["index_id"] = resolver.digest(body)
        with self.assertRaisesRegex(resolver.ResolverError, "E_INDEX_PATH"):
            resolver.validate_object_index(index)

    def test_resolution_receipt_hash_is_acyclic(self):
        object_id = "sha256:" + "9" * 64
        decision = route_decision("general")
        index = object_index({
            "concap.identity.core/1": object_id,
            "concap.workstyle.engineering/1": object_id,
        })
        receipt = resolver.resolve(decision, index, self.bindings)
        body = dict(receipt)
        claimed = body.pop("resolution_sha256")
        self.assertEqual(claimed, resolver.digest(body))


if __name__ == "__main__":
    unittest.main()
