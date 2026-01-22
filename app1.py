import streamlit as st
from core.db import init_db
from core.auth import require_login, bootstrap_admin, logout_button
from core.utils import set_app_style

st.set_page_config(
    page_title="Perishables Ordering MVP",
    page_icon="📦",
    layout="wide",
)

set_app_style()
init_db()
bootstrap_admin()

user = require_login()  # returns dict {id,email,role,client_id}

# Role-based navigation hints
with st.sidebar:
    st.caption("Workspace")
    st.write(f"Signed in as **{user['email']}**")
    st.write(f"Role: **{user['role']}**")
    logout_button()

st.title("📦 Perishables Ordering MVP")
st.write(
    "Use the left sidebar to navigate. Your access is role-based; admin pages are hidden from standard users."
)

# A friendly landing card
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Status", "Online")
with col2:
    st.metric("Mode", "Pilot / MVP")
with col3:
    st.metric("Data", "CSV Upload")

st.info(
    "Start with **User Workspace** to upload data and generate ordering recommendations."
)
