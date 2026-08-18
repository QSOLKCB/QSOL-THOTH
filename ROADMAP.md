# QSOL-THOTH Roadmap

## Phase 0 — Public deterministic router

- [x] Define CONCAP as `CONtext CAPsules` and separate semantic roles from private instances.
- [x] Add registry, ESS style state machine, exact-token router, SHA-256 decision receipts, stdlib CLI, tests, CI, and Ready-for-review invariant.

## Phase 1 — Public CONCAP contract hardening

- [x] Add machine-readable schemas, frozen positive/negative vectors, stable machine errors, role-version compatibility policy, and `thoth.py conformance`.

## Phase 2 — Historical reconstruction bases

- [x] Add `concap.history.timeline/1` and `historical_reconstruction` routing.
- [x] Define explicit semantic retention obligations.
- [x] Add deterministic transitive dependency closure.
- [x] Add exact branch-and-bound minimization by canonical record bytes.
- [x] Add deterministic search-node budget and fail-closed exhaustion.
- [x] Add a self-contained `HISTORY-BASIS/1` package that reconstructs without the discarded source dataset.
- [x] Add plan, basis, and reconstruction SHA-256 receipts.
- [x] Freeze a demonstration-only world-history scaffold and its minimum result.
- [x] Keep semantic reconstruction separate from verbatim recovery and factual authority.

## Phase 3 — Canonical source-class bindings

- [x] Define public semantic source-class bindings without exposing private repositories, commits, or source paths.
- [x] Bind `concap.culture.comedy/1` to the `authored_comedy` source class.
- [x] Bind `concap.culture.au-humour/1` to receiver-style support only.
- [x] Bind `concap.history.timeline/1` to a historical-reconstruction-basis source class without granting evidence authority.
- [x] Mark style-only source classes `best_effort`; keep data/recovery roles fail-closed when unavailable.
- [x] Keep source-class policy distinct from route, style, object availability, transport, and factual authority.

## Phase 4 — Portable CONCAP delivery

- [x] Define `QSOL-CONCAP/OBJECT-INDEX/1` for explicit role -> immutable object resolution.
- [x] Define `QSOL-CONCAP/BOOTSTRAP/1` as a small transport-neutral bundle entry document.
- [x] Define `QSOL-THOTH/RESOLUTION-RECEIPT/1` with acyclic SHA-256 identity.
- [x] Add a network-free resolver consuming a THOTH decision plus an explicit object index.
- [x] De-duplicate objects when one immutable object satisfies several roles.
- [x] Fail closed on missing required roles while reporting missing best-effort style support.
- [x] Keep object identity content-addressed and transport location outside canonical identity.
- [x] Coordinate QSOL-CONTROL deterministic portable-bundle export over existing `QSOL-RESTORE-DAT/1` objects.
- [x] Coordinate QSOL-CONTEXT explicit private export policy and QSOL-CAPSULES private role-instance map.
- [x] Preserve `MODEL_CAN_RECONSTRUCT_CONTEXT != MODEL_CAN_ACCESS_PRIVATE_SOURCE`.

## Phase 5 — QSOL-CAPSULES instance history

- [x] Define private role-to-capsule instance metadata without exposing payloads publicly.
- [x] Publish a strict public schema and validator for caller-supplied private instance-history metadata.
- [ ] Populate real accepted snapshots after capsule generation and fixed-point verification. **Operational gate:** QSOL-CAPSULES currently contains no accepted `.dat` snapshot; THOTH ships only an explicitly `synthetic-conformance` fixture and does not claim execution.
- [x] Support immutable historical instances of the same semantic CONCAP role across snapshots.
- [x] Bind accepted instances to exact source commit, source projection, generator commit, policy, verification receipt, capsule hash, and byte size.
- [x] Preserve append-only snapshot semantics with byte-identical prefix verification.

## Phase 6 — QSOL-ARK evaluation

- [x] Measure route sufficiency/minimality, style fidelity, factual accuracy, and historical reconstruction coverage separately.
- [x] Add clean-room tests where consumers receive only a portable bundle, never source-repository access.
- [x] Compare explicit local-directory, archive, static-HTTP, and capability-relay observations for byte-identical resolved objects.
- [x] Add negative-space tests for style leakage, unsupported historical interpolation, and accidental private-source dependency.
- [x] Keep `STYLE_FIDELITY != FACTUAL_ACCURACY != PHYSICAL_TRUTH` explicit and forbid aggregate truth scores.

## Phase 7 — Multi-turn ESS switching

- [x] Define deterministic style persistence, explicit transition/reset events, immediate and demonstrated hysteresis/dwell profiles, effective-route rebuilding, and replayable chained transition receipts.

## Long-term invariants

```text
CONCAP_ID != CAPSULE_BYTES
PUBLIC_ROUTE != PRIVATE_PAYLOAD
ROUTING != FACTUAL_AUTHORITY
STYLE_SWITCH != EPISTEMIC_SWITCH
STYLE_SUPPORT != EVIDENCE
SELECTED != LOADED
LOADED != TRUE
MINIMUM_SUFFICIENT != COMPLETE_HISTORY
SEMANTIC_RECONSTRUCTION != VERBATIM_SOURCE
COVERED_CLAIM != PROVEN_TRUE
SOURCE_BINDING != PRIVATE_SOURCE_PATH
ROUTING != RESOLUTION
RESOLUTION != TRANSPORT
TRANSPORT != AUTHORITY
OBJECT_IDENTITY != TRANSPORT_LOCATION
MODEL_CAN_RECONSTRUCT_CONTEXT != MODEL_CAN_ACCESS_PRIVATE_SOURCE
CLAIMED_EXECUTION != EXECUTED
SYNTHETIC_CONFORMANCE != ACCEPTED_PRIVATE_SNAPSHOT
INSTANCE_HISTORY != CAPSULE_BYTES
SNAPSHOT_APPEND_ONLY != SOURCE_IMMUTABLE
STYLE_FIDELITY != FACTUAL_ACCURACY != PHYSICAL_TRUTH
ROUTE_SUFFICIENCY != ROUTE_MINIMALITY
TRANSPORT_EQUIVALENCE != AUTHORITY
STYLE_PERSISTENCE != EPISTEMIC_PERSISTENCE
REPLAY_RECEIPT != HIDDEN_STATE
```
