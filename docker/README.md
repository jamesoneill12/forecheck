# Running forecheck in Docker

## CPU / mock (default)

```
docker compose up forecheck
```

Builds the image with no ML extras, runs `forecheck serve --backend mock`, and exposes
`8000`. `/health/live` is the container `HEALTHCHECK`. Nothing here downloads a model or
touches a GPU.

## GPU / real backend

```
FORECHECK_MODEL_ID=your-org/your-model docker compose --profile gpu up forecheck-gpu
```

The `forecheck-gpu` service is opt-in via the `gpu` Compose profile. It builds the image
with `FORECHECK_EXTRA=torch` (installing `forecheck[torch]`), reserves one NVIDIA GPU via
the `nvidia` device driver, and sets `FORECHECK_BACKEND=hf` / `FORECHECK_DEVICE=cuda`.
Requires the NVIDIA Container Toolkit on the host and a `FORECHECK_MODEL_ID`.

## Building manually

```
docker build -t forecheck:mock .
docker build -t forecheck:gpu --build-arg FORECHECK_EXTRA=torch .
```

## Configuration

Every `FORECHECK_*` variable in `.env.example` can be passed as a container
environment variable; none are required for the mock backend. Policy bundles ship
inside the image at `/app/policies`; mount a directory over it (or point
`FORECHECK_POLICY_BUNDLE` at an absolute path inside a mounted volume) to use a custom
bundle instead of `conservative` / `balanced` / `permissive`.
