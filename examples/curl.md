# curl examples

Start the service against the mock backend (no downloads, no GPU):

```
forecheck serve --backend mock --port 8000
```

## POST /v1/classify

```
curl -s http://localhost:8000/v1/classify \
  -H 'content-type: application/json' \
  -d @examples/requests/injected_exfiltration.json | jq
```

Any file under `examples/requests/` works the same way:
`benign_same_tenant_email.json`, `authorized_refund_small.json`,
`unauthorized_prod_delete.json`, `lookalike_destination.json`,
`insufficient_context.json`.

To also see the pre-calibration raw score (ordinal only, never a probability), add
`"options": {"include_uncalibrated": true}` to the body, e.g.:

```
jq '. + {options: {include_uncalibrated: true}}' examples/requests/lookalike_destination.json \
  | curl -s http://localhost:8000/v1/classify -H 'content-type: application/json' -d @- | jq
```

## POST /v1/classify/batch

```
jq -n --slurpfile a examples/requests/injected_exfiltration.json \
      --slurpfile b examples/requests/benign_same_tenant_email.json \
      '{items: [$a[0], $b[0]]}' \
  | curl -s http://localhost:8000/v1/classify/batch -H 'content-type: application/json' -d @- | jq
```

## POST /v1/policies/evaluate

Classify then evaluate in one call, against the default (`conservative`) bundle:

```
jq '{context: .context}' examples/requests/unauthorized_prod_delete.json \
  | curl -s http://localhost:8000/v1/policies/evaluate -H 'content-type: application/json' -d @- | jq
```

Against a specific bundle, via the allowlisted header:

```
jq '{context: .context}' examples/requests/authorized_refund_small.json \
  | curl -s http://localhost:8000/v1/policies/evaluate \
      -H 'content-type: application/json' \
      -H 'X-Forecheck-Policy-Bundle: permissive' \
      -d @- | jq
```

## GET /v1/policies

```
curl -s http://localhost:8000/v1/policies | jq
```

## Health, version and metrics

```
curl -s http://localhost:8000/health/live | jq
curl -s http://localhost:8000/health/ready | jq
curl -s http://localhost:8000/version | jq
curl -s http://localhost:8000/metrics | head -30
```

## Static token auth

When the service is started with `FORECHECK_AUTH_MODE=static_token` and
`FORECHECK_STATIC_TOKEN=<token>`:

```
curl -s http://localhost:8000/v1/classify \
  -H 'content-type: application/json' \
  -H 'authorization: Bearer <token>' \
  -d @examples/requests/insufficient_context.json | jq
```
