import streamlit as st
import hashlib
import json
from core.db import exec_one, exec_all, now_iso, log_event

def _pepper():
    return st.secrets.get("APP_PEPPER", "default_pepper_change_me")

def hash_pw(password: str) -> str:
    # Simple, strong-enough for MVP: SHA256(password + pepper)
    return hashlib.sha256((password + _pepper()).encode("utf-8")).hexdigest()

def bootstrap_admin():
    email = st.secrets.get("ADMIN_BOOTSTRAP_EMAIL")
    pw = st.secrets.get("ADMIN_BOOTSTRAP_PASSWORD")
    if not email or not pw:
        return
    existing = exec_one("SELECT id FROM users WHERE email=?", (email,))
    if existing:
        return
    exec_one(
        "INSERT INTO users(email, password_hash, role, client_id, created_at) VALUES(?,?,?,?,?)",
        (email, hash_pw(pw), "admin", None, now_iso())
    )

def login(email: str, password: str):
    row = exec_one(
        "SELECT id, email, role, client_id, password_hash FROM users WHERE email=?",
        (email,)
    )
    if not row:
        return None
    uid, em, role, client_id, ph = row
    if ph != hash_pw(password):
        return None
    return {"id": uid, "email": em, "role": role, "client_id": client_id}

def require_login():
    if "user" in st.session_state and st.session_state["user"]:
        return st.session_state["user"]

    st.title("🔐 Sign in")
    st.write("Access is protected. If you need an account, contact the administrator.")
    email = st.text_input("Email", placeholder="name@company.com")
    password = st.text_input("Password", type="password")

    if st.button("Sign in", use_container_width=True):
        user = login(email.strip().lower(), password)
        if user:
            st.session_state["user"] = user
            log_event(user["id"], user["client_id"], "login_success", json.dumps({"email": user["email"]}))
            st.rerun()
        else:
            st.error("Invalid credentials.")
    st.stop()

def require_admin(user):
    if user["role"] != "admin":
        st.error("You do not have access to this page.")
        st.stop()

def logout_button():
    if st.button("Log out", use_container_width=True):
        st.session_state["user"] = None
        st.rerun()
