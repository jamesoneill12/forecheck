"""Generate paper figures from the synthetic-v2 markdown result reports.

Reads docs/results/synthetic-v2/**/*.md (read-only) and writes vector PDFs to
paper/figures/. Run with: uv run python scripts/paper_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from injecagent_pair_audit import load_export, load_scores

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "docs" / "results" / "synthetic-v2"
JUDGE_README = REPO_ROOT / "docs" / "results" / "judge" / "README.md"
AGENTDOJO_DIR = REPO_ROOT / "docs" / "results" / "agentdojo"
FIGURES_DIR = REPO_ROOT / "paper" / "figures"
INJECAGENT_DIR = Path("/tmp/fc-injecagent")

BODY_RC = {
    "font.size": 7,
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "DejaVu Sans"],
    "axes.titlesize": 7,
    "axes.labelsize": 7.5,
    "xtick.labelsize": 6.5,
    "ytick.labelsize": 6.5,
    "legend.fontsize": 6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
}

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
    v2_full = parse_dimension_table(RESULTS_DIR / "decoder-2b" / "heldout_family-report.md")
    v2_stripped = parse_dimension_table(
        RESULTS_DIR / "decoder-2b" / "heldout_family-noid-report.md"
    )
    v2_rule = parse_dimension_table(
        RESULTS_DIR / "decoder-2b" / "rule_baseline" / "heldout_family-report.md"
    )
    v4_full = parse_dimension_table(RESULTS_DIR / "decoder-2b-v4" / "heldout_family-report.md")
    v4_stripped = parse_dimension_table(
        RESULTS_DIR / "decoder-2b-v4" / "heldout_family-noid-report.md"
    )
    v4_trained_stripped = parse_dimension_table(
        RESULTS_DIR / "decoder-2b-v4-noid" / "heldout_family-report.md"
    )

    log("=== fig_identity_ablation ===")
    dims = DIM_ORDER

    def series(table: dict, key: str = "auprc") -> list[float]:
        return [table[d][key] for d in dims]

    v2_full_a, v2_stripped_a, v2_rule_a = series(v2_full), series(v2_stripped), series(v2_rule)
    v4_full_a, v4_stripped_a = series(v4_full), series(v4_stripped)
    v4_trained_stripped_a = series(v4_trained_stripped)
    pos_rate = series(v2_full, "positive_rate")
    for d, f, s, r, f4, s4, ts4, p in zip(
        dims,
        v2_full_a,
        v2_stripped_a,
        v2_rule_a,
        v4_full_a,
        v4_stripped_a,
        v4_trained_stripped_a,
        pos_rate,
        strict=True,
    ):
        log(
            f"  {d}: v2_full={f:.4f} v2_stripped={s:.4f} rule={r:.4f} "
            f"v4_full={f4:.4f} v4_stripped={s4:.4f} v4_trained_stripped={ts4:.4f} "
            f"pos_rate={p:.4f}"
        )

    with plt.rc_context(RC):
        fig, (ax_v2, ax_v4) = plt.subplots(1, 2, figsize=(8.0, 2.6), sharey=True)
        x = range(len(dims))
        width = 0.26
        ax_v2.bar([i - width for i in x], v2_full_a, width, label="Full", color=COLORS["blue"])
        ax_v2.bar(x, v2_stripped_a, width, label="Identity-stripped", color=COLORS["vermillion"])
        ax_v2.bar(
            [i + width for i in x],
            v2_rule_a,
            width,
            label="Rule baseline",
            color=COLORS["bluish_green"],
        )
        for i, p in enumerate(pos_rate):
            ax_v2.plot(
                [i - 1.5 * width, i + 1.5 * width],
                [p, p],
                linestyle="--",
                color=COLORS["black"],
                linewidth=0.8,
                label="Positive rate (chance)" if i == 0 else None,
            )
        ax_v2.set_xticks(list(x))
        ax_v2.set_xticklabels([DIM_SHORT[d] for d in dims], rotation=35, ha="right", fontsize=7)
        ax_v2.set_ylabel("AUPRC")
        ax_v2.set_ylim(0, 1.05)
        ax_v2.set_title("Decoder 2B v2", fontsize=8)

        width2 = 0.26
        ax_v4.bar(
            [i - width2 for i in x],
            v4_full_a,
            width2,
            label="Full (v4)",
            color=COLORS["blue"],
        )
        ax_v4.bar(
            x,
            v4_stripped_a,
            width2,
            label="Identity-stripped (v4)",
            color=COLORS["vermillion"],
        )
        ax_v4.bar(
            [i + width2 for i in x],
            v4_trained_stripped_a,
            width2,
            label="Trained stripped (v4)",
            color=COLORS["reddish_purple"],
        )
        for i, p in enumerate(pos_rate):
            ax_v4.plot(
                [i - 1.5 * width2, i + 1.5 * width2],
                [p, p],
                linestyle="--",
                color=COLORS["black"],
                linewidth=0.8,
            )
        ax_v4.set_xticks(list(x))
        ax_v4.set_xticklabels([DIM_SHORT[d] for d in dims], rotation=35, ha="right", fontsize=7)
        ax_v4.set_title("Decoder 2B v4", fontsize=8)

        handles, labels = ax_v2.get_legend_handles_labels()
        v4_handles, v4_labels = ax_v4.get_legend_handles_labels()
        handles += v4_handles[:3]
        labels += v4_labels[:3]
        fig.legend(
            handles,
            labels,
            loc="upper center",
            ncol=3,
            bbox_to_anchor=(0.5, 1.22),
            frameon=False,
        )
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
        ax.bar([i - 1.5 * width for i in x], v3, width, label="v3 (2B)", color=COLORS["sky_blue"])
        ax.bar([i - 0.5 * width for i in x], v4, width, label="v4 (2B)", color=COLORS["orange"])
        ax.bar(
            [i + 0.5 * width for i in x],
            v5,
            width,
            label="v5 (2B, 30 kinds)",
            color=COLORS["bluish_green"],
        )
        ax.bar(
            [i + 1.5 * width for i in x], b8, width, label="v4 (8B)", color=COLORS["reddish_purple"]
        )
        ax.plot(
            x,
            rule,
            color=COLORS["black"],
            marker="o",
            markersize=3,
            linewidth=1.0,
            label="Rule baseline",
        )
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
            ax_fpr.plot(
                ks,
                fprs,
                marker="o",
                markersize=2.5,
                linewidth=1.0,
                color=strat_colors[strat],
                label=strat_labels[strat],
            )
            ax_fnr.plot(
                ks,
                fnrs,
                marker="o",
                markersize=2.5,
                linewidth=1.0,
                color=strat_colors[strat],
                label=strat_labels[strat],
            )
        ax_fpr.plot(
            enc_ks,
            enc_fprs,
            linestyle=":",
            color=COLORS["reddish_purple"],
            linewidth=1.2,
            label="encoder expected_cost_joint",
        )
        ax_fnr.plot(
            enc_ks,
            enc_fnrs,
            linestyle=":",
            color=COLORS["reddish_purple"],
            linewidth=1.2,
            label="encoder expected_cost_joint",
        )
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
    for name, rows in (
        ("v2 heldout_family", v2),
        ("v4 heldout_family", v4_hf),
        ("v4 test", v4_test),
    ):
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
            ax.plot(
                budgets, elim, marker=marker, markersize=3, linewidth=1.0, color=color, label=label
            )
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
    for d, a, s, dec, p in zip(
        dims, agent_auprc, agent_s_auprc, decoder_auprc, pos_rate, strict=True
    ):
        log(
            f"  {d}: agent8b={a:.4f} agent8b_stripped={s:.4f} decoder_v4={dec:.4f} pos_rate={p:.4f}"
        )

    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(5.5, 2.6))
        x = range(len(dims))
        width = 0.26
        ax.bar(
            [i - width for i in x],
            agent_auprc,
            width,
            label="Agent-self 8B",
            color=COLORS["vermillion"],
        )
        ax.bar(
            x, agent_s_auprc, width, label="Agent-self 8B, stripped", color=COLORS["reddish_purple"]
        )
        ax.bar(
            [i + width for i in x],
            decoder_auprc,
            width,
            label="Decoder 2B v4 (checker)",
            color=COLORS["blue"],
        )
        for i, p in enumerate(pos_rate):
            ax.plot(
                [i - 1.5 * width, i + 1.5 * width],
                [p, p],
                linestyle="--",
                color=COLORS["black"],
                linewidth=0.8,
                label="Positive rate (chance)" if i == 0 else None,
            )
        ax.set_xticks(list(x))
        ax.set_xticklabels([DIM_SHORT[d] for d in dims], rotation=35, ha="right", fontsize=7)
        ax.set_ylabel("AUPRC")
        ax.set_ylim(0, 1.05)
        ax.legend(loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.32), frameon=False)
        savefig(fig, "fig_self_judgment.pdf")


def fig_judge_agreement() -> None:
    rows = parse_markdown_table(JUDGE_README, "kappa")
    pairs = [(row["dimension"], _to_float(row["kappa"])) for row in rows]
    pairs.sort(key=lambda p: p[1])

    log("=== fig_judge_agreement ===")
    for dim, kappa in pairs:
        log(f"  {dim}: kappa={kappa:.4f}")

    labels = [DIM_SHORT[d].replace("\n", " ") for d, _ in pairs]
    kappas = [k for _, k in pairs]

    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(5.5, 3.0))
        y = range(len(labels))
        ax.barh(list(y), kappas, color=COLORS["blue"])
        ax.axvline(
            0.7,
            color=COLORS["bluish_green"],
            linestyle="--",
            linewidth=1.0,
            label="recoverable (0.7)",
        )
        ax.axvline(
            0.2,
            color=COLORS["vermillion"],
            linestyle="--",
            linewidth=1.0,
            label="not recoverable (0.2)",
        )
        ax.set_yticks(list(y))
        ax.set_yticklabels(labels)
        ax.set_xlabel(r"yes-vs-not-yes $\kappa$ (generator label vs.\ blind LLM judge)")
        ax.set_xlim(0, 1.0)
        ax.legend(loc="lower right", frameon=False)
        savefig(fig, "fig_judge_agreement.pdf")


def fig_agentdojo() -> None:
    dims = ["prompt_injection_influence", "unauthorized_scope", "policy_conflict"]
    arms = [
        ("rule-baseline-report.md", "Rule baseline", COLORS["bluish_green"]),
        ("decoder-2b-v4-report.md", "Decoder 2B v4", COLORS["blue"]),
        ("decoder-2b-v4-strip-report.md", "2B v4, eval-stripped", COLORS["vermillion"]),
        ("decoder-8b-v4-report.md", "Decoder 8B v4", COLORS["reddish_purple"]),
        ("decoder-2b-v6-report.md", "Decoder 2B v6", COLORS["sky_blue"]),
        ("decoder-8b-v6-report.md", "Decoder 8B v6", COLORS["orange"]),
    ]
    tables = {name: parse_dimension_table(AGENTDOJO_DIR / name) for name, _, _ in arms}
    pos_rate = [tables["rule-baseline-report.md"][d]["positive_rate"] for d in dims]

    log("=== fig_agentdojo ===")
    for name, label, _ in arms:
        vals = {d: tables[name][d]["auprc"] for d in dims}
        log(f"  {label}: {vals}")

    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(5.5, 2.8))
        x = list(range(len(dims)))
        n = len(arms)
        width = 0.8 / n
        offsets = [(-((n - 1) / 2) + i) * width for i in range(n)]
        for (name, label, color), off in zip(arms, offsets, strict=True):
            vals = [tables[name][d]["auprc"] for d in dims]
            ax.bar([i + off for i in x], vals, width, label=label, color=color)
        for i, p in enumerate(pos_rate):
            ax.plot(
                [i - 0.4, i + 0.4],
                [p, p],
                linestyle="--",
                color=COLORS["black"],
                linewidth=0.8,
                label="Positive rate (chance)" if i == 0 else None,
            )
        ax.set_xticks(x)
        ax.set_xticklabels([DIM_SHORT[d].replace("\n", " ") for d in dims])
        ax.set_ylabel("AUPRC")
        ax.set_ylim(0, 1.05)
        ax.legend(loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.35), frameon=False)
        savefig(fig, "fig_agentdojo.pdf")


IDENTITY_BODY_DIMS = [
    "unauthorized_scope",
    "policy_conflict",
    "insufficient_context",
    "privilege_escalation",
    "prompt_injection_influence",
    "financial_commitment",
]
IDENTITY_BODY_SHORT = {
    "unauthorized_scope": "scope",
    "policy_conflict": "policy",
    "insufficient_context": "insufficient ctx",
    "privilege_escalation": "priv. escalation",
    "prompt_injection_influence": "injection",
    "financial_commitment": "financial",
}
IDENTITY_BODY_DATA = {
    "unauthorized_scope": (0.108, 0.999, 0.125, 0.107, 0.507),
    "policy_conflict": (0.371, 0.964, 0.392, 0.429, 0.370),
    "insufficient_context": (0.087, 0.841, 0.412, 0.357, 0.232),
    "privilege_escalation": (0.071, 1.000, 1.000, None, 0.364),
    "prompt_injection_influence": (0.082, 0.804, 0.806, None, 0.287),
    "financial_commitment": (0.095, 1.000, 1.000, 1.000, 1.000),
}


def fig_identity_body() -> None:
    log("=== fig_identity_body ===")
    dims = IDENTITY_BODY_DIMS
    series_labels = ["Full", "Eval-stripped", "Train-stripped", "Rule"]
    series_colors = [
        COLORS["blue"],
        COLORS["vermillion"],
        COLORS["reddish_purple"],
        COLORS["bluish_green"],
    ]
    for d in dims:
        log(f"  {d}: {IDENTITY_BODY_DATA[d]}")

    h = 0.18
    offsets = [-1.5 * h, -0.5 * h, 0.5 * h, 1.5 * h]

    with plt.rc_context(BODY_RC):
        fig, ax = plt.subplots(figsize=(3.2, 2.45))
        for i, d in enumerate(dims):
            pos_rate, *vals = IDENTITY_BODY_DATA[d]
            for off, val, label, color in zip(offsets, vals, series_labels, series_colors, strict=True):
                if val is None:
                    continue
                ax.barh(
                    i + off,
                    val,
                    height=h,
                    color=color,
                    label=label if i == 0 else None,
                )
            ax.plot(
                [pos_rate, pos_rate],
                [i - 2 * h, i + 2 * h],
                color=COLORS["black"],
                linewidth=1.1,
                zorder=5,
                label="Positive rate (chance)" if i == 0 else None,
            )
        ax.axhline(2.5, color="black", linewidth=0.5)
        ax.set_yticks(range(len(dims)))
        ax.set_yticklabels([IDENTITY_BODY_SHORT[d] for d in dims])
        ax.invert_yaxis()
        ax.set_xlim(0, 1.05)
        ax.set_xlabel("AUPRC")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, frameon=False, fontsize=6, handlelength=1.4, columnspacing=1.0)
        savefig(fig, "fig_identity_body.pdf")


INJECAGENT_ARMS = [
    ("2B v4", "scores-2b.jsonl", "--", COLORS["blue"]),
    ("8B v4", "scores-8b.jsonl", "--", COLORS["orange"]),
    ("8B v4 stripped", "scores-8b-noid.jsonl", "--", COLORS["bluish_green"]),
    ("2B v6", "scores-2b-v6.jsonl", "-", COLORS["blue"]),
    ("8B v6", "scores-8b-v6.jsonl", "-", COLORS["orange"]),
    ("8B v6 stripped", "scores-8b-v6-noid.jsonl", "-", COLORS["bluish_green"]),
]

INJECAGENT_KNOWN_COUNTS = {
    "2B v4": (410, 382, 806),
    "2B v6": (28, 8, 1562),
    "8B v6": (17, 19, 1562),
    "8B v6 stripped": (10, 25, 1563),
    "8B v4": (418, 616, 564),
    "8B v4 stripped": (353, 634, 611),
}


def _injecagent_margins(pairs: dict, raw: dict) -> list[float]:
    margins = []
    for ids in pairs.values():
        a = raw.get(ids["poisoned"], {}).get("prompt_injection_influence")
        b = raw.get(ids["clean"], {}).get("prompt_injection_influence")
        if a is None or b is None:
            continue
        margins.append(a - b)
    return margins


def fig_injecagent_margins() -> None:
    _, pairs = load_export(INJECAGENT_DIR / "injecagent.jsonl")
    log(f"=== fig_injecagent_margins === complete pairs={len(pairs)}")

    with plt.rc_context(BODY_RC):
        fig, ax = plt.subplots(figsize=(3.2, 2.2))
        for name, fname, ls, color in INJECAGENT_ARMS:
            raw, _ = load_scores(INJECAGENT_DIR / fname)
            margins = _injecagent_margins(pairs, raw)
            neg = sum(1 for m in margins if m < 0)
            zero = sum(1 for m in margins if m == 0)
            pos = sum(1 for m in margins if m > 0)
            known = INJECAGENT_KNOWN_COUNTS.get(name)
            match = "OK" if known == (neg, zero, pos) else f"MISMATCH (expected {known})"
            log(f"  {name}: margin<0={neg} margin=0={zero} margin>0={pos} n={len(margins)} {match}")

            xs = sorted(margins)
            n = len(xs)
            ys = [j / n for j in range(1, n + 1)]
            ax.step(xs, ys, where="post", linestyle=ls, color=color, linewidth=1.1, label=name)

        ax.axvline(0, color=COLORS["black"], linestyle=":", linewidth=0.9, zorder=0)
        ax.set_xscale("symlog", linthresh=1.0, linscale=1.0)
        ax.set_xlim(-6, 30)
        ax.set_xticks([-5, -2, -1, 0, 1, 2, 5, 10, 20])
        ax.set_xticklabels(["-5", "-2", "-1", "0", "1", "2", "5", "10", "20"])
        ax.set_xlabel("poisoned $-$ clean injection logit (symlog)")
        ax.set_ylabel("fraction of pairs")
        ax.set_ylim(0, 1.02)
        ax.legend(loc="center right", frameon=False, fontsize=6, ncol=1)
        savefig(fig, "fig_injecagent_margins.pdf")


STACKING_ANCHORS = [
    ("decoder", "independent", 1, "fpr", 0.015),
    ("decoder", "independent", 1, "fnr", 0.253),
    ("decoder", "independent", 2, "fpr", 0.140),
    ("decoder", "independent", 2, "fnr", 0.080),
    ("decoder", "independent", 3, "fpr", 0.966),
    ("decoder", "independent", 3, "fnr", 0.016),
    ("decoder", "independent", 8, "fpr", 0.966),
    ("decoder", "independent", 8, "fnr", 0.007),
    ("decoder", "independent", 15, "fpr", 0.967),
    ("decoder", "independent", 15, "fnr", 0.003),
    ("decoder", "expected_cost_joint", 1, "fpr", 0.058),
    ("decoder", "expected_cost_joint", 1, "fnr", 0.170),
    ("decoder", "expected_cost_joint", 2, "fpr", 0.082),
    ("decoder", "expected_cost_joint", 2, "fnr", 0.070),
    ("decoder", "joint", 2, "fpr", 0.131),
    ("decoder", "joint", 2, "fnr", 0.105),
    ("decoder", "joint", 3, "fpr", 0.905),
    ("decoder", "joint", 3, "fnr", 0.051),
    ("encoder", "independent", 1, "fpr", 0.346),
    ("encoder", "independent", 1, "fnr", 0.163),
    ("encoder", "independent", 2, "fpr", 0.710),
    ("encoder", "independent", 2, "fnr", 0.042),
    ("encoder", "expected_cost_joint", 1, "fpr", 0.589),
    ("encoder", "expected_cost_joint", 1, "fnr", 0.050),
    ("encoder", "expected_cost_joint", 2, "fpr", 0.921),
    ("encoder", "expected_cost_joint", 2, "fnr", 0.010),
]


def fig_stacking_body() -> None:
    dec_path = RESULTS_DIR / "decoder-2b" / "heldout_family-stacking-report.md"
    enc_path = RESULTS_DIR / "encoder-granite-embedding-r2" / "heldout_family-stacking-report.md"
    dec_rows = parse_stacking_table(dec_path)
    enc_rows = parse_stacking_table(enc_path)
    by_arm = {"decoder": dec_rows, "encoder": enc_rows}

    def series(rows: list[dict], strategy: str, field: str) -> tuple[list[int], list[float]]:
        pts = [(r["k"], r[field]) for r in rows if r["strategy"] == strategy]
        pts.sort()
        return [p[0] for p in pts], [p[1] for p in pts]

    log("=== fig_stacking_body ===")
    dec_ks = sorted({r["k"] for r in dec_rows})
    enc_ks = sorted({r["k"] for r in enc_rows})
    log(f"  decoder k values: {dec_ks}")
    log(f"  encoder k values: {enc_ks}")

    for arm, strategy, k, field, expected in STACKING_ANCHORS:
        rows = by_arm[arm]
        val = next((r[field] for r in rows if r["strategy"] == strategy and r["k"] == k), None)
        match = "OK" if val is not None and abs(val - expected) < 0.002 else "MISMATCH"
        log(f"  anchor {arm}/{strategy}/k={k}/{field}: got={val} expected={expected} {match}")

    plot_series = [
        ("decoder", "independent", "2B indep.", COLORS["blue"], "-"),
        ("decoder", "joint", "2B joint", COLORS["orange"], "-"),
        ("decoder", "expected_cost_joint", "2B exp. cost", COLORS["vermillion"], "-"),
        ("encoder", "independent", "r2 indep.", COLORS["blue"], "--"),
        ("encoder", "expected_cost_joint", "r2 exp. cost", COLORS["vermillion"], "--"),
    ]

    with plt.rc_context(BODY_RC):
        fig, (ax_fpr, ax_fnr) = plt.subplots(1, 2, figsize=(3.2, 2.2), sharex=True)
        for arm, strategy, label, color, ls in plot_series:
            ks, fprs = series(by_arm[arm], strategy, "fpr")
            _, fnrs = series(by_arm[arm], strategy, "fnr")
            ax_fpr.plot(ks, fprs, color=color, linestyle=ls, linewidth=1.0, marker="o", markersize=2, label=label)
            ax_fnr.plot(ks, fnrs, color=color, linestyle=ls, linewidth=1.0, marker="o", markersize=2, label=label)
        for ax in (ax_fpr, ax_fnr):
            ax.axvline(3, color="gray", linestyle=":", linewidth=0.8, alpha=0.7, zorder=0)
            ax.set_xticks([1, 3, 5, 10, 15])
            ax.set_xlabel("$k$ stacked policies")
        ax_fpr.set_ylabel("FPR")
        ax_fnr.set_ylabel("FNR")
        ax_fpr.set_ylim(0, 1.02)
        ax_fnr.set_ylim(0, 0.3)
        handles, labels = ax_fpr.get_legend_handles_labels()
        fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, -0.04), ncol=5, frameon=False, fontsize=5.5, handlelength=1.3, columnspacing=0.8)
        savefig(fig, "fig_stacking_body.pdf")


def main() -> None:
    fig_identity_body()
    fig_injecagent_margins()
    fig_stacking_body()
    fig_identity_ablation()
    fig_policy_generalisation()
    fig_stacking()
    fig_approval_curve()
    fig_self_judgment()
    fig_judge_agreement()
    fig_agentdojo()


if __name__ == "__main__":
    main()
