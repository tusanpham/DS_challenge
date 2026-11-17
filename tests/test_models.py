import numpy as np
import pandas as pd

from ds_challenge.data import Inc
from ds_challenge.models import FEATURES, HistoricalRate

# set after the incident is declared, derived from how long it lasted, or of undocumented
# timing (README, Analytical strategy)
NOT_KNOWN_AT_DECLARATION = {
    Inc.emergency_brake,
    Inc.door,
    Inc.material_damage,
    Inc.cause_primary,
    Inc.cause_secondary,
    Inc.power_cut,
    Inc.evacuation,
    Inc.emergency_team,
    Inc.resume_clock,
    Inc.resume,
    Inc.minutes,
    Inc.duration_bin,
    Inc.major_5,
    Inc.major_10,
    Inc.major_30,
}


def test_features_are_all_known_at_declaration():
    assert not set(FEATURES) & NOT_KNOWN_AT_DECLARATION


def test_historical_rate_falls_back_when_a_cell_is_small():
    X = pd.DataFrame({Inc.symptom: ["a"] * 40 + ["b"] * 5})
    y = pd.Series([True] * 10 + [False] * 30 + [True] * 5)
    new = pd.DataFrame({Inc.symptom: ["a", "b", "never seen"]})
    overall = 15 / 45
    rate = HistoricalRate([Inc.symptom]).fit(X, y).predict_proba(new)[:, 1]
    assert np.allclose(rate, [0.25, overall, overall])


def test_historical_rate_groups_rare_values_of_a_column():
    # locations y and z have 20 rows each: too few alone, 40 rows together as "other"
    X = pd.DataFrame({Inc.symptom: ["a"] * 80, Inc.location: ["x"] * 40 + ["y"] * 20 + ["z"] * 20})
    y = pd.Series([True] * 10 + [False] * 30 + [True] * 20 + [False] * 20)
    new = pd.DataFrame({Inc.symptom: ["a"] * 3, Inc.location: ["x", "y", "never seen"]})
    model = HistoricalRate([Inc.symptom, Inc.location], group_rare=(Inc.location,)).fit(X, y)
    assert np.allclose(model.predict_proba(new)[:, 1], [0.25, 0.5, 0.5])
