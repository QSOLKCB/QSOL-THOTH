# QSOL-THOTH Conformance Suite

`QSOL-THOTH/CONFORMANCE/1` freezes public routing behavior before THOTH is bound to private source or capsule availability.

## Commands

```bash
python3 tools/thoth.py validate
python3 tools/thoth.py conformance
python3 -m unittest discover -s tests -v
```

## Positive vectors

`vectors/positive/*.json` contain a canonical request and the complete expected `QSOL-THOTH/ROUTE-DECISION/1` receipt.

The expected receipt freezes:

- canonical intent resolution;
- ESS style selection;
- ordered CONCAP role ids;
- request SHA-256;
- exact public configuration SHA-256;
- exact router implementation SHA-256;
- authority boundaries;
- acyclic decision SHA-256.

A changed implementation or public routing configuration therefore requires an explicit review of the affected known-answer vectors.

```text
IMPLEMENTATION_CHANGE != SILENT_VECTOR_REFRESH
CONFIGURATION_CHANGE != SILENT_VECTOR_REFRESH
```

## Negative vectors

`vectors/negative/*.vector.json` declare malformed or forbidden cases and the stable error code that must result.

The initial suite covers:

- ambiguous route aliases;
- duplicate CONCAP ids;
- duplicate JSON object members;
- unknown ESS support CONCAPs;
- invalid CONCAP role version zero;
- unknown route intents;
- unknown explicit styles.

Diagnostic prose may improve. The machine error code is the conformance contract.

```text
ERROR_MESSAGE != ERROR_IDENTITY
```

## Machine-readable public schemas

The public configuration is described by:

```text
schema/concap-registry.schema.json
schema/concap-compatibility.schema.json
schema/ess-style-machine.schema.json
schema/router.schema.json
schema/route-request.schema.json
schema/route-decision.schema.json
```

`tools/thoth.py validate` both checks the schema contracts themselves and validates the current configuration instances against the schema subset THOTH uses.

## Compatibility policy

`ai/concap-compatibility.json` defines role evolution.

Core rules:

```text
EXISTING_ROLE_VERSION => SEMANTICS_IMMUTABLE
SEMANTIC_CHANGE => NEW_ROLE_VERSION
NEW_ROLE_VERSION != BACKWARD_COMPATIBLE_BY_DEFAULT
COMPATIBILITY_DECLARATION != AUTOMATIC_SUBSTITUTION
```

A resolver must match the exact CONCAP role id declared by the route decision. `/2` is not an automatic substitute for `/1`.

## Scope boundary

The conformance suite proves replay of the public selector and its declared failures. It does not prove that a private capsule exists, that its payload is factually correct, or that a consumer reconstructs context correctly.

```text
CONFORMANCE_PASS != CAPSULE_AVAILABILITY
CONFORMANCE_PASS != FACTUAL_TRUTH
CONFORMANCE_PASS != RECOVERY_SUCCESS
```
