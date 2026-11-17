"""Reliability measure: train incidents per million planned km."""

import pandas as pd

from ds_challenge.data import Inc, Km, train_incidents


def per_mkm(inc: pd.DataFrame, km: pd.DataFrame) -> pd.DataFrame:
    """Train and major (10+) incidents per million planned km, by year and line, plus network.

    Raises if the two inputs cover different months in the incidents' years: planned km ends
    2023-09, so an unfiltered 2023 or any later year would give a wrong or infinite rate.
    """
    train = train_incidents(inc)
    inc_months = set(train[Inc.date].dt.to_period("M"))
    km_months = set(km.loc[km[Km.year].isin(train[Inc.year]), Km.date].dt.to_period("M"))
    if gap := sorted(inc_months ^ km_months):
        raise ValueError(f"incidents and planned km cover different months, e.g. {gap[:3]}")

    counts = train.groupby([Inc.year, Inc.line]).agg(
        incidents=(Inc.incident_id, "size"), major=(Inc.major_10, "sum")
    )
    mkm = km.groupby([Km.year, Km.line])[Km.km].sum() / 1e6
    by_line = counts.join(mkm.rename("mkm").rename_axis([Inc.year, Inc.line]))
    network = by_line.groupby(Inc.year).sum().assign(**{Inc.line: "Network"})
    rates = pd.concat([by_line.reset_index(), network.reset_index()])
    rates["incidents_per_mkm"] = rates.incidents / rates.mkm
    rates["major_per_mkm"] = rates.major / rates.mkm
    rates["major_share"] = rates.major / rates.incidents
    return rates
