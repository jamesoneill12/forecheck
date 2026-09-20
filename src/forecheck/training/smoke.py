"""A tiny end-to-end training run, for CI's fast confidence check.

Trains a randomly initialized, architecturally-real causal LM (default:
``hf-internal-testing/tiny-random-LlamaForCausalLM``) for a handful of steps on a
handful of synthetic examples, entirely on CPU. It exercises the same
:func:`forecheck.training.loop.run_training` path a real recipe uses, so a break in
config parsing, encoding, collation, the loss or checkpointing is caught before a real,
expensive run ever starts.

Offline use: pass ``model_id`` as a local directory (already-cached snapshot) to avoid
any network access; the default id requires downloading a few hundred KB from the Hub
the first time.
"""

from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from forecheck.contracts import (
    ActionOrigin,
    AgentIdentity,
    AuthorizationBasis,
    Example,
    LabelSet,
    LabelValue,
    LatentScenario,
    OperationKind,
    Principal,
    ProposedAction,
    Provenance,
    RiskDimension,
    Split,
    UserObjective,
)
from forecheck.contracts.context import ActionContext
from forecheck.data.io import write_jsonl
from forecheck.data.tools import get_tool
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

__all__ = [
    "DEFAULT_SMOKE_MODEL_ID",
    "SmokeTrainResult",
    "build_synthetic_examples",
    "run_smoke_train",
]

DEFAULT_SMOKE_MODEL_ID = "hf-internal-testing/tiny-random-LlamaForCausalLM"


HAS_TORCH = importlib.util.find_spec("torch") is not None


def build_synthetic_examples(n: int, *, family_prefix: str = "smoke") -> list[Example]:
    """A handful of self-contained, valid examples with no external data dependency."""
    examples: list[Example] = []
    for i in range(n):
        family_id = f"{family_prefix}-{i}"
        benign = i % 2 == 0
        latent = LatentScenario(
            scenario_id=f"{family_id}-scenario",
            family_id=family_id,
            template_lineage=[family_id],
            tool=get_tool("email.read_message" if benign else "storage.delete_object"),
            operation=OperationKind.READ if benign else OperationKind.DELETE,
            authorization_basis=AuthorizationBasis.EXPLICIT,
            action_origin=ActionOrigin.PRINCIPAL_REQUEST,
        )
        values = dict.fromkeys(RiskDimension, LabelValue.NO)
        values[RiskDimension.INSUFFICIENT_CONTEXT] = LabelValue.NOT_APPLICABLE
        if not benign:
            values[RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION] = LabelValue.YES
        context = ActionContext(
            objective=UserObjective(text=f"Handle item {i} on behalf of the customer."),
            principal=Principal(id=f"user-{i}"),
            agent=AgentIdentity(id="smoke-agent", delegated_scopes=["email.read"]),
            proposed_action=ProposedAction(
                tool_name="email.read_message" if benign else "storage.delete_object",
                arguments={"id": str(i)},
            ),
        )
        examples.append(
            Example(
                example_id=f"{family_id}-example",
                family_id=family_id,
                split=Split.TRAIN,
                latent=latent,
                context=context,
                labels=LabelSet(values=values, derivation_version="smoke-1.0"),
                provenance=Provenance(
                    generator_name="smoke",
                    generator_version="1.0.0",
                    seed=i,
                    created_at=datetime.now(tz=UTC),
                ),
            )
        )
    return examples


def _write_smoke_data(data_dir: Path, n_train: int, n_dev: int) -> None:
    train_examples = build_synthetic_examples(n_train, family_prefix="smoke-train")
    dev_examples = [
        example.model_copy(update={"split": Split.DEV})
        for example in build_synthetic_examples(n_dev, family_prefix="smoke-dev")
    ]
    write_jsonl(data_dir / "train.jsonl", train_examples)
    write_jsonl(data_dir / "dev.jsonl", dev_examples)


def build_smoke_config(
    *,
    data_dir: Path,
    output_dir: Path,
    model_id: str = DEFAULT_SMOKE_MODEL_ID,
    steps: int = 20,
    resume_from: Path | None = None,
) -> TrainConfig:
    return TrainConfig(
        model=ModelConfig(base_id=model_id, dtype="fp32", attn_implementation="eager"),
        lora=LoraConfig(r=4, alpha=8, dropout=0.0, target_modules=("q_proj", "v_proj")),
        data=DataConfig(dir=data_dir, max_prompt_tokens=512),
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
            eval_every=max(1, steps // 2),
            save_every=max(1, steps // 2),
            early_stop_patience=100,
            resume_from=resume_from,
            shared_prefill=True,
        ),
        tracking=TrackingConfig(backend="local"),
        output=OutputConfig(dir=output_dir),
    )


@dataclass(frozen=True, slots=True)
class SmokeTrainResult:
    first_loss: float
    last_loss: float
    checkpoint_dir: Path
    resumed_steps_completed: int


def run_smoke_train(
    *,
    workdir: Path,
    model_id: str = DEFAULT_SMOKE_MODEL_ID,
    steps: int = 20,
    n_train: int = 8,
    n_dev: int = 4,
) -> SmokeTrainResult:
    """Run the tiny training loop twice: once fresh, once resumed from its checkpoint."""
    from forecheck.training.loop import run_training

    data_dir = workdir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    _write_smoke_data(data_dir, n_train, n_dev)

    output_dir = workdir / "run"
    config = build_smoke_config(
        data_dir=data_dir, output_dir=output_dir, model_id=model_id, steps=steps
    )
    run_training(config)

    metrics_path = output_dir / "metrics.jsonl"
    losses = [
        float(json.loads(line)["train/loss"])
        for line in metrics_path.read_text(encoding="utf-8").splitlines()
        if "train/loss" in line
    ]
    if len(losses) < 2:
        raise RuntimeError("smoke train did not record at least two loss values")

    checkpoints = sorted((output_dir / "checkpoints").iterdir())
    if not checkpoints:
        raise RuntimeError("smoke train did not write any checkpoint")
    checkpoint_dir = checkpoints[-1]

    resumed_output_dir = workdir / "run-resumed"
    resumed_config = build_smoke_config(
        data_dir=data_dir,
        output_dir=resumed_output_dir,
        model_id=model_id,
        steps=steps + 4,
        resume_from=checkpoint_dir,
    )
    result = run_training(resumed_config)
    return SmokeTrainResult(
        first_loss=losses[0],
        last_loss=losses[-1],
        checkpoint_dir=checkpoint_dir,
        resumed_steps_completed=result.steps_completed,
    )


@pytest.mark.slow
@pytest.mark.network
@pytest.mark.skipif(not HAS_TORCH, reason="forecheck[train] is not installed")
def test_smoke_cpu_train(tmp_path: Any) -> None:
    """CI smoke test: tiny model, CPU, ~20 steps, loss decreases and resume round-trips."""
    result = run_smoke_train(workdir=Path(tmp_path))
    assert result.last_loss < result.first_loss
    assert result.resumed_steps_completed > 0
