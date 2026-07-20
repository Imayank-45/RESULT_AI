"""
chart_renderer.py
-----------------
Matplotlib-based chart factory that renders premium charts as high-resolution
PNG images for embedding in the PDF report.

All charts use a consistent dark corporate theme.
"""

from __future__ import annotations

import os
import tempfile
from typing import List, Dict, Optional, Tuple

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server-side rendering

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from matplotlib.patches import FancyBboxPatch, Circle, Arc
from matplotlib.colors import LinearSegmentedColormap

from report_generator.config import Colors, ReportConfig


# ═══════════════════════════════════════════════════════════════════════
#  CHART STYLE SETUP
# ═══════════════════════════════════════════════════════════════════════

def _setup_style():
    """Apply premium dark corporate chart style."""
    plt.rcParams.update({
        'figure.facecolor': '#0F172A',
        'axes.facecolor': '#1E283C',
        'axes.edgecolor': '#334155',
        'axes.labelcolor': '#CBD5E1',
        'axes.grid': True,
        'grid.color': '#334155',
        'grid.alpha': 0.3,
        'grid.linewidth': 0.5,
        'text.color': '#E2E8F0',
        'xtick.color': '#94A3B8',
        'ytick.color': '#94A3B8',
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
        'font.family': 'sans-serif',
        'font.sans-serif': ['Helvetica', 'Arial', 'DejaVu Sans'],
        'font.size': 10,
        'legend.facecolor': '#1E283C',
        'legend.edgecolor': '#334155',
        'legend.fontsize': 9,
    })


# Hex palette for matplotlib
PALETTE_HEX = [
    '#4F46E5', '#059669', '#E11D4C', '#F59E0B', '#38BDF8',
    '#7C3AED', '#EC7424', '#0CA5A5', '#E94880', '#748C1C',
]

GRADIENT_PALETTE = [
    '#6366F1', '#22C55E', '#EF4444', '#FBBF24', '#38BDF8',
    '#A78BFA', '#FB923C', '#2DD4BF', '#F472B6', '#A3E635',
]


# ═══════════════════════════════════════════════════════════════════════
#  TEMP FILE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════

_temp_files: List[str] = []


def get_temp_chart_path(name: str) -> str:
    """Generate a temp file path for a chart image."""
    path = os.path.join(tempfile.gettempdir(), f"resultai_chart_{name}.png")
    _temp_files.append(path)
    return path


def cleanup_temp_charts():
    """Remove all temporary chart files."""
    for f in _temp_files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except OSError:
            pass
    _temp_files.clear()


# ═══════════════════════════════════════════════════════════════════════
#  CHART RENDERERS
# ═══════════════════════════════════════════════════════════════════════

def render_bar_chart(
    labels: List[str],
    values: List[float],
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    colors: Optional[List[str]] = None,
    horizontal: bool = False,
    figsize: Tuple[float, float] = (8, 4.5),
    dpi: int = 200,
    name: str = "bar"
) -> str:
    """Render a vertical or horizontal bar chart. Returns path to PNG."""
    _setup_style()
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    bar_colors = colors or [PALETTE_HEX[i % len(PALETTE_HEX)] for i in range(len(labels))]

    if horizontal:
        bars = ax.barh(labels, values, color=bar_colors, height=0.6, edgecolor='none')
        ax.set_xlabel(xlabel, fontweight='bold', fontsize=10)
        ax.set_ylabel(ylabel, fontweight='bold', fontsize=10)
        ax.invert_yaxis()
        # Value labels
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + max(values) * 0.02, bar.get_y() + bar.get_height() / 2,
                    f'{val:.1f}' if isinstance(val, float) else str(val),
                    ha='left', va='center', fontsize=9, color='#CBD5E1', fontweight='bold')
    else:
        bars = ax.bar(labels, values, color=bar_colors, width=0.6, edgecolor='none')
        ax.set_xlabel(xlabel, fontweight='bold', fontsize=10)
        ax.set_ylabel(ylabel, fontweight='bold', fontsize=10)
        # Value labels on top
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.02,
                    f'{val:.1f}' if isinstance(val, float) else str(val),
                    ha='center', va='bottom', fontsize=9, color='#CBD5E1', fontweight='bold')

    if title:
        ax.set_title(title, fontweight='bold', fontsize=13, pad=15, color='#F1F5F9')

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.xticks(rotation=30 if not horizontal and len(labels) > 5 else 0, ha='right' if len(labels) > 5 else 'center')
    plt.tight_layout()

    path = get_temp_chart_path(name)
    fig.savefig(path, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    return path


def render_pie_chart(
    labels: List[str],
    values: List[float],
    title: str = "",
    colors: Optional[List[str]] = None,
    figsize: Tuple[float, float] = (6, 5),
    dpi: int = 200,
    name: str = "pie",
    donut: bool = True
) -> str:
    """Render a donut/pie chart. Returns path to PNG."""
    _setup_style()
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    # Filter out zero values
    filtered = [(l, v) for l, v in zip(labels, values) if v > 0]
    if not filtered:
        filtered = [("No Data", 1)]
    f_labels, f_values = zip(*filtered)

    chart_colors = colors or [PALETTE_HEX[i % len(PALETTE_HEX)] for i in range(len(f_labels))]

    wedges, texts, autotexts = ax.pie(
        f_values, labels=None, colors=chart_colors,
        autopct='%1.1f%%', startangle=90,
        pctdistance=0.80 if donut else 0.5,
        wedgeprops=dict(width=0.4 if donut else 1.0, edgecolor='#0F172A', linewidth=2)
    )

    for autotext in autotexts:
        autotext.set_fontsize(9)
        autotext.set_fontweight('bold')
        autotext.set_color('#F1F5F9')

    # Legend
    legend = ax.legend(
        wedges, [f"{l} ({v})" for l, v in zip(f_labels, f_values)],
        loc='center left', bbox_to_anchor=(1, 0.5),
        fontsize=9, frameon=True,
        facecolor='#1E283C', edgecolor='#334155',
    )
    for text in legend.get_texts():
        text.set_color('#CBD5E1')

    if title:
        ax.set_title(title, fontweight='bold', fontsize=13, pad=15, color='#F1F5F9')

    ax.set_aspect('equal')
    plt.tight_layout()

    path = get_temp_chart_path(name)
    fig.savefig(path, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    return path


def render_stacked_bar(
    categories: List[str],
    series: Dict[str, List[float]],
    title: str = "",
    ylabel: str = "",
    figsize: Tuple[float, float] = (9, 5),
    dpi: int = 200,
    name: str = "stacked"
) -> str:
    """Render a stacked bar chart. Returns path to PNG."""
    _setup_style()
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    x = np.arange(len(categories))
    width = 0.5
    bottom = np.zeros(len(categories))

    for i, (label, vals) in enumerate(series.items()):
        color = PALETTE_HEX[i % len(PALETTE_HEX)]
        ax.bar(x, vals, width, label=label, bottom=bottom, color=color, edgecolor='none')
        bottom += np.array(vals)

    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=30, ha='right')
    ax.set_ylabel(ylabel, fontweight='bold')
    if title:
        ax.set_title(title, fontweight='bold', fontsize=13, pad=15, color='#F1F5F9')

    ax.legend(loc='upper right', fontsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()

    path = get_temp_chart_path(name)
    fig.savefig(path, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    return path


def render_radar_chart(
    labels: List[str],
    values: List[float],
    title: str = "",
    figsize: Tuple[float, float] = (6, 6),
    dpi: int = 200,
    name: str = "radar",
    max_val: float = 10.0
) -> str:
    """Render a radar/spider chart. Returns path to PNG."""
    _setup_style()

    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    values_plot = values + [values[0]]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi, subplot_kw=dict(projection='polar'))
    fig.patch.set_facecolor('#0F172A')
    ax.set_facecolor('#0F172A')

    ax.plot(angles, values_plot, 'o-', linewidth=2, color='#6366F1')
    ax.fill(angles, values_plot, alpha=0.2, color='#6366F1')

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9, color='#CBD5E1')
    ax.set_ylim(0, max_val)
    ax.set_yticks(np.linspace(0, max_val, 5))
    ax.set_yticklabels([f'{v:.0f}' for v in np.linspace(0, max_val, 5)],
                        fontsize=7, color='#94A3B8')
    ax.grid(color='#334155', alpha=0.4)
    ax.spines['polar'].set_color('#334155')

    if title:
        ax.set_title(title, fontweight='bold', fontsize=13, pad=20, color='#F1F5F9')

    plt.tight_layout()
    path = get_temp_chart_path(name)
    fig.savefig(path, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    return path


def render_heatmap(
    data: Dict[str, Dict[str, float]],
    title: str = "",
    figsize: Tuple[float, float] = (10, 5),
    dpi: int = 200,
    name: str = "heatmap"
) -> str:
    """Render a heatmap from branch×subject data. Returns path to PNG."""
    _setup_style()

    if not data:
        return render_bar_chart(["No Data"], [0], title=title, name=name)

    rows = sorted(data.keys())
    cols = sorted(set(col for row_data in data.values() for col in row_data.keys()))

    if not cols:
        return render_bar_chart(["No Data"], [0], title=title, name=name)

    matrix = []
    for row in rows:
        row_vals = [data[row].get(col, 0.0) for col in cols]
        matrix.append(row_vals)

    matrix_np = np.array(matrix)

    # Truncate labels for readability
    col_labels = [c[:8] for c in cols]

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    cmap = LinearSegmentedColormap.from_list("custom", ['#E11D4C', '#F59E0B', '#059669'])
    im = ax.imshow(matrix_np, cmap=cmap, aspect='auto', vmin=0, vmax=10)

    ax.set_xticks(np.arange(len(col_labels)))
    ax.set_yticks(np.arange(len(rows)))
    ax.set_xticklabels(col_labels, rotation=45, ha='right', fontsize=8)
    ax.set_yticklabels(rows, fontsize=9)

    # Annotate cells
    for i in range(len(rows)):
        for j in range(len(col_labels)):
            val = matrix_np[i, j]
            color = '#FFFFFF' if val < 5 else '#0F172A'
            ax.text(j, i, f'{val:.1f}', ha='center', va='center',
                    fontsize=7, fontweight='bold', color=color)

    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.ax.tick_params(colors='#94A3B8', labelsize=8)
    cbar.set_label('Grade Points', color='#CBD5E1', fontsize=9)

    if title:
        ax.set_title(title, fontweight='bold', fontsize=13, pad=15, color='#F1F5F9')

    plt.tight_layout()
    path = get_temp_chart_path(name)
    fig.savefig(path, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    return path


def render_gauge_chart(
    value: float,
    max_val: float = 100.0,
    title: str = "",
    label: str = "",
    figsize: Tuple[float, float] = (5, 4),
    dpi: int = 200,
    name: str = "gauge"
) -> str:
    """Render a gauge/semicircle meter chart. Returns path to PNG."""
    _setup_style()
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    # Draw background arc
    theta1, theta2 = 0, 180
    arc_bg = Arc((0.5, 0.3), 0.7, 0.7, angle=0, theta1=theta1, theta2=theta2,
                  color='#334155', linewidth=20, fill=False)
    ax.add_patch(arc_bg)

    # Draw value arc
    value_angle = (value / max_val) * 180
    color = '#22C55E' if value >= 75 else '#F59E0B' if value >= 50 else '#EF4444'
    arc_val = Arc((0.5, 0.3), 0.7, 0.7, angle=0, theta1=180 - value_angle, theta2=180,
                   color=color, linewidth=20, fill=False)
    ax.add_patch(arc_val)

    # Value text
    ax.text(0.5, 0.32, f'{value:.1f}%', ha='center', va='center',
            fontsize=28, fontweight='bold', color='#F1F5F9')
    if label:
        ax.text(0.5, 0.18, label, ha='center', va='center',
                fontsize=10, color='#94A3B8')
    if title:
        ax.set_title(title, fontweight='bold', fontsize=13, pad=15, color='#F1F5F9')

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 0.75)
    ax.set_aspect('equal')
    ax.axis('off')
    plt.tight_layout()

    path = get_temp_chart_path(name)
    fig.savefig(path, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    return path


def render_histogram(
    values: List[float],
    title: str = "",
    xlabel: str = "",
    ylabel: str = "Frequency",
    bins: int = 10,
    figsize: Tuple[float, float] = (7, 4),
    dpi: int = 200,
    name: str = "histogram"
) -> str:
    """Render a histogram. Returns path to PNG."""
    _setup_style()
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    if not values:
        values = [0]

    n, bins_out, patches = ax.hist(
        values, bins=bins, color='#6366F1', edgecolor='#0F172A',
        alpha=0.85, linewidth=1.5
    )

    # Gradient color based on height
    max_n = max(n) if max(n) > 0 else 1
    for count, patch in zip(n, patches):
        fraction = count / max_n
        r = 0.388 + fraction * 0.200
        g = 0.400 - fraction * 0.200
        b = 0.945 - fraction * 0.100
        patch.set_facecolor((r, g, b))

    ax.set_xlabel(xlabel, fontweight='bold')
    ax.set_ylabel(ylabel, fontweight='bold')
    if title:
        ax.set_title(title, fontweight='bold', fontsize=13, pad=15, color='#F1F5F9')

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()

    path = get_temp_chart_path(name)
    fig.savefig(path, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    return path


def render_scatter_chart(
    x_vals: List[float],
    y_vals: List[float],
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    figsize: Tuple[float, float] = (7, 5),
    dpi: int = 200,
    name: str = "scatter"
) -> str:
    """Render a scatter plot. Returns path to PNG."""
    _setup_style()
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    ax.scatter(x_vals, y_vals, c='#6366F1', s=60, alpha=0.7,
               edgecolors='#A5B4FC', linewidth=0.5)

    # Trend line
    if len(x_vals) > 1:
        z = np.polyfit(x_vals, y_vals, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(x_vals), max(x_vals), 100)
        ax.plot(x_line, p(x_line), '--', color='#F59E0B', linewidth=1.5, alpha=0.7, label='Trend')
        ax.legend()

    ax.set_xlabel(xlabel, fontweight='bold')
    ax.set_ylabel(ylabel, fontweight='bold')
    if title:
        ax.set_title(title, fontweight='bold', fontsize=13, pad=15, color='#F1F5F9')

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()

    path = get_temp_chart_path(name)
    fig.savefig(path, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    return path


def render_line_chart(
    x_labels: List[str],
    series: Dict[str, List[float]],
    title: str = "",
    ylabel: str = "",
    figsize: Tuple[float, float] = (8, 4.5),
    dpi: int = 200,
    name: str = "line"
) -> str:
    """Render a multi-series line chart. Returns path to PNG."""
    _setup_style()
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    x = np.arange(len(x_labels))
    for i, (label, vals) in enumerate(series.items()):
        color = PALETTE_HEX[i % len(PALETTE_HEX)]
        ax.plot(x, vals, 'o-', color=color, linewidth=2, markersize=6, label=label)
        # Fill area under
        ax.fill_between(x, vals, alpha=0.08, color=color)

    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=30, ha='right')
    ax.set_ylabel(ylabel, fontweight='bold')
    if title:
        ax.set_title(title, fontweight='bold', fontsize=13, pad=15, color='#F1F5F9')

    ax.legend(loc='upper right')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()

    path = get_temp_chart_path(name)
    fig.savefig(path, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    return path
