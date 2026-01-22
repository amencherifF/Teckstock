import streamlit as st
from core.auth import require_login, require_admin, hash_pw
from core.db import exec_one, exec_all, now_iso, log_event

user = require_login()
require_admin(user)

st.title("👤 Admin — Users & Clients")

st.subheader("Create client")
client_name = st.text_input("Client name", placeholder="Monoprix Tunisia")
if st.button("Create client"):
    if client_name.strip():
        exec_one("INSERT INTO clients(name, created_at) VALUES(?,?)", (client_name.strip(), now_iso()))
        log_event(user["id"], None, "admin_create_client", client_name.strip())
        st.success("Client created.")
        st.rerun()

st.divider()

st.subheader("Create user")
clients = exec_all("SELECT id, name FROM clients ORDER BY name")
client_options = {"(none)": None, **{name: cid for cid, name in clients}}

email = st.text_input("User email", placeholder="tester@company.com")
password = st.text_input("Temporary password", type="password")
role = st.selectbox("Role", ["user", "admin"])
client_pick = st.selectbox("Client (for user role)", list(client_options.keys()))
client_id = client_options[client_pick]

if st.button("Create user", type="primary"):
    if not email.strip() or not password:
        st.error("Email and password are required.")
    else:
        exec_one(
            "INSERT INTO users(email, password_hash, role, client_id, created_at) VALUES(?,?,?,?,?)",
            (email.strip().lower(), hash_pw(password), role, client_id if role == "user" else None, now_iso())
        )
        log_event(user["id"], None, "admin_create_user", email.strip().lower())
        st.success("User created.")
        st.rerun()

st.divider()
st.subheader("Existing users")
rows = exec_all("""
SELECT u.id, u.email, u.role, c.name, u.created_at
FROM users u
LEFT JOIN clients c ON c.id = u.client_id
ORDER BY u.created_at DESC
""")
st.dataframe(rows, use_container_width=True)
