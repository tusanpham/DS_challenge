import pytest

from ds_challenge.data import Inc, Km, load_incidents, load_km
from ds_challenge.reliability import per_mkm


def test_per_mkm_refuses_months_without_planned_km():
    # planned km ends 2023-09, incidents run to 2025-09
    with pytest.raises(ValueError, match="different months"):
        per_mkm(load_incidents(), load_km())


def test_per_mkm_network_row_adds_up_the_lines():
    inc, km = load_incidents(), load_km()
    rates = per_mkm(inc[inc[Inc.year] == 2019], km[km[Km.year] == 2019])
    network = rates[rates[Inc.line] == "Network"]
    lines = rates[rates[Inc.line] != "Network"]
    assert network.incidents.item() == lines.incidents.sum()
    assert network.mkm.item() == pytest.approx(lines.mkm.sum())
