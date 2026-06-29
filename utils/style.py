from __future__ import annotations
import streamlit as st

# --- Palette ---
BLUE   = "#00c3ff"
PURPLE = "#9b59b6"
TEAL   = "#1abc9c"
ORANGE = "#f39c12"
RED    = "#e74c3c"
GREEN  = "#2ecc71"
SLATE  = "#8892a4"

COLORS = [BLUE, PURPLE, TEAL, ORANGE, RED, GREEN, "#fd79a8", "#fdcb6e"]


def fmt_money(val: float | int) -> str:
    """Abbreviate dollar amounts: $1.2M, $450K, $830."""
    if val >= 1_000_000:
        return f"${val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"${val / 1_000:.0f}K"
    return f"${val:,.0f}"


# --- Shared Plotly layout ---
def plot_layout(height: int = 300, title: str = "", **extra) -> dict:
    """Return a Plotly layout dict with sensible dark-theme defaults.

    Pass ``legend=dict(...)`` as a kwarg to *merge* with the default legend
    rather than replace it — this avoids the duplicate-keyword TypeError that
    would occur if callers spread the result and then pass ``legend=`` again.
    """
    _legend_default = dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)")
    _legend = {**_legend_default, **extra.pop("legend", {})}
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=SLATE, family="Inter, system-ui, sans-serif", size=12),
        margin=dict(l=10, r=10, t=44 if title else 16, b=10),
        height=height,
        legend=_legend,
        title=dict(text=title, font=dict(color="#c9d1d9", size=13), x=0) if title else {},
    )
    base.update(extra)
    return base

XGRID  = dict(showgrid=False, zeroline=False, linecolor="#2d3748", tickcolor="#2d3748")
YGRID  = dict(showgrid=True,  gridcolor="#21262d", zeroline=False, linecolor="#2d3748")
YNOGRID = dict(showgrid=False, zeroline=False, linecolor="#2d3748")

# --- CSS ---
CSS = """
<style>
#MainMenu, footer, header { visibility: hidden; }

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #0d1117 !important;
    border-right: 1px solid #21262d;
}

/* Metrics */
[data-testid="stMetric"] {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 14px 16px !important;
}
[data-testid="stMetricLabel"] p {
    color: #8892a4 !important;
    font-size: 0.63rem !important;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
[data-testid="stMetricValue"] {
    color: #e6edf3 !important;
    font-size: 1.45rem !important;
    line-height: 1.3 !important;
    white-space: nowrap;
}

/* Section label */
.sl {
    color: #8892a4;
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2.5px;
    margin: 22px 0 10px 0;
    padding-bottom: 7px;
    border-bottom: 1px solid #21262d;
}

/* Dividers */
hr { border-color: #21262d !important; }

/* Dataframes */
[data-testid="stDataFrame"] { border: 1px solid #21262d; border-radius: 8px; }

/* Selectbox / multiselect inputs */
[data-baseweb="select"] > div {
    background-color: #161b22 !important;
    border-color: #30363d !important;
}

/* Status badges */
.badge { display:inline-block; padding:3px 9px; border-radius:12px;
         font-size:0.68rem; font-weight:700; letter-spacing:0.4px; }
.b-green  { background:rgba(46,204,113,.15);  color:#2ecc71; }
.b-blue   { background:rgba(0,195,255,.12);   color:#00c3ff; }
.b-purple { background:rgba(155,89,182,.18);  color:#c39bd3; }
.b-orange { background:rgba(243,156,18,.15);  color:#f39c12; }
.b-slate  { background:rgba(136,146,164,.12); color:#8892a4; }

/* Pipeline stage cards */
.stage-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 10px;
}
.stage-title { color:#e6edf3; font-weight:600; font-size:0.9rem; }
.stage-desc  { color:#8892a4; font-size:0.8rem; margin-top:4px; }
</style>
"""

def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)

def page_header(title: str, subtitle: str = ""):
    sub = f'<p style="color:#8892a4;font-size:0.85rem;margin:6px 0 0 0;line-height:1.5;">{subtitle}</p>' if subtitle else ""
    st.markdown(f"""
    <div style="margin-bottom:20px;">
      <span style="font-size:0.65rem;font-weight:700;letter-spacing:2.5px;
                   color:#00c3ff;text-transform:uppercase;display:block;margin-bottom:6px;">
        HealthFlow Analytics
      </span>
      <h1 style="color:#e6edf3;font-size:1.9rem;font-weight:700;margin:0;line-height:1.2;">{title}</h1>
      {sub}
    </div>
    <hr style="border-color:#21262d;margin:0 0 24px 0;">
    """, unsafe_allow_html=True)

def section(label: str):
    st.markdown(f'<p class="sl">{label}</p>', unsafe_allow_html=True)

def badge(text: str, kind: str = "blue") -> str:
    return f'<span class="badge b-{kind}">{text}</span>'
