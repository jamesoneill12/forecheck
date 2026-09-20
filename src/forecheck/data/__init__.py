"""Synthetic-data construction: tools, labeling, rendering, contrastive pairs, splits."""

from __future__ import annotations

from forecheck.data.contrastive import AXIS_FLIPPERS, contrastive_pair_id, make_pair
from forecheck.data.io import (
    build_manifest,
    read_jsonl,
    sha256_file,
    verify_manifest,
    write_jsonl,
    write_manifests,
)
from forecheck.data.labeling import LABEL_DERIVATION_RULES, derive_labels, evaluate_predicate
from forecheck.data.rendering import OfflineTemplateRenderer, SurfaceText, assemble_action_context
from forecheck.data.splitting import (
    DEFAULT_SALT,
    SPLIT_RATIOS,
    IneligibleForSplitError,
    LeakageError,
    assert_no_leakage,
    assign_split,
    compute_group_key,
    split_examples,
)
from forecheck.data.tools import TOOL_CATALOGUE, get_tool, tools_for_family

__all__ = [
    "AXIS_FLIPPERS",
    "DEFAULT_SALT",
    "LABEL_DERIVATION_RULES",
    "SPLIT_RATIOS",
    "TOOL_CATALOGUE",
    "IneligibleForSplitError",
    "LeakageError",
    "OfflineTemplateRenderer",
    "SurfaceText",
    "assemble_action_context",
    "assert_no_leakage",
    "assign_split",
    "build_manifest",
    "compute_group_key",
    "contrastive_pair_id",
    "derive_labels",
    "evaluate_predicate",
    "get_tool",
    "make_pair",
    "read_jsonl",
    "sha256_file",
    "split_examples",
    "tools_for_family",
    "verify_manifest",
    "write_jsonl",
    "write_manifests",
]
