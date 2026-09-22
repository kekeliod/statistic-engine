"""Chart rendering for analysis results.

`chart_for_result` picks a sensible default chart per method; `render_chart`
draws a named chart kind and writes a PNG. House style mirrors the project's
existing analysis scripts (clean, muted palette, no top/right spines).
"""
from __future__ import annotations

import uuid
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "#f9f9f9",
    "axes.grid": True, "grid.alpha": 0.35, "axes.spines.top": False,
    "axes.spines.right": False, "font.size": 10, "axes.titlesize": 12,
    "axes.titleweight": "bold", "figure.dpi": 130,
})
PALETTE = ["#2a78d6", "#1baf7a", "#eda100", "#4a3aa7", "#e34948", "#eb6834", "#e87ba4"]

# method key -> default chart kind
DEFAULT_KIND = {
    "independent_ttest": "grouped_box",
    "mann_whitney": "grouped_box",
    "one_way_anova": "grouped_box",
    "kruskal_wallis": "grouped_box",
    "paired_ttest": "paired_box",
    "pearson": "scatter_fit",
    "spearman": "scatter_fit",
    "linear_regression": "actual_vs_predicted",
    "logistic_regression": "coefficient_plot",
    "chi_square": "grouped_bar",
    "descriptive": "histogram_grid",
}
ALTERNATES = {
    "grouped_box": ["grouped_box", "bar_means"],
    "scatter_fit": ["scatter_fit"],
    "histogram_grid": ["histogram_grid"],
}


def chart_for_result(result: dict) -> str:
    return DEFAULT_KIND.get(result.get("method", ""), "histogram_grid")


def alternate_kinds(method: str) -> list[str]:
    return ALTERNATES.get(DEFAULT_KIND.get(method, ""), [DEFAULT_KIND.get(method, "histogram_grid")])


def _save(fig, out_dir: Path) -> tuple[Path, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.png"
    path = out_dir / name
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path, name


# ── individual chart kinds ─────────────────────────────────────────────────

def _grouped_box(df, result, ax):
    g = result["groups"]
    outcome, group = g["outcome"], g["group"]
    d = df[[outcome, group]].copy()
    d[outcome] = pd.to_numeric(d[outcome], errors="coerce")
    d = d.dropna()
    levels = g.get("levels") or sorted(d[group].astype(str).unique())
    data = [d.loc[d[group].astype(str) == lvl, outcome].values for lvl in levels]
    bp = ax.boxplot(data, labels=levels, patch_artist=True, widths=0.55)
    for patch, c in zip(bp["boxes"], PALETTE):
        patch.set_facecolor(c)
        patch.set_alpha(0.55)
    for i, arr in enumerate(data):
        x = np.random.normal(i + 1, 0.05, len(arr))
        ax.scatter(x, arr, s=10, color=PALETTE[i % len(PALETTE)], alpha=0.5, zorder=3)
    ax.set_ylabel(outcome)
    ax.set_xlabel(group)
    ax.set_title(f"{outcome} by {group}")


def _bar_means(df, result, ax):
    g = result["groups"]
    stats = g.get("stats", {})
    names = list(stats)
    means = [stats[n]["mean"] for n in names]
    sds = [stats[n].get("sd") or 0 for n in names]
    ax.bar(names, means, yerr=sds, capsize=4, color=PALETTE[: len(names)], alpha=0.75)
    ax.set_ylabel(f"mean {g.get('outcome', '')}")
    ax.set_title(f"Mean {g.get('outcome', '')} by {g.get('group', '')}")


def _paired_box(df, result, ax):
    m1, m2 = result["groups"]["paired"]
    d = df[[m1, m2]].apply(pd.to_numeric, errors="coerce").dropna()
    for _, row in d.iterrows():
        ax.plot([1, 2], [row[m1], row[m2]], color="#bbb", lw=0.6, zorder=1)
    ax.boxplot([d[m1], d[m2]], labels=[m1, m2], widths=0.5)
    ax.set_title(f"Paired: {m1} vs {m2}")


def _scatter_fit(df, result, ax):
    g = result["groups"]
    x, y = g["x"], g["y"]
    d = df[[x, y]].apply(pd.to_numeric, errors="coerce").dropna()
    ax.scatter(d[x], d[y], s=18, color=PALETTE[0], alpha=0.6)
    if len(d) >= 2:
        m, b = np.polyfit(d[x], d[y], 1)
        xs = np.linspace(d[x].min(), d[x].max(), 100)
        ax.plot(xs, m * xs + b, color=PALETTE[4], lw=1.8)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.set_title(f"{y} vs {x}")


def _actual_vs_predicted(df, result, ax):
    g = result["groups"]
    actual = np.asarray(g.get("actual", []), dtype=float)
    fitted = np.asarray(g.get("fitted", []), dtype=float)
    ax.scatter(fitted, actual, s=18, color=PALETTE[0], alpha=0.6)
    if actual.size:
        lo, hi = min(actual.min(), fitted.min()), max(actual.max(), fitted.max())
        ax.plot([lo, hi], [lo, hi], "--", color="#888")
    ax.set_xlabel("predicted")
    ax.set_ylabel("actual")
    ax.set_title(f"{g.get('outcome', 'outcome')}: actual vs predicted")


def _coefficient_plot(df, result, ax):
    coefs = result["frequentist"].get("coefficients", [])
    coefs = [c for c in coefs if c.get("term") != "intercept"]
    terms = [c["term"] for c in coefs]
    ors = [c.get("odds_ratio", c.get("beta", 0)) for c in coefs]
    ax.barh(terms, ors, color=PALETTE[3], alpha=0.75)
    ax.axvline(1.0, color="#888", ls="--")
    ax.set_xlabel("odds ratio")
    ax.set_title("Predictor odds ratios")


def _grouped_bar(df, result, ax):
    ct = result["groups"]["crosstab"]
    idx_name, col_name = ct["index"], ct["columns"]
    counts = ct["counts"]
    row_labels = list(counts)
    col_labels = list(next(iter(counts.values())))
    x = np.arange(len(row_labels))
    w = 0.8 / max(len(col_labels), 1)
    for j, cl in enumerate(col_labels):
        vals = [counts[rl][cl] for rl in row_labels]
        ax.bar(x + j * w, vals, w, label=str(cl), color=PALETTE[j % len(PALETTE)], alpha=0.8)
    ax.set_xticks(x + 0.4 - w / 2)
    ax.set_xticklabels(row_labels)
    ax.set_xlabel(idx_name)
    ax.set_ylabel("count")
    ax.legend(title=col_name, fontsize=8)
    ax.set_title(f"{idx_name} × {col_name}")


def _histogram_grid(df, result, ax):
    # single-axis fallback used when called via render_chart's generic path
    g = result.get("groups", {})
    variables = g.get("variables") or []
    numeric = [v for v in variables if pd.to_numeric(df[v], errors="coerce").notna().mean() > 0.7]
    target = numeric[0] if numeric else (variables[0] if variables else df.columns[0])
    vals = pd.to_numeric(df[target], errors="coerce").dropna()
    ax.hist(vals, bins=min(20, max(5, len(vals) // 5)), color=PALETTE[0], alpha=0.8)
    ax.set_xlabel(target)
    ax.set_ylabel("frequency")
    ax.set_title(f"Distribution of {target}")


_KIND_FUNCS = {
    "grouped_box": _grouped_box,
    "bar_means": _bar_means,
    "paired_box": _paired_box,
    "scatter_fit": _scatter_fit,
    "actual_vs_predicted": _actual_vs_predicted,
    "coefficient_plot": _coefficient_plot,
    "grouped_bar": _grouped_bar,
    "histogram_grid": _histogram_grid,
}


def render_chart(kind: str, df: pd.DataFrame, result: dict, out_dir: Path) -> tuple[Path, str, str]:
    """Draw `kind` and save a PNG. Returns (path, filename, title)."""
    func = _KIND_FUNCS.get(kind)
    if func is None:
        raise ValueError(f"Unknown chart kind '{kind}'.")

    if kind == "histogram_grid":
        g = result.get("groups", {})
        variables = [v for v in (g.get("variables") or [])
                     if pd.to_numeric(df[v], errors="coerce").notna().mean() > 0.7]
        if len(variables) > 1:
            n = len(variables)
            cols = min(3, n)
            rows = (n + cols - 1) // cols
            fig, axes = plt.subplots(rows, cols, figsize=(4 * cols, 3 * rows), squeeze=False)
            for ax, var in zip(axes.ravel(), variables):
                vals = pd.to_numeric(df[var], errors="coerce").dropna()
                ax.hist(vals, bins=min(20, max(5, len(vals) // 5)), color=PALETTE[0], alpha=0.8)
                ax.set_title(var)
            for ax in axes.ravel()[len(variables):]:
                ax.set_visible(False)
            fig.suptitle("Distributions", fontweight="bold")
            path, name = _save(fig, out_dir)
            return path, name, "Distributions"

    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    func(df, result, ax)
    title = ax.get_title()
    path, name = _save(fig, out_dir)
    return path, name, title
