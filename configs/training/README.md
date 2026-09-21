# Training configs

Each YAML file here loads into a `forecheck.training.config.TrainConfig`. Override any
field from the command line with dotted `key.sub=value` pairs, applied in order after
the file is parsed:

```
forecheck train --config configs/training/2b.yaml data.dir=/opt/ml/fsx/forecheck/data/v1 output.dir=/opt/ml/fsx/forecheck/runs/2b-v1
```

Values are parsed with YAML, so `true`/`false`, integers and floats come through as
their native type; anything else stays a string. This is the mechanism the EKS recipes
in `configs/eks/` use to point a shared config file at a run-specific data and output
directory — see `configs/eks/README.md`.

## Selected family: Qwen3.5 (Apache-2.0)

`2b.yaml`/`4b.yaml`/`8b.yaml` default to the same base-model family Bespoke Nimble was
built on:

| Size | `model.base_id` | Licence |
|---|---|---|
| ~2B | `Qwen/Qwen3.5-2B` | Apache-2.0 |
| ~4B | `Qwen/Qwen3.5-4B` | Apache-2.0 |
| ~9B | `Qwen/Qwen3.5-9B` | Apache-2.0 (Nimble's exact base) |

Facts from the HF cards that matter for this repo:

- `config.json`: `model_type: qwen3_5`, `architectures: ["Qwen3_5ForConditionalGeneration"]`,
  a `text_config` (`model_type: qwen3_5_text`) plus a `vision_config`, and
  `transformers_version: 4.57.0.dev0` — hence `transformers>=4.57` in `pyproject.toml`.
- `layer_types` alternates 24× `linear_attention` / 8× `full_attention` (a Gated
  DeltaNet hybrid). Linear-attention layers have no `q_proj`/`k_proj`/`v_proj`/`o_proj`
  to LoRA-adapt; the MLP projections (`gate_proj`/`up_proj`/`down_proj`) exist on every
  layer regardless of attention type, so `lora.target_modules` includes them (see
  below) to get LoRA coverage on the linear-attention layers too.
- `Qwen3_5ForConditionalGeneration` is registered under transformers'
  `AutoModelForImageTextToText` mapping (it always carries a vision tower, even for
  text-only use), not `AutoModelForCausalLM`. `model.load_class: auto` (the default)
  tries `AutoModelForCausalLM` first and falls back automatically — see
  `forecheck.inference.hf_loading`. There is no public, architecture-independent
  transformers API to load only the text tower, so the fallback loads the full model:
  budget for the vision tower's weights and activation memory in addition to the ~9B
  text-tower parameters when sizing the 9B recipe's node.
- The chat models run in **thinking mode by default**. `train.use_chat_template: true`
  (the default) renders context+question through the model's own chat template via
  `forecheck.inference.chat_template`, the same helper `forecheck.inference.hf` scores
  with, and passes `enable_thinking=False` so training and serving both score the
  first non-thinking assistant token — matching how these checkpoints were
  post-trained to be prompted, rather than the plain-text template
  `forecheck.inference.prompt` renders for models with no chat template of their own
  (e.g. the CPU smoke model).

`8b.yaml` additionally matches Nimble's published recipe: LoRA rank 16 / alpha 32,
LR 5e-5, 1 epoch, BF16, effective batch 8. This repo's training loop
(`forecheck.training.loop.run_training`) is single-process/single-GPU, so the
effective batch of 8 is `optim.micro_batch_size: 8` × `optim.grad_accum: 1` on one
GPU, not 8-way data-parallel across the node's 8 GPUs (the EKS recipe still reserves a
full `p6-b200.48xlarge` node; multi-GPU DDP for this loop is not implemented yet).

## Files

| File | Size class | Purpose |
|---|---|---|
| `smoke.yaml` | tiny random model | CPU, ~20 steps, no GPU required — see `forecheck.training.smoke` |
| `2b.yaml` | ~2B params | Fast ablation / first pass |
| `4b.yaml` | ~4B params | Mid-size candidate |
| `8b.yaml` | ~9B params | Nimble-parity candidate |

`smoke.yaml` pins a real (tiny, randomly initialized) model id with no chat template,
so it explicitly sets `train.use_chat_template: false`; the config-loading and encoding
path is otherwise exercised the same way a real recipe is. `2b.yaml`/`4b.yaml`/`8b.yaml`
default to the Qwen3.5 ids above; swap `model.base_id` (and confirm the licence covers
your use) to try one of the alternatives below instead.

## Alternative base models and licences

No single model is required; Qwen3.5 is the selected family above, but these remain
valid per-size alternatives based on licence fit and availability.

| Size class | Candidate | Licence |
|---|---|---|
| ~2B | Llama-3.2-1B | Llama 3.2 Community License |
| ~2B | Qwen2.5-1.5B / Qwen3-1.7B | Apache-2.0 |
| ~2B | SmolLM2-1.7B | Apache-2.0 |
| ~4B | Llama-3.2-3B | Llama 3.2 Community License |
| ~4B | Qwen2.5-3B / Qwen3-4B | Apache-2.0 (Qwen2.5-3B is research-only, check terms) |
| ~4B | Gemma-3-4B | Gemma Terms of Use |
| ~8-9B | Qwen2.5-7B | Apache-2.0 |
| ~8-9B | Phi-4-mini | MIT |
| ~8-9B | Gemma-3-12B (nearest available) | Gemma Terms of Use |

Llama and Gemma licences carry redistribution and acceptable-use terms beyond
Apache-2.0/MIT; confirm those terms are compatible with how the resulting adapter and
any published outputs will be used before training.

## Per-size defaults

`2b.yaml`/`4b.yaml` keep the pre-Qwen3.5 generic scaling below (LoRA rank/alpha,
learning rate, micro-batch and gradient accumulation scale with model size, tuned for
a single GPU's worth of activation memory); `8b.yaml` instead follows Nimble-parity
defaults (previous section) since Qwen3.5-9B is the selected base for that size class:

| Size | LoRA r/alpha | LR | micro batch | grad accum | effective batch | `max_prompt_tokens` |
|---|---|---|---|---|---|---|
| 2B | 16/32 | 2e-4 | 16 | 1 | 16 | 4096 |
| 4B | 32/64 | 1e-4 | 8 | 2 | 16 | 4096 |
| 9B (Nimble-parity) | 16/32 | 5e-5 | 8 | 1 | 8 | 8192 |

Micro-batch drops as the model grows to keep activation memory (dominated by the
shared-prefill sequence and its 11-question block-diagonal attention) within an
80 GB-class GPU's budget; grad accumulation makes up the difference. `8b.yaml`'s larger
`max_prompt_tokens` assumes longer contexts are more likely to matter at that size —
lower it to 4096 if a run OOMs.

## Running the CPU smoke train

Once `uv sync --extra train` has installed `torch`/`transformers`/`peft`:

```
uv run pytest tests/training/test_smoke.py -m slow -q
```

This runs `forecheck.training.smoke.run_smoke_train`, which trains
`hf-internal-testing/tiny-random-LlamaForCausalLM` for a few steps on in-memory
synthetic examples, asserts the training loss decreased, and round-trips a checkpoint
through resume. Pass a local snapshot directory as the model id to run fully offline.
