"""Generate paper figures from the synthetic-v2 markdown result reports.

Reads docs/results/synthetic-v2/**/*.md (read-only) and writes vector PDFs to
paper/figures/. Run with: uv run python scripts/paper_figures.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "docs" / "results" / "synthetic-v2"
FIGURES_DIR = REPO_ROOT / "paper" / "figures"

COLORS = {
    "orange": "#E69F00",
    "sky_blue": "#56B4E9",
    "bluish_green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "reddish_purple": "#CC79A7",
    "black": "#000000",
}

DIM_ORDER = [
    "prompt_injection_influence",
    "unauthorized_scope",
    "sensitive_data_exposure",
    "untrusted_destination",
    "privilege_escalation",
    "destructive_or_irreversible_action",
    "financial_commitment",
    "external_communication",
    "policy_conflict",
    "suspicious_action_sequence",
    "insufficient_context",
]

DIM_SHORT = {
    "prompt_injection_influence": "prompt\ninjection",
    "unauthorized_scope": "unauthorized\nscope",
    "sensitive_data_exposure": "sensitive\ndata",
    "untrusted_destination": "untrusted\ndest.",
    "privilege_escalation": "privilege\nescalation",
    "destructive_or_irreversible_action": "destructive/\nirreversible",
    "financial_commitment": "financial\ncommitment",
    "external_communication": "external\ncomm.",
    "policy_conflict": "policy\nconflict",
    "suspicious_action_sequence": "suspicious\nsequence",
    "insufficient_context": "insufficient\ncontext",
}

RC = {
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 6.5,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
}


def log(msg: str) -> None:
    print(msg)


def _split_row(line: str) -> list[str]:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return cells


def _to_float(cell: str) -> float | None:
    cell = cell.strip()
    if cell in ("n/a", "", "---"):
        return None
    cell = cell.rstrip("%")
    try:
        return float(cell)
    except ValueError:
        return None


def parse_markdown_table(path: Path, header_marker: str) -> list[dict[str, str]]:
    """Parse the first markdown table whose header row contains header_marker."""
    text = path.read_text()
    lines = text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and header_marker in line:
            header_idx = i
            break
    if header_idx is None:
        raise ValueError(f"no table with header {header_marker!r} found in {path}")
    header = [h.strip() for h in _split_row(lines[header_idx])]
    rows: list[dict[str, str]] = []
    for line in lines[header_idx + 2 :]:
        if not line.strip().startswith("|"):
            break
        cells = _split_row(line)
        if len(cells) != len(header):
            continue
        rows.append(dict(zip(header, cells, strict=True)))
    return rows


def parse_dimension_table(path: Path) -> dict[str, dict[str, float | None]]:
    rows = parse_markdown_table(path, "dimension")
    out: dict[str, dict[str, float | None]] = {}
    for row in rows:
        dim = row["dimension"]
        out[dim] = {k: _to_float(v) for k, v in row.items() if k != "dimension"}
    return out


def parse_stacking_table(path: Path) -> list[dict[str, str | float | None]]:
    text = path.read_text()
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "## Multi-policy stacking":
            start = i
            break
    if start is None:
        raise ValueError(f"no '## Multi-policy stacking' section in {path}")
    sub = "\n".join(lines[start:])
    tmp = path.with_suffix(".tmp-stacking")
    tmp.write_text(sub)
    try:
        rows = parse_markdown_table(tmp, "strategy")
    finally:
        tmp.unlink()
    out = []
    for row in rows:
        out.append(
            {
                "k": int(row["k"]),
                "strategy": row["strategy"],
                "fpr": _to_float(row["fpr"]),
                "fnr": _to_float(row["fnr"]),
            }
        )
    return out


def parse_approval_reweighted(path: Path) -> list[dict[str, float | None]]:
    text = path.read_text()
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "### Reweighted":
            start = i
            break
    if start is None:
        raise ValueError(f"no '### Reweighted' section in {path}")
    sub = "\n".join(lines[start:])
    tmp = path.with_suffix(".tmp-approval")
    tmp.write_text(sub)
    try:
        rows = parse_markdown_table(tmp, "budget")
    finally:
        tmp.unlink()
    out = []
    for row in rows:
        budget = _to_float(row["budget"])  # percent
        out.append(
            {
                "budget_pct": budget,
                "eliminated": _to_float(row["approvals eliminated"]),
            }
        )
    return out


def savefig(fig: plt.Figure, name: str) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FIGURES_DIR / name
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    log(f"wrote {out_path.relative_to(REPO_ROOT)}")


def fig_identity_ablation() -> None:
    full = parse_dimension_table(RESULTS_DIR / "decoder-2b" / "heldout_family-report.md")
    stripped = parse_dimension_table(
        RESULTS_DIR / "decoder-2b" / "heldout_family-noid-report.md"
    )
    rule = parse_dimension_table(
        RESULTS_DIR / "decoder-2b" / "rule_baseline" / "heldout_family-report.md"
    )

    log("=== fig_identity_ablation ===")
    dims = DIM_ORDER
    full_auprc = [full[d]["auprc"] for d in dims]
    stripped_auprc = [stripped[d]["auprc"] for d in dims]
    rule_auprc = [rule[d]["auprc"] for d in dims]
    pos_rate = [full[d]["positive_rate"] for d in dims]
    for d, f, s, r, p in zip(dims, full_auprc, stripped_auprc, rule_auprc, pos_rate, strict=True):
        log(f"  {d}: full={f:.4f} stripped={s:.4f} rule={r:.4f} pos_rate={p:.4f}")

    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(5.5, 2.6))
        x = range(len(dims))
        width = 0.26
        ax.bar(
            [i - width for i in x], full_auprc, width, label="Decoder 2B v2 (full)",
            color=COLORS["blue"],
        )
        ax.bar(
            x, stripped_auprc, width, label="Decoder 2B v2 (identity-stripped)",
            color=COLORS["vermillion"],
        )
        ax.bar(
            [i + width for i in x], rule_auprc, width, label="Rule baseline",
            color=COLORS["bluish_green"],
        )
        for i, p in enumerate(pos_rate):
            ax.plot(
                [i - 1.5 * width, i + 1.5 * width], [p, p], linestyle="--",
                color=COLORS["black"], linewidth=0.8,
                label="Positive rate (chance)" if i == 0 else None,
            )
        ax.set_xticks(list(x))
        ax.set_xticklabels([DIM_SHORT[d] for d in dims], rotation=35, ha="right", fontsize=7)
        ax.set_ylabel("AUPRC")
        ax.set_ylim(0, 1.05)
        ax.legend(loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.32), frameon=False)
        savefig(fig, "fig_identity_ablation.pdf")


def fig_policy_generalisation() -> None:
    splits = ["test", "heldout_family", "heldout_policy_kind", "heldout_policy_phrasing"]
    split_labels = ["test", "heldout\nfamily", "heldout\npolicy kind", "heldout\nphrasing"]

    def get(arm: str, split: str) -> float:
        d = parse_dimension_table(RESULTS_DIR / arm / f"{split}-report.md")
        return d["policy_conflict"]["auprc"]

    def get_rule(arm: str, split: str) -> float:
        d = parse_dimension_table(RESULTS_DIR / arm / "rule_baseline" / f"{split}-report.md")
        return d["policy_conflict"]["auprc"]

    v3 = [get("decoder-2b-v3", s) for s in splits]
    v4 = [get("decoder-2b-v4", s) for s in splits]
    v5 = [get("decoder-2b-v5", s) for s in splits]
    b8 = [get("decoder-8b-v4", s) for s in splits]
    rule = [get_rule("decoder-2b-v4", s) for s in splits]

    log("=== fig_policy_generalisation ===")
    for s, a, b, c, d, r in zip(splits, v3, v4, v5, b8, rule, strict=True):
        log(f"  {s}: v3={a:.4f} v4={b:.4f} v5={c:.4f} 8b_v4={d:.4f} rule={r:.4f}")

    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(5.5, 2.6))
        x = list(range(len(splits)))
        width = 0.19
        ax.bar([i - 1.5 * width for i in x], v3, width, label="v3 (2B)",
               color=COLORS["sky_blue"])
        ax.bar([i - 0.5 * width for i in x], v4, width, label="v4 (2B)",
               color=COLORS["orange"])
        ax.bar([i + 0.5 * width for i in x], v5, width, label="v5 (2B, 30 kinds)",
               color=COLORS["bluish_green"])
        ax.bar([i + 1.5 * width for i in x], b8, width, label="v4 (8B)",
               color=COLORS["reddish_purple"])
        ax.plot(x, rule, color=COLORS["black"], marker="o",
                 markersize=3, linewidth=1.0, label="Rule baseline")
        ax.set_xticks(x)
        ax.set_xticklabels(split_labels)
        ax.set_ylabel("policy_conflict AUPRC")
        ax.set_ylim(0, 1.05)
        ax.legend(loc="lower left", frameon=False, ncol=3)
        savefig(fig, "fig_policy_generalisation.pdf")


def fig_stacking() -> None:
    dec_path = RESULTS_DIR / "decoder-2b" / "heldout_family-stacking-report.md"
    enc_path = RESULTS_DIR / "encoder-granite-embedding-r2" / "heldout_family-stacking-report.md"
    dec_rows = parse_stacking_table(dec_path)
    enc_rows = parse_stacking_table(enc_path)

    def series(rows: list[dict], strategy: str, field: str) -> tuple[list[int], list[float]]:
        pts = [(r["k"], r[field]) for r in rows if r["strategy"] == strategy]
        pts.sort()
        return [p[0] for p in pts], [p[1] for p in pts]

    log("=== fig_stacking ===")
    for strat in ("independent", "joint", "expected_cost_joint"):
        ks, fprs = series(dec_rows, strat, "fpr")
        _, fnrs = series(dec_rows, strat, "fnr")
        log(f"  decoder {strat}: fpr={fprs}")
        log(f"  decoder {strat}: fnr={fnrs}")
    enc_ks, enc_fprs = series(enc_rows, "expected_cost_joint", "fpr")
    _, enc_fnrs = series(enc_rows, "expected_cost_joint", "fnr")
    log(f"  encoder expected_cost_joint: fpr={enc_fprs}")
    log(f"  encoder expected_cost_joint: fnr={enc_fnrs}")

    strat_colors = {
        "independent": COLORS["vermillion"],
        "joint": COLORS["orange"],
        "expected_cost_joint": COLORS["blue"],
    }
    strat_labels = {
        "independent": "independent",
        "joint": "joint",
        "expected_cost_joint": "expected_cost_joint",
    }

    with plt.rc_context(RC):
        fig, (ax_fpr, ax_fnr) = plt.subplots(1, 2, figsize=(5.5, 2.4), sharex=True)
        for strat in ("independent", "joint", "expected_cost_joint"):
            ks, fprs = series(dec_rows, strat, "fpr")
            _, fnrs = series(dec_rows, strat, "fnr")
            ax_fpr.plot(ks, fprs, marker="o", markersize=2.5, linewidth=1.0,
                        color=strat_colors[strat], label=strat_labels[strat])
            ax_fnr.plot(ks, fnrs, marker="o", markersize=2.5, linewidth=1.0,
                        color=strat_colors[strat], label=strat_labels[strat])
        ax_fpr.plot(enc_ks, enc_fprs, linestyle=":", color=COLORS["reddish_purple"],
                    linewidth=1.2, label="encoder expected_cost_joint")
        ax_fnr.plot(enc_ks, enc_fnrs, linestyle=":", color=COLORS["reddish_purple"],
                    linewidth=1.2, label="encoder expected_cost_joint")
        ax_fpr.set_xlabel("$k$ stacked policies")
        ax_fnr.set_xlabel("$k$ stacked policies")
        ax_fpr.set_ylabel("FPR")
        ax_fnr.set_ylabel("FNR")
        ax_fpr.set_ylim(0, 1.02)
        ax_fnr.set_ylim(0, 0.3)
        ax_fnr.legend(loc="upper right", frameon=False)
        savefig(fig, "fig_stacking.pdf")


def fig_approval_curve() -> None:
    v2 = parse_approval_reweighted(RESULTS_DIR / "decoder-2b" / "heldout_family-approval-report.md")
    v4_hf = parse_approval_reweighted(
        RESULTS_DIR / "decoder-2b-v4" / "heldout_family-approval-report.md"
    )
    v4_test = parse_approval_reweighted(RESULTS_DIR / "decoder-2b-v4" / "test-approval-report.md")

    log("=== fig_approval_curve ===")
    for name, rows in (("v2 heldout_family", v2), ("v4 heldout_family", v4_hf), ("v4 test", v4_test)):
        for r in rows:
            log(f"  {name}: budget={r['budget_pct']}% eliminated={r['eliminated']}")

    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(3.3, 2.6))
        for rows, label, color, marker in (
            (v2, "v2, heldout_family", COLORS["blue"], "o"),
            (v4_hf, "v4, heldout_family", COLORS["orange"], "s"),
            (v4_test, "v4, test", COLORS["bluish_green"], "^"),
        ):
            budgets = [r["budget_pct"] for r in rows]
            elim = [r["eliminated"] for r in rows]
            ax.plot(budgets, elim, marker=marker, markersize=3, linewidth=1.0,
                    color=color, label=label)
        ax.set_xscale("log")
        ax.set_xlabel("incident budget (%, reweighted to 5%)")
        ax.set_ylabel("approvals eliminated")
        ax.set_ylim(0, 1.05)
        ax.legend(loc="lower right", frameon=False)
        savefig(fig, "fig_approval_curve.pdf")


def fig_self_judgment() -> None:
    agent = parse_dimension_table(RESULTS_DIR / "agent-self-8b" / "heldout_family-report.md")
    agent_stripped = parse_dimension_table(
        RESULTS_DIR / "agent-self-8b" / "heldout_family-noid-report.md"
    )
    decoder = parse_dimension_table(RESULTS_DIR / "decoder-2b-v4" / "heldout_family-report.md")

    log("=== fig_self_judgment ===")
    dims = DIM_ORDER
    agent_auprc = [agent[d]["auprc"] for d in dims]
    agent_s_auprc = [agent_stripped[d]["auprc"] for d in dims]
    decoder_auprc = [decoder[d]["auprc"] for d in dims]
    pos_rate = [agent[d]["positive_rate"] for d in dims]
    for d, a, s, dec, p in zip(dims, agent_auprc, agent_s_auprc, decoder_auprc, pos_rate, strict=True):
        log(f"  {d}: agent8b={a:.4f} agent8b_stripped={s:.4f} decoder_v4={dec:.4f} pos_rate={p:.4f}")

    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(5.5, 2.6))
        x = range(len(dims))
        width = 0.26
        ax.bar([i - width for i in x], agent_auprc, width, label="Agent-self 8B",
               color=COLORS["vermillion"])
        ax.bar(x, agent_s_auprc, width, label="Agent-self 8B, stripped",
               color=COLORS["reddish_purple"])
        ax.bar([i + width for i in x], decoder_auprc, width, label="Decoder 2B v4 (checker)",
               color=COLORS["blue"])
        for i, p in enumerate(pos_rate):
            ax.plot([i - 1.5 * width, i + 1.5 * width], [p, p], linestyle="--",
                    color=COLORS["black"], linewidth=0.8,
                    label="Positive rate (chance)" if i == 0 else None)
        ax.set_xticks(list(x))
        ax.set_xticklabels([DIM_SHORT[d] for d in dims], rotation=35, ha="right", fontsize=7)
        ax.set_ylabel("AUPRC")
        ax.set_ylim(0, 1.05)
        ax.legend(loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.32), frameon=False)
        savefig(fig, "fig_self_judgment.pdf")


def main() -> None:
    fig_identity_ablation()
    fig_policy_generalisation()
    fig_stacking()
    fig_approval_curve()
    fig_self_judgment()


if __name__ == "__main__":
    main()
