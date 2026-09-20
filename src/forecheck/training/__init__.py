"""LoRA/QLoRA fine-tuning for the forecheck candidate-logit backend.

This package trains against exactly the prompt contract and candidate-token
resolution used at serve time (:mod:`forecheck.inference.prompt`,
:mod:`forecheck.inference.serialization`, :mod:`forecheck.inference.hf`), so a
checkpoint trained here scores identically under :class:`~forecheck.inference.hf.HFBackend`.
Everything that touches ``torch``/``transformers``/``peft`` imports those lazily so this
package always imports cleanly when the ``train`` extra is not installed.
"""

from __future__ import annotations

from forecheck.training.config import TrainConfig

__all__ = ["TrainConfig"]
