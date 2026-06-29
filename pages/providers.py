import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.bq_client import CLAIMS, bq
from utils.style import BLUE, ORANGE, PURPLE, TEAL, XGRID, YGRID, plot_layout, section

# ---------- Sidebar ----------

with st.sidebar:
    st.markdown("#### Options")
    top_n = st.slider("Show top N providers", 10, 50, 25, 5)
    metric = st.selectbox("Rank by", ["Total Billed", "Total Claims", "Unique Patients", "Avg Claim Cost"])

_rank_col = {
    "Total Billed":       "total_billed",
    "Total Claims":       "total_claims",
    "Unique Patients":    "unique_patients",
    "Avg Claim Cost":     "avg_cost",
}[metric]

# ---------- Data ----------

def load_providers(n: int):
    return bq(f"""
        SELECT
            provider_id,
            COUNT(*)                         AS total_claims,
            ROUND(SUM(total_claim_cost), 0)  AS total_billed,
            ROUND(AVG(total_claim_cost), 0)  AS avg_cost,
            ROUND(SUM(payer_coverage), 0)    AS total_payer_coverage,
            ROUND(SUM(out_of_pocket), 0)     AS total_oop,
            COUNT(DISTINCT patient_id)       AS unique_patients,
            COUNT(DISTINCT encounter_class)  AS encounter_types
        FROM {CLAIMS}
        WHERE provider_id IS NOT NULL
        GROUP BY 1
        ORDER BY total_billed DESC
        LIMIT {n}
    """)

def load_kpis():
    return bq(f"""
        SELECT
            COUNT(DISTINCT provider_id)              AS total_providers,
            ROUND(AVG(total_claim_cost), 0)          AS network_avg_cost,
            ROUND(SUM(total_claim_cost), 0)          AS network_total,
            ROUND(AVG(payer_coverage / NULLIF(total_claim_cost,0))*100, 1) AS network_payer_pct
        FROM {CLAIMS}
        WHERE provider_id IS NOT NULL
    """)

# ---------- Render ----------

st.markdown("## Provider Leaderboard")
st.markdown('<span style="color:#8892a4;">Top providers ranked by billing volume, claims count, and patient reach.</span>', unsafe_allow_html=True)
st.divider()

with st.spinner("Querying BigQuery..."):
    kpis = load_kpis()
    df   = load_providers(top_n)

o = kpis.iloc[0]

section("Network Overview")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Providers",       f"{int(o['total_providers']):,}")
c2.metric("Network Total Billed",  f"${int(o['network_total']):,}")
c3.metric("Network Avg Cost",      f"${int(o['network_avg_cost']):,}")
c4.metric("Network Payer Coverage",f"{o['network_payer_pct']}%")

# Rank & shorten provider ID for display
df_sorted = df.sort_values(_rank_col, ascending=False).reset_index(drop=True)
df_sorted["rank"] = df_sorted.index + 1
df_sorted["short_id"] = df_sorted["provider_id"].str[:8] + "..."

# Row 1 — ranked bar + scatter
section(f"Top {top_n} Providers by {metric}")
col1, col2 = st.columns([3, 2])

with col1:
    fig = px.bar(
        df_sorted.sort_values(_rank_col),
        x=_rank_col, y="short_id", orientation="h",
        text=_rank_col,
        color=_rank_col, color_continuous_scale=[[0, "#161b22"], [0.4, BLUE], [1, PURPLE]],
        labels={_rank_col: metric, "short_id": "Provider"},
        hover_data={"provider_id": True, "total_claims": ":,", "unique_patients": ":,",
                    "avg_cost": ":$,.0f", "total_billed": ":$,.0f"},
        title=f"Top {top_n} Providers — {metric}",
    )
    fmt = "$%{text:,.0f}" if "Billed" in metric or "Cost" in metric else "%{text:,}"
    fig.update_traces(texttemplate=fmt, textposition="outside", marker_line_width=0)
    fig.update_coloraxes(showscale=False)
    fig.update_layout(**plot_layout(max(320, top_n * 14), f"Top {top_n} Providers — {metric}"),
                      xaxis=dict(showgrid=False, zeroline=False), yaxis=dict(showgrid=False))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.scatter(
        df_sorted,
        x="unique_patients", y="total_billed",
        size="total_claims", size_max=28,
        color="avg_cost", color_continuous_scale=[[0, "#1abc9c"], [1, "#e74c3c"]],
        hover_name="provider_id",
        hover_data={"total_claims": ":,", "avg_cost": ":$,.0f",
                    "unique_patients": ":,", "total_billed": ":$,.0f"},
        title="Unique Patients vs Total Billed",
        labels={"unique_patients": "Unique Patients", "total_billed": "Total Billed ($)",
                "avg_cost": "Avg Cost ($)"},
    )
    fig.update_traces(marker_line_width=0)
    fig.update_coloraxes(colorbar=dict(title="Avg Cost", tickprefix="$", len=0.6, thickness=10))
    fig.update_layout(**plot_layout(max(320, top_n * 14), "Unique Patients vs Total Billed"),
                      xaxis=XGRID, yaxis={**YGRID, "tickprefix": "$"})
    st.plotly_chart(fig, use_container_width=True)

# Row 2 — claims vs coverage stacked bar
section("Billing Split — Payer vs Patient Responsibility")
fig = go.Figure()
fig.add_trace(go.Bar(
    name="Payer Coverage",
    x=df_sorted["short_id"], y=df_sorted["total_payer_coverage"],
    marker_color=TEAL, marker_line_width=0,
    hovertemplate="%{x}<br>Payer: $%{y:,.0f}<extra></extra>",
))
fig.add_trace(go.Bar(
    name="Out-of-Pocket",
    x=df_sorted["short_id"], y=df_sorted["total_oop"],
    marker_color=ORANGE, marker_line_width=0,
    hovertemplate="%{x}<br>OOP: $%{y:,.0f}<extra></extra>",
))
fig.update_layout(
    **plot_layout(300, "Payer Coverage vs Out-of-Pocket by Provider"),
    barmode="stack", bargap=0.2,
    xaxis=dict(showgrid=False, zeroline=False, tickangle=-45),
    yaxis={**YGRID, "tickprefix": "$"},
    legend=dict(orientation="h", x=0, y=1.1),
)
st.plotly_chart(fig, use_container_width=True)

# Table
section(f"Provider Detail — Top {top_n}")
st.dataframe(
    df_sorted[["rank", "provider_id", "total_claims", "total_billed",
               "avg_cost", "unique_patients", "total_payer_coverage", "total_oop"]].rename(columns={
        "rank": "#", "provider_id": "Provider ID", "total_claims": "Claims",
        "total_billed": "Total Billed ($)", "avg_cost": "Avg Cost ($)",
        "unique_patients": "Unique Patients", "total_payer_coverage": "Payer Coverage ($)",
        "total_oop": "Out-of-Pocket ($)",
    }),
    use_container_width=True,
    hide_index=True,
)
