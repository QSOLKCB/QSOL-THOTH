# AGENTS.md — QSOL-THOTH

QSOL-THOTH is a public routing, reconstruction, and portable-resolution protocol. Treat its public/private and authority boundaries as hard invariants.

## Required behavior

- Read `README4AI.md` before modifying routing, reconstruction, or resolution semantics.
- Run `python3 tools/thoth.py validate` and `python3 tools/thoth.py conformance`.
- Run `python3 tools/concap_resolver.py validate-bindings`.
- Run `python3 tools/instance_history.py validate --history examples/instances/synthetic-instance-history.json`.
- Run `python3 tools/ark_evaluation.py validate-policy` and evaluate the synthetic clean-room observation.
- Run `python3 tools/ess_session.py validate-policy` and replay the demonstrated hysteresis session twice byte-for-byte.
- Run `python3 -m unittest discover -s tests -v` after implementation changes.
- For history changes, run plan → pack → reconstruct on `examples/history/world-history-scaffold.json` twice and compare bytes.
- Keep canonical routing, resolution, and reconstruction network-free, clock-free, and random-free.
- Fail closed on ambiguity, unknown ids, missing required objects, receipt drift, unsatisfied retention obligations, dependency cycles, or deterministic search-budget exhaustion.
- Treat changed known-answer routing receipts and frozen history metrics as review events.
- Version semantic role changes rather than redefining an existing CONCAP id.
- Keep routing, resolution, transport, style, evidence, historical coverage, and factual authority separate.
- Keep public source bindings abstract: source classes and load requirements only, never private source paths.
- Keep object paths content-derived and relative; transport URLs and capability tokens are runtime inputs, not canonical object identity.
- Keep synthetic instance history explicitly classified as synthetic; never mark it as a real accepted capsule snapshot.
- Keep ARK evaluation dimensions separate and forbid aggregate truth scores.
- Keep multi-turn style transitions explicit and rebuild effective routes with persisted style support roles.
- Open PRs intended for Codex review marked Ready for review, not draft.

## Forbidden behavior

Do not commit private capsule bytes, secrets, capability tokens, provider-private state, hidden reasoning, private repository URLs, private source paths, or private context records. Do not use fuzzy/model inference as a canonical router, resolver, or ESS transition input. Do not query private repository/capsule availability from canonical THOTH routing. Do not silently substitute role versions. Do not treat historical compression as permission to discard information outside explicitly declared retention obligations. Do not claim semantic reconstruction is verbatim recovery or historical evidence. Do not treat content addressing as encryption. Do not relabel synthetic conformance metadata as executed private snapshots. Do not collapse style, factual, historical, or physical-truth measurements into one score.

## Boundary contract

```text
CONCAP_ID != CAPSULE_BYTES
ROUTING != FACTUAL_AUTHORITY
STYLE_SWITCH != EPISTEMIC_SWITCH
STYLE_SUPPORT != EVIDENCE
ROUTE_DECISION != CAPSULE_AVAILABILITY
NEW_ROLE_VERSION != BACKWARD_COMPATIBLE_BY_DEFAULT
CONFORMANCE_PASS != FACTUAL_TRUTH
SOURCE_BINDING != PRIVATE_SOURCE_PATH
ROUTING != RESOLUTION
RESOLUTION != TRANSPORT
TRANSPORT != AUTHORITY
OBJECT_IDENTITY != TRANSPORT_LOCATION
RESOLUTION != FACTUAL_AUTHORITY
RESOLVED != LOADED
LOADED != TRUE
MODEL_CAN_RECONSTRUCT_CONTEXT != MODEL_CAN_ACCESS_PRIVATE_SOURCE
INSTANCE_HISTORY != CAPSULE_BYTES
SNAPSHOT_APPEND_ONLY != SOURCE_IMMUTABLE
STYLE_FIDELITY != FACTUAL_ACCURACY != PHYSICAL_TRUTH
TRANSPORT_EQUIVALENCE != AUTHORITY
STYLE_PERSISTENCE != EPISTEMIC_PERSISTENCE
REPLAY_RECEIPT != HIDDEN_STATE
MINIMUM_SUFFICIENT != COMPLETE_HISTORY
SEMANTIC_RECONSTRUCTION != VERBATIM_SOURCE
COVERED_CLAIM != PROVEN_TRUE
CODEX_REVIEW_REQUESTED => PR_DRAFT == FALSE
```
