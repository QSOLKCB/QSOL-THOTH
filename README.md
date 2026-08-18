# QSOL-THOTH

**Public deterministic routing, portable resolution, session-style, and conformance layer for the QSOL-CONCAP system.**

QSOL-THOTH decides **which semantic context capsules are needed** for a declared task, **which ESS-style receiver state should be used**, and—when given an explicit portable object index—**which immutable objects satisfy those roles**. It also validates private instance-history metadata, replays explicit multi-turn style events, and builds separated QSOL-ARK evaluation receipts. It does not store private context, real capsule payloads, model memory, credentials, transport secrets, or factual authority.

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
  routing + multi-turn ESS + transport-neutral resolution
        |
        v
model / consumer
        |
        v
QSOL-ARK
  explicit clean-room evaluation authority
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
python3 tools/instance_history.py validate --history examples/instances/synthetic-instance-history.json
python3 tools/ark_evaluation.py validate-policy
python3 tools/ess_session.py validate-policy
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

## Immutable instance history

`tools/instance_history.py` validates caller-supplied private metadata for accepted CONCAP snapshots without reading or publishing capsule payloads. Snapshot identities bind source, source projection, generator, policy, verification receipt, role, capsule hash, and size. A separate append-only command rejects truncation or mutation of an accepted history prefix.

The committed example is explicitly `synthetic-conformance`; it is not evidence that a real QSOL-CAPSULES snapshot was generated.

See `INSTANCE-HISTORY.md`.

## QSOL-ARK evaluation

`tools/ark_evaluation.py` turns explicit observations into a deterministic evaluation receipt. Route sufficiency, route minimality, style fidelity, factual accuracy, and historical coverage remain separate exact fractions. Clean-room requirements, four-transport byte equivalence, and negative-space violations fail closed. No aggregate truth score is emitted.

See `ARK-EVALUATION.md`.

## Multi-turn ESS sessions

`tools/ess_session.py` persists receiver style across routed turns until an explicit transition or reset. It supports immediate switching plus a demonstrated deterministic hysteresis/dwell profile, rebuilds each effective route with the persisted style's support CONCAPs, and emits chained acyclic transition receipts.

```bash
python3 tools/ess_session.py replay \
  --session examples/ess/demonstrated-hysteresis.session.json
```

See `ESS-SESSIONS.md`.

## Hard boundaries

```text
CONCAP_ID != CAPSULE_BYTES
PUBLIC_ROUTE != PRIVATE_PAYLOAD
ROUTING != FACTUAL_AUTHORITY
STYLE_SWITCH != EPISTEMIC_SWITCH
STYLE_PERSISTENCE != EPISTEMIC_PERSISTENCE
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
INSTANCE_HISTORY != CAPSULE_BYTES
SNAPSHOT_APPEND_ONLY != SOURCE_IMMUTABLE
STYLE_FIDELITY != FACTUAL_ACCURACY != PHYSICAL_TRUTH
TRANSPORT_EQUIVALENCE != AUTHORITY
REPLAY_RECEIPT != HIDDEN_STATE
```

For exact recovery of an original source file, retain its bytes directly or through a lossless deterministic encoding. Portable delivery changes how approved bytes reach a consumer; it does not change their epistemic status.

## Review invariant

```text
CODEX_REVIEW_REQUESTED => PR_DRAFT == FALSE
```

## License

MPL-2.0. See `LICENSE`.
