"""forecheck: a calibrated pre-execution risk model for AI-agent actions.

Two layers, deliberately separate:

* :mod:`forecheck.inference` scores atomic, descriptive risk dimensions.
* :mod:`forecheck.policies` maps those scores, deterministically, to
  ``ALLOW`` / ``REVIEW`` / ``DENY``.

The model never decides. The policy engine never guesses.
"""

from __future__ import annotations

from forecheck.version import __version__

__all__ = ["__version__"]
