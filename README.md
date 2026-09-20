# forecheck

**A calibrated pre-execution risk model for AI-agent actions.**

forecheck answers one question, in single-digit milliseconds to a few hundred, before a
tool call runs:

> Given who is asking, what they asked for, what the agent has already done, what it has
> read and from whom, what this call touches, where the result goes, and what the
> organization's policy says — what is the probability that this specific action is
> injection-driven, out of scope, exfiltrating, escalating, destructive, financially
> committing, or otherwise risky?

It returns typed numbers, not prose:

```json
{
  "scores": [
    {"dimension": "prompt_injection_influence", "probability": 0.93, "calibrated": true},
    {"dimension": "sensitive_data_exposure",    "probability": 0.88, "calibrated": true},
    {"dimension": "untrusted_destination",      "probability": 0.97, "calibrated": true},
    {"dimension": "destructive_or_irreversible_action", "probability": 0.04, "calibrated": true}
  ]
}
```

A separate, deterministic, inspectable policy engine turns those numbers into
`ALLOW` / `REVIEW` / `DENY`. **The model never decides. The policy engine never guesses.**

## Why the two layers are separate

An action is not safe or unsafe on its own. `delete_bucket` is routine in a developer's
scratch account and catastrophic in production. `send_email` is the job of a support
agent and an exfiltration channel for a compromised one. A `$40,000` wire is fraud or
payroll depending entirely on who authorized it.

So forecheck's model is trained to identify *facts* — this action is irreversible, this
destination is external, this instruction came from a web page rather than from the
user — and never to decide whether facts add up to permission. That judgement is
tenant-specific, auditable and subject to change without retraining, which makes it a
policy problem, not a modelling problem.

## Status

Pre-alpha. The offline path is implemented and tested end to end: synthetic data
generation, deterministic labelling, leakage-safe splitting, a mock classifier, the
calibration layer, the evaluation suite, the policy engine and the HTTP service all run
on a laptop with no GPU, no API key and no network.

**No trained weights are published yet, and no real-world safety claims are made.** All
reported numbers are on synthetic data and are labelled as such. See
[`docs/evaluation-plan.md`](docs/evaluation-plan.md) for the three evaluation classes we
hold separate, and [`docs/research-landscape.md`](docs/research-landscape.md) for the
prior-art scan and the novelty verdict that justifies building this at all.

## Five-minute quickstart

```bash
git clone https://github.com/jamesoneill12/forecheck
cd forecheck
uv sync --extra dev

# Everything below runs offline against the mock classifier.
uv run forecheck serve --backend mock &
curl -s localhost:8000/v1/classify -H 'content-type: application/json' \
  -d @examples/requests/injected_exfiltration.json | jq
```

See [`examples/`](examples/) for the middleware and MCP interceptor examples, and
[`docs/product-spec.md`](docs/product-spec.md) for the full request contract.

## Licence

Apache-2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
