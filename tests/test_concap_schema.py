from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import concap_resolver as resolver


class PortableConcapSchemaTests(unittest.TestCase):
    def setUp(self):
        self.bindings = resolver.load_json(ROOT / "ai" / "concap-source-bindings.json")

    def test_source_binding_schema_semantics(self):
        schema = resolver.load_json(ROOT / "schema" / "concap-source-bindings.schema.json")
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["protocol"], {"const": resolver.BINDING_PROTOCOL})
        self.assertEqual(schema["properties"]["schema_version"], {"const": "1.0.0"})
        self.assertEqual(schema["properties"]["authority"], {"const": "resolution-metadata-only"})
        role = schema["properties"]["roles"]["items"]
        self.assertFalse(role["additionalProperties"])
        self.assertEqual(set(role["required"]), {"role_id", "source_class", "load_requirement", "delivery", "style_support_only", "factual_authority"})
        self.assertEqual(role["properties"]["delivery"], {"const": "portable_object"})
        self.assertEqual(role["properties"]["factual_authority"], {"const": "none-by-resolution"})
        self.assertEqual(schema["properties"]["boundaries"]["prefixItems"], [{"const": value} for value in resolver.BINDING_BOUNDARIES])
        self.assertEqual(schema["properties"]["boundaries"]["minItems"], len(resolver.BINDING_BOUNDARIES))
        self.assertEqual(schema["properties"]["boundaries"]["maxItems"], len(resolver.BINDING_BOUNDARIES))

    def test_object_index_schema_semantics(self):
        schema = resolver.load_json(ROOT / "schema" / "concap-object-index.schema.json")
        self.assertEqual(schema["properties"]["protocol"], {"const": resolver.OBJECT_INDEX_PROTOCOL})
        self.assertFalse(schema["additionalProperties"])
        obj = schema["properties"]["objects"]["items"]
        self.assertEqual(obj["properties"]["media_type"], {"const": "application/vnd.qsol.restore-dat"})
        self.assertEqual(obj["properties"]["container"], {"const": "qsol-restore-dat/1"})
        self.assertEqual(schema["properties"]["boundaries"]["prefixItems"], [{"const": value} for value in resolver.INDEX_BOUNDARIES])

    def test_bootstrap_schema_semantics(self):
        schema = resolver.load_json(ROOT / "schema" / "concap-bootstrap.schema.json")
        self.assertEqual(schema["properties"]["protocol"], {"const": "QSOL-CONCAP/BOOTSTRAP/1"})
        self.assertEqual(schema["properties"]["object_index_path"], {"const": "OBJECTS.json"})
        self.assertFalse(schema["additionalProperties"])

    def test_resolution_schema_semantics(self):
        schema = resolver.load_json(ROOT / "schema" / "concap-resolution-receipt.schema.json")
        self.assertEqual(schema["properties"]["protocol"], {"const": resolver.RESOLUTION_PROTOCOL})
        self.assertEqual(schema["properties"]["boundaries"]["prefixItems"], [{"const": value} for value in resolver.RECEIPT_BOUNDARIES])
        self.assertEqual(schema["properties"]["boundaries"]["minItems"], len(resolver.RECEIPT_BOUNDARIES))
        self.assertEqual(schema["properties"]["boundaries"]["maxItems"], len(resolver.RECEIPT_BOUNDARIES))

    def test_runtime_rejects_schema-relevant_contract_drift(self):
        altered = copy.deepcopy(self.bindings)
        altered["boundaries"].append("PRIVATE_PATH=/srv/secret/repo")
        with self.assertRaisesRegex(resolver.ResolverError, "E_RESOLVE_BOUNDARIES"):
            resolver.validate_bindings(altered)


if __name__ == "__main__":
    unittest.main()
