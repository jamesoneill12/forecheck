from __future__ import annotations

import builtins
import importlib.util
from types import SimpleNamespace

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


@requires_torch
def test_log_odds_prefers_yes_when_yes_logits_dominate() -> None:
    import torch

    from forecheck.inference.hf import _log_odds

    logits = torch.zeros(10)
    logits[0] = 5.0
    logits[1] = -5.0
    assert _log_odds(torch, logits, {0}, {1}) > 0


@requires_torch
def test_shared_prefill_matches_naive_fallback_numerically() -> None:
    import torch

    from forecheck.inference.hf import HFBackend, HFBackendConfig

    torch.manual_seed(0)
    vocab_size = 64
    dim = 8
    yes_id, no_id = 2, 3

    class ToyCausalLM(torch.nn.Module):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.embed = torch.nn.Embedding(vocab_size, dim)
            self.q_proj = torch.nn.Linear(dim, dim, bias=False)
            self.k_proj = torch.nn.Linear(dim, dim, bias=False)
            self.v_proj = torch.nn.Linear(dim, dim, bias=False)
            self.out_proj = torch.nn.Linear(dim, vocab_size, bias=False)
            self.config = SimpleNamespace(is_encoder_decoder=False)

        def forward(
            self,
            input_ids: torch.Tensor,
            past_key_values: object = None,
            use_cache: bool = False,
        ) -> SimpleNamespace:
            x = self.embed(input_ids)
            k_new = self.k_proj(x)
            v_new = self.v_proj(x)
            if past_key_values is not None:
                past_k, past_v = past_key_values  # type: ignore[misc]
                k = torch.cat([past_k, k_new], dim=1)
                v = torch.cat([past_v, v_new], dim=1)
            else:
                k, v = k_new, v_new
            q = self.q_proj(x)
            scores = torch.matmul(q, k.transpose(-1, -2)) / (dim**0.5)
            t_new, t_total = q.shape[1], k.shape[1]
            offset = t_total - t_new
            mask = torch.full((t_new, t_total), float("-inf"))
            for i in range(t_new):
                mask[i, : offset + i + 1] = 0.0
            attn = torch.softmax(scores + mask, dim=-1)
            ctx = torch.matmul(attn, v)
            logits = self.out_proj(ctx)
            new_past = (k, v) if use_cache else None
            return SimpleNamespace(logits=logits, past_key_values=new_past)

    class ToyTokenizer:
        def __call__(self, text: str, return_tensors: str = "pt") -> SimpleNamespace:
            ids = [self._id_for(w) for w in text.split()] or [0]
            return SimpleNamespace(input_ids=torch.tensor([ids], dtype=torch.long))

        def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
            return [self._id_for(w) for w in text.split()] or [0]

        @staticmethod
        def _id_for(word: str) -> int:
            lowered = word.lower()
            if lowered == "yes":
                return yes_id
            if lowered == "no":
                return no_id
            return (hash(word) % (vocab_size - 4)) + 4

    model = ToyCausalLM()
    model.eval()
    tokenizer = ToyTokenizer()

    def fake_load(self: HFBackend, torch_mod: object) -> tuple[object, object, str]:
        return model, tokenizer, "cpu"

    shared_backend = HFBackend(HFBackendConfig(model_id="toy", shared_prefill=True))
    naive_backend = HFBackend(HFBackendConfig(model_id="toy", shared_prefill=False))
    shared_backend._load_model_and_tokenizer = fake_load.__get__(shared_backend)  # type: ignore[method-assign]
    naive_backend._load_model_and_tokenizer = fake_load.__get__(naive_backend)  # type: ignore[method-assign]

    context = make_context()
    dims = [RiskDimension.PROMPT_INJECTION_INFLUENCE, RiskDimension.FINANCIAL_COMMITMENT]

    shared_result = shared_backend.score(context, dims)
    naive_result = naive_backend.score(context, dims)

    assert shared_backend.capabilities.supports_shared_prefill is True
    for dim in dims:
        assert shared_result.scores[dim] == pytest.approx(naive_result.scores[dim], abs=1e-4)
