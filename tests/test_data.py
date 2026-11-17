import pandas as pd

from ds_challenge.data import Inc, Km, load_incidents, load_km, parse_service_clock


def test_service_clock_rolls_past_midnight():
    day = pd.Series(pd.to_datetime(["2019-01-01", "2019-01-01"]))
    out = parse_service_clock(day, pd.Series(["23:10", "25:20:00"]))
    assert list(out) == [pd.Timestamp("2019-01-01 23:10"), pd.Timestamp("2019-01-02 01:20")]


def test_loaders_keep_every_row():
    inc = load_incidents()
    assert len(inc) == 45_561
    assert inc[[Inc.start, Inc.resume]].notna().all().all()

    km = load_km()
    assert len(km) == 8_472
    assert km[Km.km].notna().all()
