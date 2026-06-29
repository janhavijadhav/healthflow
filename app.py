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
    st.markdown("""
    <div style="padding:4px 0 20px 0;border-bottom:1px solid #21262d;margin-bottom:4px;">
        <div style="font-size:0.6rem;font-weight:700;letter-spacing:2.5px;
                    color:#00c3ff;text-transform:uppercase;margin-bottom:6px;">
            HealthFlow
        </div>
        <div style="font-size:1.15rem;font-weight:700;color:#e6edf3;line-height:1.3;">
            Analytics Dashboard
        </div>
        <div style="font-size:0.72rem;color:#8892a4;margin-top:5px;line-height:1.5;">
            Synthetic EHR &middot; BigQuery<br>
            6,000+ claims &middot; 111 patients
        </div>
    </div>
    """, unsafe_allow_html=True)

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
