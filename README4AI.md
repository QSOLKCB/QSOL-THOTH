# QSOL-THOTH — AI Bootstrap

QSOL-THOTH is the **public deterministic routing layer** for QSOL-CONCAP.

It does not contain private user context or capsule payload bytes.

## Load order

1. `ai/concap-registry.json`
2. `ai/concap-compatibility.json`
3. `ai/ess-style-machine.json`
4. `ai/router.json`
5. `schema/concap-registry.schema.json`
6. `schema/concap-compatibility.schema.json`
7. `schema/ess-style-machine.schema.json`
8. `schema/router.schema.json`
9. `schema/route-request.schema.json`
10. `schema/route-decision.schema.json`
11. `CONFORMANCE.md`
12. `tools/thoth.py`
13. `README.md`

## Core interpretation

```text
CONCAP = semantic context-capsule role
THOTH  = deterministic selector/router
ESS    = deterministic receiver-style state machine
CONTROL = byte-exact capsule pack/verify implementation
CAPSULES = private immutable capsule instances
ARK = recovery/evaluation authority
```

Do not reinterpret CONCAP ids as actual capsule bytes.

## Routing rules

- Accept exact declared ASCII intent tokens only.
- Resolve only exact canonical ids or exact declared aliases.
- Unknown intents fail closed.
- Unknown styles fail closed.
- An explicit declared style wins over the route default.
- A style remains fixed for one route decision.
- De-duplicate selected CONCAP ids.
- Order selected CONCAP ids by `ai/concap-registry.json#capsules[].order`.
- Do not use fuzzy matching, embeddings, wall-clock state, random input, or network state in canonical routing.

## CONCAP versioning

CONCAP role ids are versioned semantic identities.

```text
EXISTING_ROLE_VERSION => SEMANTICS_IMMUTABLE
SEMANTIC_CHANGE => NEW_ROLE_VERSION
NEW_ROLE_VERSION != BACKWARD_COMPATIBLE_BY_DEFAULT
```

Never silently substitute another version. Read `ai/concap-compatibility.json`.

## Conformance

Before changing routing semantics, run:

```bash
python3 tools/thoth.py validate
python3 tools/thoth.py conformance
python3 -m unittest discover -s tests -v
```

Positive vectors freeze complete route decisions. Negative vectors freeze stable error codes.

Do not regenerate expected receipts merely to make CI green. A changed known-answer receipt is a semantic review event.

## Authority boundaries

```text
CONCAP_ID != CAPSULE_BYTES
PUBLIC_ROUTE != PRIVATE_PAYLOAD
ROUTING != FACTUAL_AUTHORITY
STYLE_SWITCH != EPISTEMIC_SWITCH
STYLE != TRUTH
STYLE != CLAIM_CLASS
STYLE_SUPPORT != EVIDENCE
SELECTED != LOADED
LOADED != TRUE
```

A style support CONCAP can affect presentation and collaboration tone. It cannot grant evidence status to a claim.

Comedy artifacts and deliberate fiction remain non-factual even when selected to guide receiver style.

## Decision receipts

A `QSOL-THOTH/ROUTE-DECISION/1` receipt binds:

- canonical request bytes;
- the exact public THOTH routing configuration;
- the exact `tools/thoth.py` implementation bytes;
- the canonical intent;
- the selected ESS style;
- the ordered CONCAP ids;
- mandatory authority boundaries.

`decision_sha256` hashes the decision body **without** `decision_sha256` itself.

```text
DECISION_RECEIPT != SELF_HASH_INPUT
```

## Private-data prohibition

Never add real private capsule payloads, secrets, credentials, provider-private state, hidden reasoning, or private context records to QSOL-THOTH.

Public synthetic examples and known-answer vectors are allowed.

## Review workflow

Before requesting or expecting Codex review:

```text
CODEX_REVIEW_REQUESTED => PR_DRAFT == FALSE
```

If the PR is draft, mark it Ready for review first.
