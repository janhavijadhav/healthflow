import os
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

GCP_PROJECT = os.getenv("GCP_PROJECT", "healthflow-analytics-500100")
BQ_DATASET  = os.getenv("BQ_DATASET",  "healthflow_dev")

app = FastAPI(
    title="HealthFlow Analytics API",
    description="REST API for healthcare claims analytics powered by BigQuery",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_bq_client():
    return bigquery.Client(project=GCP_PROJECT)

@app.get("/health")
def health_check():
    return {
        "status":      "healthy",
        "service":     "healthflow-api",
        "timestamp":   datetime.utcnow().isoformat(),
        "version":     "1.0.0",
        "gcp_project": GCP_PROJECT,
        "bq_dataset":  BQ_DATASET,
    }

@app.get("/claims/summary")
def claims_summary(
    limit:           int            = Query(100, ge=1, le=1000),
    encounter_class: Optional[str]  = Query(None),
    cost_tier:       Optional[str]  = Query(None),
    age_group:       Optional[str]  = Query(None),
):
    client  = get_bq_client()
    filters = []
    if encounter_class:
        filters.append(f"encounter_class = '{encounter_class}'")
    if cost_tier:
        filters.append(f"cost_tier = '{cost_tier}'")
    if age_group:
        filters.append(f"age_group = '{age_group}'")
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    query = f"""
        SELECT
            encounter_id, patient_id, encounter_class,
            encounter_date, total_claim_cost, payer_coverage,
            out_of_pocket, cost_tier, age_group, gender, state
        FROM `{GCP_PROJECT}.{BQ_DATASET}_marts.mart_claims_summary`
        {where}
        ORDER BY encounter_date DESC
        LIMIT {limit}
    """
    rows = list(client.query(query).result())
    return {"total": len(rows), "claims": [dict(r) for r in rows]}

@app.get("/claims/stats")
def claims_stats():
    client = get_bq_client()
    query  = f"""
        SELECT
            encounter_class,
            cost_tier,
            age_group,
            COUNT(*)                        AS total_claims,
            ROUND(AVG(total_claim_cost), 2) AS avg_cost,
            ROUND(SUM(total_claim_cost), 2) AS total_cost,
            ROUND(AVG(out_of_pocket), 2)    AS avg_out_of_pocket
        FROM `{GCP_PROJECT}.{BQ_DATASET}_marts.mart_claims_summary`
        GROUP BY encounter_class, cost_tier, age_group
        ORDER BY total_claims DESC
    """
    rows = list(client.query(query).result())
    return {"stats": [dict(r) for r in rows]}

@app.get("/patients/metrics")
def patient_metrics(
    limit:     int            = Query(50, ge=1, le=500),
    age_group: Optional[str]  = Query(None),
    state:     Optional[str]  = Query(None),
):
    client  = get_bq_client()
    filters = []
    if age_group:
        filters.append(f"age_group = '{age_group}'")
    if state:
        filters.append(f"state = '{state}'")
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    query = f"""
        SELECT
            patient_id, gender, race, state, age_years, age_group,
            total_encounters, total_claim_cost, avg_claim_cost,
            total_out_of_pocket, emergency_visits,
            chronic_conditions, active_medications
        FROM `{GCP_PROJECT}.{BQ_DATASET}_marts.mart_patient_metrics`
        {where}
        ORDER BY total_claim_cost DESC
        LIMIT {limit}
    """
    rows = list(client.query(query).result())
    return {"total": len(rows), "patients": [dict(r) for r in rows]}

@app.get("/patients/{patient_id}")
def get_patient(patient_id: str):
    client = get_bq_client()
    query  = f"""
        SELECT *
        FROM `{GCP_PROJECT}.{BQ_DATASET}_marts.mart_patient_metrics`
        WHERE patient_id = '{patient_id}'
        LIMIT 1
    """
    rows = list(client.query(query).result())
    if not rows:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return dict(rows[0])

@app.get("/providers/top")
def top_providers(limit: int = Query(10, ge=1, le=100)):
    client = get_bq_client()
    query  = f"""
        SELECT
            provider_id,
            COUNT(*)                        AS total_claims,
            ROUND(SUM(total_claim_cost), 2) AS total_billed,
            ROUND(AVG(total_claim_cost), 2) AS avg_claim_cost,
            COUNT(DISTINCT patient_id)      AS unique_patients
        FROM `{GCP_PROJECT}.{BQ_DATASET}_marts.mart_claims_summary`
        WHERE provider_id IS NOT NULL
        GROUP BY provider_id
        ORDER BY total_billed DESC
        LIMIT {limit}
    """
    rows = list(client.query(query).result())
    return {"providers": [dict(r) for r in rows]}

@app.get("/analytics/cost-by-state")
def cost_by_state():
    client = get_bq_client()
    query  = f"""
        SELECT
            state,
            COUNT(*)                        AS total_claims,
            ROUND(SUM(total_claim_cost), 2) AS total_cost,
            ROUND(AVG(total_claim_cost), 2) AS avg_cost,
            ROUND(AVG(out_of_pocket), 2)    AS avg_out_of_pocket
        FROM `{GCP_PROJECT}.{BQ_DATASET}_marts.mart_claims_summary`
        WHERE state IS NOT NULL
        GROUP BY state
        ORDER BY total_cost DESC
    """
    rows = list(client.query(query).result())
    return {"cost_by_state": [dict(r) for r in rows]}
