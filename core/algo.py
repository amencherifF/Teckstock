import numpy as np
import pandas as pd

def recommend_orders(
    df: pd.DataFrame,
    sku_col: str,
    sales_col: str,
    stock_col: str,
    days_to_expiry_col: str,
    R: int,            # days until next delivery
    beta: float,       # safety factor (0.0 to 1.0)
    n_hist: int,       # history window for avg demand
    moq: int = 1,      # minimum order multiple / pack size
):
    """
    Simple, concrete, expiry-aware ordering:
      Dhat = avg last n days sales (per SKU)
      cycle_demand = R * Dhat
      expiring_excess E = max(0, stock - S * Dhat)
      usable U = stock - E
      target T = cycle_demand * (1 + beta)
      Q = max(0, T - U) rounded up to MOQ
    """

    work = df.copy()
    work[days_to_expiry_col] = pd.to_numeric(work[days_to_expiry_col], errors="coerce")
    work[sales_col] = pd.to_numeric(work[sales_col], errors="coerce")
    work[stock_col] = pd.to_numeric(work[stock_col], errors="coerce")

    # Dhat: average demand per SKU using provided rows as "history"
    # Expect df includes historical sales rows per SKU (date optional)
    demand = (
        work.groupby(sku_col)[sales_col]
        .tail(n_hist)  # last n rows per SKU (works if sorted by date before upload; UI suggests sorting)
        .groupby(work[sku_col])
        .mean()
        .rename("Dhat")
        .reset_index()
    )

    # Current state per SKU: we take the latest row per SKU for stock and days_to_expiry
    latest = (
        work.groupby(sku_col)
        .tail(1)[[sku_col, stock_col, days_to_expiry_col]]
        .rename(columns={stock_col: "Stock", days_to_expiry_col: "S"})
        .reset_index(drop=True)
    )

    out = latest.merge(demand, on=sku_col, how="left")
    out["Dhat"] = out["Dhat"].fillna(0.0)
    out["S"] = out["S"].fillna(0.0)
    out["Stock"] = out["Stock"].fillna(0.0)

    out["CycleDemand"] = R * out["Dhat"]
    out["Buffer"] = beta * out["CycleDemand"]
    out["Target"] = out["CycleDemand"] + out["Buffer"]

    # Expiring excess: if stock bigger than can be sold before expiry
    out["ExpiringExcess"] = np.maximum(0.0, out["Stock"] - out["S"] * out["Dhat"])
    out["UsableStock"] = np.maximum(0.0, out["Stock"] - out["ExpiringExcess"])

    out["RawOrder"] = np.maximum(0.0, out["Target"] - out["UsableStock"])

    # MOQ rounding
    if moq < 1:
        moq = 1
    out["RecommendedOrder"] = (np.ceil(out["RawOrder"] / moq) * moq).astype(int)

    # Waste-risk proxy (simple): share of stock likely to expire
    out["WasteRiskRatio"] = np.where(out["Stock"] > 0, out["ExpiringExcess"] / out["Stock"], 0.0)

    return out.sort_values("WasteRiskRatio", ascending=False)
