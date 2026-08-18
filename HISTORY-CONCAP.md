# Historical Reconstruction CONCAPs

QSOL-THOTH can treat history as a **declared reconstruction problem** rather than a requirement to retain every available record.

The design is inspired by aggressively compressed chronological presentations such as Bill Wurtz's *history of the entire world, i guess*: a very large chronology can remain recognizable when a small set of anchors and transitions preserve its broad structure. QSOL-THOTH borrows only that information-architecture idea. It does not copy the video's script, music, visuals, or presentation style.

Reference: https://www.youtube.com/watch?v=xuCn8ux2gbs

## The question

> What is the smallest deterministic historical basis that still permits a later consumer to reconstruct every explicitly required semantic anchor?

The answer depends on **retention obligations**. THOTH does not guess what must survive.

A dataset therefore declares semantic obligations, candidate records, dependencies, compact summaries, and a hard non-authority boundary. The planner computes an exact minimum by canonical record bytes.

```text
SOURCE RECORD SET
      |
      v
RETENTION OBLIGATIONS
      |
      v
EXACT BRANCH-AND-BOUND
      |
      v
MINIMUM DEPENDENCY-CLOSED BASIS
      |
      v
SELF-CONTAINED HISTORY BASIS
      |
      v
DETERMINISTIC RECONSTRUCTION
```

## What minimum means

For `QSOL-THOTH/HISTORY-RECONSTRUCTION-POLICY/1`:

1. Every retention obligation must be covered.
2. Selecting a record automatically selects its transitive dependencies.
3. Cost is the sum of canonical JSON bytes for selected records.
4. Search is exact branch-and-bound, not a greedy approximation.
5. Ties resolve by total bytes, then record count, then UTF-8 record ids.
6. Search uses a deterministic node budget, never a wall-clock timeout.
7. Exceeding that budget fails closed.

The selected record payload is wrapped in a self-contained `QSOL-THOTH/HISTORY-BASIS/1`. Reconstruction needs the basis only; it does not require the discarded candidate dataset.

## Demonstration result

`world_history_scaffold` is deliberately **demonstration-only**, not historical authority. It declares 10 retention obligations and 17 candidate records. The exact planner selects seven dependency-closed anchors:

```text
cosmic_anchor
biological_anchor
civilization_anchor
exchange_anchor
industrial_anchor
conflict_anchor
digital_anchor
```

Frozen result:

```text
candidate records:             17
selected records:               7
candidate canonical record:  3397 bytes
selected canonical records:  1541 bytes
record-payload retention:   1541 / 3397 = 45.36%

canonical source dataset:    3986 bytes
self-contained basis:        2426 bytes
full basis retention:      2426 / 3986 = 60.86%
```

The distinction matters. The semantic records themselves compress below half of candidate-record bytes, but a genuinely reconstructable package also needs identifiers, obligations, hashes, boundaries, and provenance links. Those structural costs are counted in the self-contained basis figure.

## Hard boundaries

```text
MINIMUM_SUFFICIENT != COMPLETE_HISTORY
SEMANTIC_RECONSTRUCTION != VERBATIM_SOURCE
COVERED_CLAIM != PROVEN_TRUE
HISTORICAL_SUMMARY != PRIMARY_EVIDENCE
COMPRESSION != OMISSION_AUTHORITY
```

For exact recovery of an original source file, its bytes must still be retained directly or through a lossless deterministic encoding. This protocol targets **declared semantic reconstruction**.

## Commands

```bash
python3 tools/history_minset.py plan --dataset examples/history/world-history-scaffold.json
python3 tools/history_minset.py pack --dataset examples/history/world-history-scaffold.json > /tmp/history-basis.json
python3 tools/history_minset.py reconstruct --basis /tmp/history-basis.json
```

Running any command twice with unchanged inputs must produce identical bytes.
