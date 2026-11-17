"""Models for: when a train incident is declared, will it reach a 10+ minute delay?

Three models, from simplest to least simple: the 10+ rate of the symptom, the 10+ rate of the
symptom x location cell, and a logistic regression on every field known at declaration. Each is
a scikit-learn classifier (`fit`, `predict_proba`), so any other one can be added to `MODELS`.
Why each field is in or out: README, Analytical strategy.
"""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder

from ds_challenge.data import Inc

TARGET = Inc.major_10
# the only columns a model is given: all known when the incident is declared
FEATURES = [Inc.symptom, Inc.line, Inc.location, Inc.hour, Inc.weekday, Inc.month]
MIN_ROWS = 30  # a category or rate cell with fewer training rows is not trusted on its own


class HistoricalRate(ClassifierMixin, BaseEstimator):
    """Historical 10+ rate: the share of training incidents in the same `keys` cell that were major.

    A cell under `min_rows` falls back to the rate of the cell without its last key, and in the
    end to the overall rate. In the `group_rare` columns, values under `min_rows` training rows
    are grouped as "other" first (the same grouping the logistic regression's encoder applies).
    """

    def __init__(self, keys: list[str], group_rare: tuple[str, ...] = (), min_rows: int = MIN_ROWS):
        self.keys = keys
        self.group_rare = group_rare
        self.min_rows = min_rows

    def _grouped(self, X: pd.DataFrame) -> pd.DataFrame:
        return X.assign(
            **{c: X[c].where(X[c].isin(self.common_[c]), "other") for c in self.common_}
        )

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "HistoricalRate":
        self.classes_ = np.array([False, True])
        self.common_ = {}
        for column in self.group_rare:
            counts = X[column].value_counts()
            self.common_[column] = counts.index[counts >= self.min_rows]
        self.overall_ = y.mean()
        # one rate table per fallback level: all the keys first, then one key fewer each time
        self.tables_ = []
        cells = self._grouped(X).assign(major=y.to_numpy())
        for n in range(len(self.keys), 0, -1):
            cell = cells.groupby(self.keys[:n])["major"].agg(["mean", "size"])
            self.tables_.append(cell.loc[cell["size"] >= self.min_rows, "mean"].rename("rate"))
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        X = self._grouped(X)
        rate = pd.Series(np.nan, index=X.index)
        for table in self.tables_:
            rate = rate.fillna(X.join(table, on=table.index.names)["rate"])
        rate = rate.fillna(self.overall_).to_numpy()
        return np.column_stack([1 - rate, rate])


def logistic_regression() -> Pipeline:
    """Every column it is given one-hot (hour, weekday and month as levels), default
    regularisation."""
    return make_pipeline(
        OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=MIN_ROWS),
        LogisticRegression(max_iter=1000),
    )


MODELS: dict[str, BaseEstimator] = {
    "symptom": HistoricalRate([Inc.symptom]),
    "symptom_location": HistoricalRate([Inc.symptom, Inc.location], group_rare=(Inc.location,)),
    "logistic_regression": logistic_regression(),
}
