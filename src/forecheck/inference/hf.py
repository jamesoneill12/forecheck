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

import copy
import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from forecheck.contracts import LABEL_SCHEMA_VERSION, Limits, ModelInfo, RiskDimension
from forecheck.inference.base import BackendCapabilities, BaseBackend, RawScores
from forecheck.inference.chat_template import (
    ChatPrefillPlan,
    ChatPrefillPlanner,
    render_full_chat_text,
)
from forecheck.inference.hf_loading import LoadClass, load_model, load_tokenizer
from forecheck.inference.prompt import QUESTIONS, USE_CHAT_TEMPLATE_DEFAULT, prompt_contract_hash
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
    load_class: LoadClass = "auto"
    use_chat_template: bool = USE_CHAT_TEMPLATE_DEFAULT
    strip_identity: bool = False
    # Kept above len(QUESTIONS) so one row's dimensions batch into a single forward.
    batch_size: int = 32


def _auto_device(torch: Any) -> str:
    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    return "cpu"


def _resolve_dtype(torch: Any, dtype_name: str | None, device: str) -> Any:
    if dtype_name is not None:
        short_names = {"bf16": "bfloat16", "fp16": "float16", "fp32": "float32"}
        return getattr(torch, short_names.get(dtype_name, dtype_name))
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
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
        # A forwarding **kwargs signature may accept these unnamed; trust it.
        return True
    return "past_key_values" in params and "use_cache" in params


def _log_odds(torch: Any, logits: Any, yes_ids: set[int], no_ids: set[int]) -> float:
    yes_index = torch.tensor(sorted(yes_ids), dtype=torch.long, device=logits.device)
    no_index = torch.tensor(sorted(no_ids), dtype=torch.long, device=logits.device)
    yes_logp = torch.logsumexp(logits.index_select(-1, yes_index), dim=-1)
    no_logp = torch.logsumexp(logits.index_select(-1, no_index), dim=-1)
    return float(yes_logp - no_logp)


def _pad_token_id(tokenizer: Any) -> int:
    for attr in ("pad_token_id", "eos_token_id"):
        candidate = getattr(tokenizer, attr, None)
        if candidate is not None:
            return int(candidate)
    return 0


def _pad_sequences(
    torch: Any, sequences: list[tuple[int, ...]], pad_id: int
) -> tuple[Any, list[int]]:
    lengths = [len(s) for s in sequences]
    max_len = max(lengths)
    padded = torch.full((len(sequences), max_len), pad_id, dtype=torch.long)
    for i, seq in enumerate(sequences):
        padded[i, : len(seq)] = torch.tensor(seq, dtype=torch.long)
    return padded, lengths


def _repeat_past_key_values(past: Any, n: int) -> Any | None:
    """Expand a batch-1 KV cache to batch size ``n`` on an independent copy.

    Uses the Cache API's own ``batch_repeat_interleave`` (present on every
    transformers Cache class we target); returns ``None`` when unavailable, telling
    callers to fall back to the verified per-question path instead of guessing at an
    unfamiliar cache's internal tensor layout.
    """
    if not hasattr(past, "batch_repeat_interleave"):
        return None
    batched = copy.deepcopy(past)
    batched.batch_repeat_interleave(n)
    return batched


class HFBackend(BaseBackend):
    def __init__(self, config: HFBackendConfig) -> None:
        self._config = config
        self._model: Any = None
        self._tokenizer: Any = None
        self._device: str | None = None
        self._yes_ids: set[int] | None = None
        self._no_ids: set[int] | None = None
        self._supports_cache_reuse: bool = False
        self._chat_planner: ChatPrefillPlanner | None = None

    def _load_model_and_tokenizer(self, torch: Any) -> tuple[Any, Any, str]:
        device = self._config.device or _auto_device(torch)
        dtype = _resolve_dtype(torch, self._config.dtype, device)
        tokenizer = load_tokenizer(self._config.model_id, revision=self._config.revision)
        model = load_model(
            self._config.model_id,
            load_class=self._config.load_class,
            revision=self._config.revision,
            torch_dtype=dtype,
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
        self._chat_planner = ChatPrefillPlanner(tokenizer)

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
        rendered = serialize_context(
            context,
            max_tokens=self._config.max_prompt_tokens,
            strip_identity=self._config.strip_identity,
        )
        prefix_ids = tokenizer(rendered.text, return_tensors="pt").input_ids.to(self._device)
        use_shared = self._config.shared_prefill and self._supports_cache_reuse

        scores: dict[RiskDimension, float] = {}
        with torch.no_grad():
            if self._config.use_chat_template:
                scores = self._score_chat_template(
                    torch,
                    model,
                    tokenizer,
                    rendered.text,
                    dims,
                    yes_ids,
                    no_ids,
                    use_shared=use_shared,
                )
            elif use_shared:
                prefix_out = model(prefix_ids, use_cache=True)
                items = [
                    (
                        dim,
                        tuple(
                            int(t)
                            for t in tokenizer(
                                "\n\n" + QUESTIONS[dim], return_tensors="pt"
                            ).input_ids[0]
                        ),
                    )
                    for dim in dims
                ]
                scores = self._score_suffix_batch(
                    torch,
                    model,
                    int(prefix_ids.shape[-1]),
                    prefix_out.past_key_values,
                    items,
                    _pad_token_id(tokenizer),
                    yes_ids,
                    no_ids,
                )
            else:
                for dim in dims:
                    full_text = rendered.text + "\n\n" + QUESTIONS[dim]
                    ids = tokenizer(full_text, return_tensors="pt").input_ids.to(self._device)
                    out = model(ids, use_cache=False)
                    scores[dim] = _log_odds(torch, out.logits[0, -1], yes_ids, no_ids)

        return RawScores(
            scores=scores, truncation=rendered.truncation, prompt_tokens=int(prefix_ids.shape[-1])
        )

    def _score_chat_template(
        self,
        torch: Any,
        model: Any,
        tokenizer: Any,
        context_text: str,
        dims: list[RiskDimension],
        yes_ids: set[int],
        no_ids: set[int],
        *,
        use_shared: bool,
    ) -> dict[RiskDimension, float]:
        scores: dict[RiskDimension, float] = {}
        assert self._chat_planner is not None
        plans: dict[RiskDimension, ChatPrefillPlan] = {}
        fallback_dims: list[RiskDimension] = []
        for dim in dims:
            plan = self._chat_planner.plan(context_text, QUESTIONS[dim]) if use_shared else None
            if plan is not None:
                plans[dim] = plan
            else:
                fallback_dims.append(dim)

        if plans:
            # Every plan for this context shares the same verified prefix split.
            prefix_ids = next(iter(plans.values())).prefix_ids
            prefix_tensor = torch.tensor([list(prefix_ids)], dtype=torch.long, device=self._device)
            prefix_out = model(prefix_tensor, use_cache=True)
            items = [(dim, plan.suffix_ids) for dim, plan in plans.items()]
            scores.update(
                self._score_suffix_batch(
                    torch,
                    model,
                    len(prefix_ids),
                    prefix_out.past_key_values,
                    items,
                    _pad_token_id(tokenizer),
                    yes_ids,
                    no_ids,
                )
            )

        for dim in fallback_dims:
            full_text = render_full_chat_text(tokenizer, context_text, QUESTIONS[dim])
            full_ids = tokenizer.encode(full_text, add_special_tokens=False)
            full_tensor = torch.tensor([list(full_ids)], dtype=torch.long, device=self._device)
            out = model(full_tensor, use_cache=False)
            scores[dim] = _log_odds(torch, out.logits[0, -1], yes_ids, no_ids)
        return scores

    def _score_suffix_batch(
        self,
        torch: Any,
        model: Any,
        prefix_len: int,
        prefix_past: Any,
        items: list[tuple[RiskDimension, tuple[int, ...]]],
        pad_id: int,
        yes_ids: set[int],
        no_ids: set[int],
    ) -> dict[RiskDimension, float]:
        """Score every ``(dim, suffix)`` pair against one cached prefix, batching up
        to ``HFBackendConfig.batch_size`` of them per forward call by expanding the
        prefix cache with ``batch_repeat_interleave`` (see
        ``_repeat_past_key_values``). Falls back to the original one-question-at-a-time
        deepcopy loop for cache types that don't support it.
        """
        scores: dict[RiskDimension, float] = {}
        chunk = max(1, self._config.batch_size)
        for start in range(0, len(items), chunk):
            group = items[start : start + chunk]
            batched_past = _repeat_past_key_values(prefix_past, len(group))
            if batched_past is None:
                for dim, suffix_ids in group:
                    past = copy.deepcopy(prefix_past)
                    suffix_tensor = torch.tensor(
                        [list(suffix_ids)], dtype=torch.long, device=self._device
                    )
                    out = model(suffix_tensor, past_key_values=past, use_cache=True)
                    scores[dim] = _log_odds(torch, out.logits[0, -1], yes_ids, no_ids)
                continue
            suffix_tensor, lengths = _pad_sequences(torch, [s for _, s in group], pad_id)
            suffix_tensor = suffix_tensor.to(self._device)
            attention_mask = torch.zeros(
                (len(group), prefix_len + suffix_tensor.shape[1]), dtype=torch.long
            )
            attention_mask[:, :prefix_len] = 1
            for i, length in enumerate(lengths):
                attention_mask[i, prefix_len : prefix_len + length] = 1
            out = model(
                suffix_tensor,
                past_key_values=batched_past,
                use_cache=True,
                attention_mask=attention_mask.to(self._device),
            )
            for i, (dim, _suffix_ids) in enumerate(group):
                scores[dim] = _log_odds(torch, out.logits[i, lengths[i] - 1], yes_ids, no_ids)
        return scores
