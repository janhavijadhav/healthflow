import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.bq_client import CLAIMS, PATIENTS, bq
from utils.style import BLUE, COLORS, PURPLE, TEAL, XGRID, YGRID, plot_layout, section

# ---------- Data ----------

@st.cache_data(ttl=3600, show_spinner=False)
def load_kpis():
    return bq(f"""
        SELECT
            COUNT(*)                                                         AS total_claims,
            COUNT(DISTINCT patient_id)                                       AS total_patients,
            ROUND(SUM(total_claim_cost), 0)                                  AS total_cost,
            ROUND(AVG(total_claim_cost), 2)                                  AS avg_cost,
            ROUND(SUM(payer_coverage) / NULLIF(SUM(total_claim_cost),0)*100, 1) AS payer_pct,
            ROUND(AVG(out_of_pocket), 2)                                     AS avg_oop
        FROM {CLAIMS}
    """)

@st.cache_data(ttl=3600, show_spinner=False)
def load_trend():
    return bq(f"""
        SELECT
            DATE(encounter_year, encounter_month, 1)   AS month,
            COUNT(*)                                    AS claims,
            ROUND(SUM(total_claim_cost), 0)             AS total_cost
        FROM {CLAIMS}
        GROUP BY 1 ORDER BY 1
    """)

@st.cache_data(ttl=3600, show_spinner=False)
def load_tiers():
    return bq(f"SELECT cost_tier, COUNT(*) AS n FROM {CLAIMS} GROUP BY 1")

@st.cache_data(ttl=3600, show_spinner=False)
def load_classes():
    return bq(f"""
        SELECT encounter_class, COUNT(*) AS claims,
               ROUND(AVG(total_claim_cost), 0) AS avg_cost
        FROM {CLAIMS} WHERE encounter_class IS NOT NULL
        GROUP BY 1 ORDER BY claims DESC
    """)

@st.cache_data(ttl=3600, show_spinner=False)
def load_ages():
    return bq(f"""
        SELECT age_group,
               COUNT(*) AS claims,
               ROUND(AVG(total_claim_cost), 0) AS avg_cost,
               ROUND(AVG(out_of_pocket), 0)    AS avg_oop
        FROM {CLAIMS} WHERE age_group IS NOT NULL GROUP BY 1
    """)

@st.cache_data(ttl=3600, show_spinner=False)
def load_gender():
    return bq(f"""
        SELECT gender, COUNT(DISTINCT patient_id) AS patients
        FROM {PATIENTS} WHERE gender IS NOT NULL GROUP BY 1
    """)

@st.cache_data(ttl=3600, show_spinner=False)
def load_state_top():
    return bq(f"""
        SELECT state, COUNT(*) AS claims, ROUND(SUM(total_claim_cost), 0) AS total_cost
        FROM {CLAIMS} WHERE state IS NOT NULL
        GROUP BY 1 ORDER BY claims DESC LIMIT 12
    """)

# ---------- Render ----------

st.markdown("## Overview")
st.markdown('<span style="color:#8892a4;">All claims activity across the full synthetic EHR pipeline.</span>', unsafe_allow_html=True)
st.divider()

with st.spinner("Querying BigQuery..."):
    kpis    = load_kpis()
    trend   = load_trend()
    tiers   = load_tiers()
    classes = load_classes()
    ages    = load_ages()
    gender  = load_gender()
    states  = load_state_top()

o = kpis.iloc[0]

# KPIs
section("Key Metrics")
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Claims",    f"{int(o['total_claims']):,}")
c2.metric("Unique Patients", f"{int(o['total_patients']):,}")
c3.metric("Total Billed",    f"${int(o['total_cost']):,}")
c4.metric("Avg Claim Cost",  f"${o['avg_cost']:,.2f}")
c5.metric("Payer Coverage",  f"{o['payer_pct']}%")
c6.metric("Avg Out-of-Pocket", f"${o['avg_oop']:,.2f}")

# Row 1 — trend + tiers
section("Volume & Cost Distribution")
col1, col2 = st.columns([3, 2])

with col1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend["month"], y=trend["claims"],
        mode="lines+markers",
        line=dict(color=BLUE, width=2.5),
        marker=dict(size=5),
        fill="tozeroy", fillcolor="rgba(0,195,255,0.07)",
        name="Claims",
        hovertemplate="%{x|%b %Y}<br>%{y:,} claims<extra></extra>",
    ))
    fig.update_layout(**plot_layout(290, "Monthly Claims Volume"), xaxis=XGRID, yaxis=YGRID)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    tier_map = {"zero_cost": "Zero", "low": "Low (<$500)", "medium": "Medium (<$5k)", "high": "High (≥$5k)"}
    tiers["label"] = tiers["cost_tier"].map(tier_map).fillna(tiers["cost_tier"])
    fig = go.Figure(go.Pie(
        labels=tiers["label"], values=tiers["n"],
        hole=0.56,
        marker=dict(colors=COLORS, line=dict(color="#0d1117", width=2)),
        hovertemplate="%{label}<br>%{value:,} claims (%{percent})<extra></extra>",
    ))
    fig.update_layout(**plot_layout(290, "Cost Tier Breakdown"),
                      legend=dict(orientation="v", x=1.0, y=0.5, font=dict(size=11)))
    st.plotly_chart(fig, use_container_width=True)

# Row 2 — encounter class + age group
section("Encounter Analysis")
col3, col4 = st.columns(2)

with col3:
    fig = px.bar(
        classes.sort_values("claims"),
        x="claims", y="encounter_class", orientation="h",
        text="claims",
        color_discrete_sequence=[BLUE],
        title="Claims by Encounter Class",
        labels={"claims": "Claims", "encounter_class": ""},
    )
    fig.update_traces(texttemplate="%{text:,}", textposition="outside", marker_line_width=0)
    fig.update_layout(**plot_layout(300), xaxis=dict(showgrid=False, zeroline=False), yaxis=dict(showgrid=False))
    st.plotly_chart(fig, use_container_width=True)

with col4:
    age_map = {"pediatric": "Pediatric (<18)", "adult": "Adult (18-64)", "senior": "Senior (65+)"}
    ages["label"] = ages["age_group"].map(age_map).fillna(ages["age_group"])
    fig = px.bar(
        ages.sort_values("avg_cost", ascending=False),
        x="label", y="avg_cost",
        text="avg_cost",
        color_discrete_sequence=[PURPLE],
        title="Avg Claim Cost by Age Group",
        labels={"label": "", "avg_cost": "Avg Cost ($)"},
    )
    fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside", marker_line_width=0)
    fig.update_layout(**plot_layout(300), xaxis=dict(showgrid=False), yaxis=dict(showgrid=False, zeroline=False))
    st.plotly_chart(fig, use_container_width=True)

# Row 3 — monthly cost + gender + top states
section("Financial & Geographic Snapshot")
col5, col6, col7 = st.columns([3, 1, 2])

with col5:
    fig = go.Figure(go.Bar(
        x=trend["month"], y=trend["total_cost"],
        marker_color=PURPLE, marker_line_width=0,
        hovertemplate="%{x|%b %Y}<br>$%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(**plot_layout(260, "Monthly Total Billed"),
                      xaxis=XGRID, yaxis={**YGRID, "tickprefix": "$"}, bargap=0.25)
    st.plotly_chart(fig, use_container_width=True)

with col6:
    fig = go.Figure(go.Pie(
        labels=gender["gender"], values=gender["patients"],
        hole=0.58,
        marker=dict(colors=[BLUE, "#e74c3c"], line=dict(color="#0d1117", width=2)),
        hovertemplate="%{label}<br>%{value:,} patients<extra></extra>",
    ))
    fig.update_layout(**plot_layout(260, "Gender"),
                      legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.15, font=dict(size=11)))
    st.plotly_chart(fig, use_container_width=True)

with col7:
    fig = px.bar(
        states.sort_values("claims"),
        x="claims", y="state", orientation="h",
        text="claims",
        color_discrete_sequence=[TEAL],
        title="Top States by Claims",
        labels={"claims": "Claims", "state": ""},
    )
    fig.update_traces(texttemplate="%{text:,}", textposition="outside", marker_line_width=0)
    fig.update_layout(**plot_layout(260), xaxis=dict(showgrid=False, zeroline=False), yaxis=dict(showgrid=False))
    st.plotly_chart(fig, use_container_width=True)
