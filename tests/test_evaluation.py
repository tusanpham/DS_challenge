import numpy as np
import pandas as pd

from ds_challenge.data import Inc
from ds_challenge.evaluation import backtest, top_budget
from ds_challenge.models import TARGET, HistoricalRate
from ds_challenge.splits import expanding_year_splits


def test_top_budget_splits_alerts_across_a_tie():
    # budget of 2 alerts: one goes to the top score, the three tied scores share the other
    alert = top_budget(np.array([0.9, 0.5, 0.5, 0.5, 0.1]), budget=0.4)
    assert np.allclose(alert, [1, 1 / 3, 1 / 3, 1 / 3, 0])
    assert np.isclose(alert.sum(), 2)


def test_backtest_takes_custom_models_and_splits_and_keeps_the_row_index():
    df = pd.DataFrame(
        {
            Inc.year: [2020] * 40 + [2021] * 20,
            Inc.symptom: ["a", "b"] * 30,
            TARGET: [True, False, False, False] * 15,
        },
        index=range(100, 160),
    )
    first, last = df.index < 130, df.index >= 130
    results, alerts = backtest(
        df,
        models={"symptom": HistoricalRate([Inc.symptom])},
        splits=[("halves", first, last)],
        budget=0.5,
        features=[Inc.symptom],
    )
    assert list(results.index) == [("halves", "symptom")]
    assert alerts.index.equals(df.index[last])
    assert set(alerts["split"]) == {"halves"}


def test_expanding_year_splits_train_only_on_earlier_years():
    df = pd.DataFrame({Inc.year: [2020, 2021, 2022, 2022]})
    [(label, train, test)] = expanding_year_splits(df, [2022])
    assert label == 2022
    assert train.tolist() == [True, True, False, False]
    assert test.tolist() == [False, False, True, True]
