"""Train/test splits for the backtest: each is a label and two row masks over the same frame."""

import pandas as pd

from ds_challenge.data import Inc

TEST_YEARS = [2022, 2023, 2024]

Split = tuple[object, pd.Series, pd.Series]  # label, train row mask, test row mask


def expanding_year_splits(df: pd.DataFrame, test_years: list[int] = TEST_YEARS) -> list[Split]:
    """Train on every year before each test year, test on that year."""
    return [(year, df[Inc.year] < year, df[Inc.year] == year) for year in test_years]
