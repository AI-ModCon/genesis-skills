from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


def save_average_calibration_plot(
    exp_proportions,
    obs_proportions,
    plot_path: Path,
) -> None:
    """Render and save a reliability diagram for average calibration."""
    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(6, 6))
    sns.lineplot(
        x=[0.0, 1.0],
        y=[0.0, 1.0],
        ax=ax,
        linestyle="--",
        color="#ff7f0e",
        label="Ideal",
        zorder=4,
        clip_on=False,
    )
    sns.lineplot(
        x=exp_proportions,
        y=obs_proportions,
        ax=ax,
        color="#1f77b4",
        label="Observed",
        zorder=5,
        clip_on=False,
    )
    ax.fill_between(
        exp_proportions,
        exp_proportions,
        obs_proportions,
        alpha=0.2,
        color="#1f77b4",
        zorder=2,
    )

    ax.set_xlabel("Predicted Proportion in Interval")
    ax.set_ylabel("Observed Proportion in Interval")
    ax.set_aspect("equal", adjustable="box")

    buff = 0.00
    ax.set_xlim((0 - buff, 1 + buff))
    ax.set_ylim((0 - buff, 1 + buff))

    # Keep the border visible but behind plotted content at the axis limits.
    for spine in ax.spines.values():
        spine.set_zorder(1)

    ax.set_title("Average Calibration")
    fig.tight_layout()
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)


def save_residual_distribution_plot(
    residuals,
    plot_path: Path,
) -> None:
    """Render and save a residual distribution plot (histogram + KDE)."""
    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(7, 4.5))

    sns.histplot(
        residuals,
        bins=30,
        kde=True,
        stat="density",
        color="#1f77b4",
        alpha=0.35,
        edgecolor=None,
        ax=ax,
    )

    ax.axvline(
        x=0.0,
        linestyle="--",
        color="#ff7f0e",
        linewidth=1.8,
        label="Zero residual",
    )

    ax.set_title("Residual Distribution")
    ax.set_xlabel("Residual (y_true - y_pred)")
    ax.set_ylabel("Density")
    ax.legend()

    fig.tight_layout()
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)


def save_confusion_matrix_plot(
    confusion_matrix: "np.ndarray",
    class_labels: list[str],
    plot_path: Path,
) -> None:
    """Render and save a confusion matrix heatmap."""
    sns.set_theme(style="white")
    n = len(class_labels)
    # Scale figure size with number of classes, capped reasonably
    size = max(5, min(n * 1.2, 16))
    fig, ax = plt.subplots(figsize=(size, size * 0.85))

    sns.heatmap(
        confusion_matrix,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=class_labels,
        yticklabels=class_labels,
        linewidths=0.5,
        linecolor="white",
        ax=ax,
        cbar=False,
    )

    ax.set_xlabel("Predicted Label", labelpad=10)
    ax.set_ylabel("True Label", labelpad=10)
    ax.set_title("Confusion Matrix")
    ax.tick_params(axis="x", rotation=45)
    ax.tick_params(axis="y", rotation=0)

    fig.tight_layout()
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)


def save_reliability_diagram_plot(
    mean_predicted_probs: list[float],
    fraction_of_positives: list[float],
    plot_path: Path,
    class_label: Optional[str] = None,
    extra_curves: Optional[list[tuple[list[float], list[float], str]]] = None,
) -> None:
    """Render and save a reliability diagram for probabilistic calibration.

    For binary classifiers, pass mean_predicted_probs and fraction_of_positives
    directly. For multiclass (one-vs-rest), pass the first class as the primary
    curve and remaining classes via extra_curves.
    """
    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(6, 6))

    # Ideal diagonal
    sns.lineplot(
        x=[0.0, 1.0],
        y=[0.0, 1.0],
        ax=ax,
        linestyle="--",
        color="#ff7f0e",
        label="Ideal",
        zorder=4,
        clip_on=False,
    )

    all_curves = [(mean_predicted_probs, fraction_of_positives, class_label if class_label else "Observed")]
    if extra_curves:
        all_curves += [(mp, fp, lbl) for mp, fp, lbl in extra_curves]

    palette = sns.color_palette("tab10", len(all_curves))
    for i, (mp, fp, lbl) in enumerate(all_curves):
        ax.plot(mp, fp, "o-", color=palette[i], label=lbl, zorder=5, alpha=0.85)

    ax.set_xlabel("Mean Predicted Probability")
    ax.set_ylabel("Fraction of Positives")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_title("Reliability Diagram")
    ax.legend(loc="upper left", fontsize="small")

    fig.tight_layout()
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)
