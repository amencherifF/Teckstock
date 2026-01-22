import streamlit as st
import pandas as pd
import json

from core.auth import require_login
from core.db import exec_one, exec_all, now_iso, log_event
from core.algo import recommend_orders
from core.forecast import ml_forecast_dhat

user = require_login()

st.title("🧭 User Workspace")
st.caption("Upload data, map columns, configure parameters, run recommendations.")

# --- Client selection/creation (multi-tenant)
st.subheader("Client")
if user["role"] == "admin":
    # Admin can run as any client (useful for demos)
    clients = exec_all("SELECT id, name FROM clients ORDER BY name")
    options = {name: cid for cid, name in clients}
    client_name = st.selectbox("Select client", ["(none)"] + list(options.keys()))
    client_id = options.get(client_name) if client_name != "(none)" else None
else:
    client_id = user["client_id"]
    if client_id:
        row = exec_one("SELECT name FROM clients WHERE id=?", (client_id,))
        st.write(f"Client: **{row[0]}**")
    else:
        st.warning("No client assigned. Ask the admin to link your account to a client.")
        st.stop()

# --- Upload
st.subheader("Upload CSV")
uploaded = st.file_uploader("Upload your CSV", type=["csv"])

if uploaded:
    df = pd.read_csv(uploaded)
    st.write("Preview")
    st.dataframe(df.head(50), use_container_width=True)

    # Log upload
    exec_one(
        "INSERT INTO uploads(user_id, client_id, filename, row_count, created_at) VALUES(?,?,?,?,?)",
        (user["id"], client_id, uploaded.name, int(df.shape[0]), now_iso())
    )
    log_event(user["id"], client_id, "upload_csv", json.dumps({"filename": uploaded.name, "rows": int(df.shape[0])}))

    st.subheader("Column mapping")
    cols = list(df.columns)

    sku_col = st.selectbox("SKU column", cols)
    sales_col = st.selectbox("Sales column (units sold per day)", cols)
    stock_col = st.selectbox("Current stock column (on hand)", cols)
    expiry_col = st.selectbox("Days to expiry column (remaining days)", cols)

    st.subheader("Parameters")
    colA, colB, colC, colD = st.columns(4)
    with colA:
        R = st.number_input("Delivery cycle R (days)", min_value=1, max_value=30, value=3)
    with colB:
        beta = st.slider("Safety factor β", min_value=0.0, max_value=1.0, value=0.2, step=0.05)
    with colC:
        n_hist = st.number_input("History window (rows/SKU)", min_value=3, max_value=60, value=14)
    with colD:
        moq = st.number_input("MOQ / pack size", min_value=1, max_value=200, value=1)

    use_ml = st.toggle("Use simple ML forecast (if enough history exists)", value=False)

    if st.button("Run recommendations", type="primary", use_container_width=True):
        work = df.copy()

        # Optional ML forecast override
        if use_ml:
            ml = ml_forecast_dhat(work, sku_col=sku_col, sales_col=sales_col, n_hist=int(n_hist))
            # We'll merge ML Dhat into algo by temporarily replacing sales with a single-row demand representation
            # Simpler: we pass df and then post-merge Dhat_ml to override Dhat in output
            rec = recommend_orders(
                work, sku_col, sales_col, stock_col, expiry_col,
                R=int(R), beta=float(beta), n_hist=int(n_hist), moq=int(moq)
            )
            rec = rec.merge(ml, on=sku_col, how="left")
            rec["Dhat_final"] = rec["Dhat_ml"].fillna(rec["Dhat"])
            # Recompute key fields with Dhat_final (simple overwrite)
            rec["CycleDemand"] = int(R) * rec["Dhat_final"]
            rec["Buffer"] = float(beta) * rec["CycleDemand"]
            rec["Target"] = rec["CycleDemand"] + rec["Buffer"]
            rec["ExpiringExcess"] = (rec["Stock"] - rec["S"] * rec["Dhat_final"]).clip(lower=0.0)
            rec["UsableStock"] = (rec["Stock"] - rec["ExpiringExcess"]).clip(lower=0.0)
            rec["RawOrder"] = (rec["Target"] - rec["UsableStock"]).clip(lower=0.0)
            rec["RecommendedOrder"] = ( (rec["RawOrder"] / int(moq)).apply(lambda x: int((x // 1) if x.is_integer() else int(x) + 1)) * int(moq) )
        else:
            rec = recommend_orders(
                work, sku_col, sales_col, stock_col, expiry_col,
                R=int(R), beta=float(beta), n_hist=int(n_hist), moq=int(moq)
            )
            rec["Dhat_final"] = rec["Dhat"]

        # KPI tiles
        st.subheader("Results")
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("SKUs", int(rec.shape[0]))
        with k2:
            st.metric("Total recommended order", int(rec["RecommendedOrder"].sum()))
        with k3:
            st.metric("Avg waste risk", f"{rec['WasteRiskRatio'].mean():.2%}")
        with k4:
            st.metric("High-risk SKUs (risk ≥ 30%)", int((rec["WasteRiskRatio"] >= 0.30).sum()))

        st.dataframe(
            rec[[sku_col, "Stock", "S", "Dhat_final", "UsableStock", "WasteRiskRatio", "RecommendedOrder"]],
            use_container_width=True
        )

        # Save run summary
        summary = {
            "skus": int(rec.shape[0]),
            "total_recommended_order": int(rec["RecommendedOrder"].sum()),
            "avg_waste_risk": float(rec["WasteRiskRatio"].mean()),
            "high_risk_skus": int((rec["WasteRiskRatio"] >= 0.30).sum()),
            "use_ml": bool(use_ml),
        }
        params = {
            "R": int(R), "beta": float(beta), "n_hist": int(n_hist), "moq": int(moq),
            "sku_col": sku_col, "sales_col": sales_col, "stock_col": stock_col, "expiry_col": expiry_col
        }

        exec_one(
            "INSERT INTO runs(user_id, client_id, params_json, result_summary_json, created_at) VALUES(?,?,?,?,?)",
            (user["id"], client_id, json.dumps(params), json.dumps(summary), now_iso())
        )
        log_event(user["id"], client_id, "run_recommendations", json.dumps({"summary": summary}))

        # Download
        csv_bytes = rec.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download recommendations CSV",
            data=csv_bytes,
            file_name="recommendations.csv",
            mime="text/csv",
            use_container_width=True
        )
