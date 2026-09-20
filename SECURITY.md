# Security policy

forecheck is a security control. Bugs in it have security consequences for its users,
so we treat correctness bugs in labelling, calibration, policy evaluation and
serialization as security issues, not just defects.

## Reporting

Please **do not** open a public issue for a vulnerability. Use GitHub's private
vulnerability reporting on this repository ("Report a vulnerability" under the Security
tab). If that is unavailable, open an issue titled "security contact request" with no
details and a maintainer will reply with a private channel.

We aim to acknowledge within 5 working days.

## In scope

- Any input that causes the policy engine to return a less restrictive decision than
  the bundle specifies (fail-open).
- Any input that lets untrusted observation content forge a section boundary or
  otherwise escape its fenced region in the serialized prompt.
- Calibration or classifier code paths that return a `probability` when
  `CalibrationInfo.method == "none"`, or that mark an abstained dimension as scored.
- Request bodies or argument values appearing in logs, metrics labels, or error
  responses.
- Bundle loading that accepts unknown dimension or fact names.
- Leakage of `eval_only` or canary-bearing records into training or calibration splits.
- Dependency vulnerabilities with a reachable path from the service.

## Out of scope

- Adversarial inputs that move a *score* without violating any of the above. That is a
  model-quality question and is measured, not patched; please file it as a normal issue
  with the example so it can join the adversarial evaluation slice.
- Deployments that bypass forecheck entirely (see `docs/threat-model.md` FC-03).
- Issues in third-party models forecheck is configured to load.

## Supply chain

Dependencies are bounded in `pyproject.toml` and audited in CI with `pip-audit`. No
third-party source is vendored. Release artefacts are built from tagged commits by CI.

## Disclosure

We follow coordinated disclosure with a default 90-day window, shortened by agreement
when a fix ships sooner.
