"""Hugging Face candidate-token-logit backend.

Scores a dimension as ``log p(yes) - log p(no)`` over the renormalised two-way
candidate set, read directly off the final-position logits -- never by generating
text. Requires ``pip install 'forecheck[torch]'``; all torch/transformers imports are
deferred to call time so the package imports without that extra installed.

Shared-prefill reuse assumes the "\\n\\n" question separator tokenizes the same way
whether or not it is preceded by the context text; this holds for the fixed separator
used here on the tokenizers this backend targets, and is exercised by the shared vs.
naive equivalence test.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from forecheck.contracts import LABEL_SCHEMA_VERSION, Limits, ModelInfo, RiskDimension
from forecheck.inference.base import BackendCapabilities, BaseBackend, RawScores
from forecheck.inference.prompt import QUESTIONS, prompt_contract_hash
from forecheck.inference.serialization import serialize_context

if TYPE_CHECKING:
    from collections.abc import Sequence

    from forecheck.contracts import ActionContext

__all__ = ["HFBackend", "HFBackendConfig"]

DEFAULT_YES_SURFACE_FORMS: tuple[str, ...] = ("yes", "Yes", " yes", " Yes", "YES")
DEFAULT_NO_SURFACE_FORMS: tuple[str, ...] = ("no", "No", " no", " No", "NO")

_TORCH_INSTALL_HINT = (
    "the Hugging Face backend requires torch and transformers; "
    "install with pip install 'forecheck[torch]'"
)


def _require_torch() -> Any:
    try:
        import torch  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(_TORCH_INSTALL_HINT) from exc
    return torch


@dataclass(frozen=True, slots=True)
class HFBackendConfig:
    model_id: str
    revision: str | None = None
    adapter_id: str | None = None
    device: str | None = None
    dtype: str | None = None
    shared_prefill: bool = True
    yes_surface_forms: tuple[str, ...] = DEFAULT_YES_SURFACE_FORMS
    no_surface_forms: tuple[str, ...] = DEFAULT_NO_SURFACE_FORMS
    max_prompt_tokens: int = Limits.MAX_PROMPT_TOKENS


def _auto_device(torch: Any) -> str:
    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    return "cpu"


def _resolve_dtype(torch: Any, dtype_name: str | None, device: str) -> Any:
    if dtype_name is not None:
        return getattr(torch, dtype_name)
    return torch.float32 if device == "cpu" else torch.bfloat16


def _resolve_candidate_ids(tokenizer: Any, surface_forms: tuple[str, ...], label: str) -> set[int]:
    ids: set[int] = set()
    for form in surface_forms:
        token_ids = tokenizer.encode(form, add_special_tokens=False)
        if len(token_ids) != 1:
            raise ValueError(
                f"surface form {form!r} for class {label!r} tokenizes to "
                f"{len(token_ids)} tokens; expected exactly 1"
            )
        ids.add(int(token_ids[0]))
    return ids


def _detect_cache_reuse_support(model: Any) -> bool:
    try:
        params = inspect.signature(model.forward).parameters
    except (TypeError, ValueError):
        return False
    return "past_key_values" in params and "use_cache" in params


def _log_odds(torch: Any, logits: Any, yes_ids: set[int], no_ids: set[int]) -> float:
    yes_index = torch.tensor(sorted(yes_ids), dtype=torch.long, device=logits.device)
    no_index = torch.tensor(sorted(no_ids), dtype=torch.long, device=logits.device)
    yes_logp = torch.logsumexp(logits.index_select(-1, yes_index), dim=-1)
    no_logp = torch.logsumexp(logits.index_select(-1, no_index), dim=-1)
    return float(yes_logp - no_logp)


class HFBackend(BaseBackend):
    def __init__(self, config: HFBackendConfig) -> None:
        self._config = config
        self._model: Any = None
        self._tokenizer: Any = None
        self._device: str | None = None
        self._yes_ids: set[int] | None = None
        self._no_ids: set[int] | None = None
        self._supports_cache_reuse: bool = False

    def _load_model_and_tokenizer(self, torch: Any) -> tuple[Any, Any, str]:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        device = self._config.device or _auto_device(torch)
        dtype = _resolve_dtype(torch, self._config.dtype, device)
        tokenizer = AutoTokenizer.from_pretrained(
            self._config.model_id, revision=self._config.revision
        )
        model = AutoModelForCausalLM.from_pretrained(
            self._config.model_id, revision=self._config.revision, torch_dtype=dtype
        )
        if self._config.adapter_id is not None:
            from peft import PeftModel

            model = PeftModel.from_pretrained(model, self._config.adapter_id)
        model.to(device)
        model.eval()
        return model, tokenizer, device

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        torch = _require_torch()
        model, tokenizer, device = self._load_model_and_tokenizer(torch)
        yes_ids = _resolve_candidate_ids(tokenizer, self._config.yes_surface_forms, "yes")
        no_ids = _resolve_candidate_ids(tokenizer, self._config.no_surface_forms, "no")
        overlap = yes_ids & no_ids
        if overlap:
            raise ValueError(f"yes/no candidate token ids collide: {sorted(overlap)}")
        self._model = model
        self._tokenizer = tokenizer
        self._device = device
        self._yes_ids = yes_ids
        self._no_ids = no_ids
        self._supports_cache_reuse = _detect_cache_reuse_support(model)

    def warmup(self) -> None:
        self._ensure_loaded()

    def close(self) -> None:
        if self._model is not None:
            torch = _require_torch()
            self._model = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    @property
    def model_info(self) -> ModelInfo:
        return ModelInfo(
            backend="huggingface",
            model_id=self._config.model_id,
            revision=self._config.revision,
            base_model=self._config.model_id,
            adapter_id=self._config.adapter_id,
            prompt_contract_hash=prompt_contract_hash(),
            label_schema_version=LABEL_SCHEMA_VERSION,
            quantization=None,
        )

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            supports_batching=False,
            supports_shared_prefill=self._config.shared_prefill,
            max_prompt_tokens=self._config.max_prompt_tokens,
            device=self._device or self._config.device or "cpu",
            deterministic=True,
        )

    def score(
        self, context: ActionContext, dimensions: Sequence[RiskDimension] | None = None
    ) -> RawScores:
        self._ensure_loaded()
        torch = _require_torch()
        model, tokenizer = self._model, self._tokenizer
        yes_ids, no_ids = self._yes_ids, self._no_ids
        assert (
            model is not None
            and tokenizer is not None
            and yes_ids is not None
            and no_ids is not None
        )

        dims = list(dimensions) if dimensions is not None else list(RiskDimension)
        rendered = serialize_context(context, max_tokens=self._config.max_prompt_tokens)
        prefix_ids = tokenizer(rendered.text, return_tensors="pt").input_ids.to(self._device)
        use_shared = self._config.shared_prefill and self._supports_cache_reuse

        scores: dict[RiskDimension, float] = {}
        with torch.no_grad():
            if use_shared:
                prefix_out = model(prefix_ids, use_cache=True)
                past = prefix_out.past_key_values
                for dim in dims:
                    q_text = "\n\n" + QUESTIONS[dim]
                    q_ids = tokenizer(q_text, return_tensors="pt").input_ids.to(self._device)
                    out = model(q_ids, past_key_values=past, use_cache=True)
                    scores[dim] = _log_odds(torch, out.logits[0, -1], yes_ids, no_ids)
            else:
                for dim in dims:
                    full_text = rendered.text + "\n\n" + QUESTIONS[dim]
                    ids = tokenizer(full_text, return_tensors="pt").input_ids.to(self._device)
                    out = model(ids, use_cache=False)
                    scores[dim] = _log_odds(torch, out.logits[0, -1], yes_ids, no_ids)

        return RawScores(
            scores=scores, truncation=rendered.truncation, prompt_tokens=int(prefix_ids.shape[-1])
        )
