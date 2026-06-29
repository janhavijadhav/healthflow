import streamlit as st
from utils.style import inject_css

st.set_page_config(
    page_title="HealthFlow Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "HealthFlow — Cloud-native healthcare claims analytics on synthetic EHR data."},
)

inject_css()

with st.sidebar:
    st.markdown("### HealthFlow")
    st.markdown(
        '<span style="color:#8892a4;font-size:0.8rem;line-height:1.6;">'
        "Healthcare Claims Analytics<br>"
        "Synthetic EHR · 14K+ records · 6 tables"
        "</span>",
        unsafe_allow_html=True,
    )
    st.divider()

pg = st.navigation(
    {
        "Analytics": [
            st.Page("pages/overview.py",  title="Overview",             default=True),
            st.Page("pages/claims.py",    title="Claims Analytics"),
            st.Page("pages/patients.py",  title="Patient Explorer"),
            st.Page("pages/providers.py", title="Provider Leaderboard"),
        ],
        "Project": [
            st.Page("pages/pipeline.py",  title="Pipeline Overview"),
        ],
    }
)

with st.sidebar:
    st.divider()
    st.caption("Data · Google BigQuery")
    st.caption("Project · healthflow-analytics-500100")
    st.divider()
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

pg.run()
