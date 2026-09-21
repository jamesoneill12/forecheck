"""The encoder-classifier training loop: forward, masked BCE loss, checkpoint, early stop.

Mirrors :mod:`forecheck.training.loop`'s structure (seeded resumable sampling, the
``LocalJsonTracker``/``MlflowTracker`` protocol, run-dir capture, dev macro-AUPRC early
stopping) but trains a pooled-embedding encoder backbone plus an 11-logit linear head
instead of LoRA-tuning a decoder's candidate-token logits. Every ``torch``/
``transformers``/``safetensors`` symbol is imported lazily inside functions so this
module -- and therefore ``forecheck.training`` -- imports cleanly without the ``train``
extra installed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from forecheck.contracts import LabelValue, RiskDimension
from forecheck.evaluation.metrics import (
    DimensionMetrics,
    compute_dimension_metrics,
    extract_dimension_arrays,
    macro_average,
)
from forecheck.inference.encoder import (
    BACKBONE_DIR,
    HEAD_CONFIG_FILE,
    HEAD_WEIGHTS_FILE,
    Pooling,
    pool_hidden_states,
)
from forecheck.inference.prompt import serialization_contract_hash
from forecheck.inference.serialization import serialize_context
from forecheck.training.capture import write_checkpoint_manifest, write_run_capture
from forecheck.training.config import EncoderTrainConfig
from forecheck.training.dataset import DIMENSION_ORDER
from forecheck.training.loop import SeededEpochSampler
from forecheck.training.loss import masked_bce_with_logits, resolve_pos_weight
from forecheck.training.tracking import ExperimentTracker, LocalJsonTracker

if TYPE_CHECKING:
    from forecheck.contracts import Example

__all__ = ["EncoderTrainResult", "run_encoder_training"]

_MASKED_LABELS: frozenset[LabelValue] = frozenset(
    {LabelValue.NOT_APPLICABLE, LabelValue.UNDETERMINED}
)
_TRAINER_STATE_FILE = "trainer_state.json"


def _require_torch() -> Any:
    try:
        import torch  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "forecheck.training.encoder_loop requires torch; install forecheck[train]"
        ) from exc
    return torch


@dataclass(frozen=True, slots=True)
class EncoderTrainResult:
    run_dir: Path
    steps_completed: int
    best_step: int | None
    best_dev_macro_auprc: float | None
    stopped_early: bool


def _auto_device(torch: Any) -> str:
    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    return "cpu"


_DTYPE_ATTRS = {"bf16": "bfloat16", "fp16": "float16", "fp32": "float32"}


def _resolve_dtype(torch: Any, dtype_name: str, device: str) -> Any:
    if dtype_name == "auto":
        return torch.bfloat16 if device != "cpu" else torch.float32
    return getattr(torch, _DTYPE_ATTRS[dtype_name])


def build_backbone_and_tokenizer(config: EncoderTrainConfig) -> tuple[Any, Any, str]:
    torch = _require_torch()
    from transformers import AutoModel, AutoTokenizer

    device = _auto_device(torch)
    dtype = _resolve_dtype(torch, config.model.dtype, device)
    backbone = AutoModel.from_pretrained(config.model.base_id, torch_dtype=dtype)
    tokenizer = AutoTokenizer.from_pretrained(config.model.base_id)
    backbone.to(device)
    return backbone, tokenizer, device


def build_head(torch: Any, hidden_size: int, n_dimensions: int) -> Any:
    return torch.nn.Linear(hidden_size, n_dimensions)


def _encode_batch(
    torch: Any,
    tokenizer: Any,
    examples: list[Example],
    *,
    max_tokens: int,
    device: str,
) -> dict[str, Any]:
    texts = [serialize_context(e.context, max_tokens=max_tokens).text for e in examples]
    encoded = tokenizer(
        texts, return_tensors="pt", truncation=True, padding=True, max_length=max_tokens
    )
    encoded = {k: v.to(device) for k, v in encoded.items()}

    targets = torch.zeros((len(examples), len(DIMENSION_ORDER)), dtype=torch.float32)
    mask = torch.zeros((len(examples), len(DIMENSION_ORDER)), dtype=torch.float32)
    for row, example in enumerate(examples):
        for col, dimension in enumerate(DIMENSION_ORDER):
            label = example.labels.values[dimension]
            if label in _MASKED_LABELS:
                continue
            mask[row, col] = 1.0
            if label is LabelValue.YES:
                targets[row, col] = 1.0
    encoded["targets"] = targets.to(device)
    encoded["mask"] = mask.to(device)
    return encoded


def _forward(torch: Any, backbone: Any, head: Any, batch: dict[str, Any], pooling: Pooling) -> Any:
    model_inputs = {k: v for k, v in batch.items() if k in ("input_ids", "attention_mask")}
    outputs = backbone(**model_inputs)
    pooled = pool_hidden_states(torch, outputs.last_hidden_state, batch["attention_mask"], pooling)
    return head(pooled.to(head.weight.dtype))


def _evaluate(
    torch: Any,
    backbone: Any,
    head: Any,
    dev_examples: list[Example],
    tokenizer: Any,
    *,
    pooling: Pooling,
    max_tokens: int,
    device: str,
    micro_batch_size: int,
) -> tuple[float | None, dict[RiskDimension, DimensionMetrics]]:
    backbone.eval()
    head.eval()
    labels_by_dim: dict[RiskDimension, list[LabelValue]] = {d: [] for d in DIMENSION_ORDER}
    probs_by_dim: dict[RiskDimension, list[float]] = {d: [] for d in DIMENSION_ORDER}
    with torch.no_grad():
        for start in range(0, len(dev_examples), micro_batch_size):
            chunk = dev_examples[start : start + micro_batch_size]
            batch = _encode_batch(torch, tokenizer, chunk, max_tokens=max_tokens, device=device)
            logits = _forward(torch, backbone, head, batch, pooling)
            probs = torch.sigmoid(logits).detach().cpu().tolist()
            for example, row_probs in zip(chunk, probs, strict=True):
                for col, dimension in enumerate(DIMENSION_ORDER):
                    labels_by_dim[dimension].append(example.labels.values[dimension])
                    probs_by_dim[dimension].append(float(row_probs[col]))
    metrics: dict[RiskDimension, DimensionMetrics] = {}
    for dimension in DIMENSION_ORDER:
        y_true, y_prob, _ = extract_dimension_arrays(
            labels_by_dim[dimension], list(probs_by_dim[dimension])
        )
        metrics[dimension] = compute_dimension_metrics(dimension, y_true, y_prob)
    macro_auprc = macro_average(metrics, "auprc")
    return macro_auprc, metrics


def _save_best_checkpoint(
    torch: Any,
    run_dir: Path,
    step: int,
    backbone: Any,
    tokenizer: Any,
    head: Any,
    config: EncoderTrainConfig,
    dev_macro_auprc: float | None,
) -> Path:
    from safetensors.torch import save_file

    checkpoint_dir = run_dir / "checkpoints" / "best"
    backbone_dir = checkpoint_dir / BACKBONE_DIR
    backbone_dir.mkdir(parents=True, exist_ok=True)
    backbone.save_pretrained(str(backbone_dir))
    tokenizer.save_pretrained(str(backbone_dir))

    head_state = {
        "weight": head.weight.detach().cpu().contiguous(),
        "bias": head.bias.detach().cpu().contiguous(),
    }
    save_file(head_state, str(checkpoint_dir / HEAD_WEIGHTS_FILE))

    head_config = {
        "dimension_order": [d.value for d in DIMENSION_ORDER],
        "pooling": config.model.pooling,
        "model_id": config.model.base_id,
        "max_tokens": config.model.max_tokens,
        "serialization_contract_hash": serialization_contract_hash(),
    }
    (checkpoint_dir / HEAD_CONFIG_FILE).write_text(
        json.dumps(head_config, indent=2, sort_keys=True), encoding="utf-8"
    )
    (checkpoint_dir / _TRAINER_STATE_FILE).write_text(
        json.dumps({"step": step, "dev_macro_auprc": dev_macro_auprc}, indent=2), encoding="utf-8"
    )

    from forecheck.data.io import sha256_file

    files = {HEAD_WEIGHTS_FILE: sha256_file(checkpoint_dir / HEAD_WEIGHTS_FILE)}
    write_checkpoint_manifest(checkpoint_dir, step=step, files=files, extra={"kind": "encoder"})
    return checkpoint_dir


def run_encoder_training(
    config: EncoderTrainConfig,
    *,
    tracker: ExperimentTracker | None = None,
    repo_dir: Path | None = None,
) -> EncoderTrainResult:
    torch = _require_torch()
    from forecheck.training.dataset import load_examples

    run_dir = config.output.dir
    run_dir.mkdir(parents=True, exist_ok=True)
    write_run_capture(run_dir, config, repo_dir=repo_dir)
    active_tracker = tracker or LocalJsonTracker(run_dir)
    active_tracker.log_params(json.loads(config.model_dump_json()))

    backbone, tokenizer, device = build_backbone_and_tokenizer(config)
    hidden_size = backbone.config.hidden_size
    head = build_head(torch, hidden_size, len(DIMENSION_ORDER))
    head.to(device)

    if config.train.freeze_backbone:
        for param in backbone.parameters():
            param.requires_grad_(False)

    train_examples = load_examples(config.data.dir, config.data.train_split)
    dev_examples = load_examples(config.data.dir, config.data.dev_split)

    pos_weight = resolve_pos_weight(train_examples, DIMENSION_ORDER, config.loss.pos_weight_mode)
    if pos_weight is not None:
        pos_weight = pos_weight.to(device)

    param_groups = [{"params": head.parameters(), "lr": config.optim.head_lr}]
    if not config.train.freeze_backbone:
        param_groups.append({"params": backbone.parameters(), "lr": config.optim.backbone_lr})
    optimizer = torch.optim.AdamW(param_groups, weight_decay=config.optim.weight_decay)

    steps_per_epoch = max(1, len(train_examples) // config.optim.micro_batch_size)
    total_steps = steps_per_epoch * config.optim.epochs
    if config.optim.max_steps is not None:
        total_steps = min(total_steps, config.optim.max_steps)

    from transformers import get_scheduler

    warmup_steps = int(config.optim.warmup_ratio * total_steps)
    scheduler = get_scheduler(
        config.optim.scheduler,
        optimizer=optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )

    sampler = SeededEpochSampler(len(train_examples), seed=config.train.seed)

    best_step: int | None = None
    best_macro_auprc: float | None = None
    stale_evals = 0
    stopped_early = False
    step = 0

    backbone.train()
    head.train()
    for indices in sampler.batches(config.optim.epochs, config.optim.micro_batch_size):
        chunk = [train_examples[i] for i in indices]
        batch = _encode_batch(
            torch, tokenizer, chunk, max_tokens=config.model.max_tokens, device=device
        )
        logits = _forward(torch, backbone, head, batch, config.model.pooling)
        loss_output = masked_bce_with_logits(
            logits, batch["targets"], batch["mask"], pos_weight=pos_weight
        )
        optimizer.zero_grad()
        loss_output.loss.backward()
        trainable_params = [p for p in head.parameters() if p.requires_grad]
        if not config.train.freeze_backbone:
            trainable_params.extend(p for p in backbone.parameters() if p.requires_grad)
        torch.nn.utils.clip_grad_norm_(trainable_params, config.optim.grad_clip)
        optimizer.step()
        scheduler.step()
        step += 1

        active_tracker.log_metrics(step, {"train/loss": float(loss_output.loss.detach())})

        if step % config.train.eval_every == 0:
            macro_auprc, _dim_metrics = _evaluate(
                torch,
                backbone,
                head,
                dev_examples,
                tokenizer,
                pooling=config.model.pooling,
                max_tokens=config.model.max_tokens,
                device=device,
                micro_batch_size=config.optim.micro_batch_size,
            )
            if macro_auprc is not None:
                active_tracker.log_metrics(step, {"dev/macro_auprc": macro_auprc})
                if best_macro_auprc is None or macro_auprc > best_macro_auprc:
                    best_macro_auprc = macro_auprc
                    best_step = step
                    stale_evals = 0
                    _save_best_checkpoint(
                        torch, run_dir, step, backbone, tokenizer, head, config, macro_auprc
                    )
                else:
                    stale_evals += 1
                if stale_evals >= config.train.early_stop_patience:
                    stopped_early = True
            backbone.train()
            head.train()

        if stopped_early or step >= total_steps:
            break

    active_tracker.finish()
    return EncoderTrainResult(
        run_dir=run_dir,
        steps_completed=step,
        best_step=best_step,
        best_dev_macro_auprc=best_macro_auprc,
        stopped_early=stopped_early,
    )
