# utils/anomaly.py
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

NUMERIC_FEATURES = ["amount", "unit_price", "quantity", "lead_time_days"]

def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in NUMERIC_FEATURES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = np.nan
    for col in NUMERIC_FEATURES:
        if df[col].isna().all():
            df[col] = 0.0
        else:
            df[col] = df[col].fillna(df[col].median())
    for col in ["invoice_id","supplier","item","date"]:
        if col not in df.columns:
            df[col] = ""
    return df

def _zscore_cols(df: pd.DataFrame, cols):
    out = {}
    for c in cols:
        mu = np.nanmean(df[c].values)
        sd = np.nanstd(df[c].values) + 1e-9
        out[c] = (df[c].values - mu) / sd
    return pd.DataFrame(out, index=df.index)

def fit_isolation_forest(df: pd.DataFrame, contamination: float = 0.07, random_state: int = 42):
    X = df[NUMERIC_FEATURES].values
    clf = IsolationForest(contamination=contamination, random_state=random_state)
    clf.fit(X)
    scores = -clf.score_samples(X)  # higher = more anomalous
    preds = clf.predict(X)          # -1 = anomaly, 1 = normal

    df_out = df.copy()
    df_out["anomaly_score"] = scores
    df_out["is_anomaly"] = (preds == -1)

    # Human-readable reasons (top-2 deviating features by |z|)
    z = _zscore_cols(df_out, NUMERIC_FEATURES).abs()
    reasons = []
    for i in range(len(df_out)):
        row = z.iloc[i]
        order = list(row.sort_values(ascending=False).index[:2])
        txt = ", ".join([f"{f} z≈{row[f]:.1f}" for f in order])
        reasons.append(txt)
    df_out["reason_top_features"] = reasons
    return df_out, clf

def supplier_risk_table(scored: pd.DataFrame) -> pd.DataFrame:
    agg = scored.groupby("supplier").agg(
        total=("invoice_id","count"),
        anomalies=("is_anomaly","sum"),
        avg_score=("anomaly_score","mean")
    ).reset_index()
    if len(agg) == 0:
        agg["risk_score"] = 0.0
        return agg
    rate = (agg["anomalies"] / agg["total"]).fillna(0)
    norm = (agg["avg_score"] - agg["avg_score"].min()) / (agg["avg_score"].max() - agg["avg_score"].min() + 1e-9)
    agg["risk_score"] = ((0.6 * rate + 0.4 * norm) * 100).round(1)
    return agg.sort_values("risk_score", ascending=False)
