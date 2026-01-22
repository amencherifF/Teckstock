import streamlit as st
import json
from core.auth import require_login
from core.db import exec_all

user = require_login()
st.title("🕒 History")

if user["role"] == "admin":
    st.info("Admins can see all runs in the Admin Dashboard.")
    st.stop()

rows = exec_all(
    "SELECT created_at, params_json, result_summary_json FROM runs WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
    (user["id"],)
)

if not rows:
    st.write("No runs yet.")
    st.stop()

for created_at, params_json, summary_json in rows:
    params = json.loads(params_json)
    summary = json.loads(summary_json)
    with st.expander(f"Run at {created_at} — Total order: {summary['total_recommended_order']}"):
        st.write("Parameters:", params)
        st.write("Summary:", summary)
