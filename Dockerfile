FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir uv

ARG FORECHECK_EXTRA=""

WORKDIR /build
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY policies ./policies
COPY README.md LICENSE NOTICE ./

RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    if [ -n "$FORECHECK_EXTRA" ]; then uv pip install ".[$FORECHECK_EXTRA]"; else uv pip install .; fi

FROM python:3.12-slim AS runtime

RUN groupadd --system forecheck && useradd --system --gid forecheck --create-home forecheck

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/policies /app/policies

ENV PATH="/opt/venv/bin:$PATH" \
    FORECHECK_BACKEND=mock \
    FORECHECK_HOST=0.0.0.0 \
    FORECHECK_PORT=8000

WORKDIR /app
USER forecheck

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live').read()" || exit 1

ENTRYPOINT ["forecheck"]
CMD ["serve", "--backend", "mock", "--host", "0.0.0.0", "--port", "8000"]
