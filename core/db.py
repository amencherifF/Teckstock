import sqlite3
import streamlit as st
from pathlib import Path
from datetime import datetime

DB_PATH = Path("mvp.sqlite3")

def _conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = _conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,              -- 'user' or 'admin'
        client_id INTEGER,               -- null for admin
        created_at TEXT NOT NULL,
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS uploads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        client_id INTEGER,
        filename TEXT NOT NULL,
        row_count INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        client_id INTEGER,
        params_json TEXT NOT NULL,
        result_summary_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        client_id INTEGER,
        event_name TEXT NOT NULL,
        event_json TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )
    """)

    conn.commit()
    conn.close()

def now_iso():
    return datetime.utcnow().isoformat()

def exec_one(query, params=()):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(query, params)
    row = cur.fetchone()
    conn.commit()
    conn.close()
    return row

def exec_all(query, params=()):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.commit()
    conn.close()
    return rows

def log_event(user_id, client_id, event_name, event_json=None):
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO events(user_id, client_id, event_name, event_json, created_at) VALUES(?,?,?,?,?)",
        (user_id, client_id, event_name, event_json, now_iso())
    )
    conn.commit()
    conn.close()
