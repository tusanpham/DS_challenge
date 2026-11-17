"""Backtest the models: fit on past years, flag the top-scored incidents of the next year."""

from collections.abc import Callable

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, clone
from sklearn.metrics import average_precision_score

from ds_challenge.models import FEATURES, MODELS, TARGET
from ds_challenge.splits import Split, expanding_year_splits

BUDGET = 0.10  # share of incidents flagged


def top_budget(score: np.ndarray, budget: float = BUDGET) -> np.ndarray:
    """Alert weight per incident: 1 inside the top `budget` share of scores, 0 outside.

    A group of tied scores that straddles the cut shares the remaining alerts equally (a rate table
    has few distinct scores), so the result does not depend on row order.
    """
    k = budget * len(score)
    ranks = pd.Series(score)
    first = ranks.rank(method="min", ascending=False).to_numpy()  # tie group's first rank
    last = ranks.rank(method="max", ascending=False).to_numpy()  # tie group's last rank
    return np.clip((k - first + 1) / (last - first + 1), 0, 1)


# a metric reads the test set's outcomes (True = major), scores and alert weights
Metric = Callable[[np.ndarray, np.ndarray, np.ndarray], float]

METRICS: dict[str, Metric] = {
    "recall": lambda major, score, alert: (major * alert).sum() / major.sum(),
    "precision": lambda major, score, alert: (major * alert).sum() / alert.sum(),
    # no-skill value: the share of major incidents
    "pr_auc": lambda major, score, alert: average_precision_score(major, score),
}


def backtest(
    df: pd.DataFrame,
    models: dict[str, BaseEstimator] = MODELS,
    splits: list[Split] | None = None,
    budget: float = BUDGET,
    target: str = TARGET,
    features: list[str] = FEATURES,
    metrics: dict[str, Metric] = METRICS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit a fresh copy of each model on each split's train rows and score its test rows.

    A model is given the `features` columns only. `splits` defaults to `expanding_year_splits`.
    The budget applies within each test set. Returns the metrics per split and model, and the
    alert weight of every test incident (one column per model, indexed like `df`) for
    `recall_lead`.
    """
    if splits is None:
        splits = expanding_year_splits(df)
    rows, alerts = [], []
    for label, train_mask, test_mask in splits:
        train, test = df[train_mask], df[test_mask]
        major = test[target].to_numpy()
        split_alerts = pd.DataFrame({"split": label, target: major}, index=test.index)
        for name, model in models.items():
            fitted = clone(model).fit(train[features], train[target])
            score = fitted.predict_proba(test[features])[:, 1]
            alert = top_budget(score, budget)
            split_alerts[name] = alert
            values = {metric: compute(major, score, alert) for metric, compute in metrics.items()}
            rows.append({"split": label, "model": name, **values})
        alerts.append(split_alerts)
    return pd.DataFrame(rows).set_index(["split", "model"]), pd.concat(alerts)


def recall_lead(
    alerts: pd.DataFrame, a: str, b: str, draws: int = 1000, seed: int = 0, target: str = TARGET
) -> tuple[float, float, float]:
    """Recall of model `a` minus model `b` over all splits, with a 95% bootstrap interval.

    Recall is the mean alert weight of the major incidents, so the major incidents are resampled
    and both models are read on the same resample (paired). The fitted models are held fixed.
    """
    major = alerts[alerts[target]]
    diff = (major[a] - major[b]).to_numpy()
    rng = np.random.default_rng(seed)
    resampled = rng.choice(diff, size=(draws, len(diff))).mean(axis=1)
    low, high = np.percentile(resampled, [2.5, 97.5])
    return diff.mean(), low, high
