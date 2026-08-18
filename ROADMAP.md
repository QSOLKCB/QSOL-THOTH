# QSOL-THOTH Roadmap

## Phase 0 — Public deterministic router

- [x] Define CONCAP as `CONtext CAPsules`.
- [x] Separate semantic role ids from concrete private capsule instances.
- [x] Add public CONCAP registry.
- [x] Add finite ESS-style receiver state machine.
- [x] Add exact-token deterministic intent router.
- [x] Fail closed on unknown intent and style ids.
- [x] Add canonical route-decision SHA-256 receipts.
- [x] Bind decisions to request, public configuration, and implementation bytes.
- [x] Add standard-library validator/router CLI.
- [x] Add regression tests and CI determinism checks.
- [x] Enforce `CODEX_REVIEW_REQUESTED => PR_DRAFT == FALSE` in PR CI.
- [x] Preserve `STYLE_SWITCH != EPISTEMIC_SWITCH`.

## Phase 1 — Public CONCAP contract hardening

- [ ] Add machine-readable role schema for `ai/concap-registry.json`.
- [ ] Add machine-readable ESS state-machine schema.
- [ ] Add machine-readable router schema.
- [ ] Add canonical known-answer route vectors with frozen expected receipts.
- [ ] Add negative vectors for ambiguous aliases, duplicate ids, duplicate JSON members, and unknown support CONCAPs.
- [ ] Add a versioned compatibility policy for CONCAP role evolution.

## Phase 2 — Canonical source bindings

- [ ] Define a public binding contract from CONCAP role ids to QSOL-CONTEXT pack-spec roles without exposing private source records.
- [ ] Bind `concap.culture.comedy/1` to the cultural-artifact class that includes authored comedy and related visual/media artifacts.
- [ ] Bind `concap.culture.au-humour/1` to receiver-style guidance only.
- [ ] Prove by validation that cultural receiver support cannot grant fact authority.
- [ ] Keep source-selection policy distinct from style-selection policy.

## Phase 3 — QSOL-CONTROL integration

- [ ] Add a CONTROL adapter that consumes a THOTH route decision and resolves declared CONCAP ids against an explicit private availability map.
- [ ] Preserve raw source bytes for binary/media entries.
- [ ] Reject undeclared role-to-instance mappings.
- [ ] Emit a resolver receipt binding THOTH decision id to exact selected capsule instance ids.
- [ ] Keep `ROUTE_DECISION != CAPSULE_AVAILABILITY` explicit.

## Phase 4 — QSOL-CAPSULES integration

- [ ] Add private CONCAP instance metadata without exposing payloads publicly.
- [ ] Support immutable historical instances of the same semantic CONCAP role.
- [ ] Bind each instance to exact source, generator, policy, and capsule hashes.
- [ ] Preserve append-only snapshot semantics.
- [ ] Route `culture.dat` content through CONCAP semantic roles rather than one monolithic style blob.

## Phase 5 — QSOL-ARK evaluation

- [ ] Measure route sufficiency: did the selected CONCAP set contain enough context for the task?
- [ ] Measure route minimality: was unnecessary private context avoided?
- [ ] Measure style fidelity separately from factual accuracy.
- [ ] Add negative-space tests for style leakage into factual claims.
- [ ] Add clean-room tests across multiple consumers.
- [ ] Keep `STYLE_FIDELITY != FACTUAL_ACCURACY != PHYSICAL_TRUTH` explicit.

## Phase 6 — Multi-turn ESS switching

- [ ] Define deterministic style persistence across a conversation route epoch.
- [ ] Define explicit transition events rather than model-inferred mood switching.
- [ ] Add hysteresis/dwell rules only if multi-turn chattering becomes a demonstrated problem.
- [ ] Make transition receipts replayable from explicit request events.

## Long-term invariants

```text
CONCAP_ID != CAPSULE_BYTES
PUBLIC_ROUTE != PRIVATE_PAYLOAD
ROUTING != FACTUAL_AUTHORITY
STYLE_SWITCH != EPISTEMIC_SWITCH
STYLE_SUPPORT != EVIDENCE
SELECTED != LOADED
LOADED != TRUE
```
