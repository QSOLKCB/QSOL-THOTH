# QSOL-THOTH

**Public deterministic routing layer for the QSOL-CONCAP system.**

QSOL-THOTH decides **which semantic context capsules are needed** for a declared task and **which ESS-style receiver state should be used**. It does not store private context, capsule payloads, model memory, or factual authority.

## Architecture

```text
QSOL-CONTEXT
  canonical context source
        |
        v
CONCAP semantic namespace
        |
        v
QSOL-THOTH
  deterministic routing
  + ESS-style switching
  + historical basis planning
        |
        v
QSOL-CONTROL -> QSOL-CAPSULES -> QSOL-ARK
```

## CONCAP

`CONCAP` means **CONtext CAPsules**. A CONCAP id names a semantic recovery role, not a particular byte sequence.

```text
concap.identity.core/1
concap.workstyle.engineering/1
concap.research.active/1
concap.receipts/1
concap.culture.core/1
concap.culture.au-humour/1
concap.culture.comedy/1
concap.culture.music/1
concap.history.timeline/1
```

Private capsule instances remain outside this public repository.

## Routing and ESS

Canonical routing uses exact declared tokens only. Unknown ids fail closed; there is no fuzzy matching, embedding search, model guess, wall-clock input, randomness, or network dependency.

```bash
python3 tools/thoth.py route --intent comedy
python3 tools/thoth.py route --intent software_review --style australian_humour
python3 tools/thoth.py route --intent historical_reconstruction
```

Receiver style can affect presentation and request style-support CONCAPs. It cannot change evidence or factual authority.

## CONCAP Conformance Suite

```bash
python3 tools/thoth.py validate
python3 tools/thoth.py conformance
python3 -m unittest discover -s tests -v
```

The suite publishes machine-readable schemas, frozen request→decision receipts, negative vectors with stable machine error codes, and explicit role-version compatibility rules. See `CONFORMANCE.md`.

```text
SAME_REQUEST + SAME_CONFIGURATION + SAME_IMPLEMENTATION
= SAME_DECISION_BYTES
IMPLEMENTATION_CHANGE != SILENT_VECTOR_REFRESH
NEW_ROLE_VERSION != BACKWARD_COMPATIBLE_BY_DEFAULT
```

## Historical reconstruction

`concap.history.timeline/1` provides a deterministic semantic history role. A dataset declares retention obligations and candidate records; `tools/history_minset.py` finds the exact minimum dependency-closed set by canonical record bytes and packages it into a self-contained basis.

The demonstration freezes this result:

```text
candidate records:             17
selected records:               7
candidate record bytes:      3397
selected record bytes:       1541   (45.36%)
canonical dataset bytes:     3986
self-contained basis bytes:  2426   (60.86%)
```

```bash
python3 tools/history_minset.py plan --dataset examples/history/world-history-scaffold.json
python3 tools/history_minset.py pack --dataset examples/history/world-history-scaffold.json > /tmp/history-basis.json
python3 tools/history_minset.py reconstruct --basis /tmp/history-basis.json
```

See `HISTORY-CONCAP.md`.

## Hard boundaries

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
RESTORED_CONTEXT != ORIGINAL_ASSISTANT_INSTANCE
```

For exact recovery of an original source file, retain its bytes directly or through a lossless deterministic encoding. Historical min-set planning targets declared semantic reconstruction only.

## Review invariant

```text
CODEX_REVIEW_REQUESTED => PR_DRAFT == FALSE
```

## License

MPL-2.0. See `LICENSE`.
