"""Shared plotly style and figure export, so every notebook figure looks the same.

Importing this module sets the default plotly template to "plotly_white+stm".
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio

# shortcut: path from the source tree, like data.RAW
FIGURES = Path(__file__).resolve().parents[2] / "docs" / "figures"
MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# official STM line colours
LINE_COLORS = {
    "Ligne verte": "#008E4F",
    "Ligne orange": "#EF8122",
    "Ligne jaune": "#FFD200",
    "Ligne bleue": "#0083CA",
}
COVID_YEARS = (2020, 2021)

pio.templates["stm"] = go.layout.Template(
    layout=dict(
        font=dict(family="Helvetica, Arial, sans-serif", size=13),
        title=dict(x=0, xanchor="left"),
        margin=dict(l=60, r=20, t=90, b=50),
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0),
    )
)
pio.templates.default = "plotly_white+stm"


def shade_years(fig: go.Figure, years: tuple[int, int], label: str) -> go.Figure:
    """Grey band over a span of years on a numeric year axis (e.g. COVID, incomplete data)."""
    fig.add_vrect(
        x0=years[0] - 0.5,
        x1=years[1] + 0.5,
        fillcolor="grey",
        opacity=0.12,
        line_width=0,
        annotation_text=label,
        annotation_position="top left",
    )
    return fig


def _chrome() -> str:
    """Chrome binary for PNG export: $CHROME, the macOS app, or one on PATH."""
    candidates = [os.environ.get("CHROME"), MAC_CHROME]
    candidates += [shutil.which(n) for n in ("google-chrome", "chromium", "chromium-browser")]
    for c in candidates:
        if c and Path(c).exists():
            return c
    raise FileNotFoundError("PNG export needs Chrome: install it or set $CHROME to its binary")


def save(fig: go.Figure, name: str, width: int = 900, height: int = 450) -> go.Figure:
    """Write docs/figures/<name>.png and return fig.

    Screenshots the figure's HTML with headless Chrome. shortcut: kaleido (plotly's exporter)
    fails on this machine; switch back once a kaleido release works with current Chrome.
    """
    fig.update_layout(legend_title_text="")  # plotly express always titles the legend
    FIGURES.mkdir(parents=True, exist_ok=True)
    png = FIGURES / f"{name}.png"
    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp) / "fig.html"
        go.Figure(fig).update_layout(width=width, height=height).write_html(
            html, include_plotlyjs=True, config={"staticPlot": True}
        )
        subprocess.run(
            [
                _chrome(),
                "--headless",
                "--disable-gpu",
                "--hide-scrollbars",
                "--force-device-scale-factor=2",
                f"--window-size={width},{height}",
                "--virtual-time-budget=5000",
                f"--screenshot={png}",
                html.as_uri(),
            ],
            check=True,
            capture_output=True,
        )
    return fig
