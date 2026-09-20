"""Shared factory for building minimal, valid :class:`LatentScenario` fixtures.

The default scenario returned by :func:`make_latent` is deliberately benign: every
risk dimension derives to ``NO`` or ``NOT_APPLICABLE``. Individual tests override just
the fields relevant to the behaviour under test.
"""

from __future__ import annotations

from typing import Any

from forecheck.contracts import (
    ActionOrigin,
    AuthorizationBasis,
    ContextGap,
    DestinationRelationship,
    DifficultyTier,
    LatentScenario,
    OperationKind,
    Sensitivity,
    SequencePattern,
    Stage,
    TrustLevel,
)
from forecheck.data.tools import get_tool

__all__ = ["make_latent"]


def make_latent(**overrides: Any) -> LatentScenario:
    defaults: dict[str, Any] = {
        "scenario_id": "test-scenario",
        "family_id": "test-family",
        "template_lineage": ["test-family"],
        "tool": get_tool("email.read_message"),
        "operation": OperationKind.READ,
        "principal_roles": ["employee"],
        "principal_entitlements": ["email.read"],
        "agent_delegated_scopes": ["email.read"],
        "required_scopes": ["email.read"],
        "authorization_basis": AuthorizationBasis.EXPLICIT,
        "action_origin": ActionOrigin.PRINCIPAL_REQUEST,
        "resource_sensitivity": Sensitivity.INTERNAL,
        "resource_reversible": True,
        "record_count": 1,
        "destination_present": False,
        "destination_relationship": DestinationRelationship.SELF,
        "destination_trust": TrustLevel.TRUSTED_TOOL,
        "stage": Stage.PRODUCTION,
        "change_freeze": False,
        "financial_amount": 0.0,
        "financial_currency": "USD",
        "financial_material_threshold": 100.0,
        "untrusted_content_present": False,
        "untrusted_content_contains_instruction": False,
        "authority_before": [],
        "authority_after": [],
        "policy_predicates": [],
        "policy_supplied": False,
        "sequence_pattern": SequencePattern.NONE,
        "trajectory_length": 0,
        "context_gaps": [ContextGap.NONE],
        "difficulty": DifficultyTier.EASY,
        "is_benign_hard_negative": False,
        "notes": "",
    }
    defaults.update(overrides)
    return LatentScenario(**defaults)
