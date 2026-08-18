# Multi-turn ESS Sessions

`tools/ess_session.py` extends one-turn ESS selection into a deterministic multi-turn receiver-style session without adding model inference, time, randomness, or network state.

## Events

`QSOL-THOTH/ESS-SESSION/1` supports three explicit event kinds:

- `route` — contains a normal route request with no embedded style override;
- `transition` — requests one exact declared target style;
- `reset` — clears the persisted style so the next route reinitializes from its route default.

The first route seeds the session from the route's declared default. Later routes preserve the current style until an explicit transition or reset.

When style persists across a new intent, the engine reruns the canonical router with that persisted style as an explicit input. The resulting effective decision therefore includes the correct style-support CONCAPs; persistence is not a cosmetic label pasted onto an incompatible route.

```text
ROUTE_DEFAULT != FORCED_SESSION_TRANSITION
EXPLICIT_STYLE_TRANSITION != MODEL_INFERENCE
```

## Profiles

The policy defines two frozen profiles:

| Profile | Minimum routed turns before another change | Matching confirmations |
|---|---:|---:|
| `immediate` | 0 | 1 |
| `demonstrated_hysteresis` | 1 | 2 |

For the demonstration profile, transition confirmations must be consecutive. A routed turn clears a pending confirmation. Dwell counts routed events, not elapsed time.

```text
HYSTERESIS != AMBIGUITY
DWELL_COUNT != WALL_CLOCK_TIME
```

## Replay

```bash
python3 tools/ess_session.py validate-policy

python3 tools/ess_session.py replay \
  --session examples/ess/demonstrated-hysteresis.session.json
```

Every event emits `QSOL-THOTH/ESS-TRANSITION-RECEIPT/1` containing:

- the canonical event SHA-256;
- the prior receipt SHA-256;
- before/after style;
- base and effective route-decision ids when applicable;
- effective CONCAP roles;
- dwell and pending-confirmation state;
- an acyclic receipt SHA-256.

The complete replay has its own acyclic `replay_sha256`. The receipt chain contains declared public state only; it is not hidden model state.

```text
STYLE_SWITCH != EPISTEMIC_SWITCH
STYLE_PERSISTENCE != EPISTEMIC_PERSISTENCE
REPLAY_RECEIPT != HIDDEN_STATE
```

Schemas:

```text
schema/ess-session-policy.schema.json
schema/ess-session.schema.json
schema/ess-session-replay.schema.json
```
