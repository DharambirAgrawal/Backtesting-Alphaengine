from __future__ import annotations

import io
from typing import Any

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier


FEATURE_COLS = (
    "rsi",
    "macd",
    "macd_signal",
    "bb_position",
    "volume_ratio",
    "return_5d",
    "return_10d",
    "return_20d",
    "day_of_week",
)


class TinyLSTM(nn.Module):
    def __init__(self, input_dim: int, hidden: int = 32, num_layers: int = 1) -> None:
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        last = out[:, -1, :]
        return self.fc(last)


def _direction_target(df: pd.DataFrame) -> pd.Series:
    close = df["close"].astype(float)
    return (close.shift(-1) > close).astype(np.int32)


def fit_xgb_direction(
    features: pd.DataFrame,
    test_fraction: float = 0.15,
    min_samples: int = 80,
) -> tuple[dict[str, Any], float]:
    """Train XGBoost on next-day direction; return payload for joblib + holdout accuracy."""
    work = features.copy()
    if "close" not in work.columns:
        raise ValueError("features must include 'close'")

    work["target_up"] = _direction_target(work)
    usable = work.dropna(subset=list(FEATURE_COLS)).copy()
    usable = usable.iloc[:-1].dropna(subset=["target_up"])

    if len(usable) < min_samples:
        raise ValueError(f"need at least {min_samples} rows after feature alignment")

    split = max(int(len(usable) * (1.0 - test_fraction)), len(usable) // 10)
    split = min(split, len(usable) - 15)
    split = max(split, min_samples // 2)

    train_df = usable.iloc[:split]
    test_df = usable.iloc[split:]

    X_train = train_df[list(FEATURE_COLS)].astype(np.float64).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    y_train = train_df["target_up"].astype(np.int32)
    X_test = test_df[list(FEATURE_COLS)].astype(np.float64).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    y_test = test_df["target_up"].astype(np.int32)

    clf = XGBClassifier(
        n_estimators=120,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=42,
        n_jobs=1,
        verbosity=0,
    )
    clf.fit(X_train, y_train)
    pred = clf.predict(X_test)
    acc = float(accuracy_score(y_test, pred))

    bundle = {
        "kind": "xgboost_direction",
        "model": clf,
        "feature_cols": list(FEATURE_COLS),
        "version": 1,
    }
    buf = io.BytesIO()
    joblib.dump(bundle, buf)
    return {"bytes": buf.getvalue(), "bundle": bundle}, acc


def fit_lstm_price_direction(
    features: pd.DataFrame,
    seq_len: int = 16,
    test_fraction: float = 0.15,
    min_samples: int = 80,
    epochs: int = 45,
    lr: float = 0.02,
) -> tuple[dict[str, Any], float]:
    """Small LSTM on normalized feature windows; accuracy = directional match on holdout."""
    work = features.dropna(subset=list(FEATURE_COLS)).copy()
    if len(work) < min_samples:
        raise ValueError(f"need at least {min_samples} rows for LSTM")

    mat = work[list(FEATURE_COLS)].astype(np.float64).replace([np.inf, -np.inf], np.nan).fillna(0.0).values
    close = work["close"].astype(np.float64).values

    split_idx = max(int(len(work) * (1.0 - test_fraction)), seq_len + 10)
    split_idx = min(split_idx, len(work) - 20)

    train_mat = mat[:split_idx]

    mean = train_mat.mean(axis=0)
    std = train_mat.std(axis=0) + 1e-9

    train_X_list: list[np.ndarray] = []
    train_y_list: list[float] = []
    for i in range(seq_len, split_idx):
        window = (mat[i - seq_len : i] - mean) / std
        ret = close[i] / max(close[i - 1], 1e-12) - 1.0
        train_X_list.append(window)
        train_y_list.append(ret)

    train_X = np.stack(train_X_list, axis=0).astype(np.float32)
    train_y = np.asarray(train_y_list, dtype=np.float32)

    test_X_list: list[np.ndarray] = []
    test_actual: list[float] = []
    for i in range(split_idx, len(work)):
        window = (mat[i - seq_len : i] - mean) / std
        ret = close[i] / max(close[i - 1], 1e-12) - 1.0
        test_X_list.append(window)
        test_actual.append(ret)

    if train_X.shape[0] < 25 or len(test_actual) < 8:
        raise ValueError("not enough sequence samples for LSTM")

    train_X_t = torch.from_numpy(train_X)
    train_y_t = torch.from_numpy(train_y.reshape(-1, 1))

    net = TinyLSTM(input_dim=train_X.shape[2], hidden=36, num_layers=1)
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    net.train()
    for _ in range(epochs):
        opt.zero_grad()
        pred = net(train_X_t)
        loss = loss_fn(pred, train_y_t)
        loss.backward()
        opt.step()

    net.eval()
    test_X_arr = np.stack(test_X_list, axis=0).astype(np.float32)
    test_xt = torch.from_numpy(test_X_arr)
    actual_dir = np.asarray([a > 0 for a in test_actual], dtype=np.int32)
    with torch.no_grad():
        preds = net(test_xt).numpy().flatten()
        pred_dir = (preds > 0).astype(np.int32)
        acc = float(accuracy_score(actual_dir, pred_dir))

    buf = io.BytesIO()
    payload = {
        "kind": "tiny_lstm",
        "state_dict": net.state_dict(),
        "mean": mean.tolist(),
        "std": std.tolist(),
        "seq_len": seq_len,
        "feature_cols": list(FEATURE_COLS),
        "input_dim": train_X.shape[2],
        "hidden": 36,
        "version": 1,
    }
    torch.save(payload, buf)

    return {"bytes": buf.getvalue(), "payload": payload}, acc
