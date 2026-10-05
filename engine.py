from __future__ import annotations

import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score, accuracy_score


def _normalise_target(s):
    if pd.api.types.is_numeric_dtype(s):
        vals = pd.to_numeric(s, errors="coerce")
        if set(vals.dropna().unique()).issubset({0, 1}):
            return vals.astype(float)

    mapping = {
        "yes":1, "y":1, "true":1, "late":1, "paid late":1, "overdue":1,
        "no":0, "n":0, "false":0, "on time":0, "ontime":0, "paid on time":0,
    }
    out = s.astype(str).str.strip().str.lower().map(mapping)
    return out.fillna(pd.to_numeric(s, errors="coerce")).astype(float)


def _clean_features(X):
    X = X.copy()

    for col in list(X.columns):
        if pd.api.types.is_datetime64_any_dtype(X[col]):
            X[col+"__year"] = X[col].dt.year
            X[col+"__month"] = X[col].dt.month
            X[col+"__dow"] = X[col].dt.dayofweek
            X = X.drop(columns=[col])

    for col in list(X.columns):
        if X[col].dtype == "object":
            parsed = pd.to_datetime(X[col], errors="coerce")
            if parsed.notna().mean() > 0.8:
                X[col+"__year"] = parsed.dt.year
                X[col+"__month"] = parsed.dt.month
                X[col+"__dow"] = parsed.dt.dayofweek
                X = X.drop(columns=[col])

    drop = []
    for col in X.columns:
        name = str(col).lower()
        if any(k in name for k in ["invoice id","invoice no","invoice number","document id","document number","phone","email","customer name","address"]):
            drop.append(col)

    X = X.drop(columns=drop, errors="ignore")

    for col in X.columns:
        if X[col].dtype == "object":
            X[col] = X[col].fillna("__MISSING__").astype(str)
        else:
            X[col] = pd.to_numeric(X[col], errors="coerce")

    return X


def prepare_dataset(df, target_col, amount_col, customer_col, invoice_col, date_col, current_only=True):
    work = df.copy()
    target = _normalise_target(work[target_col])
    labeled_mask = target.notna()
    current_mask = ~labeled_mask

    if labeled_mask.sum() < 30:
        raise ValueError("At least 30 historical rows with a known Paid Late outcome are recommended.")

    if target.loc[labeled_mask].nunique() < 2:
        raise ValueError("The target needs both classes: some invoices paid late and some not late.")

    excluded = [target_col]
    for col in [customer_col, invoice_col]:
        if col:
            excluded.append(col)

    X = _clean_features(work.drop(columns=excluded, errors="ignore"))
    y = target.loc[labeled_mask].astype(int)

    return {
        "labeled": work.loc[labeled_mask].copy(),
        "current": work.loc[current_mask].copy(),
        "X_train": X.loc[labeled_mask].copy(),
        "y_train": y,
        "X_current": X.loc[current_mask].copy(),
    }


def train_tabpfn(X, y):
    from tabpfn import TabPFNClassifier
    model = TabPFNClassifier()
    model.fit(X, y)
    return model


def score_current_invoices(model, X_current):
    return model.predict_proba(X_current)[:, 1]


def _prepare_xgb_data(X_train, X_test=None):
    train = X_train.copy()
    test = X_test.copy() if X_test is not None else None

    for col in train.columns:
        if train[col].dtype == "object":
            combined = pd.concat([train[col], test[col]], axis=0) if test is not None else train[col]
            categories = pd.Series(combined.astype(str)).astype("category").cat.categories
            mapping = {v:i for i,v in enumerate(categories)}
            train[col] = train[col].astype(str).map(mapping).fillna(-1).astype(float)
            if test is not None:
                test[col] = test[col].astype(str).map(mapping).fillna(-1).astype(float)

    train = train.replace([np.inf,-np.inf], np.nan).fillna(0)
    if test is not None:
        test = test.replace([np.inf,-np.inf], np.nan).fillna(0)

    return train, test


def train_xgboost(X, y):
    from xgboost import XGBClassifier
    X2, _ = _prepare_xgb_data(X)

    model = XGBClassifier(
        n_estimators=150,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        eval_metric="logloss",
        tree_method="hist",
        random_state=42,
        n_jobs=2,
    )
    model.fit(X2, y)
    return model


def _xgb_predict(model, X_train, X_test):
    _, X2 = _prepare_xgb_data(X_train, X_test)
    return model.predict_proba(X2)[:, 1]


def _metrics(y_true, probabilities):
    pred = (probabilities >= 0.5).astype(int)
    try:
        auc = roc_auc_score(y_true, probabilities)
    except Exception:
        auc = float("nan")

    return {
        "ROC-AUC": round(float(auc), 4) if not np.isnan(auc) else None,
        "F1": round(float(f1_score(y_true, pred, zero_division=0)), 4),
        "Accuracy": round(float(accuracy_score(y_true, pred)), 4),
    }


def evaluate_models(X, y):
    if len(X) < 50:
        raise ValueError("Not enough historical rows for a benchmark.")
    if pd.Series(y).nunique() < 2:
        raise ValueError("Benchmark requires both target classes.")

    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    tab = train_tabpfn(Xtr, ytr)
    p_tab = tab.predict_proba(Xte)[:, 1]

    xgb = train_xgboost(Xtr, ytr)
    p_xgb = _xgb_predict(xgb, Xtr, Xte)

    return [
        {"Model":"TabPFN", **_metrics(yte, p_tab)},
        {"Model":"XGBoost", **_metrics(yte, p_xgb)},
    ]


def make_priority_table(current, probabilities, amount_col, customer_col, invoice_col):
    out = current.copy()
    out["Risk %"] = probabilities * 100

    if amount_col:
        amount = pd.to_numeric(out[amount_col], errors="coerce").fillna(0)
    else:
        amount = pd.Series(np.ones(len(out)), index=out.index)

    out["Potential Exposure"] = amount * probabilities

    display = {}
    if customer_col:
        display["Customer"] = out[customer_col].astype(str)
    if invoice_col:
        display["Invoice"] = out[invoice_col].astype(str)
    if amount_col:
        display["Invoice Amount"] = amount

    result = pd.DataFrame(display, index=out.index)
    result["Risk %"] = out["Risk %"]
    result["Potential Exposure"] = out["Potential Exposure"]

    return result.sort_values(
        ["Potential Exposure","Risk %"],
        ascending=False,
    ).reset_index(drop=True)
