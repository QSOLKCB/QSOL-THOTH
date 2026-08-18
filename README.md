# QSOL-THOTH

**Public deterministic routing and portable resolution layer for the QSOL-CONCAP system.**

QSOL-THOTH decides **which semantic context capsules are needed** for a declared task, **which ESS-style receiver state should be used**, and—when given an explicit portable object index—**which immutable objects satisfy those roles**. It does not store private context, capsule payloads, model memory, credentials, transport secrets, or factual authority.

## Architecture

```text
QSOL-CONTEXT
  private canonical context source
        |
        | explicit export policy
        v
QSOL-CONTROL
  deterministic QSOL-RESTORE-DAT/1 packing
        |
        v
portable CONCAP bundle
  BOOTSTRAP.json + OBJECTS.json + objects/
        |
---------------- trust boundary ----------------
        |
        v
QSOL-THOTH
  routing + ESS + transport-neutral resolution
        |
        v
model / consumer
```

QSOL-CAPSULES remains the private immutable recovery-artifact store. A consumer does not need access to QSOL-CONTEXT or QSOL-CAPSULES merely to load an approved portable export.

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

## Routing and ESS

Canonical routing uses exact declared tokens only. Unknown ids fail closed; there is no fuzzy matching, embedding search, model guess, wall-clock input, randomness, private availability lookup, or network dependency.

```bash
python3 tools/thoth.py route --intent comedy
python3 tools/thoth.py route --intent software_review --style australian_humour
python3 tools/thoth.py route --intent historical_reconstruction
```

Receiver style can affect presentation and request style-support CONCAPs. It cannot change evidence or factual authority.

## Portable resolution

`ai/concap-source-bindings.json` publishes abstract source classes and load requirements without publishing private repository paths. `tools/concap_resolver.py` consumes a THOTH route decision plus an explicit `QSOL-CONCAP/OBJECT-INDEX/1` and emits a deterministic resolution receipt.

```bash
python3 tools/thoth.py route --intent research > /tmp/route.json
python3 tools/concap_resolver.py resolve \
  --decision /tmp/route.json \
  --index /path/to/bundle/OBJECTS.json
```

Portable object identity is the SHA-256 of exact object bytes. Object paths are content-derived and relative, so the same bundle can be copied or served through local disk, USB, archive, LAN, static HTTPS, or a capability relay without changing semantic identity.

```text
ROUTING != RESOLUTION
RESOLUTION != TRANSPORT
OBJECT_IDENTITY != TRANSPORT_LOCATION
MODEL_CAN_LOAD_OBJECT != MODEL_CAN_ACCESS_SOURCE_REPOSITORY
```

See `PORTABLE-CONCAPS.md`.

## CONCAP Conformance Suite

```bash
python3 tools/thoth.py validate
python3 tools/thoth.py conformance
python3 tools/concap_resolver.py validate-bindings
python3 -m unittest discover -s tests -v
```

The routing suite publishes machine-readable schemas, frozen request→decision receipts, negative vectors with stable machine error codes, and explicit role-version compatibility rules. Portable resolution has separate public schemas and receipts so transport work does not silently alter the frozen router implementation identity.

```text
SAME_REQUEST + SAME_CONFIGURATION + SAME_IMPLEMENTATION
= SAME_DECISION_BYTES
IMPLEMENTATION_CHANGE != SILENT_VECTOR_REFRESH
NEW_ROLE_VERSION != BACKWARD_COMPATIBLE_BY_DEFAULT
```

See `CONFORMANCE.md`.

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
SOURCE_BINDING != PRIVATE_SOURCE_PATH
RESOLUTION != TRANSPORT
TRANSPORT != AUTHORITY
OBJECT_IDENTITY != TRANSPORT_LOCATION
RESOLUTION != FACTUAL_AUTHORITY
MODEL_CAN_RECONSTRUCT_CONTEXT != MODEL_CAN_ACCESS_PRIVATE_SOURCE
RESTORED_CONTEXT != ORIGINAL_ASSISTANT_INSTANCE
```

For exact recovery of an original source file, retain its bytes directly or through a lossless deterministic encoding. Portable delivery changes how approved bytes reach a consumer; it does not change their epistemic status.

## Review invariant

```text
CODEX_REVIEW_REQUESTED => PR_DRAFT == FALSE
```

## License

MPL-2.0. See `LICENSE`.
