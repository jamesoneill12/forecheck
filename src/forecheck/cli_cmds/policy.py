"""``forecheck policy check <bundle.yaml>``."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from forecheck.policies.loader import hash_bundle, load_bundle_file

__all__ = ["policy_app"]

policy_app = typer.Typer(no_args_is_help=True, help="Policy bundle utilities.")


@policy_app.command("check")
def check(bundle_path: Annotated[Path, typer.Argument(exists=True)]) -> None:
    """Load and validate a policy bundle, then print its identity, hash and rule count."""
    bundle = load_bundle_file(bundle_path)
    digest = hash_bundle(bundle)
    typer.echo(
        f"bundle_id={bundle.bundle_id} version={bundle.version} dsl_version={bundle.dsl_version}"
    )
    typer.echo(f"default_decision={bundle.default_decision.value} rules={len(bundle.rules)}")
    typer.echo(f"hash={digest}")
