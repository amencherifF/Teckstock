import streamlit as st

def set_app_style():
    # Clean “Dynamics-like” feel: roomy, subtle borders, consistent headers.
    st.markdown("""
    <style>
      .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
      .stMetric { border: 1px solid rgba(49,51,63,.2); padding: 12px; border-radius: 10px; }
      .stDataFrame { border: 1px solid rgba(49,51,63,.2); border-radius: 10px; overflow: hidden; }
      h1,h2,h3 { letter-spacing: -0.02em; }
      .small-note { font-size: 0.9rem; opacity: 0.8; }
    </style>
    """, unsafe_allow_html=True)
