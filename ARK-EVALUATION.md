# QSOL-ARK Evaluation Contract

QSOL-ARK owns recovery evaluation authority. QSOL-THOTH supplies a deterministic measurement contract and receipt builder for route, style, fact, history, transport, and clean-room observations.

The evaluator does not inspect model prose and announce truth. An assessor supplies explicit structured observations; THOTH validates, counts, compares, and hashes them.

```text
MEASURED_OBSERVATION != AUTOMATIC_TRUTH
```

## Separate dimensions

`tools/ark_evaluation.py` emits exact integer fractions for:

1. route sufficiency — selected required roles / declared required roles;
2. route minimality — selected justified roles / all selected roles;
3. style fidelity — passed / assessed style obligations;
4. factual accuracy — correct / assessed claims;
5. historical reconstruction coverage — covered / assessed retention obligations.

There is deliberately no aggregate score.

```text
STYLE_FIDELITY != FACTUAL_ACCURACY != PHYSICAL_TRUTH
ROUTE_SUFFICIENCY != ROUTE_MINIMALITY
HISTORICAL_COVERAGE != HISTORICAL_TRUTH
AGGREGATE_SCORE = FORBIDDEN
```

## Commands

```bash
python3 tools/ark_evaluation.py validate-policy

python3 tools/ark_evaluation.py evaluate \
  --observation examples/evaluation/synthetic-clean-room-observation.json
```

The output is `QSOL-ARK/THOTH-EVALUATION-RECEIPT/1` with an acyclic `evaluation_sha256`.

## Clean-room contract

An accepted observation must declare:

- portable inputs only;
- no private source-repository access;
- no private context connector;
- no hidden provider-memory dependency.

The conformance test resolves a normal THOTH decision using only a synthetic portable object index and the public fixture object. No private repository metadata enters the consumer-side receipt.

## Transport equivalence

Each observation supplies independently recorded object identities, byte sizes, and exact byte hashes for:

```text
local-directory
archive
static-http
capability-relay
```

All four object observations must match byte-for-byte. The transport itself remains outside object identity and authority.

```text
TRANSPORT_EQUIVALENCE != AUTHORITY
```

The synthetic fixture's declared object id is also checked against the actual committed public object bytes.

## Negative space

Evaluation fails closed when any observation reports:

- style leakage into claim authority;
- unsupported historical interpolation;
- accidental private-source dependency.

Schemas:

```text
schema/ark-evaluation-policy.schema.json
schema/ark-evaluation-observation.schema.json
schema/ark-evaluation-receipt.schema.json
```
