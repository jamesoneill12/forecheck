"""Model/tokenizer loading shared by the HF backend and the training loop.

Some checkpoints register in transformers only under the ``AutoModelForImageTextToText``
mapping, even when used text-only, because their architecture always carries a vision
tower. ``load_class="auto"`` tries the causal-LM mapping first and falls back to the
image-text-to-text mapping on failure, so callers do not need to know in advance which
mapping a given ``base_id`` needs; the resulting model's ``.logits`` shape at the final
position is unchanged either way. The fallback loads the *full* model, including its
vision tower -- there is no public, architecture-independent transformers API to load
only the text tower's weights.
"""

from __future__ import annotations

from typing import Any, Literal

__all__ = ["LoadClass", "load_model", "load_tokenizer"]

LoadClass = Literal["auto", "causal_lm", "image_text_to_text"]


def load_model(model_id: str, *, load_class: LoadClass = "auto", **kwargs: Any) -> Any:
    """Load a causal-LM (or image-text-to-text) model for candidate-logit scoring."""
    from transformers import AutoModelForCausalLM

    if load_class == "causal_lm":
        return AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
    if load_class == "image_text_to_text":
        from transformers import AutoModelForImageTextToText

        return AutoModelForImageTextToText.from_pretrained(model_id, **kwargs)
    try:
        return AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
    except ValueError:
        from transformers import AutoModelForImageTextToText

        return AutoModelForImageTextToText.from_pretrained(model_id, **kwargs)


def load_tokenizer(model_id: str, *, revision: str | None = None) -> Any:
    """Load a tokenizer, falling back to an ``AutoProcessor``'s tokenizer for models
    that only ship a processor (typical of multimodal checkpoints)."""
    from transformers import AutoTokenizer

    try:
        return AutoTokenizer.from_pretrained(model_id, revision=revision)
    except ValueError:
        from transformers import AutoProcessor

        processor = AutoProcessor.from_pretrained(model_id, revision=revision)
        return getattr(processor, "tokenizer", processor)
