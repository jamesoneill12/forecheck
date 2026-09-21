#!/usr/bin/env python3
"""Throughput microbenchmark for ``HFBackend.score``: reports rows/s and per-row CPU
ms over ``n`` fixture rows for a given backend config. Runs entirely offline against
a random-weight model by default (``--tiny``, using the real tokenizer named by
``--model-id`` so chat-template and candidate-token behaviour matches production);
pass ``--no-tiny`` to load real weights instead.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import typer

app = typer.Typer(add_completion=False)


def _load_contexts(fixtures: Path, n: int) -> list[Any]:
    from forecheck.contracts.records import Example

    contexts = []
    with fixtures.open() as f:
        for i, line in enumerate(f):
            if i >= n:
                break
            contexts.append(Example.model_validate_json(line).context)
    return contexts


def _build_tiny_backend(
    model_id: str, *, shared_prefill: bool, use_chat_template: bool, batch_size: int
) -> Any:
    import torch
    from transformers import AutoTokenizer, GraniteConfig, GraniteForCausalLM

    from forecheck.inference.hf import HFBackend, HFBackendConfig

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    config = GraniteConfig(
        vocab_size=len(tokenizer),
        hidden_size=32,
        intermediate_size=64,
        num_hidden_layers=2,
        num_attention_heads=4,
        num_key_value_heads=2,
        max_position_embeddings=8192,
        pad_token_id=tokenizer.pad_token_id,
    )
    torch.manual_seed(0)
    model = GraniteForCausalLM(config)
    model.eval()

    backend = HFBackend(
        HFBackendConfig(
            model_id=model_id,
            shared_prefill=shared_prefill,
            use_chat_template=use_chat_template,
            batch_size=batch_size,
        )
    )

    def fake_load(self: HFBackend, torch_mod: object) -> tuple[Any, Any, str]:
        return model, tokenizer, "cpu"

    backend._load_model_and_tokenizer = fake_load.__get__(backend)  # type: ignore[method-assign]
    return backend


@app.command()
def main(
    model_id: str = typer.Option("ibm-granite/granite-3.3-2b-instruct", help="Tokenizer/model id."),
    fixtures: Path = typer.Option(Path("data/fixtures/dev.jsonl"), help="JSONL fixture file."),
    n: int = typer.Option(200, help="Number of rows to score."),
    batch_size: int = typer.Option(32, help="HFBackendConfig.batch_size."),
    shared_prefill: bool = typer.Option(True, help="HFBackendConfig.shared_prefill."),
    use_chat_template: bool = typer.Option(True, help="HFBackendConfig.use_chat_template."),
    tiny: bool = typer.Option(True, help="Use a random-weight tiny model instead of real weights."),
    adapter_id: str | None = typer.Option(None, help="LoRA adapter id (ignored with --tiny)."),
    device: str | None = typer.Option(None, help="Device override (ignored with --tiny)."),
) -> None:
    if tiny:
        backend = _build_tiny_backend(
            model_id,
            shared_prefill=shared_prefill,
            use_chat_template=use_chat_template,
            batch_size=batch_size,
        )
    else:
        from forecheck.inference.hf import HFBackend, HFBackendConfig

        backend = HFBackend(
            HFBackendConfig(
                model_id=model_id,
                adapter_id=adapter_id,
                device=device,
                shared_prefill=shared_prefill,
                use_chat_template=use_chat_template,
                batch_size=batch_size,
            )
        )
    backend.warmup()

    contexts = _load_contexts(fixtures, n)
    rows = len(contexts)

    wall_start = time.perf_counter()
    cpu_start = time.process_time()
    for context in contexts:
        backend.score(context)
    cpu_elapsed = time.process_time() - cpu_start
    wall_elapsed = time.perf_counter() - wall_start

    typer.echo(
        f"rows={rows} batch_size={batch_size} shared_prefill={shared_prefill} "
        f"use_chat_template={use_chat_template} tiny={tiny}"
    )
    typer.echo(f"wall: {wall_elapsed:.2f}s  rows/s={rows / wall_elapsed:.2f}")
    typer.echo(f"cpu:  {cpu_elapsed:.2f}s  cpu_ms/row={1000 * cpu_elapsed / rows:.2f}")


if __name__ == "__main__":
    sys.exit(app())
