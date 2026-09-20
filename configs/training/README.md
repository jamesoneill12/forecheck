# Training configs

Each YAML file here loads into a `forecheck.training.config.TrainConfig`. Override any
field from the command line with dotted `key.sub=value` pairs, applied in order after
the file is parsed:

```
forecheck train --config configs/training/1b.yaml data.dir=/opt/ml/fsx/forecheck/data/v1 output.dir=/opt/ml/fsx/forecheck/runs/1b-v1
```

Values are parsed with YAML, so `true`/`false`, integers and floats come through as
their native type; anything else stays a string. This is the mechanism the EKS recipes
in `configs/eks/` use to point a shared config file at a run-specific data and output
directory — see `configs/eks/README.md`.

## Files

| File | Size class | Purpose |
|---|---|---|
| `smoke.yaml` | tiny random model | CPU, ~20 steps, no GPU required — see `forecheck.training.smoke` |
| `1b.yaml` | ~1B params | Fast ablation / first pass |
| `4b.yaml` | ~4B params | Mid-size candidate |
| `8b.yaml` | ~8-9B params | Largest candidate evaluated so far |

`smoke.yaml` pins a real (tiny, randomly initialized) model id so the config-loading and
encoding path is exercised the same way a real recipe is. `1b.yaml`/`4b.yaml`/`8b.yaml`
each carry a `REPLACE_WITH_APPROVED_*_BASE_MODEL` placeholder instead of a hard-coded
choice: pick one from the table below, confirm the licence covers your use, and set
`model.base_id` accordingly.

## Candidate base models and licences

No single model is "the" choice; pick per run based on licence fit and availability.

| Size class | Candidate | Licence |
|---|---|---|
| ~1B | Llama-3.2-1B | Llama 3.2 Community License |
| ~1B | Qwen2.5-1.5B / Qwen3-1.7B | Apache-2.0 |
| ~1B | SmolLM2-1.7B | Apache-2.0 |
| ~4B | Llama-3.2-3B | Llama 3.2 Community License |
| ~4B | Qwen2.5-3B / Qwen3-4B | Apache-2.0 (Qwen2.5-3B is research-only, check terms) |
| ~4B | Gemma-3-4B | Gemma Terms of Use |
| ~8-9B | Qwen2.5-7B / Qwen3.5-9B | Apache-2.0 |
| ~8-9B | Phi-4-mini | MIT |
| ~8-9B | Gemma-3-12B (nearest available) | Gemma Terms of Use |

Llama and Gemma licences carry redistribution and acceptable-use terms beyond
Apache-2.0/MIT; confirm those terms are compatible with how the resulting adapter and
any published outputs will be used before training.

## Per-size defaults

LoRA rank/alpha, learning rate, micro-batch and gradient accumulation scale with model
size, tuned for a single 8×B200 node:

| Size | LoRA r/alpha | LR | micro batch | grad accum | effective batch (×8 GPUs, DDP) | `max_prompt_tokens` |
|---|---|---|---|---|---|---|
| 1B | 16/32 | 2e-4 | 16 | 1 | 128 | 4096 |
| 4B | 32/64 | 1e-4 | 8 | 2 | 128 | 4096 |
| 8-9B | 64/128 | 5e-5 | 4 | 4 | 128 | 8192 |

All three keep the same effective batch (128) so a size comparison isn't confounded by
batch size. Micro-batch drops as the model grows to keep activation memory (dominated
by the shared-prefill sequence and its 11-question block-diagonal attention) within an
80 GB-class GPU's budget; grad accumulation makes up the difference. The 8-9B row's
larger `max_prompt_tokens` assumes longer contexts are more likely to matter at that
size — lower it to 4096 if a run OOMs.

## Running the CPU smoke train

Once `uv sync --extra train` has installed `torch`/`transformers`/`peft`:

```
uv run pytest tests/training/test_smoke.py -m slow -q
```

This runs `forecheck.training.smoke.run_smoke_train`, which trains
`hf-internal-testing/tiny-random-LlamaForCausalLM` for a few steps on in-memory
synthetic examples, asserts the training loss decreased, and round-trips a checkpoint
through resume. Pass a local snapshot directory as the model id to run fully offline.
