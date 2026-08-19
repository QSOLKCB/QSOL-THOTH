# CONCAP Instance History

QSOL-THOTH publishes a validator for **private instance metadata** without publishing private capsule payloads.

The contract is `QSOL-CAPSULES/CONCAP-INSTANCE-HISTORY/1`. It records an ordered chain of accepted snapshots. Each snapshot binds:

- its exact predecessor;
- the exact canonical-source Git commit;
- the SHA-256 of the projected source bytes;
- the exact generator Git commit;
- the capsule policy SHA-256;
- the fixed-point verification receipt SHA-256;
- each role's capsule basename, exact byte size, and capsule SHA-256.

The `snapshot_id` is an acyclic SHA-256 over the snapshot body. The `history_id` is an acyclic SHA-256 over the complete history body.

```text
INSTANCE_HISTORY != CAPSULE_BYTES
ACCEPTED_METADATA != FACTUAL_AUTHORITY
CAPSULE_PRESENT != CAPSULE_VERIFIED
```

## Historical role instances

The same semantic role may appear in many snapshots. Each occurrence remains separately bound to its snapshot and exact capsule hash. Later instances do not overwrite earlier ones.

Within one snapshot, role ids are unique and UTF-8 sorted. Several roles may name the same capsule file only when its hash and size metadata agree exactly. Across the complete history, one capsule hash must always bind the same exact byte size, even when different basenames refer to it.

## Append-only check

```bash
python3 tools/instance_history.py validate \
  --history examples/instances/synthetic-instance-history.json

python3 tools/instance_history.py check-append-only \
  --base old-history.json \
  --candidate new-history.json
```

The append check validates both documents, rejects truncation, preserves `record_class`, and requires every accepted base snapshot to remain byte-identical as the candidate's prefix. A synthetic history therefore cannot be relabeled as accepted private execution during append validation.

```text
SNAPSHOT_APPEND_ONLY != SOURCE_IMMUTABLE
HISTORICAL_INSTANCE != CURRENT_INSTANCE
```

## Synthetic versus real records

`record_class` prevents a public test vector from masquerading as completed private execution:

```text
synthetic-conformance
accepted-private-metadata
```

This public repository intentionally continues to ship only the `synthetic-conformance` fixture. A real accepted snapshot and its `accepted-private-metadata` history now exist in private QSOL-CAPSULES after pinned capsule generation, fixed-point verification, repeat-pack byte comparison, immutable snapshot acceptance, and validation with this public THOTH contract.

THOTH does not publish the private capsule payloads or turn their existence into factual authority.

See `schema/concap-instance-history.schema.json`.
