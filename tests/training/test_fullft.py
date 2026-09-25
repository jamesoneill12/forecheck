from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from forecheck.contracts import Split
from forecheck.data.io import write_jsonl
from forecheck.training.config import (
    DataConfig,
    LoraConfig,
    ModelConfig,
    OptimConfig,
    OutputConfig,
    TrackingConfig,
    TrainConfig,
    TrainLoopConfig,
)
from forecheck.training.smoke import DEFAULT_SMOKE_MODEL_ID, build_synthetic_examples

HAS_TORCH = importlib.util.find_spec("torch") is not None
requires_torch = pytest.mark.skipif(not HAS_TORCH, reason="forecheck[train] is not installed")


def _write_data(data_dir: Path, n_train: int, n_dev: int) -> None:
    train_examples = build_synthetic_examples(n_train, family_prefix="fullft-train")
    dev_examples = [
        example.model_copy(update={"split": Split.DEV})
        for example in build_synthetic_examples(n_dev, family_prefix="fullft-dev")
    ]
    write_jsonl(data_dir / "train.jsonl", train_examples)
    write_jsonl(data_dir / "dev.jsonl", dev_examples)


def _build_fullft_config(
    *, data_dir: Path, output_dir: Path, steps: int = 2, resume_from: Path | None = None
) -> TrainConfig:
    return TrainConfig(
        model=ModelConfig(
            base_id=DEFAULT_SMOKE_MODEL_ID, dtype="fp32", attn_implementation="eager"
        ),
        lora=LoraConfig(enabled=False),
        data=DataConfig(dir=data_dir, max_prompt_tokens=1024),
        optim=OptimConfig(
            lr=1e-3,
            epochs=steps,
            max_steps=steps,
            micro_batch_size=2,
            grad_accum=1,
            scheduler="constant",
        ),
        train=TrainLoopConfig(
            seed=0,
            eval_every=max(1, steps),
            save_every=max(1, steps),
            early_stop_patience=100,
            resume_from=resume_from,
            shared_prefill=True,
            use_chat_template=False,
        ),
        tracking=TrackingConfig(backend="local"),
        output=OutputConfig(dir=output_dir),
    )


@pytest.mark.slow
@pytest.mark.network
@requires_torch
def test_full_finetune_writes_model_checkpoint_not_adapter(tmp_path: Path) -> None:
    from forecheck.training.loop import run_training

    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    _write_data(data_dir, n_train=4, n_dev=2)

    output_dir = tmp_path / "run"
    config = _build_fullft_config(data_dir=data_dir, output_dir=output_dir, steps=2)
    run_training(config)

    checkpoints = sorted((output_dir / "checkpoints").iterdir())
    assert checkpoints
    checkpoint_dir = checkpoints[-1]

    assert (checkpoint_dir / "model" / "config.json").exists()
    assert not (checkpoint_dir / "adapter").exists()

    manifest = json.loads((checkpoint_dir / "checkpoint_manifest.json").read_text(encoding="utf-8"))
    assert manifest["weights"] == "full"


@pytest.mark.slow
@pytest.mark.network
@requires_torch
def test_full_finetune_resume_constructs_without_peft(tmp_path: Path) -> None:
    from peft import PeftModel

    from forecheck.training.loop import attach_lora, build_base_model_and_tokenizer, run_training

    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    _write_data(data_dir, n_train=4, n_dev=2)

    output_dir = tmp_path / "run"
    config = _build_fullft_config(data_dir=data_dir, output_dir=output_dir, steps=2)
    run_training(config)

    checkpoint_dir = sorted((output_dir / "checkpoints").iterdir())[-1]

    resumed_config = _build_fullft_config(
        data_dir=data_dir, output_dir=tmp_path / "run-resumed", steps=4, resume_from=checkpoint_dir
    )
    base_model, _tokenizer, _device = build_base_model_and_tokenizer(resumed_config, checkpoint_dir)
    model = attach_lora(base_model, resumed_config, checkpoint_dir)

    assert not isinstance(model, PeftModel)
