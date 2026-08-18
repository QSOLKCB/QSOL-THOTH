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
- [ ] Populate real accepted snapshots after capsule generation and fixed-point verification.
- [ ] Support immutable historical instances of the same semantic CONCAP role across snapshots.
- [ ] Bind accepted instances to exact source, generator, policy, and capsule hashes.
- [ ] Preserve append-only snapshot semantics.

## Phase 6 — QSOL-ARK evaluation

- [ ] Measure route sufficiency/minimality, style fidelity, factual accuracy, and historical reconstruction coverage separately.
- [ ] Add clean-room tests where consumers receive only a portable bundle, never source-repository access.
- [ ] Compare local-directory, archive, static-HTTP, and capability-relay transports for byte-identical resolved objects.
- [ ] Add negative-space tests for style leakage, unsupported historical interpolation, and accidental private-source dependency.
- [ ] Keep `STYLE_FIDELITY != FACTUAL_ACCURACY != PHYSICAL_TRUTH` explicit.

## Phase 7 — Multi-turn ESS switching

- [ ] Define deterministic style persistence, explicit transition events, optional demonstrated hysteresis/dwell rules, and replayable transition receipts.

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
```
