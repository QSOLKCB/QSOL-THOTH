# QSOL-THOTH — AI Bootstrap

QSOL-THOTH is the **public deterministic routing, portable-resolution, multi-turn style, and conformance layer** for QSOL-CONCAP. It does not contain private user context or real capsule payload bytes.

## Load order

1. `ai/concap-registry.json`
2. `ai/concap-compatibility.json`
3. `ai/concap-source-bindings.json`
4. `ai/ess-style-machine.json`
5. `ai/router.json`
6. `ai/history-reconstruction-policy.json`
7. `ai/ess-session-policy.json` when multi-turn style state is in scope
8. `ai/ark-evaluation-policy.json` when evaluation is in scope
9. `CONFORMANCE.md`
10. `PORTABLE-CONCAPS.md`
11. `HISTORY-CONCAP.md`
12. `INSTANCE-HISTORY.md` when private instance metadata is in scope
13. `ARK-EVALUATION.md` when evaluation is in scope
14. `ESS-SESSIONS.md` when multi-turn style state is in scope
15. `tools/thoth.py`
16. `tools/concap_resolver.py`
17. `tools/history_minset.py`
18. `tools/instance_history.py` when instance metadata is in scope
19. `tools/ark_evaluation.py` when evaluation is in scope
20. `tools/ess_session.py` when multi-turn style state is in scope
21. `README.md`

Machine schemas live under `schema/`; frozen routing vectors live under `vectors/`.

## Core interpretation

```text
CONCAP = semantic context-capsule role
THOTH = deterministic selector/router
ESS = deterministic receiver-style state machine
SOURCE BINDING = public semantic source class, not private path
OBJECT INDEX = explicit role -> immutable object map
RESOLVER = transport-neutral role-to-object selector
HISTORY BASIS = minimum declared semantic reconstruction package
INSTANCE HISTORY = private append-only accepted-instance metadata, not payload bytes
ESS SESSION = explicit multi-turn receiver-style event replay
ARK EVALUATION RECEIPT = deterministic measurement of explicit observations
CONTROL = byte-exact capsule pack/export/verify implementation
CAPSULES = private immutable capsule instances
ARK = recovery/evaluation authority
```

Do not reinterpret CONCAP ids as actual capsule bytes.

## Routing rules

- Accept exact declared ASCII intent tokens only.
- Resolve only exact canonical ids or exact declared aliases.
- Unknown intents/styles fail closed.
- Explicit declared style wins over route default.
- De-duplicate selected CONCAP ids and order by registry ordinal.
- Do not use fuzzy matching, embeddings, wall-clock state, random input, network state, or private availability as canonical routing inputs.

## Portable-resolution rules

- Read `ai/concap-source-bindings.json` for public source classes and required/best-effort loading policy.
- Never infer a private repository path from a source class.
- Never put private repository URLs, credentials, capability tokens, or private source paths in canonical object indexes or resolution receipts.
- Accept only an explicit `QSOL-CONCAP/OBJECT-INDEX/1` for object availability.
- Object identity is `sha256(exact object bytes)`.
- Canonical object paths are content-derived relative paths, never transport URLs.
- The same object may satisfy several semantic roles.
- A missing `required` role fails closed.
- A missing `best_effort` style-support role is reported but does not fail resolution.
- Resolution does not fetch bytes and does not access the network.

```text
ROUTING != RESOLUTION
RESOLUTION != TRANSPORT
OBJECT_IDENTITY != TRANSPORT_LOCATION
RESOLUTION != FACTUAL_AUTHORITY
MODEL_CAN_LOAD_OBJECT != MODEL_CAN_ACCESS_SOURCE_REPOSITORY
```

## Versioning and conformance

```text
EXISTING_ROLE_VERSION => SEMANTICS_IMMUTABLE
SEMANTIC_CHANGE => NEW_ROLE_VERSION
NEW_ROLE_VERSION != BACKWARD_COMPATIBLE_BY_DEFAULT
```

Before changing routing or portable-resolution semantics:

```bash
python3 tools/thoth.py validate
python3 tools/thoth.py conformance
python3 tools/concap_resolver.py validate-bindings
python3 tools/instance_history.py validate --history examples/instances/synthetic-instance-history.json
python3 tools/ark_evaluation.py validate-policy
python3 tools/ess_session.py validate-policy
python3 -m unittest discover -s tests -v
```

Do not refresh frozen routing receipts merely to make CI green. Portable-resolution changes should remain outside `tools/thoth.py` unless routing semantics genuinely change.

## Historical reconstruction rules

`concap.history.timeline/1` is a semantic role for chronological reconstruction anchors. It does not grant historical authority.

A history dataset explicitly declares what must survive in `retention_obligations`. `tools/history_minset.py` performs exact deterministic branch-and-bound over dependency-closed candidate records, minimizing canonical record bytes. Search is bounded by a declared node count, never time.

A `QSOL-THOTH/HISTORY-BASIS/1` is self-contained: reconstruction uses the basis alone, not the discarded candidate dataset.

```text
MINIMUM_SUFFICIENT != COMPLETE_HISTORY
SEMANTIC_RECONSTRUCTION != VERBATIM_SOURCE
COVERED_CLAIM != PROVEN_TRUE
HISTORICAL_SUMMARY != PRIMARY_EVIDENCE
COMPRESSION != OMISSION_AUTHORITY
```

For original-byte recovery, preserve the original bytes or a lossless deterministic encoding instead.

## Instance-history rules

- Accept private instance history only as explicit caller-supplied metadata.
- Require exact source commit, source-projection hash, generator commit, policy hash, verification receipt, capsule hash, and byte size.
- Preserve every historical occurrence of a role; a later snapshot never overwrites an earlier one.
- Require the accepted history to be an immutable byte-identical prefix of any extension.
- Treat `synthetic-conformance` as a test class, never as proof of real capsule generation.

```text
INSTANCE_HISTORY != CAPSULE_BYTES
CAPSULE_PRESENT != CAPSULE_VERIFIED
SNAPSHOT_APPEND_ONLY != SOURCE_IMMUTABLE
```

## ARK-evaluation rules

- QSOL-ARK owns evaluation authority; THOTH validates and receipts explicit observations.
- Keep route sufficiency, route minimality, style fidelity, factual accuracy, and historical coverage separate.
- Never emit an aggregate truth score.
- Require portable-only clean-room inputs and no private source, connector, or hidden-memory dependency.
- Require local-directory, archive, static-HTTP, and capability-relay observations to name byte-identical objects.
- Fail closed on style leakage, unsupported historical interpolation, or accidental private-source dependency.

```text
STYLE_FIDELITY != FACTUAL_ACCURACY != PHYSICAL_TRUTH
MEASURED_OBSERVATION != AUTOMATIC_TRUTH
AGGREGATE_SCORE = FORBIDDEN
```

## Multi-turn ESS rules

- Route events contain a normal request without an embedded style override.
- The first route initializes from its declared default; later routes persist the current style.
- Rebuild effective route decisions using the persisted style so support CONCAPs remain correct.
- Style changes occur only through explicit transition or reset events.
- Dwell is counted in routed events, never wall-clock time.
- Chained replay receipts expose declared state only, never hidden model state.

```text
STYLE_PERSISTENCE != EPISTEMIC_PERSISTENCE
EXPLICIT_STYLE_TRANSITION != MODEL_INFERENCE
REPLAY_RECEIPT != HIDDEN_STATE
```

## Authority boundaries

```text
CONCAP_ID != CAPSULE_BYTES
PUBLIC_ROUTE != PRIVATE_PAYLOAD
ROUTING != FACTUAL_AUTHORITY
STYLE_SWITCH != EPISTEMIC_SWITCH
STYLE_SUPPORT != EVIDENCE
SELECTED != LOADED
LOADED != TRUE
SOURCE_BINDING != PRIVATE_SOURCE_PATH
RESOLUTION != TRANSPORT
TRANSPORT != AUTHORITY
OBJECT_IDENTITY != TRANSPORT_LOCATION
MODEL_CAN_RECONSTRUCT_CONTEXT != MODEL_CAN_ACCESS_PRIVATE_SOURCE
INSTANCE_HISTORY != CAPSULE_BYTES
STYLE_FIDELITY != FACTUAL_ACCURACY != PHYSICAL_TRUTH
REPLAY_RECEIPT != HIDDEN_STATE
```

Comedy remains non-factual when selected for receiver style; historical coverage remains non-evidence when selected for reconstruction. Portable delivery never promotes a claim.

## Private-data prohibition

Never add real private capsule payloads, secrets, credentials, capability tokens, provider-private state, hidden reasoning, private source paths, or private context records to QSOL-THOTH. Public synthetic examples, known-answer vectors, public source-class metadata, and demonstration-only history scaffolds are allowed.

## Review workflow

```text
CODEX_REVIEW_REQUESTED => PR_DRAFT == FALSE
```
