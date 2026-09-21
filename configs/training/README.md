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

## Selected base models (Apache-2.0)

`2b.yaml`/`3b.yaml`/`8b.yaml`/`olmo3-7b.yaml` default to these bases, all verified
Apache-2.0 on their HF cards:

| Size | `model.base_id` | Licence |
|---|---|---|
| ~2B | `ibm-granite/granite-3.3-2b-instruct` | Apache-2.0 |
| ~3B | `ibm-granite/granite-4.0-micro` | Apache-2.0 |
| ~8B | `ibm-granite/granite-3.3-8b-instruct` | Apache-2.0 (Nimble's exact recipe, different base) |
| ~7B | `allenai/Olmo-3-7B-Instruct` | Apache-2.0 |

Facts from each `config.json` that matter for this repo:

- **Granite 3.3 (2B/8B)**: `architectures: ["GraniteForCausalLM"]`, a plain dense
  transformer with GQA (32 query heads / 8 KV heads), 40 layers, `vocab_size: 49159`,
  `tie_word_embeddings: true`, `transformers_version: 4.49.0`. Registered under
  `AutoModelForCausalLM` directly — the `AutoModelForImageTextToText` fallback in
  `forecheck.inference.hf_loading` never triggers for this family, it exists for other
  checkpoints that only register under that mapping.
- **Granite 4.0 Micro (3B)**: verified via `config.json` on 2026-09-21 —
  `architectures: ["GraniteMoeHybridForCausalLM"]`, `model_type: granitemoehybrid`,
  `hidden_size: 2560`, `num_hidden_layers: 40`, `num_attention_heads: 40`,
  `num_key_value_heads: 8`, `vocab_size: 100352`, `tie_word_embeddings: true`,
  `transformers_version: 4.56.0`. This is the dense, non-hybrid member of the Granite
  4.0 family: `layer_types` lists 40× `attention` (no `mamba` entries) and
  `num_local_experts: 0` / `num_experts_per_tok: 0` (no MoE routing, the MLP is the
  `shared_intermediate_size` dense path) — it shares the hybrid family's model class
  and config schema, but every knob that would make it hybrid or sparse is switched
  off. Standard `q_proj`/`k_proj`/`v_proj`/`o_proj` attention projections, so
  `lora.target_modules` needs no special-casing.
- **OLMo 3 7B Instruct**: verified via `config.json` on 2026-09-21 —
  `architectures: ["Olmo3ForCausalLM"]`, `model_type: olmo3`, `hidden_size: 4096`,
  `num_hidden_layers: 32`, `num_attention_heads: 32`, `num_key_value_heads: 32` (MHA,
  no GQA), `vocab_size: 100278`, `tie_word_embeddings: false`,
  `transformers_version: 4.57.1`. Mixes sliding-window and full attention layers
  (`layer_types`), which is transparent to this repo — LoRA still targets the standard
  attention/MLP projection names.
- None of these four models defaults to a "thinking" mode the way some instruction
  models do, but their chat templates differ in whether they expose a thinking toggle
  at all, and under what keyword. `train.use_chat_template: true` (the default)
  renders context+question through the model's own chat template via
  `forecheck.inference.chat_template`, the same helper `forecheck.inference.hf` scores
  with. That module's `thinking_kwargs()` inspects the tokenizer's `chat_template`
  string and passes `enable_thinking=False` (SmolLM3-style templates), `thinking=False`
  (Granite 3.3's convention), or nothing at all (OLMo 3 and Granite 4.0 Micro have no
  thinking toggle) — so training and serving both score the same rendered token
  regardless of which of these four bases is configured, rather than the plain-text
  template `forecheck.inference.prompt` renders for models with no chat template of
  their own (e.g. the CPU smoke model).
- Granite's chat template injects a default system message (containing today's date)
  when no system message is supplied. `forecheck.inference.chat_template` always
  passes an explicit system message, so the rendered prompt does not change from day
  to day — see that module's docstring.

`8b.yaml` and `olmo3-7b.yaml` both match Nimble's published recipe: LoRA rank 16 /
alpha 32, LR 5e-5, 1 epoch, BF16, effective batch 8. The comparison across these two
files is now "same recipe, different base" — Granite 3.3 8B vs. OLMo 3 7B under
identical hyperparameters. This repo's training loop
(`forecheck.training.loop.run_training`) is single-process/single-GPU, so the
effective batch of 8 is `optim.micro_batch_size: 8` × `optim.grad_accum: 1` on one
GPU, not 8-way data-parallel across the node's 8 GPUs (the EKS recipe still reserves a
full `p6-b200.48xlarge` node; multi-GPU DDP for this loop is not implemented yet).

## Files

| File | Size class | Purpose |
|---|---|---|
| `smoke.yaml` | tiny random model | CPU, ~20 steps, no GPU required — see `forecheck.training.smoke` |
| `2b.yaml` | ~2B params | Fast ablation / first pass |
| `3b.yaml` | ~3B params | Mid-size candidate |
| `8b.yaml` | ~8B params | Nimble-parity candidate |
| `olmo3-7b.yaml` | ~7B params | Second 8B-class arm, same recipe as `8b.yaml` |

`smoke.yaml` pins a real (tiny, randomly initialized) model id with no chat template,
so it explicitly sets `train.use_chat_template: false`; the config-loading and encoding
path is otherwise exercised the same way a real recipe is. `2b.yaml`/`3b.yaml`/`8b.yaml`/
`olmo3-7b.yaml` default to the ids above; swap `model.base_id` (and confirm the licence
covers your use) to try one of the alternatives below instead.

## Alternative base models and licences

No single model is required; the four bases above are the selected set, but these
remain valid per-size alternatives based on licence fit and availability.

| Size class | Candidate | Licence |
|---|---|---|
| ~2B | Llama-3.2-1B | Llama 3.2 Community License |
| ~2B | SmolLM2-1.7B | Apache-2.0 |
| ~4B | Llama-3.2-3B | Llama 3.2 Community License |
| ~4B | Gemma-3-4B | Gemma Terms of Use |
| ~8-9B | Phi-4-mini | MIT |
| ~8-9B | Gemma-3-12B (nearest available) | Gemma Terms of Use |

Llama and Gemma licences carry redistribution and acceptable-use terms beyond
Apache-2.0/MIT; confirm those terms are compatible with how the resulting adapter and
any published outputs will be used before training.

## Per-size defaults

`2b.yaml`/`3b.yaml` keep the pre-existing generic scaling below (LoRA rank/alpha,
learning rate, micro-batch and gradient accumulation scale with model size, tuned for
a single GPU's worth of activation memory); `8b.yaml`/`olmo3-7b.yaml` instead follow
Nimble-parity defaults (previous section):

| Size | LoRA r/alpha | LR | micro batch | grad accum | effective batch | `max_prompt_tokens` |
|---|---|---|---|---|---|---|
| 2B | 16/32 | 2e-4 | 16 | 1 | 16 | 4096 |
| 3B | 32/64 | 1e-4 | 8 | 2 | 16 | 4096 |
| 8B / 7B (Nimble-parity) | 16/32 | 5e-5 | 8 | 1 | 8 | 8192 |

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
