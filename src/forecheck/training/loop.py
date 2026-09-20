"""The LoRA/QLoRA training loop: forward, loss, checkpoint, resume, eval, early stop.

Every ``torch``/``transformers``/``peft`` symbol is imported lazily inside functions
(never at module scope, never under ``TYPE_CHECKING``) so this module — and therefore
the whole ``forecheck.training`` package — imports cleanly when the ``train`` extra is
not installed. Only :class:`SeededEpochSampler` has no torch dependency at all, so its
resume-determinism guarantee is unit-tested directly.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from forecheck.contracts import LabelValue, RiskDimension
from forecheck.evaluation.metrics import (
    DimensionMetrics,
    compute_dimension_metrics,
    extract_dimension_arrays,
    macro_average,
)
from forecheck.inference.hf import DEFAULT_NO_SURFACE_FORMS, DEFAULT_YES_SURFACE_FORMS
from forecheck.training.capture import write_checkpoint_manifest, write_run_capture
from forecheck.training.collate import Batch, build_batch
from forecheck.training.config import TrainConfig
from forecheck.training.dataset import (
    DIMENSION_ORDER,
    EncodedSequence,
    TrainableExampleDataset,
    load_examples,
)
from forecheck.training.loss import candidate_cross_entropy, resolve_candidate_ids
from forecheck.training.tracking import ExperimentTracker, LocalJsonTracker

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["SeededEpochSampler", "TrainResult", "run_training"]

_TRAINER_STATE_FILE = "trainer_state.json"
_ADAPTER_DIR = "adapter"
_OPTIMIZER_FILE = "optimizer.pt"
_SCHEDULER_FILE = "scheduler.pt"
_RNG_FILE = "rng.pt"


def _require_torch() -> Any:
    try:
        import torch  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(
            "forecheck.training.loop requires torch; install forecheck[train]"
        ) from exc
    return torch


class SeededEpochSampler:
    """Deterministic, resumable example ordering with no torch dependency.

    ``epoch_indices(e)`` is a seeded permutation of ``range(n_examples)`` (or identity
    when ``shuffle=False``). ``batches(...)`` flattens epochs into one long index
    stream and resumes it at a step offset, so re-running with the same seed and the
    same ``resume_from_step`` always replays the same remaining batches byte-for-byte.
    """

    def __init__(self, n_examples: int, *, seed: int, shuffle: bool = True) -> None:
        if n_examples <= 0:
            raise ValueError("n_examples must be positive")
        self._n = n_examples
        self._seed = seed
        self._shuffle = shuffle

    def epoch_indices(self, epoch: int) -> list[int]:
        if not self._shuffle:
            return list(range(self._n))
        rng = np.random.default_rng(self._seed + epoch)
        return [int(i) for i in rng.permutation(self._n)]

    def flat_order(self, n_epochs: int) -> list[int]:
        order: list[int] = []
        for epoch in range(n_epochs):
            order.extend(self.epoch_indices(epoch))
        return order

    def batches(
        self, n_epochs: int, batch_size: int, *, resume_from_step: int = 0
    ) -> Iterator[list[int]]:
        flat = self.flat_order(n_epochs)
        start = resume_from_step * batch_size
        for offset in range(start, len(flat), batch_size):
            batch = flat[offset : offset + batch_size]
            if batch:
                yield batch


@dataclass(frozen=True, slots=True)
class TrainResult:
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


def _resolve_dtype(torch: Any, dtype_name: str, device: str) -> Any:
    if dtype_name == "auto":
        return torch.bfloat16 if device != "cpu" else torch.float32
    return getattr(torch, dtype_name)


def build_base_model_and_tokenizer(config: TrainConfig) -> tuple[Any, Any, str]:
    torch = _require_torch()
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = _auto_device(torch)
    dtype = _resolve_dtype(torch, config.model.dtype, device)
    tokenizer = AutoTokenizer.from_pretrained(config.model.base_id, revision=config.model.revision)
    model_kwargs: dict[str, Any] = {"revision": config.model.revision, "torch_dtype": dtype}
    if config.model.attn_implementation is not None:
        model_kwargs["attn_implementation"] = config.model.attn_implementation
    if config.lora.qlora:
        if device != "cuda":
            raise RuntimeError("lora.qlora=true requires a CUDA device")
        from transformers import BitsAndBytesConfig

        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=dtype,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        model_kwargs["device_map"] = {"": 0}
    model = AutoModelForCausalLM.from_pretrained(config.model.base_id, **model_kwargs)
    if not config.lora.qlora:
        model.to(device)
    return model, tokenizer, device


def attach_lora(base_model: Any, config: TrainConfig, resume_from: Path | None) -> Any:
    from peft import LoraConfig as PeftLoraConfig
    from peft import PeftModel, get_peft_model

    if config.lora.qlora:
        from peft import prepare_model_for_kbit_training

        base_model = prepare_model_for_kbit_training(base_model)
    if resume_from is not None:
        return PeftModel.from_pretrained(
            base_model, str(resume_from / _ADAPTER_DIR), is_trainable=True
        )
    peft_config = PeftLoraConfig(
        r=config.lora.r,
        lora_alpha=config.lora.alpha,
        lora_dropout=config.lora.dropout,
        target_modules=list(config.lora.target_modules),
        bias="none",
        task_type="CAUSAL_LM",
    )
    return get_peft_model(base_model, peft_config)


def _additive_mask(torch: Any, keep_mask: np.ndarray, device: Any, dtype: Any) -> Any:
    keep = torch.from_numpy(keep_mask).to(device)
    min_value = torch.finfo(dtype).min
    return torch.zeros(keep.shape, dtype=dtype, device=device).masked_fill(~keep, min_value)


def _forward_batch(torch: Any, model: Any, batch: Batch, device: Any, dtype: Any) -> Any:
    input_ids = torch.from_numpy(batch.input_ids).to(device)
    attention_mask = _additive_mask(torch, batch.keep_mask, device, dtype)
    outputs = model(input_ids=input_ids, attention_mask=attention_mask)
    return outputs.logits


def _gather_target_logits(torch: Any, logits: Any, batch: Batch) -> Any:
    batch_index = torch.from_numpy(batch.target_batch_index).to(logits.device)
    position_index = torch.from_numpy(batch.target_position).to(logits.device)
    return logits[batch_index, position_index]


def _resolve_batch_sequences(
    dataset: TrainableExampleDataset, indices: list[int]
) -> list[EncodedSequence]:
    sequences: list[EncodedSequence] = []
    for index in indices:
        sequences.extend(dataset[index])
    return sequences


def _build_optimizer_and_scheduler(
    torch: Any, model: Any, config: TrainConfig, total_steps: int
) -> tuple[Any, Any]:
    from transformers import get_scheduler

    trainable = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(
        trainable, lr=config.optim.lr, weight_decay=config.optim.weight_decay
    )
    warmup_steps = int(config.optim.warmup_ratio * total_steps)
    scheduler = get_scheduler(
        config.optim.scheduler,
        optimizer=optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )
    return optimizer, scheduler


def _rng_state() -> dict[str, Any]:
    return {"python": random.getstate(), "numpy": np.random.get_state()}


def _restore_rng_state(state: dict[str, Any]) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])


def _save_checkpoint(
    torch: Any,
    run_dir: Path,
    step: int,
    model: Any,
    optimizer: Any,
    scheduler: Any,
) -> Path:
    checkpoint_dir = run_dir / "checkpoints" / f"step-{step}"
    adapter_dir = checkpoint_dir / _ADAPTER_DIR
    adapter_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(adapter_dir))
    torch.save(optimizer.state_dict(), checkpoint_dir / _OPTIMIZER_FILE)
    torch.save(scheduler.state_dict(), checkpoint_dir / _SCHEDULER_FILE)
    torch.save(_rng_state(), checkpoint_dir / _RNG_FILE)
    (checkpoint_dir / _TRAINER_STATE_FILE).write_text(
        json.dumps({"step": step}, indent=2), encoding="utf-8"
    )
    from forecheck.data.io import sha256_file

    files = {
        name: sha256_file(checkpoint_dir / name)
        for name in (_OPTIMIZER_FILE, _SCHEDULER_FILE, _RNG_FILE)
    }
    write_checkpoint_manifest(checkpoint_dir, step=step, files=files)
    return checkpoint_dir


def _load_checkpoint_state(torch: Any, checkpoint_dir: Path, optimizer: Any, scheduler: Any) -> int:
    """Restore optimizer/scheduler/RNG state from a checkpoint this same code wrote.

    ``weights_only=False`` is required (RNG/optimizer state hold non-tensor Python
    objects); ``checkpoint_dir`` must be a run's own directory, never untrusted input.
    """
    optimizer.load_state_dict(torch.load(checkpoint_dir / _OPTIMIZER_FILE, weights_only=False))
    scheduler.load_state_dict(torch.load(checkpoint_dir / _SCHEDULER_FILE, weights_only=False))
    _restore_rng_state(torch.load(checkpoint_dir / _RNG_FILE, weights_only=False))
    state = json.loads((checkpoint_dir / _TRAINER_STATE_FILE).read_text(encoding="utf-8"))
    return int(state["step"])


def _evaluate(
    torch: Any,
    model: Any,
    dev_dataset: TrainableExampleDataset,
    *,
    yes_ids: frozenset[int],
    no_ids: frozenset[int],
    device: Any,
    dtype: Any,
    pad_token_id: int,
    micro_batch_size: int,
) -> tuple[float | None, dict[RiskDimension, DimensionMetrics]]:
    model.eval()
    labels_by_dim: dict[RiskDimension, list[LabelValue]] = {d: [] for d in DIMENSION_ORDER}
    probs_by_dim: dict[RiskDimension, list[float]] = {d: [] for d in DIMENSION_ORDER}
    yes_index = sorted(yes_ids)
    no_index = sorted(no_ids)
    with torch.no_grad():
        for start in range(0, len(dev_dataset), micro_batch_size):
            indices = list(range(start, min(start + micro_batch_size, len(dev_dataset))))
            sequences = _resolve_batch_sequences(dev_dataset, indices)
            batch = build_batch(sequences, pad_token_id=pad_token_id)
            logits = _forward_batch(torch, model, batch, device, dtype)
            target_logits = _gather_target_logits(torch, logits, batch)
            yes_logp = torch.logsumexp(target_logits[:, yes_index], dim=-1)
            no_logp = torch.logsumexp(target_logits[:, no_index], dim=-1)
            log_z = torch.logsumexp(torch.stack([yes_logp, no_logp], dim=-1), dim=-1)
            prob_yes = torch.exp(yes_logp - log_z).detach().cpu().tolist()
            for dimension, label, prob in zip(
                batch.target_dimension, batch.target_label, prob_yes, strict=True
            ):
                labels_by_dim[dimension].append(label)
                probs_by_dim[dimension].append(float(prob))
    metrics: dict[RiskDimension, DimensionMetrics] = {}
    for dimension in DIMENSION_ORDER:
        y_true, y_prob, _ = extract_dimension_arrays(
            labels_by_dim[dimension], list(probs_by_dim[dimension])
        )
        metrics[dimension] = compute_dimension_metrics(dimension, y_true, y_prob)
    macro_auprc = macro_average(metrics, "auprc")
    return macro_auprc, metrics


def run_training(
    config: TrainConfig,
    *,
    tracker: ExperimentTracker | None = None,
    repo_dir: Path | None = None,
) -> TrainResult:
    torch = _require_torch()
    run_dir = config.output.dir
    run_dir.mkdir(parents=True, exist_ok=True)
    write_run_capture(run_dir, config, repo_dir=repo_dir)
    active_tracker = tracker or LocalJsonTracker(run_dir)
    active_tracker.log_params(json.loads(config.model_dump_json()))

    base_model, tokenizer, device = build_base_model_and_tokenizer(config)
    resume_from = config.train.resume_from
    model = attach_lora(base_model, config, resume_from)
    dtype = _resolve_dtype(torch, config.model.dtype, device)
    pad_token_id = tokenizer.pad_token_id
    if pad_token_id is None:
        pad_token_id = tokenizer.eos_token_id

    yes_ids, no_ids = resolve_candidate_ids(
        tokenizer, DEFAULT_YES_SURFACE_FORMS, DEFAULT_NO_SURFACE_FORMS
    )

    train_examples = load_examples(config.data.dir, config.data.train_split)
    dev_examples = load_examples(config.data.dir, config.data.dev_split)
    train_dataset = TrainableExampleDataset(
        train_examples,
        tokenizer,
        shared_prefill=config.train.shared_prefill,
        max_prompt_tokens=config.data.max_prompt_tokens,
    )
    dev_dataset = TrainableExampleDataset(
        dev_examples,
        tokenizer,
        shared_prefill=config.train.shared_prefill,
        max_prompt_tokens=config.data.max_prompt_tokens,
    )

    steps_per_epoch = max(1, len(train_dataset) // config.optim.micro_batch_size)
    total_micro_steps = steps_per_epoch * config.optim.epochs
    total_optim_steps = max(1, total_micro_steps // config.optim.grad_accum)
    if config.optim.max_steps is not None:
        total_optim_steps = min(total_optim_steps, config.optim.max_steps)

    optimizer, scheduler = _build_optimizer_and_scheduler(torch, model, config, total_optim_steps)

    resume_step = 0
    if resume_from is not None:
        resume_step = _load_checkpoint_state(torch, resume_from, optimizer, scheduler)

    sampler = SeededEpochSampler(len(train_dataset), seed=config.train.seed)
    resume_micro_step = resume_step * config.optim.grad_accum

    best_step: int | None = None
    best_macro_auprc: float | None = None
    stale_evals = 0
    stopped_early = False
    optim_step = resume_step
    accum_loss = 0.0
    optimizer.zero_grad()

    model.train()
    epoch_batches = sampler.batches(
        config.optim.epochs, config.optim.micro_batch_size, resume_from_step=resume_micro_step
    )
    for micro_step, indices in enumerate(epoch_batches, start=resume_micro_step):
        sequences = _resolve_batch_sequences(train_dataset, indices)
        batch = build_batch(sequences, pad_token_id=pad_token_id)
        logits = _forward_batch(torch, model, batch, device, dtype)
        target_logits = _gather_target_logits(torch, logits, batch)
        loss_output = candidate_cross_entropy(
            target_logits,
            list(batch.target_dimension),
            list(batch.target_label),
            yes_ids=yes_ids,
            no_ids=no_ids,
            dimension_weights=config.data.dimension_weights,
        )
        (loss_output.loss / config.optim.grad_accum).backward()
        accum_loss += float(loss_output.loss.detach())

        if (micro_step + 1) % config.optim.grad_accum != 0:
            continue

        torch.nn.utils.clip_grad_norm_(
            (p for p in model.parameters() if p.requires_grad), config.optim.grad_clip
        )
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad()
        optim_step += 1
        mean_loss = accum_loss / config.optim.grad_accum
        accum_loss = 0.0
        active_tracker.log_metrics(optim_step, {"train/loss": mean_loss})

        if optim_step % config.train.eval_every == 0:
            macro_auprc, _dim_metrics = _evaluate(
                torch,
                model,
                dev_dataset,
                yes_ids=yes_ids,
                no_ids=no_ids,
                device=device,
                dtype=dtype,
                pad_token_id=pad_token_id,
                micro_batch_size=config.optim.micro_batch_size,
            )
            if macro_auprc is not None:
                active_tracker.log_metrics(optim_step, {"dev/macro_auprc": macro_auprc})
                if best_macro_auprc is None or macro_auprc > best_macro_auprc:
                    best_macro_auprc = macro_auprc
                    best_step = optim_step
                    stale_evals = 0
                else:
                    stale_evals += 1
                if stale_evals >= config.train.early_stop_patience:
                    stopped_early = True
            model.train()

        if optim_step % config.train.save_every == 0:
            _save_checkpoint(torch, run_dir, optim_step, model, optimizer, scheduler)

        if stopped_early or optim_step >= total_optim_steps:
            break

    active_tracker.finish()
    return TrainResult(
        run_dir=run_dir,
        steps_completed=optim_step,
        best_step=best_step,
        best_dev_macro_auprc=best_macro_auprc,
        stopped_early=stopped_early,
    )
