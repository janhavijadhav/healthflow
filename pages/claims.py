import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.bq_client import CLAIMS, bq
from utils.style import BLUE, COLORS, ORANGE, PURPLE, TEAL, XGRID, YGRID, plot_layout, section

# ---------- Sidebar filters ----------

with st.sidebar:
    st.markdown("#### Filters")

    all_classes = ["ambulatory", "emergency", "inpatient", "outpatient", "urgentcare", "wellness"]
    sel_class = st.multiselect("Encounter Class", all_classes, default=all_classes)

    all_tiers = ["zero_cost", "low", "medium", "high"]
    tier_labels = {"zero_cost": "Zero", "low": "Low (<$500)", "medium": "Medium (<$5k)", "high": "High (≥$5k)"}
    sel_tier = st.multiselect("Cost Tier", all_tiers, default=all_tiers,
                               format_func=lambda x: tier_labels.get(x, x))

    all_ages = ["pediatric", "adult", "senior"]
    age_labels = {"pediatric": "Pediatric (<18)", "adult": "Adult (18–64)", "senior": "Senior (65+)"}
    sel_age = st.multiselect("Age Group", all_ages, default=all_ages,
                              format_func=lambda x: age_labels.get(x, x))

    st.divider()
    max_rows = st.slider("Table rows", 50, 1000, 200, 50)


def _in(col: str, vals: list) -> str:
    quoted = ", ".join(f"'{v}'" for v in vals)
    return f"{col} IN ({quoted})"


WHERE = (
    f"WHERE {_in('encounter_class', sel_class or all_classes)}"
    f"  AND {_in('cost_tier', sel_tier or all_tiers)}"
    f"  AND {_in('age_group', sel_age or all_ages)}"
)

# ---------- Data ----------

def load_kpis(where: str):
    return bq(f"""
        SELECT
            COUNT(*)                                                            AS claims,
            ROUND(AVG(total_claim_cost), 2)                                     AS avg_cost,
            ROUND(SUM(payer_coverage) / NULLIF(SUM(total_claim_cost),0)*100, 1) AS payer_pct,
            ROUND(AVG(out_of_pocket), 2)                                        AS avg_oop,
            ROUND(SUM(total_claim_cost), 0)                                     AS total_cost
        FROM {CLAIMS} {where}
    """)

def load_state_cost(where: str):
    return bq(f"""
        SELECT state,
               COUNT(*)                          AS claims,
               ROUND(SUM(total_claim_cost), 0)   AS total_cost,
               ROUND(AVG(total_claim_cost), 0)   AS avg_cost,
               ROUND(AVG(out_of_pocket), 0)      AS avg_oop
        FROM {CLAIMS} {where} AND state IS NOT NULL
        GROUP BY 1 ORDER BY total_cost DESC LIMIT 15
    """)

def load_class_split(where: str):
    return bq(f"""
        SELECT encounter_class,
               ROUND(AVG(payer_coverage), 0) AS avg_payer,
               ROUND(AVG(out_of_pocket), 0)  AS avg_oop
        FROM {CLAIMS} {where} AND encounter_class IS NOT NULL
        GROUP BY 1 ORDER BY avg_payer DESC
    """)

def load_trend(where: str):
    return bq(f"""
        SELECT DATE(encounter_year, encounter_month, 1) AS month,
               COUNT(*) AS claims,
               ROUND(AVG(total_claim_cost), 0) AS avg_cost
        FROM {CLAIMS} {where}
        GROUP BY 1 ORDER BY 1
    """)

def load_table(where: str, limit: int):
    return bq(f"""
        SELECT
            encounter_id, encounter_class, encounter_date,
            state, age_group, gender,
            total_claim_cost, payer_coverage, out_of_pocket, cost_tier
        FROM {CLAIMS} {where}
        ORDER BY encounter_date DESC
        LIMIT {limit}
    """)

# ---------- Render ----------

st.markdown("## Claims Analytics")
st.markdown('<span style="color:#8892a4;">Drill into claims data with encounter class, cost tier, and age group filters.</span>', unsafe_allow_html=True)
st.divider()

with st.spinner("Querying BigQuery..."):
    kpis       = load_kpis(WHERE)
    state_cost = load_state_cost(WHERE.replace("WHERE", "WHERE", 1))
    cls_split  = load_class_split(WHERE.replace("WHERE", "WHERE", 1))
    trend      = load_trend(WHERE)
    table      = load_table(WHERE, max_rows)

o = kpis.iloc[0]

section("Filtered Metrics")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Claims",        f"{int(o['claims']):,}")
c2.metric("Total Billed",  f"${int(o['total_cost']):,}")
c3.metric("Avg Cost",      f"${o['avg_cost']:,.2f}")
c4.metric("Payer Coverage",f"{o['payer_pct']}%")
c5.metric("Avg Out-of-Pocket", f"${o['avg_oop']:,.2f}")

# Row 1 — state + class split
section("Geographic & Coverage Breakdown")
col1, col2 = st.columns([3, 2])

with col1:
    fig = px.bar(
        state_cost.sort_values("total_cost"),
        x="total_cost", y="state", orientation="h",
        text="total_cost",
        color="avg_cost", color_continuous_scale=[[0, "#161b22"], [1, BLUE]],
        title="Total Cost by State (Top 15)",
        labels={"total_cost": "Total Billed ($)", "state": "", "avg_cost": "Avg Cost"},
        hover_data={"avg_cost": ":$,.0f", "claims": ":,", "total_cost": ":$,.0f"},
    )
    fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside", marker_line_width=0)
    fig.update_coloraxes(showscale=False)
    fig.update_layout(**plot_layout(380, "Total Cost by State (Top 15)"),
                      xaxis=dict(showgrid=False, zeroline=False), yaxis=dict(showgrid=False))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Payer Coverage", x=cls_split["encounter_class"],
                         y=cls_split["avg_payer"], marker_color=TEAL, marker_line_width=0))
    fig.add_trace(go.Bar(name="Out-of-Pocket",  x=cls_split["encounter_class"],
                         y=cls_split["avg_oop"],   marker_color=ORANGE, marker_line_width=0))
    fig.update_layout(**plot_layout(380, "Avg Coverage vs Out-of-Pocket by Class",
                                    barmode="group", xaxis=XGRID, yaxis={**YGRID, "tickprefix": "$"},
                                    legend=dict(orientation="h", x=0, y=1.12)))
    st.plotly_chart(fig, use_container_width=True)

# Row 2 — trend
section("Claims Trend (Filtered)")
col3, col4 = st.columns(2)

with col3:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend["month"], y=trend["claims"],
        mode="lines+markers", line=dict(color=BLUE, width=2.5), marker=dict(size=5),
        fill="tozeroy", fillcolor="rgba(0,195,255,0.07)",
        hovertemplate="%{x|%b %Y}<br>%{y:,} claims<extra></extra>",
    ))
    fig.update_layout(**plot_layout(260, "Monthly Claims"), xaxis=XGRID, yaxis=YGRID)
    st.plotly_chart(fig, use_container_width=True)

with col4:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend["month"], y=trend["avg_cost"],
        mode="lines+markers", line=dict(color=PURPLE, width=2.5), marker=dict(size=5),
        fill="tozeroy", fillcolor="rgba(155,89,182,0.07)",
        hovertemplate="%{x|%b %Y}<br>$%{y:,.0f} avg cost<extra></extra>",
    ))
    fig.update_layout(**plot_layout(260, "Monthly Avg Claim Cost"),
                      xaxis=XGRID, yaxis={**YGRID, "tickprefix": "$"})
    st.plotly_chart(fig, use_container_width=True)

# Table
section(f"Claims Detail — {len(table):,} rows")
st.dataframe(
    table.rename(columns={
        "encounter_id": "Encounter ID", "encounter_class": "Class",
        "encounter_date": "Date", "state": "State", "age_group": "Age Group",
        "gender": "Gender", "total_claim_cost": "Total Cost ($)",
        "payer_coverage": "Payer Coverage ($)", "out_of_pocket": "Out-of-Pocket ($)",
        "cost_tier": "Cost Tier",
    }),
    use_container_width=True,
    hide_index=True,
)
