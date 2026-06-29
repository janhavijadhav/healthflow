import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.bq_client import PATIENTS, bq
from utils.style import BLUE, COLORS, GREEN, ORANGE, PURPLE, RED, TEAL, XGRID, YGRID, plot_layout, section

# ---------- Sidebar ----------

with st.sidebar:
    st.markdown("#### Filters")

    states_raw = bq(f"SELECT DISTINCT state FROM {PATIENTS} WHERE state IS NOT NULL ORDER BY 1")
    all_states = states_raw["state"].tolist()
    sel_state = st.multiselect("State", all_states, default=[])

    sel_age = st.multiselect(
        "Age Group", ["pediatric", "adult", "senior"], default=[],
        format_func=lambda x: {"pediatric": "Pediatric (<18)", "adult": "Adult (18–64)", "senior": "Senior (65+)"}[x],
    )
    sel_gender = st.multiselect("Gender", ["M", "F"], default=[])

    st.divider()
    max_rows = st.slider("Table rows", 50, 500, 100, 50)


def _where():
    clauses = []
    if sel_state:
        q = ", ".join(f"'{s}'" for s in sel_state)
        clauses.append(f"state IN ({q})")
    if sel_age:
        q = ", ".join(f"'{a}'" for a in sel_age)
        clauses.append(f"age_group IN ({q})")
    if sel_gender:
        q = ", ".join(f"'{g}'" for g in sel_gender)
        clauses.append(f"gender IN ({q})")
    return "WHERE " + " AND ".join(clauses) if clauses else ""


WHERE = _where()

# ---------- Data ----------

def load_kpis(where: str):
    return bq(f"""
        SELECT
            COUNT(*)                                     AS total_patients,
            ROUND(AVG(total_encounters), 1)              AS avg_encounters,
            ROUND(AVG(chronic_conditions), 1)            AS avg_chronic,
            ROUND(AVG(active_medications), 1)            AS avg_meds,
            ROUND(AVG(total_claim_cost), 0)              AS avg_cost,
            ROUND(COUNTIF(emergency_visits > 0) / COUNT(*) * 100, 1) AS pct_emergency,
            ROUND(AVG(total_out_of_pocket), 0)           AS avg_oop
        FROM {PATIENTS} {where}
    """)

def load_race(where: str):
    return bq(f"""
        SELECT race, COUNT(*) AS patients,
               ROUND(AVG(total_claim_cost), 0) AS avg_cost
        FROM {PATIENTS} {where}
        WHERE race IS NOT NULL {'AND' if where else 'WHERE'} 1=1
        GROUP BY 1 ORDER BY patients DESC
    """).head(10) if not where else bq(f"""
        SELECT race, COUNT(*) AS patients,
               ROUND(AVG(total_claim_cost), 0) AS avg_cost
        FROM {PATIENTS} {where} AND race IS NOT NULL
        GROUP BY 1 ORDER BY patients DESC LIMIT 10
    """)

def load_age_dist(where: str):
    return bq(f"""
        SELECT age_years, COUNT(*) AS n
        FROM {PATIENTS} {where if where else 'WHERE 1=1'}
        {'AND' if where else 'AND'} age_years IS NOT NULL
        GROUP BY 1 ORDER BY 1
    """)

def load_scatter(where: str):
    return bq(f"""
        SELECT patient_id, age_group, gender,
               total_encounters, total_claim_cost, chronic_conditions,
               active_medications, emergency_visits
        FROM {PATIENTS} {where if where else ''}
        LIMIT 800
    """)

def load_conditions(where: str):
    return bq(f"""
        SELECT chronic_conditions, COUNT(*) AS patients
        FROM {PATIENTS} {where if where else ''}
        {'WHERE' if not where else 'AND'} chronic_conditions IS NOT NULL
        GROUP BY 1 ORDER BY 1
    """)

def load_table(where: str, limit: int):
    return bq(f"""
        SELECT patient_id, gender, race, state, age_years, age_group,
               total_encounters, total_claim_cost, avg_claim_cost,
               total_out_of_pocket, emergency_visits, chronic_conditions, active_medications
        FROM {PATIENTS} {where}
        ORDER BY total_claim_cost DESC LIMIT {limit}
    """)

# ---------- Render ----------

st.markdown("## Patient Explorer")
st.markdown('<span style="color:#8892a4;">Per-patient rollup of encounters, conditions, and medications.</span>', unsafe_allow_html=True)
st.divider()


def _fix_where(where: str, extra: str) -> str:
    """Append an AND clause cleanly whether WHERE exists or not."""
    return where + f" AND {extra}" if where else f"WHERE {extra}"


with st.spinner("Querying BigQuery..."):
    kpis    = load_kpis(WHERE)
    scatter = load_scatter(WHERE)
    cond    = load_conditions(WHERE)
    table   = load_table(WHERE, max_rows)

    # race / age_dist need the "IS NOT NULL" logic already in the SQL
    race_df = bq(
        f"SELECT race, COUNT(*) AS patients, ROUND(AVG(total_claim_cost),0) AS avg_cost "
        f"FROM {PATIENTS} {_fix_where(WHERE,'race IS NOT NULL')} GROUP BY 1 ORDER BY patients DESC LIMIT 10"
    )
    age_df = bq(
        f"SELECT age_years, COUNT(*) AS n FROM {PATIENTS} "
        f"{_fix_where(WHERE,'age_years IS NOT NULL')} GROUP BY 1 ORDER BY 1"
    )

o = kpis.iloc[0]

section("Key Metrics")
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("Patients",         f"{int(o['total_patients']):,}")
c2.metric("Avg Encounters",   f"{o['avg_encounters']}")
c3.metric("Avg Chronic Conds",f"{o['avg_chronic']}")
c4.metric("Avg Active Meds",  f"{o['avg_meds']}")
c5.metric("Avg Claim Cost",   f"${int(o['avg_cost']):,}")
c6.metric("Avg Out-of-Pocket",f"${int(o['avg_oop']):,}")
c7.metric("% With Emergency", f"{o['pct_emergency']}%")

# Row 1 — age dist + race
section("Demographics")
col1, col2 = st.columns(2)

with col1:
    fig = px.histogram(
        age_df, x="age_years", y="n", nbins=30,
        color_discrete_sequence=[BLUE],
        title="Patient Age Distribution",
        labels={"age_years": "Age (years)", "n": "Patients"},
    )
    fig.update_traces(marker_line_width=0)
    fig.update_layout(**plot_layout(280, "Patient Age Distribution"), xaxis=XGRID, yaxis=YGRID)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.bar(
        race_df.sort_values("patients"),
        x="patients", y="race", orientation="h",
        text="patients",
        color="avg_cost", color_continuous_scale=[[0, "#161b22"], [1, PURPLE]],
        title="Patients by Race / Ethnicity",
        labels={"patients": "Patients", "race": "", "avg_cost": "Avg Cost ($)"},
    )
    fig.update_traces(texttemplate="%{text:,}", textposition="outside", marker_line_width=0)
    fig.update_coloraxes(showscale=False)
    fig.update_layout(**plot_layout(280), xaxis=dict(showgrid=False, zeroline=False), yaxis=dict(showgrid=False))
    st.plotly_chart(fig, use_container_width=True)

# Row 2 — encounter vs cost scatter + chronic conditions
section("Clinical Profile")
col3, col4 = st.columns(2)

with col3:
    age_color = {"pediatric": TEAL, "adult": BLUE, "senior": ORANGE}
    scatter["color"] = scatter["age_group"].map(age_color).fillna(BLUE)
    fig = px.scatter(
        scatter,
        x="total_encounters", y="total_claim_cost",
        color="age_group",
        color_discrete_map={"pediatric": TEAL, "adult": BLUE, "senior": ORANGE},
        size="chronic_conditions", size_max=20,
        opacity=0.7,
        hover_data={"patient_id": True, "emergency_visits": True, "active_medications": True,
                    "total_claim_cost": ":$,.0f"},
        title="Encounters vs Total Claim Cost",
        labels={"total_encounters": "Total Encounters", "total_claim_cost": "Total Claim Cost ($)",
                "age_group": "Age Group"},
    )
    fig.update_traces(marker_line_width=0)
    fig.update_layout(**plot_layout(300, "Encounters vs Total Claim Cost"),
                      xaxis=XGRID, yaxis={**YGRID, "tickprefix": "$"})
    st.plotly_chart(fig, use_container_width=True)

with col4:
    fig = px.bar(
        cond, x="chronic_conditions", y="patients",
        text="patients",
        color_discrete_sequence=[RED],
        title="Patients by Chronic Condition Count",
        labels={"chronic_conditions": "Chronic Conditions", "patients": "Patients"},
    )
    fig.update_traces(texttemplate="%{text:,}", textposition="outside", marker_line_width=0)
    fig.update_layout(**plot_layout(300), xaxis=dict(showgrid=False), yaxis=dict(showgrid=False, zeroline=False))
    st.plotly_chart(fig, use_container_width=True)

# Table
section(f"Patient Detail — {len(table):,} rows (ranked by total claim cost)")
st.dataframe(
    table.rename(columns={
        "patient_id": "Patient ID", "gender": "Gender", "race": "Race",
        "state": "State", "age_years": "Age", "age_group": "Age Group",
        "total_encounters": "Encounters", "total_claim_cost": "Total Cost ($)",
        "avg_claim_cost": "Avg Cost ($)", "total_out_of_pocket": "Total OOP ($)",
        "emergency_visits": "ER Visits", "chronic_conditions": "Chronic Conds",
        "active_medications": "Active Meds",
    }),
    use_container_width=True,
    hide_index=True,
)
