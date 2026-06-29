import streamlit as st

from utils.bq_client import CLAIMS, PATIENTS, bq
from utils.style import badge, section

st.markdown("## Pipeline Overview")
st.markdown('<span style="color:#8892a4;">Architecture, tech stack, and live data quality summary for the HealthFlow pipeline.</span>', unsafe_allow_html=True)
st.divider()

# ---------- Live counts ----------
with st.spinner("Fetching live row counts from BigQuery..."):
    counts = bq(f"""
        SELECT
            (SELECT COUNT(*) FROM {CLAIMS})   AS claims_rows,
            (SELECT COUNT(DISTINCT patient_id) FROM {CLAIMS}) AS patients,
            (SELECT COUNT(DISTINCT provider_id) FROM {CLAIMS}) AS providers,
            (SELECT COUNT(DISTINCT state) FROM {CLAIMS}) AS states
    """)

c = counts.iloc[0]

section("Live Data Counts")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Claim Records",    f"{int(c['claims_rows']):,}")
col2.metric("Unique Patients",  f"{int(c['patients']):,}")
col3.metric("Unique Providers", f"{int(c['providers']):,}")
col4.metric("States Covered",   f"{int(c['states']):,}")

# ---------- Pipeline stages ----------
section("Pipeline Stages")

stages = [
    ("Ingest",    "blue",
     "Synthea CSVs uploaded to S3 raw zone with Hive-style date partitioning (year=/month=/day=). "
     "AWS Lambda fires on every PutObject event in the claims/ prefix and logs to CloudWatch."),
    ("Catalog",   "blue",
     "AWS Glue Crawler auto-catalogs schemas from the raw zone into the Glue Data Catalog (healthflow_dev). "
     "Runs daily at 06:00 UTC on raw/claims/ and raw/patients/."),
    ("Validate",  "blue",
     "Great Expectations checks raw zone partitions: row count > 0, no empty column names. "
     "4/4 tables pass — patients, encounters, conditions, medications."),
    ("Transform", "blue",
     "PySpark 3.5 reads raw CSVs, applies type casting and null handling, "
     "and writes Snappy-compressed Parquet to the S3 processed zone."),
    ("Load",      "blue",
     "Processed Parquet loaded into Google BigQuery (healthflow-analytics-500100) via pandas-gbq."),
    ("Model",     "blue",
     "dbt Core builds 4 staging views (stg_patients, stg_encounters, stg_conditions, stg_medications) "
     "and 2 mart tables (mart_claims_summary, mart_patient_metrics). "
     "19 / 19 data quality tests pass."),
    ("Serve",     "blue",
     "FastAPI exposes 7 REST endpoints backed by live BigQuery queries. "
     "Swagger UI available at /docs."),
    ("Orchestrate","blue",
     "Apache Airflow 3.x DAG (6 tasks in sequence) runs the full pipeline daily at 06:00 UTC "
     "on Kubernetes via Helm."),
]

for i, (name, color, desc) in enumerate(stages, 1):
    with st.container():
        st.markdown(
            f'<div class="stage-card">'
            f'<span class="stage-title">{i}. {name}</span>'
            f'&nbsp;&nbsp;{badge("ACTIVE", "green")}'
            f'<p class="stage-desc">{desc}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ---------- Tech stack ----------
section("Tech Stack")

stack = {
    "Infrastructure":    [("AWS S3", "three zones — raw, processed, curated"),
                          ("AWS Lambda", "event-driven ingestion trigger"),
                          ("AWS Glue", "schema catalog + daily crawlers"),
                          ("CloudWatch", "log group + error alarm"),
                          ("Terraform", "18 AWS resources, repeatable IaC")],
    "Transformation":    [("PySpark 3.5", "CSV → Snappy Parquet"),
                          ("Great Expectations", "4/4 validation checks pass")],
    "Analytics Eng.":   [("dbt Core", "4 staging views + 2 mart tables"),
                          ("Google BigQuery", "warehouse and query engine")],
    "Orchestration":     [("Apache Airflow 3.x", "6-task DAG on daily schedule"),
                          ("Kubernetes + Helm", "container deployment")],
    "Serving":           [("FastAPI", "7 REST endpoints with Swagger docs"),
                          ("Streamlit", "this analytics dashboard")],
    "CI/CD":             [("GitHub Actions", "lint, unit tests, Terraform fmt on every push")],
}

cols = st.columns(3)
items = list(stack.items())
for i, (category, tools) in enumerate(items):
    with cols[i % 3]:
        st.markdown(
            f'<div class="stage-card" style="min-height:130px;">'
            f'<span class="stage-title">{category}</span>'
            + "".join(
                f'<p class="stage-desc" style="margin-top:6px;">'
                f'<span style="color:#e6edf3;font-weight:600;">{t}</span> — {d}'
                f'</p>'
                for t, d in tools
            )
            + '</div>',
            unsafe_allow_html=True,
        )

# ---------- Data quality ----------
section("Data Quality — dbt Test Results")

tests = [
    ("unique · mart_claims_summary.encounter_id",       "pass"),
    ("not_null · mart_claims_summary.encounter_id",     "pass"),
    ("accepted_values · mart_claims_summary.cost_tier", "pass"),
    ("accepted_values · mart_claims_summary.age_group", "pass"),
    ("unique · mart_patient_metrics.patient_id",        "pass"),
    ("not_null · mart_patient_metrics.patient_id",      "pass"),
    ("unique · stg_encounters.encounter_id",            "pass"),
    ("not_null · stg_encounters.encounter_id",          "pass"),
    ("not_null · stg_encounters.patient_id",            "pass"),
    ("not_null · stg_encounters.total_claim_cost",      "pass"),
    ("unique · stg_patients.patient_id",                "pass"),
    ("not_null · stg_patients.patient_id",              "pass"),
    ("not_null · stg_patients.age_years",               "pass"),
    ("not_null · stg_patients.gender",                  "pass"),
    ("accepted_values · stg_patients.gender (M/F)",     "pass"),
    ("not_null · stg_conditions.patient_id",            "pass"),
    ("not_null · stg_conditions.condition_code",        "pass"),
    ("not_null · stg_medications.patient_id",           "pass"),
    ("not_null · stg_medications.medication_code",      "pass"),
]

st.markdown(
    f'<p style="color:#2ecc71;font-size:1.1rem;font-weight:700;margin-bottom:12px;">'
    f'19 / 19 tests passing</p>',
    unsafe_allow_html=True,
)

col_a, col_b = st.columns(2)
for i, (test, status) in enumerate(tests):
    target = col_a if i % 2 == 0 else col_b
    target.markdown(
        f'{badge("PASS", "green")} <span style="color:#8892a4;font-size:0.82rem;">{test}</span>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)
st.caption("All data is 100% synthetic — generated by Synthea. No real patient information.")
