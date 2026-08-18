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

## Phase 3 — Canonical source bindings

- [ ] Define a public binding contract from CONCAP role ids to QSOL-CONTEXT pack-spec roles without exposing private source records.
- [ ] Bind `concap.culture.comedy/1` to authored comedy and related visual/media artifacts.
- [ ] Bind `concap.culture.au-humour/1` to receiver-style guidance only.
- [ ] Define source-class bindings for `concap.history.timeline/1` without granting evidence authority.
- [ ] Prove cultural and historical support cannot grant fact authority.
- [ ] Keep source-selection policy distinct from style-selection policy.

## Phase 4 — QSOL-CONTROL integration

- [ ] Add a CONTROL adapter consuming a THOTH decision plus explicit private availability map.
- [ ] Preserve raw binary/media bytes; reject undeclared role-to-instance mappings.
- [ ] Emit resolver receipts binding THOTH decisions to exact capsule instances.
- [ ] Keep `ROUTE_DECISION != CAPSULE_AVAILABILITY` explicit.

## Phase 5 — QSOL-CAPSULES integration

- [ ] Add private CONCAP instance metadata and immutable historical instances.
- [ ] Bind instances to exact source, generator, policy, and capsule hashes.
- [ ] Preserve append-only snapshot semantics.
- [ ] Route culture/history content through semantic roles rather than monolithic style blobs.

## Phase 6 — QSOL-ARK evaluation

- [ ] Measure route sufficiency/minimality, style fidelity, factual accuracy, and historical reconstruction coverage separately.
- [ ] Add negative-space tests for style leakage and unsupported historical interpolation.
- [ ] Add clean-room tests across multiple consumers.
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
```
