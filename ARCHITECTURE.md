# QSOL-THOTH Architecture

## Role

QSOL-THOTH is the public deterministic control plane between semantic context requirements and private capsule resolution.

It answers one narrow question:

> Given an explicit task intent and optional explicit receiver style, which versioned CONCAP roles should be requested, and which ESS style state should be applied?

It does not answer whether the requested private capsules exist, whether their contents are true, or whether a recovery succeeded.

## Layer separation

```text
QSOL-CONTEXT
  canonical source authority
        |
        v
CONCAP
  public semantic role namespace
        |
        v
QSOL-THOTH
  route + ESS style decision
        |
        v
private resolver
  role -> concrete instance mapping
        |
        v
QSOL-CONTROL
  deterministic byte operations
        |
        v
QSOL-CAPSULES
  immutable private artifact store
        |
        v
QSOL-ARK
  clean-room recovery evaluation
```

### Authority ownership

| Layer | Owns | Does not own |
|---|---|---|
| QSOL-CONTEXT | canonical context records | generated capsule identity |
| CONCAP | semantic role ids | concrete bytes |
| QSOL-THOTH | deterministic role/style selection | factual truth or private availability |
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

THOTH emits semantic role ids only. It does not enumerate private files or inspect QSOL-CAPSULES.

This makes route decisions publicly auditable while private resolution remains private.

```text
PUBLIC_ROUTE != PRIVATE_PAYLOAD
ROUTE_DECISION != CAPSULE_AVAILABILITY
```

Future private resolvers should consume a route decision plus an explicit availability map and emit their own separately hashed resolution receipt.
