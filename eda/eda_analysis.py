"""
UniAssist – Exploratory Data Analysis (EDA) Script
===================================================
Generates a structured text summary and 7+ professional visualizations
for the UniAssist chatbot interaction dataset.

Prerequisites
-------------
    pip install matplotlib seaborn pandas numpy

Usage
-----
    python eda/eda_analysis.py                    # uses default path ../data/dataset.csv
    python eda/eda_analysis.py path/to/data.csv   # custom dataset path
"""

import os
import sys
import warnings
from pathlib import Path

# Fix Windows console UTF-8 encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for CI / headless environments
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.backends.backend_pdf import PdfPages
import seaborn as sns

# ── Global style ────────────────────────────────────────────────────────────
warnings.filterwarnings("ignore", category=FutureWarning)
sns.set_theme(style="whitegrid", font_scale=1.1)
PALETTE = sns.color_palette("Set2")
ACCENT  = "#2196F3"

# ── Paths ───────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).resolve().parent
CHARTS_DIR  = SCRIPT_DIR / "charts"
DEFAULT_CSV = SCRIPT_DIR / ".." / "data" / "dataset.csv"
REPORT_PDF  = SCRIPT_DIR / "EDA_Report.pdf"

# ── Helpers ─────────────────────────────────────────────────────────────────

def _ensure_dirs():
    """Create output directories if they don't exist."""
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)


def load_dataset(path: str | Path | None = None) -> pd.DataFrame:
    """Load the CSV dataset and apply basic type conversions."""
    csv_path = Path(path) if path else DEFAULT_CSV
    csv_path = csv_path.resolve()
    print(f"\n📂  Loading dataset from: {csv_path}")
    if not csv_path.exists():
        print(f"❌  File not found: {csv_path}")
        sys.exit(1)

    df = pd.read_csv(csv_path)

    # Parse timestamp if present
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    # Ensure correct dtypes
    if "escalated" in df.columns:
        df["escalated"] = df["escalated"].astype(int)
    if "user_rating" in df.columns:
        df["user_rating"] = df["user_rating"].astype(int)

    return df


# ══════════════════════════════════════════════════════════════════════════════
#  1.  TEXT SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

def print_summary(df: pd.DataFrame) -> None:
    """Print a structured text summary of the dataset."""
    sep = "─" * 60
    print(f"\n{'═' * 60}")
    print("  📊  DATASET SUMMARY")
    print(f"{'═' * 60}")

    # Shape
    print(f"\n▸ Shape: {df.shape[0]} rows × {df.shape[1]} columns")

    # Dtypes
    print(f"\n▸ Column Data Types:\n{sep}")
    for col in df.columns:
        print(f"   {col:<25s}  {str(df[col].dtype)}")

    # Null counts
    print(f"\n▸ Missing Values:\n{sep}")
    nulls = df.isnull().sum()
    if nulls.sum() == 0:
        print("   No missing values found ✅")
    else:
        for col, cnt in nulls.items():
            if cnt > 0:
                print(f"   {col:<25s}  {cnt} ({cnt / len(df) * 100:.1f}%)")

    # Basic statistics for numeric columns
    print(f"\n▸ Descriptive Statistics (Numeric Columns):\n{sep}")
    numeric_desc = df.describe().T
    for col in numeric_desc.index:
        row = numeric_desc.loc[col]
        print(f"   {col}:")
        print(f"     mean={row['mean']:.3f}  std={row['std']:.3f}  "
              f"min={row['min']:.2f}  max={row['max']:.2f}  "
              f"median={row['50%']:.2f}")

    # Value counts for categorical columns
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    if "intent" in df.columns and "intent" not in cat_cols:
        cat_cols.append("intent")
    if "user_query_type" in df.columns and "user_query_type" not in cat_cols:
        cat_cols.append("user_query_type")

    for col in cat_cols:
        print(f"\n▸ Value Counts – {col}:\n{sep}")
        vc = df[col].value_counts()
        for val, cnt in vc.items():
            pct = cnt / len(df) * 100
            print(f"   {val:<25s}  {cnt:>5d}  ({pct:.1f}%)")


# ══════════════════════════════════════════════════════════════════════════════
#  2.  VISUALIZATIONS
# ══════════════════════════════════════════════════════════════════════════════

def chart_intent_distribution(df: pd.DataFrame) -> plt.Figure:
    """Chart 1 – Bar chart: count of queries per intent (with % labels)."""
    fig, ax = plt.subplots(figsize=(9, 5))
    vc = df["intent"].value_counts().sort_values(ascending=False)
    total = len(df)
    bars = ax.bar(vc.index, vc.values, color=PALETTE[:len(vc)], edgecolor="white")
    for bar, count in zip(bars, vc.values):
        pct = count / total * 100
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + total * 0.005,
                f"{count}\n({pct:.1f}%)", ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_title("Query Distribution by Intent", fontsize=14, fontweight="bold")
    ax.set_xlabel("Intent Category")
    ax.set_ylabel("Number of Queries")
    ax.set_ylim(0, vc.max() * 1.18)
    fig.tight_layout()
    return fig


def chart_confidence_histogram(df: pd.DataFrame) -> plt.Figure:
    """Chart 2 – Histogram of confidence_score with KDE, mean & median."""
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.histplot(df["confidence_score"], bins=30, kde=True, color=ACCENT, alpha=0.65, ax=ax)
    mean_val = df["confidence_score"].mean()
    median_val = df["confidence_score"].median()
    ax.axvline(mean_val, color="crimson", linestyle="--", linewidth=1.5, label=f"Mean = {mean_val:.3f}")
    ax.axvline(median_val, color="green", linestyle="-.", linewidth=1.5, label=f"Median = {median_val:.3f}")
    ax.legend(fontsize=10)
    ax.set_title("Confidence Score Distribution", fontsize=14, fontweight="bold")
    ax.set_xlabel("Confidence Score")
    ax.set_ylabel("Frequency")
    fig.tight_layout()
    return fig


def chart_escalation_by_intent(df: pd.DataFrame) -> plt.Figure:
    """Chart 3 – Grouped bar chart: escalation rate by intent."""
    fig, ax = plt.subplots(figsize=(9, 5))
    esc_stats = df.groupby("intent")["escalated"].agg(["sum", "count"]).reset_index()
    esc_stats.columns = ["intent", "escalated", "total"]
    esc_stats["not_escalated"] = esc_stats["total"] - esc_stats["escalated"]
    esc_stats["rate"] = esc_stats["escalated"] / esc_stats["total"] * 100
    esc_stats = esc_stats.sort_values("rate", ascending=False)

    x = np.arange(len(esc_stats))
    w = 0.38
    ax.bar(x - w / 2, esc_stats["not_escalated"], w, label="Not Escalated", color=PALETTE[0])
    ax.bar(x + w / 2, esc_stats["escalated"], w, label="Escalated", color=PALETTE[3])

    # Annotate with rate
    for i, row in esc_stats.reset_index(drop=True).iterrows():
        ax.text(i + w / 2, row["escalated"] + esc_stats["total"].max() * 0.01,
                f"{row['rate']:.1f}%", ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(esc_stats["intent"])
    ax.set_title("Escalation Rate by Intent", fontsize=14, fontweight="bold")
    ax.set_xlabel("Intent Category")
    ax.set_ylabel("Number of Queries")
    ax.legend()
    fig.tight_layout()
    return fig


def chart_rating_distribution(df: pd.DataFrame) -> plt.Figure:
    """Chart 4 – Bar chart of user_rating distribution (1-5)."""
    fig, ax = plt.subplots(figsize=(8, 5))
    vc = df["user_rating"].value_counts().sort_index()
    colors = sns.color_palette("RdYlGn", n_colors=5)
    bars = ax.bar(vc.index.astype(str), vc.values, color=colors, edgecolor="white", width=0.6)
    total = len(df)
    for bar, count in zip(bars, vc.values):
        pct = count / total * 100
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + total * 0.003,
                f"{pct:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_title("User Rating Distribution", fontsize=14, fontweight="bold")
    ax.set_xlabel("Rating (1 = Poor, 5 = Excellent)")
    ax.set_ylabel("Number of Responses")
    ax.set_ylim(0, vc.max() * 1.12)
    fig.tight_layout()
    return fig


def chart_confidence_vs_rating(df: pd.DataFrame) -> plt.Figure:
    """Chart 5 – Heatmap: average confidence score by user_rating & intent."""
    fig, ax = plt.subplots(figsize=(9, 5))
    pivot = df.pivot_table(values="confidence_score", index="intent",
                           columns="user_rating", aggfunc="mean")
    sns.heatmap(pivot, annot=True, fmt=".3f", cmap="YlGnBu", linewidths=0.5, ax=ax)
    ax.set_title("Avg Confidence Score by Rating & Intent", fontsize=14, fontweight="bold")
    ax.set_xlabel("User Rating")
    ax.set_ylabel("Intent")
    fig.tight_layout()
    return fig


def chart_queries_over_time(df: pd.DataFrame) -> plt.Figure:
    """Chart 6 – Line chart: query volume over time (weekly aggregation)."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ts = df.set_index("timestamp").resample("W").size()
    ax.plot(ts.index, ts.values, marker="o", markersize=4, linewidth=2, color=ACCENT)
    ax.fill_between(ts.index, ts.values, alpha=0.15, color=ACCENT)
    ax.set_title("Weekly Query Volume Over Time", fontsize=14, fontweight="bold")
    ax.set_xlabel("Week")
    ax.set_ylabel("Number of Queries")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %d"))
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    return fig


def chart_correlation_matrix(df: pd.DataFrame) -> plt.Figure:
    """Chart 7 – Correlation heatmap of all numeric columns."""
    fig, ax = plt.subplots(figsize=(7, 5))
    numeric_df = df.select_dtypes(include=[np.number])
    corr = numeric_df.corr()
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="coolwarm",
                center=0, linewidths=0.5, square=True, ax=ax)
    ax.set_title("Correlation Matrix (Numeric Features)", fontsize=14, fontweight="bold")
    fig.tight_layout()
    return fig


# ══════════════════════════════════════════════════════════════════════════════
#  3.  KEY FINDINGS
# ══════════════════════════════════════════════════════════════════════════════

def print_key_findings(df: pd.DataFrame) -> None:
    """Print actionable EDA insights to the console."""
    sep = "─" * 60
    print(f"\n{'═' * 60}")
    print("  🔍  KEY EDA FINDINGS")
    print(f"{'═' * 60}")

    # Most common intent
    top_intent = df["intent"].value_counts().idxmax()
    top_intent_pct = df["intent"].value_counts(normalize=True).max() * 100
    print(f"\n  ▸ Most common intent: {top_intent} ({top_intent_pct:.1f}%)")

    # Average confidence
    avg_conf = df["confidence_score"].mean()
    print(f"  ▸ Average confidence score: {avg_conf:.3f}")

    # Escalation rate
    esc_rate = df["escalated"].mean() * 100
    print(f"  ▸ Overall escalation rate: {esc_rate:.1f}%")

    # Average rating
    avg_rating = df["user_rating"].mean()
    print(f"  ▸ Average user rating: {avg_rating:.2f} / 5")

    # Highest escalation intent
    esc_by_intent = df.groupby("intent")["escalated"].mean() * 100
    worst_intent = esc_by_intent.idxmax()
    worst_rate = esc_by_intent.max()
    print(f"  ▸ Highest escalation intent: {worst_intent} ({worst_rate:.1f}%)")

    # Lowest-rated intent
    rating_by_intent = df.groupby("intent")["user_rating"].mean()
    low_intent = rating_by_intent.idxmin()
    low_rating = rating_by_intent.min()
    print(f"  ▸ Lowest-rated intent: {low_intent} (avg {low_rating:.2f})")

    # Dataset time span
    if "timestamp" in df.columns and pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        t_min = df["timestamp"].min().strftime("%Y-%m-%d")
        t_max = df["timestamp"].max().strftime("%Y-%m-%d")
        print(f"  ▸ Data spans from {t_min} to {t_max}")

    # Confidence below threshold
    low_conf_pct = (df["confidence_score"] < 0.7).mean() * 100
    print(f"  ▸ Low-confidence queries (<0.70): {low_conf_pct:.1f}%")

    print(f"\n{'═' * 60}\n")


# ══════════════════════════════════════════════════════════════════════════════
#  4.  MAIN PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    _ensure_dirs()

    # Accept optional CSV path from command line
    csv_path = sys.argv[1] if len(sys.argv) > 1 else None
    df = load_dataset(csv_path)

    # ── Text summary ────────────────────────────────────────────────────
    print_summary(df)

    # ── Generate charts ─────────────────────────────────────────────────
    chart_funcs = [
        ("intent_distribution",          chart_intent_distribution),
        ("confidence_histogram",         chart_confidence_histogram),
        ("escalation_by_intent",         chart_escalation_by_intent),
        ("rating_distribution",          chart_rating_distribution),
        ("confidence_vs_rating_heatmap", chart_confidence_vs_rating),
        ("queries_over_time",            chart_queries_over_time),
        ("correlation_matrix",           chart_correlation_matrix),
    ]

    figures: list[tuple[str, plt.Figure]] = []
    for name, func in chart_funcs:
        print(f"  📈  Generating {name} ...")
        fig = func(df)
        png_path = CHARTS_DIR / f"{name}.png"
        fig.savefig(png_path, dpi=150, bbox_inches="tight")
        figures.append((name, fig))
        print(f"       → Saved to {png_path}")

    # ── Combined PDF report ─────────────────────────────────────────────
    try:
        with PdfPages(str(REPORT_PDF)) as pdf:
            for name, fig in figures:
                pdf.savefig(fig, bbox_inches="tight")
        print(f"\n  📄  Combined PDF report saved to: {REPORT_PDF}")
    except Exception as exc:
        print(f"\n  ⚠️  Could not create PDF report: {exc}")
        print("       Individual PNGs are still available in the charts/ folder.")

    plt.close("all")

    # ── Key findings ────────────────────────────────────────────────────
    print_key_findings(df)

    print("✅  EDA analysis complete!")


if __name__ == "__main__":
    main()
