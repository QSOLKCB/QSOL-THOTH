# CONCAP — CONtext CAPsules

CONCAP is the public semantic namespace used by QSOL-THOTH to describe **what kind of context is required** without exposing or identifying private payload bytes.

## Three separate identities

A complete recovery system must not collapse these identities:

```text
semantic role      -> concap.culture.comedy/1
concrete instance  -> private content-addressed capsule artifact
container bytes    -> exact QSOL-RESTORE-DAT/1 byte sequence
```

Therefore:

```text
CONCAP_ROLE != CAPSULE_INSTANCE
CAPSULE_INSTANCE != CONTAINER_FORMAT
CONCAP_ID != CAPSULE_BYTES
```

## Why CONCAP exists

Without a semantic layer, a router has only two bad options:

1. load one giant context object for every task; or
2. know private filenames and storage details directly.

CONCAP lets THOTH instead emit a minimal public request such as:

```json
{
  "intent": "comedy",
  "style": "australian_humour",
  "concaps": [
    "concap.culture.core/1",
    "concap.culture.au-humour/1",
    "concap.culture.comedy/1"
  ]
}
```

A private resolver can later map those semantic ids to concrete available artifacts.

## Minimum sufficient selection

THOTH SHOULD select the smallest declared CONCAP set sufficient for the route and receiver style.

THOTH MUST NOT treat selection as evidence that a concrete private capsule exists.

```text
SELECTED != AVAILABLE
AVAILABLE != VERIFIED
VERIFIED != FACTUAL_TRUTH
```

The public router has no authority to inspect private QSOL-CAPSULES state during canonical routing.

## Receiver support

ESS-style states may declare `support_concaps`.

Example:

```text
software_review
  route context:
    workstyle + receipts

explicit style:
  australian_humour

receiver support:
  culture.core + culture.au-humour + culture.comedy
```

The union is deterministic, but the authority classes remain separate.

```text
STYLE_SUPPORT != EVIDENCE
COMEDY_ARTIFACT != BIOGRAPHICAL_FACT
DELIBERATE_FICTION != OBSERVATION
```

## Binary and media artifacts

CONCAP is media-neutral. A concrete context capsule may contain UTF-8 text, JSON, JPEG, PNG, WAV, PDF, or other raw bytes when the underlying pack implementation supports them.

QSOL-CONTROL already owns deterministic byte packing. CONCAP does not introduce Base64 wrapping or a second binary container merely to route media.

## Versioning

The `/1` suffix is part of the semantic role id.

Changing the meaning or authority expectations of a role requires a new semantic versioned id rather than silently redefining an existing one.

Example:

```text
concap.culture.comedy/1
concap.culture.comedy/2
```

A new concrete capsule instance containing updated artifacts does **not** by itself require a new CONCAP role version if the semantic role remains unchanged.

## Public/private split

Public QSOL-THOTH may contain:

- role ids;
- route mappings;
- style mappings;
- schemas;
- validators;
- synthetic fixtures.

Private systems may contain:

- actual user context;
- content-addressed capsule instances;
- restricted cultural artifacts;
- private provenance and receipts.

The public layer must remain useful without disclosure of the private layer.
