from __future__ import annotations

import builtins
import importlib.util
from types import SimpleNamespace
from typing import Any

import pytest

from forecheck.contracts import RiskDimension
from tests.inference.conftest import make_context

HAS_TORCH = importlib.util.find_spec("torch") is not None
requires_torch = pytest.mark.skipif(not HAS_TORCH, reason="torch is not installed")


def test_hf_module_imports_without_torch() -> None:
    from forecheck.inference import hf

    assert hasattr(hf, "HFBackend")
    assert hasattr(hf, "HFBackendConfig")


def test_require_torch_raises_helpful_error_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    from forecheck.inference import hf

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "torch":
            raise ImportError("simulated missing torch")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError, match=r"forecheck\[torch\]"):
        hf._require_torch()


def test_resolve_candidate_ids_requires_single_token() -> None:
    from forecheck.inference.hf import _resolve_candidate_ids

    class _Tok:
        def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
            return [1, 2] if text == "multi" else [hash(text) % 1000]

    with pytest.raises(ValueError, match="expected exactly 1"):
        _resolve_candidate_ids(_Tok(), ("multi",), "yes")


def test_resolve_candidate_ids_collects_variant_ids() -> None:
    from forecheck.inference.hf import _resolve_candidate_ids

    class _Tok:
        def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
            return [{"yes": 1, "Yes": 1, " yes": 2}[text]]

    ids = _resolve_candidate_ids(_Tok(), ("yes", "Yes", " yes"), "yes")
    assert ids == {1, 2}


def test_detect_cache_reuse_support_true_for_standard_signature() -> None:
    from forecheck.inference.hf import _detect_cache_reuse_support

    class _Model:
        def forward(
            self, input_ids: object, past_key_values: object = None, use_cache: bool = False
        ) -> None:
            pass

    assert _detect_cache_reuse_support(_Model()) is True


def test_detect_cache_reuse_support_false_without_past_key_values() -> None:
    from forecheck.inference.hf import _detect_cache_reuse_support

    class _Model:
        def forward(self, input_ids: object) -> None:
            pass

    assert _detect_cache_reuse_support(_Model()) is False


def test_detect_cache_reuse_support_true_for_forwarding_kwargs_signature() -> None:
    from forecheck.inference.hf import _detect_cache_reuse_support

    class _Model:
        def forward(self, input_ids: object, **kwargs: object) -> None:
            pass

    assert _detect_cache_reuse_support(_Model()) is True


@requires_torch
def test_log_odds_prefers_yes_when_yes_logits_dominate() -> None:
    import torch

    from forecheck.inference.hf import _log_odds

    logits = torch.zeros(10)
    logits[0] = 5.0
    logits[1] = -5.0
    assert _log_odds(torch, logits, {0}, {1}) > 0


if HAS_TORCH:
    import torch as _torch

    class _MutableKVCache:
        """Minimal stand-in for transformers' ``DynamicCache``: ``update`` mutates its
        own state in place and returns the concatenated tensors, exactly the semantics
        that make passing the same cache object to two questions unsafe."""

        def __init__(self, k: Any, v: Any) -> None:
            self.k = k
            self.v = v

        def update(self, k_new: Any, v_new: Any) -> tuple[Any, Any]:
            self.k = _torch.cat([self.k, k_new], dim=1)
            self.v = _torch.cat([self.v, v_new], dim=1)
            return self.k, self.v

    class _ToyCausalLM(_torch.nn.Module):  # type: ignore[misc]
        def __init__(self, vocab_size: int, dim: int) -> None:
            super().__init__()
            self.dim = dim
            self.embed = _torch.nn.Embedding(vocab_size, dim)
            self.q_proj = _torch.nn.Linear(dim, dim, bias=False)
            self.k_proj = _torch.nn.Linear(dim, dim, bias=False)
            self.v_proj = _torch.nn.Linear(dim, dim, bias=False)
            self.out_proj = _torch.nn.Linear(dim, vocab_size, bias=False)
            self.config = SimpleNamespace(is_encoder_decoder=False)

        def forward(
            self,
            input_ids: Any,
            past_key_values: _MutableKVCache | None = None,
            use_cache: bool = False,
        ) -> SimpleNamespace:
            x = self.embed(input_ids)
            k_new = self.k_proj(x)
            v_new = self.v_proj(x)
            if past_key_values is not None:
                k, v = past_key_values.update(k_new, v_new)
            else:
                k, v = k_new, v_new
                if use_cache:
                    past_key_values = _MutableKVCache(k, v)
            q = self.q_proj(x)
            scores = _torch.matmul(q, k.transpose(-1, -2)) / (self.dim**0.5)
            t_new, t_total = q.shape[1], k.shape[1]
            offset = t_total - t_new
            mask = _torch.full((t_new, t_total), float("-inf"))
            for i in range(t_new):
                mask[i, : offset + i + 1] = 0.0
            attn = _torch.softmax(scores + mask, dim=-1)
            ctx = _torch.matmul(attn, v)
            logits = self.out_proj(ctx)
            return SimpleNamespace(
                logits=logits, past_key_values=past_key_values if use_cache else None
            )


def _build_toy_model_and_tokenizer(vocab_size: int = 64, dim: int = 8) -> tuple[Any, Any, int, int]:
    import torch

    torch.manual_seed(0)
    yes_id, no_id = 2, 3

    class ToyTokenizer:
        def __call__(self, text: str, return_tensors: str = "pt") -> SimpleNamespace:
            ids = [self._id_for(w) for w in text.split()] or [0]
            return SimpleNamespace(input_ids=torch.tensor([ids], dtype=torch.long))

        def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
            return [self._id_for(w) for w in text.split()] or [0]

        def apply_chat_template(
            self,
            messages: list[dict[str, str]],
            *,
            add_generation_prompt: bool = True,
            tokenize: bool = False,
            **kwargs: object,
        ) -> str:
            system, user_context, assistant_ack, user_question = (m["content"] for m in messages)
            text = f"{system} {user_context} {assistant_ack} {user_question}"
            if add_generation_prompt:
                text += " GEN"
            return text

        @staticmethod
        def _id_for(word: str) -> int:
            lowered = word.lower()
            if lowered == "yes":
                return yes_id
            if lowered == "no":
                return no_id
            return (hash(word) % (vocab_size - 4)) + 4

    model = _ToyCausalLM(vocab_size, dim)
    model.eval()
    return model, ToyTokenizer(), yes_id, no_id


@requires_torch
def test_shared_prefill_matches_naive_fallback_numerically() -> None:
    from forecheck.inference.hf import HFBackend, HFBackendConfig

    model, tokenizer, _yes_id, _no_id = _build_toy_model_and_tokenizer()

    def fake_load(self: HFBackend, torch_mod: object) -> tuple[object, object, str]:
        return model, tokenizer, "cpu"

    shared_backend = HFBackend(
        HFBackendConfig(model_id="toy", shared_prefill=True, use_chat_template=False)
    )
    naive_backend = HFBackend(
        HFBackendConfig(model_id="toy", shared_prefill=False, use_chat_template=False)
    )
    shared_backend._load_model_and_tokenizer = fake_load.__get__(shared_backend)  # type: ignore[method-assign]
    naive_backend._load_model_and_tokenizer = fake_load.__get__(naive_backend)  # type: ignore[method-assign]

    context = make_context()
    dims = [RiskDimension.PROMPT_INJECTION_INFLUENCE, RiskDimension.FINANCIAL_COMMITMENT]

    shared_result = shared_backend.score(context, dims)
    naive_result = naive_backend.score(context, dims)

    assert shared_backend.capabilities.supports_shared_prefill is True
    for dim in dims:
        assert shared_result.scores[dim] == pytest.approx(naive_result.scores[dim], abs=1e-4)


@requires_torch
def test_shared_prefill_cache_copy_prevents_cross_question_contamination() -> None:
    """Reproduces the fixed bug: without copying the prefix cache per question, the
    second question's forward pass silently attends to the first question's tokens
    because DynamicCache-style ``update()`` mutates the shared cache object in place."""
    import torch

    from forecheck.inference.hf import HFBackend, HFBackendConfig, _log_odds
    from forecheck.inference.prompt import QUESTIONS
    from forecheck.inference.serialization import serialize_context

    model, tokenizer, yes_id, no_id = _build_toy_model_and_tokenizer()
    dims = [RiskDimension.PROMPT_INJECTION_INFLUENCE, RiskDimension.FINANCIAL_COMMITMENT]
    yes_ids, no_ids = {yes_id}, {no_id}
    context = make_context()
    rendered = serialize_context(context)
    prefix_ids = tokenizer(rendered.text).input_ids

    def naive_score(dim: RiskDimension) -> float:
        full_text = rendered.text + "\n\n" + QUESTIONS[dim]
        ids = tokenizer(full_text).input_ids
        out = model(ids, use_cache=False)
        return _log_odds(torch, out.logits[0, -1], yes_ids, no_ids)

    naive_scores = {dim: naive_score(dim) for dim in dims}

    buggy_scores: dict[RiskDimension, float] = {}
    prefix_out = model(prefix_ids, use_cache=True)
    base_past = prefix_out.past_key_values
    for dim in dims:
        q_ids = tokenizer("\n\n" + QUESTIONS[dim]).input_ids
        out = model(q_ids, past_key_values=base_past, use_cache=True)
        buggy_scores[dim] = _log_odds(torch, out.logits[0, -1], yes_ids, no_ids)

    assert buggy_scores[dims[0]] == pytest.approx(naive_scores[dims[0]], abs=1e-4)
    assert buggy_scores[dims[1]] != pytest.approx(naive_scores[dims[1]], abs=1e-4)

    def fake_load(self: HFBackend, torch_mod: object) -> tuple[object, object, str]:
        return model, tokenizer, "cpu"

    fixed_backend = HFBackend(
        HFBackendConfig(model_id="toy", shared_prefill=True, use_chat_template=False)
    )
    fixed_backend._load_model_and_tokenizer = fake_load.__get__(fixed_backend)  # type: ignore[method-assign]
    fixed_result = fixed_backend.score(context, dims)

    for dim in dims:
        assert fixed_result.scores[dim] == pytest.approx(naive_scores[dim], abs=1e-4)


@requires_torch
def test_strip_identity_shrinks_rendered_prompt_token_count() -> None:
    from forecheck.contracts import AgentIdentity, Principal
    from forecheck.inference.hf import HFBackend, HFBackendConfig

    model, tokenizer, _yes_id, _no_id = _build_toy_model_and_tokenizer()

    def fake_load(self: HFBackend, torch_mod: object) -> tuple[object, object, str]:
        return model, tokenizer, "cpu"

    context = make_context(
        principal=Principal(id="user-1", entitlements=["billing:refund:<=500", "billing:view"]),
        agent=AgentIdentity(id="agent-1", delegated_scopes=["billing:refund"]),
    )
    dims = [RiskDimension.FINANCIAL_COMMITMENT]

    full_backend = HFBackend(
        HFBackendConfig(model_id="toy", use_chat_template=False, strip_identity=False)
    )
    stripped_backend = HFBackend(
        HFBackendConfig(model_id="toy", use_chat_template=False, strip_identity=True)
    )
    full_backend._load_model_and_tokenizer = fake_load.__get__(full_backend)  # type: ignore[method-assign]
    stripped_backend._load_model_and_tokenizer = fake_load.__get__(stripped_backend)  # type: ignore[method-assign]

    full_result = full_backend.score(context, dims)
    stripped_result = stripped_backend.score(context, dims)

    assert stripped_result.prompt_tokens is not None and full_result.prompt_tokens is not None
    assert stripped_result.prompt_tokens < full_result.prompt_tokens


@requires_torch
def test_shared_prefill_chat_template_matches_naive_fallback_numerically() -> None:
    from forecheck.inference.hf import HFBackend, HFBackendConfig

    model, tokenizer, _yes_id, _no_id = _build_toy_model_and_tokenizer()

    def fake_load(self: HFBackend, torch_mod: object) -> tuple[object, object, str]:
        return model, tokenizer, "cpu"

    shared_backend = HFBackend(
        HFBackendConfig(model_id="toy", shared_prefill=True, use_chat_template=True)
    )
    naive_backend = HFBackend(
        HFBackendConfig(model_id="toy", shared_prefill=False, use_chat_template=True)
    )
    shared_backend._load_model_and_tokenizer = fake_load.__get__(shared_backend)  # type: ignore[method-assign]
    naive_backend._load_model_and_tokenizer = fake_load.__get__(naive_backend)  # type: ignore[method-assign]

    context = make_context()
    dims = [RiskDimension.PROMPT_INJECTION_INFLUENCE, RiskDimension.FINANCIAL_COMMITMENT]

    shared_result = shared_backend.score(context, dims)
    naive_result = naive_backend.score(context, dims)

    for dim in dims:
        assert shared_result.scores[dim] == pytest.approx(naive_result.scores[dim], abs=1e-4)


class _BoundaryMergingToyTokenizer:
    """Same ``>I`` boundary merge as ``_BoundaryMergingTokenizer`` in
    ``test_chat_template.py`` -- the second user turn's role marker (``>``) merges with
    an immediately following ``I`` in joint tokenization -- sized for the toy model's
    vocabulary, so a real ``HFBackend.score()`` call exercises the shared-cache branch
    for one dimension and the non-shared fallback branch for another in the same
    request."""

    def __init__(self, vocab_size: int, yes_id: int, no_id: int) -> None:
        self._vocab_size = vocab_size
        self._yes_id = yes_id
        self._no_id = no_id

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        add_generation_prompt: bool = True,
        tokenize: bool = False,
        **kwargs: object,
    ) -> str:
        system, user_context, assistant_ack, user_question = (m["content"] for m in messages)
        text = f"{system}|{user_context}|{assistant_ack}|>{user_question}"
        if add_generation_prompt:
            text += "|GEN"
        return text

    def __call__(self, text: str, return_tensors: str = "pt") -> SimpleNamespace:
        import torch

        return SimpleNamespace(input_ids=torch.tensor([self.encode(text)], dtype=torch.long))

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        stripped = text.strip().lower()
        if stripped == "yes":
            return [self._yes_id]
        if stripped == "no":
            return [self._no_id]
        ids: list[int] = []
        i = 0
        while i < len(text):
            if text[i : i + 2] == ">I":
                ids.append(self._id_for("<MERGED>"))
                i += 2
                continue
            ids.append(self._id_for(text[i]))
            i += 1
        return ids

    def _id_for(self, token: str) -> int:
        return (hash(token) % (self._vocab_size - 4)) + 4


@requires_torch
def test_score_falls_back_to_non_shared_for_a_question_with_an_unstable_boundary() -> None:
    """PROMPT_INJECTION_INFLUENCE ("Is...") hits the tokenizer's >I merge and falls
    back to a non-shared forward pass; FINANCIAL_COMMITMENT ("Does...") does not and
    uses the shared-cache branch -- both must still score correctly."""
    import torch

    from forecheck.inference.chat_template import render_full_chat_text
    from forecheck.inference.hf import HFBackend, HFBackendConfig, _log_odds
    from forecheck.inference.prompt import QUESTIONS
    from forecheck.inference.serialization import serialize_context

    vocab_size, dim = 64, 8
    model, _plain_tokenizer, yes_id, no_id = _build_toy_model_and_tokenizer(vocab_size, dim)
    tokenizer = _BoundaryMergingToyTokenizer(vocab_size, yes_id, no_id)

    def fake_load(self: HFBackend, torch_mod: object) -> tuple[object, object, str]:
        return model, tokenizer, "cpu"

    backend = HFBackend(
        HFBackendConfig(model_id="toy", shared_prefill=True, use_chat_template=True)
    )
    backend._load_model_and_tokenizer = fake_load.__get__(backend)  # type: ignore[method-assign]

    context = make_context()
    dims = [RiskDimension.PROMPT_INJECTION_INFLUENCE, RiskDimension.FINANCIAL_COMMITMENT]
    result = backend.score(context, dims)

    rendered = serialize_context(context)
    for question_dim in dims:
        full_text = render_full_chat_text(tokenizer, rendered.text, QUESTIONS[question_dim])
        full_ids = tokenizer.encode(full_text, add_special_tokens=False)
        ids = torch.tensor([full_ids], dtype=torch.long)
        out = model(ids, use_cache=False)
        expected = _log_odds(torch, out.logits[0, -1], {yes_id}, {no_id})
        assert result.scores[question_dim] == pytest.approx(expected, abs=1e-4)
