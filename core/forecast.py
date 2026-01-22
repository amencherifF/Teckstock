import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

def ml_forecast_dhat(df, sku_col, sales_col, n_hist=28, min_points=10):
    """
    Returns Dhat per SKU using a simple regression on time index.
    If insufficient data, fallback to mean.
    Expect df rows for each SKU over time (sorted).
    """
    out = []
    for sku, g in df.groupby(sku_col):
        y = pd.to_numeric(g[sales_col], errors="coerce").dropna().values
        if len(y) < min_points:
            dhat = float(np.mean(y)) if len(y) else 0.0
            out.append((sku, dhat))
            continue
        y = y[-n_hist:]
        X = np.arange(len(y)).reshape(-1, 1)
        model = LinearRegression().fit(X, y)
        # predict next day demand (simple)
        dhat = float(model.predict([[len(y)]])[0])
        dhat = max(0.0, dhat)
        out.append((sku, dhat))
    return pd.DataFrame(out, columns=[sku_col, "Dhat_ml"])
