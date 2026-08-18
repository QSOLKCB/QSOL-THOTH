# QSOL-THOTH Architecture

## Role

QSOL-THOTH is the public deterministic control plane between semantic context requirements, portable object resolution, explicit receiver-style state, and recovery conformance.

Its canonical router answers one narrow question:

> Given an explicit task intent and optional explicit receiver style, which versioned CONCAP roles should be requested, and which ESS style state should be applied?

Separate THOTH side contracts can validate caller-supplied instance metadata, replay explicit multi-turn style events, and receipt structured ARK observations. None of those contracts answers whether private capsules actually exist, whether their contents are true, or whether a recovery succeeded.

## Layer separation

```text
QSOL-CONTEXT
  canonical source authority
        |
        v
QSOL-CONTROL
  deterministic export / byte operations
        |
        v
portable CONCAP bundle
  explicit immutable objects
        |
        v
QSOL-THOTH
  route + resolve + replay public contracts
        |
        v
consumer
        |
        v
QSOL-ARK
  clean-room recovery evaluation authority

QSOL-CAPSULES
  private immutable artifact store
        |
        +-- supplies explicit private instance metadata when authorized
```

### Authority ownership

| Layer | Owns | Does not own |
|---|---|---|
| QSOL-CONTEXT | canonical context records | generated capsule identity |
| CONCAP | semantic role ids | concrete bytes |
| QSOL-THOTH | deterministic role/style selection, portable resolution, session replay, conformance receipts | factual truth, private availability, or ARK evaluation authority |
| QSOL-CONTROL | pack/unpack/verify implementation | context truth |
| QSOL-CAPSULES | private immutable artifact instances | canonical factual authority |
| QSOL-ARK | recovery evaluation | source authorship |

## Canonical routing algorithm

For `QSOL-THOTH/ROUTE-REQUEST/1`:

1. Reject duplicate JSON object members when reading request files.
2. Require an exact protocol id.
3. Require an ASCII intent token matching `^[a-z0-9_.-]+$`.
4. Resolve only an exact canonical intent or exact declared alias.
5. Fail closed if no route exists.
6. If an explicit style token is present, require an exact declared ESS state.
7. Otherwise use the route's declared default style.
8. Take the set union of route CONCAPs and style receiver-support CONCAPs.
9. Sort the set by the public registry's unique integer order, then UTF-8 id as defensive tie-break.
10. Hash the canonical request.
11. Hash the exact public routing configuration bytes.
12. Hash the exact router implementation bytes.
13. Construct the decision body.
14. Hash the canonical decision body to create `decision_sha256`.
15. Emit canonical JSON.

No canonical step depends on a clock, random source, network query, embedding, fuzzy matcher, model classification, or private storage state.

## Acyclic decision receipt

```text
request bytes ---------> request_sha256
configuration bytes ---> configuration_sha256
implementation bytes --> implementation_sha256
          \                |               /
           \               |              /
            +-------- decision body ------+
                         |
                         v
                   decision_sha256
```

`decision_sha256` is not present in its own hash input.

```text
DECISION_ID != SELF_HASH_INPUT
```

## ESS-style state machine

ESS-style switching is deliberately smaller than a general persona system.

A state declares:

- stable public id;
- deterministic order;
- receiver role;
- optional receiver-support CONCAP ids.

The style state is fixed for a route decision. A new explicit request creates a new route decision rather than silently mutating an existing one.

Initial states:

```text
neutral
technical
formal
research
creative
australian_humour
```

## Multi-turn ESS sessions

The one-turn router remains unchanged. `QSOL-THOTH/ESS-SESSION/1` adds an explicit event log above it.

- the first route uses its declared default style;
- a current style persists across later route events;
- the effective route is rebuilt with that style so its support CONCAPs are selected correctly;
- only explicit transition/reset events change session state;
- optional dwell and hysteresis count declared events, not time;
- every event receipt is chained to the previous receipt.

```text
STYLE_PERSISTENCE != EPISTEMIC_PERSISTENCE
REPLAY_RECEIPT != HIDDEN_STATE
```

## Instance-history validation

`QSOL-CAPSULES/CONCAP-INSTANCE-HISTORY/1` is caller-supplied private metadata. THOTH validates content-addressed snapshot chains, exact source/generator/policy/capsule bindings, historical role instances, and append-only prefixes. THOTH neither discovers nor stores the underlying private bytes.

```text
INSTANCE_HISTORY != CAPSULE_BYTES
SYNTHETIC_CONFORMANCE != ACCEPTED_PRIVATE_SNAPSHOT
```

## ARK evaluation receipts

QSOL-ARK retains evaluation authority. THOTH's evaluator deterministically counts explicit observations across separate dimensions, enforces portable-only clean-room declarations, compares transport object observations, and rejects negative-space violations. It emits no aggregate truth score.

```text
STYLE_FIDELITY != FACTUAL_ACCURACY != PHYSICAL_TRUTH
MEASURED_OBSERVATION != AUTOMATIC_TRUTH
```

## Style and epistemics

Receiver support can influence phrasing, pacing, examples, humour, formatting, and collaboration tone.

It cannot promote or demote evidence.

```text
STYLE_SWITCH != EPISTEMIC_SWITCH
STYLE_SUPPORT != EVIDENCE
COMEDIC_FICTION != BIOGRAPHICAL_FACT
RECEIVER_STYLE != CANONICAL_CONTEXT
```

A technically reviewed claim remains subject to the same provenance requirements whether delivered neutrally or with Australian humour.

## Minimal disclosure principle

Canonical routing emits semantic role ids only. It does not enumerate private files or inspect QSOL-CAPSULES. The separate instance-history validator reads only the explicit metadata file supplied by its caller and never performs repository discovery.

This makes route decisions publicly auditable while private resolution remains private.

```text
PUBLIC_ROUTE != PRIVATE_PAYLOAD
ROUTE_DECISION != CAPSULE_AVAILABILITY
```

Portable resolution consumes a route decision plus an explicit object index and emits its own separately hashed receipt.
