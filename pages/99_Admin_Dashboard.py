import streamlit as st
import pandas as pd
import json
from core.auth import require_login, require_admin
from core.db import exec_all

user = require_login()
require_admin(user)

st.title("🛡️ Admin Dashboard")

# High-level KPIs
runs_today = exec_all("SELECT COUNT(*) FROM runs WHERE substr(created_at,1,10)=substr(datetime('now'),1,10)")
uploads_today = exec_all("SELECT COUNT(*) FROM uploads WHERE substr(created_at,1,10)=substr(datetime('now'),1,10)")
users_count = exec_all("SELECT COUNT(*) FROM users")
events_count = exec_all("SELECT COUNT(*) FROM events")

k1,k2,k3,k4 = st.columns(4)
k1.metric("Runs (today)", runs_today[0][0])
k2.metric("Uploads (today)", uploads_today[0][0])
k3.metric("Users", users_count[0][0])
k4.metric("Events logged", events_count[0][0])

st.subheader("Recent runs")
rows = exec_all("""
SELECT r.created_at, u.email, u.role, c.name, r.params_json, r.result_summary_json
FROM runs r
LEFT JOIN users u ON u.id = r.user_id
LEFT JOIN clients c ON c.id = r.client_id
ORDER BY r.created_at DESC
LIMIT 100
""")

if rows:
    data = []
    for created_at, email, role, client_name, params_json, summary_json in rows:
        params = json.loads(params_json)
        summary = json.loads(summary_json)
        data.append({
            "created_at": created_at,
            "email": email,
            "role": role,
            "client": client_name,
            "R": params.get("R"),
            "beta": params.get("beta"),
            "moq": params.get("moq"),
            "use_ml": summary.get("use_ml"),
            "total_recommended_order": summary.get("total_recommended_order"),
            "avg_waste_risk": summary.get("avg_waste_risk"),
            "high_risk_skus": summary.get("high_risk_skus"),
        })
    st.dataframe(pd.DataFrame(data), use_container_width=True)
else:
    st.write("No runs yet.")

st.subheader("Recent events (usage tracking)")
ev = exec_all("""
SELECT e.created_at, u.email, c.name, e.event_name, e.event_json
FROM events e
LEFT JOIN users u ON u.id = e.user_id
LEFT JOIN clients c ON c.id = e.client_id
ORDER BY e.created_at DESC
LIMIT 200
""")
if ev:
    st.dataframe(pd.DataFrame(ev, columns=["created_at","email","client","event_name","event_json"]), use_container_width=True)
