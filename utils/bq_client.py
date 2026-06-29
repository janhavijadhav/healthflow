from __future__ import annotations

import json
import os

import pandas as pd
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

PROJECT  = "healthflow-analytics-500100"
DATASET  = "healthflow_dev_marts"
CLAIMS   = f"`{PROJECT}.{DATASET}.mart_claims_summary`"
PATIENTS = f"`{PROJECT}.{DATASET}.mart_patient_metrics`"


@st.cache_resource
def get_bq_client() -> bigquery.Client:
    """Return a BigQuery client.

    Priority:
    1. Streamlit Cloud  → st.secrets["gcp_service_account"]
    2. Local dev        → gcp-key.json in project root
    3. Fallback         → Application Default Credentials (gcloud auth)
    """
    try:
        info = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/bigquery"],
        )
        return bigquery.Client(credentials=creds, project=PROJECT)
    except (KeyError, AttributeError):
        pass

    key_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gcp-key.json")
    if os.path.exists(key_path):
        with open(key_path) as f:
            info = json.load(f)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/bigquery"],
        )
        return bigquery.Client(credentials=creds, project=PROJECT)

    return bigquery.Client(project=PROJECT)


@st.cache_data(ttl=3600, show_spinner=False)
def bq(sql: str) -> pd.DataFrame:
    """Execute SQL against BigQuery. Results are cached for 1 hour."""
    return get_bq_client().query(sql).to_dataframe()
