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
  what context roles exist
        |
        v
QSOL-THOTH
  deterministic routing
  + ESS-style switching
        |
        +-------------------+
        |                   |
        v                   v
 minimum CONCAP set     receiver style state
        |                   |
        +---------+---------+
                  |
                  v
            QSOL-CONTROL
       byte-exact pack / verify
                  |
                  v
           QSOL-CAPSULES
      private immutable instances
                  |
                  v
              QSOL-ARK
       clean-room recovery scoring
```

## CONCAP

`CONCAP` means **CONtext CAPsules**.

A CONCAP id names a semantic recovery role. It does **not** name a particular byte sequence.

Initial public ids include:

```text
concap.identity.core/1
concap.workstyle.engineering/1
concap.research.active/1
concap.receipts/1
concap.culture.core/1
concap.culture.au-humour/1
concap.culture.comedy/1
concap.culture.music/1
```

Private capsule instances remain outside this public repository.

## Deterministic routing

The router accepts an explicit intent token and optional explicit style token.

```text
request
  -> validate exact protocol
  -> resolve intent by exact id or declared alias
  -> choose fixed route
  -> choose explicit style or route default
  -> union route CONCAPs with receiver-support CONCAPs
  -> order by registry ordinal
  -> emit canonical decision receipt + SHA-256 identity
```

Unknown intent ids fail closed. There is no fuzzy matching, embedding search, model guess, wall-clock input, random input, or network dependency in canonical routing.

## ESS-style switching

THOTH treats style switching as a finite public state machine. The initial states are:

```text
neutral
technical
formal
research
creative
australian_humour
```

An explicit user style request wins when it names a declared state. Otherwise the selected route supplies the default style.

Style support may request cultural CONCAPs, but those entries remain receiver guidance only.

## CONCAP Conformance Suite

Phase 1 freezes the public router before private source binding.

```bash
python3 tools/thoth.py validate
python3 tools/thoth.py conformance
python3 -m unittest discover -s tests -v
```

The conformance suite includes machine-readable schemas, frozen positive request→decision receipts, negative vectors with stable machine error codes, and an explicit role-version compatibility policy.

```text
SAME_REQUEST + SAME_CONFIGURATION + SAME_IMPLEMENTATION
= SAME_DECISION_BYTES

IMPLEMENTATION_CHANGE != SILENT_VECTOR_REFRESH
NEW_ROLE_VERSION != BACKWARD_COMPATIBLE_BY_DEFAULT
```

See `CONFORMANCE.md`.

## Hard boundaries

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
RESTORED_CONTEXT != ORIGINAL_ASSISTANT_INSTANCE
```

The same canonical context may be projected through different receiver styles without changing the factual status of any claim.

## CLI

Validate all public contracts:

```bash
python3 tools/thoth.py validate
```

Replay the frozen conformance vectors:

```bash
python3 tools/thoth.py conformance
```

Route an intent:

```bash
python3 tools/thoth.py route --intent comedy
```

Explicitly select a declared receiver style:

```bash
python3 tools/thoth.py route --intent software_review --style australian_humour
```

The route output is canonical JSON and includes configuration, implementation, request, and decision SHA-256 receipts.

## Public/private boundary

QSOL-THOTH is intentionally public. It may publish:

- CONCAP ids and roles;
- routing policy;
- role-version compatibility policy;
- style-state policy;
- schemas;
- synthetic requests and conformance vectors;
- deterministic routing code.

It must not publish:

- real private capsule bytes;
- private source records;
- secrets or credentials;
- provider-private state;
- hidden reasoning;
- claims that a route decision proves factual truth.

## Review invariant

Pull requests intended for Codex review must be **Ready for review**, never left as draft.

```text
CODEX_REVIEW_REQUESTED => PR_DRAFT == FALSE
```

## License

MPL-2.0. See `LICENSE`.
