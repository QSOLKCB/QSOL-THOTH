# AGENTS.md — QSOL-THOTH

QSOL-THOTH is a public routing protocol. Treat its public/private boundary as a hard invariant.

## Required behavior

- Read `README4AI.md` before modifying routing semantics.
- Validate with `python3 tools/thoth.py validate`.
- Replay frozen vectors with `python3 tools/thoth.py conformance`.
- Run `python3 -m unittest discover -s tests -v` after implementation changes.
- Keep canonical routing deterministic, network-free, clock-free, and random-free.
- Use exact declared intent/style tokens only.
- Fail closed on ambiguity or unknown canonical ids.
- Version semantic changes rather than silently changing the meaning of an existing CONCAP id.
- Treat any changed known-answer receipt as a review event; never refresh it just to make CI green.
- Keep route selection, style selection, evidence admission, and factual authority as separate concepts.
- Open PRs intended for Codex review marked Ready for review, not draft.

## Forbidden behavior

Do not:

- commit real private capsule bytes;
- commit secrets, credentials, provider-private state, or hidden reasoning;
- make THOTH query private QSOL-CAPSULES state as part of canonical public routing;
- use embeddings, fuzzy semantic matching, nondeterministic model classification, network results, random state, or wall-clock state as canonical route inputs;
- let receiver style promote a claim's epistemic class;
- treat deliberate fiction or comedy as biographical evidence;
- redefine an existing versioned CONCAP id in place;
- silently substitute `/2` when a route declares `/1`;
- auto-accept conformance drift.

## Boundary contract

```text
CONCAP_ID != CAPSULE_BYTES
ROUTING != FACTUAL_AUTHORITY
STYLE_SWITCH != EPISTEMIC_SWITCH
STYLE_SUPPORT != EVIDENCE
ROUTE_DECISION != CAPSULE_AVAILABILITY
NEW_ROLE_VERSION != BACKWARD_COMPATIBLE_BY_DEFAULT
CONFORMANCE_PASS != FACTUAL_TRUTH
CODEX_REVIEW_REQUESTED => PR_DRAFT == FALSE
```

If a proposed change violates one of these boundaries, stop and redesign the change rather than weakening the invariant.
