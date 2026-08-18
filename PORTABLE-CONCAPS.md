# Portable CONCAP Delivery

QSOL-THOTH separates **semantic routing** from **instance resolution** and **transport** so a model can consume approved context objects without receiving access to the private repositories that authored them.

## Architecture

```text
PRIVATE AUTHORING / BUILD SIDE

QSOL-CONTEXT and other private sources
        |
        | explicit allow-listed export specification
        v
QSOL-CONTROL
        |
        | deterministic QSOL-RESTORE-DAT/1 objects
        | private source references stripped from portable manifests
        v
portable CONCAP bundle
  BOOTSTRAP.json
  OBJECTS.json
  objects/sha256/<prefix>/<digest>.dat

------------------------- trust boundary -------------------------

CONSUMER SIDE

THOTH route decision
        |
        v
concap_resolver.py
        |
        | role id -> content-addressed object id
        v
portable bundle / static endpoint / LAN / USB / capability relay
        |
        v
model
```

The model does not need GitHub credentials, repository paths, `.git` metadata, or direct access to QSOL-CONTEXT or QSOL-CAPSULES.

## Three separate decisions

```text
THOTH ROUTING
  decides WHAT semantic roles are required

CONCAP RESOLUTION
  decides WHICH immutable object satisfies each selected role

TRANSPORT
  decides WHERE the verified object bytes are obtained
```

```text
ROUTING != RESOLUTION
RESOLUTION != TRANSPORT
TRANSPORT != AUTHORITY
```

Canonical THOTH routing remains network-free and availability-free. A route can be computed when no bundle is present. Resolution happens afterwards against an explicit `QSOL-CONCAP/OBJECT-INDEX/1` supplied by the consumer environment.

## Public source-class bindings

`ai/concap-source-bindings.json` defines only public semantic source classes and loading requirements.

It deliberately does **not** contain:

- private repository names;
- private repository URLs;
- private source paths;
- source commits from a private repository;
- credentials or capability tokens;
- concrete capsule availability.

```text
SOURCE_BINDING != PRIVATE_SOURCE_PATH
DECLARED_ROLE != AVAILABLE_OBJECT
```

Receiver-style roles are `best_effort`. Missing style enrichment does not convert into a factual failure. Data/recovery roles marked `required` fail closed when an explicit object index cannot satisfy them.

## Portable object index

A `QSOL-CONCAP/OBJECT-INDEX/1` binds versioned CONCAP role ids to immutable object ids.

Object identity is always:

```text
sha256(exact object bytes)
```

and the canonical relative path is derived from that identity:

```text
objects/sha256/<first-two-hex>/<64-hex>.dat
```

The index contains no canonical network URL. The same verified bundle may therefore be copied to a USB device, unpacked from a deterministic archive, served by static HTTPS, mounted over a LAN, or exposed through an authenticated capability relay without changing its object identities.

```text
OBJECT_IDENTITY != TRANSPORT_LOCATION
```

The same object may satisfy several semantic roles. For example, one exported cultural object may be bound to `concap.culture.core/1`, `concap.culture.au-humour/1`, and `concap.culture.comedy/1`; the resolver returns that object once in `objects_to_fetch` while preserving every role binding in the receipt.

## Bootstrap

`QSOL-CONCAP/BOOTSTRAP/1` is the small entry document for a portable bundle. It identifies the exact `OBJECTS.json` bytes and counts the declared objects and roles. It carries no private source path.

A clean consumer can therefore be given only a bundle or bundle location:

```text
BOOTSTRAP.json
      |
      v
OBJECTS.json
      |
      v
content-addressed .dat objects
```

GitHub is not part of this recovery dependency.

## Resolution

Create a normal THOTH decision:

```bash
python3 tools/thoth.py route --intent research > /tmp/route.json
```

Resolve it against an explicit portable object index:

```bash
python3 tools/concap_resolver.py resolve \
  --decision /tmp/route.json \
  --index /path/to/bundle/OBJECTS.json
```

The resolver verifies the route-decision receipt, source-binding contract, object-index receipt, role references, object declarations and content-derived paths. It performs no network access.

A `QSOL-THOTH/RESOLUTION-RECEIPT/1` then records:

- the exact THOTH route-decision id;
- the exact public binding-configuration id;
- the exact portable object-index id;
- selected role -> object bindings;
- the de-duplicated objects that must be fetched;
- optional style roles that were unavailable;
- an acyclic resolution SHA-256 receipt.

```text
RESOLVED != LOADED
LOADED != TRUE
RESOLUTION != FACTUAL_AUTHORITY
```

## Privacy and export boundary

A portable bundle can still contain sensitive material. Content addressing is integrity, not encryption.

The coordinated QSOL-CONTROL exporter constructs new `QSOL-RESTORE-DAT/1` objects from explicit pack specifications and omits private `source_ref` metadata from the portable manifests. That removes repository/path references from transport metadata; it does not magically anonymize the source payload itself.

```text
RESTRICTED_BUNDLE != ENCRYPTED_BUNDLE
SOURCE_REF_STRIPPED != SOURCE_BYTES_ANONYMIZED
PRIVATE_SOURCE != PORTABLE_BUNDLE
BUNDLE_OBJECT != CANONICAL_SOURCE
```

Public object delivery is appropriate only for objects whose export policy permits public release. Restricted objects must remain in a restricted channel such as a local copy, encrypted outer transport, or authenticated relay.

## Capability relay

A capability relay is a **transport implementation**, not part of canonical THOTH resolution. A relay may authorize a model/session to retrieve only the object ids named by a resolution receipt.

The capability token, relay URL, expiry time and network state stay outside canonical object identity and THOTH routing.

```text
MODEL_HAS_CAPABILITY != MODEL_HAS_REPOSITORY_ACCESS
```

This means the same bundle contract can be implemented later by a local HTTP service, object store, signed URL service, or another broker without changing the semantic routing protocol.

## Core invariant

```text
MODEL_CAN_RECONSTRUCT_CONTEXT
!=
MODEL_CAN_ACCESS_PRIVATE_SOURCE
```

Private repositories are authoring and verification environments. Portable verified objects are the consumer interface.
