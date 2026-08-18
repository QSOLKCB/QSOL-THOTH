# QSOL-THOTH — AI Bootstrap

QSOL-THOTH is the **public deterministic routing layer** for QSOL-CONCAP. It does not contain private user context or capsule payload bytes.

## Load order

1. `ai/concap-registry.json`
2. `ai/concap-compatibility.json`
3. `ai/ess-style-machine.json`
4. `ai/router.json`
5. `ai/history-reconstruction-policy.json`
6. `CONFORMANCE.md`
7. `HISTORY-CONCAP.md`
8. `tools/thoth.py`
9. `tools/history_minset.py`
10. `README.md`

Machine schemas live under `schema/`; frozen routing vectors live under `vectors/`.

## Core interpretation

```text
CONCAP = semantic context-capsule role
THOTH = deterministic selector/router
ESS = deterministic receiver-style state machine
HISTORY BASIS = minimum declared semantic reconstruction package
CONTROL = byte-exact capsule pack/verify implementation
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
- Do not use fuzzy matching, embeddings, wall-clock state, random input, or network state in canonical routing.

## Versioning and conformance

```text
EXISTING_ROLE_VERSION => SEMANTICS_IMMUTABLE
SEMANTIC_CHANGE => NEW_ROLE_VERSION
NEW_ROLE_VERSION != BACKWARD_COMPATIBLE_BY_DEFAULT
```

Before changing routing semantics:

```bash
python3 tools/thoth.py validate
python3 tools/thoth.py conformance
python3 -m unittest discover -s tests -v
```

Do not refresh frozen receipts merely to make CI green.

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

## Authority boundaries

```text
CONCAP_ID != CAPSULE_BYTES
PUBLIC_ROUTE != PRIVATE_PAYLOAD
ROUTING != FACTUAL_AUTHORITY
STYLE_SWITCH != EPISTEMIC_SWITCH
STYLE_SUPPORT != EVIDENCE
SELECTED != LOADED
LOADED != TRUE
```

Comedy remains non-factual when selected for receiver style; historical coverage remains non-evidence when selected for reconstruction.

## Private-data prohibition

Never add real private capsule payloads, secrets, credentials, provider-private state, hidden reasoning, or private context records to QSOL-THOTH. Public synthetic examples, known-answer vectors, and demonstration-only history scaffolds are allowed.

## Review workflow

```text
CODEX_REVIEW_REQUESTED => PR_DRAFT == FALSE
```
