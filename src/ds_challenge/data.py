"""Load and clean the two STM open datasets.

Columns are renamed to English snake_case. Nothing is dropped: questionable rows are
flagged so every exclusion is an explicit choice downstream (see the README, Data).
"""

from enum import StrEnum, auto
from pathlib import Path

import pandas as pd

# shortcut: path from the source tree, breaks if installed non-editable; pass `path` then
RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
INCIDENTS_FILE = RAW / "incidents_metro_20260707.csv"
KM_FILE = RAW / "km_planifie_metro_20260707.csv"

LINES = ["Ligne verte", "Ligne orange", "Ligne jaune", "Ligne bleue"]

# official duration bins, in order, with their minute bounds
BIN_MINUTES = {
    "02 min et moins": (0, 2),
    "03 à 04 min": (3, 4),
    "05 à 09 min": (5, 9),
    "10 à 14 min": (10, 14),
    "15 à 19 min": (15, 19),
    "20 à 24 min": (20, 24),
    "25 à 29 min": (25, 29),
    "30 min et plus": (30, float("inf")),
}
DURATION_BINS = list(BIN_MINUTES)
LAST_FULL_YEAR = 2024  # 2025 is still filling in (reporting lag)

# primary causes, in English
CAUSES = {
    "Clientèle": "Customer",
    "Équipements fixes": "Fixed equipment",
    "Matériel roulant": "Rolling stock",
    "Exploitation trains": "Train operations",
}


class Inc(StrEnum):
    """Incident columns: use as inc[Inc.duration_bin]."""

    incident_id = auto()
    type = auto()  # T = train, S = station
    cause_primary = auto()
    cause_secondary = auto()
    symptom = auto()
    line = auto()
    run = auto()
    start_clock = auto()
    resume_clock = auto()
    duration_bin = auto()
    vehicle = auto()
    car_door = auto()
    rolling_stock = auto()
    location = auto()
    material_damage = auto()
    emergency_brake = auto()
    door = auto()
    emergency_team = auto()
    power_cut = auto()
    evacuation = auto()
    weekday = auto()  # 1 = Monday
    date = auto()
    # derived in load_incidents
    start = auto()
    resume = auto()
    minutes = auto()
    year = auto()
    month = auto()
    hour = auto()
    multi_line = auto()
    major_5 = auto()
    major_10 = auto()
    major_30 = auto()


class Km(StrEnum):
    """Planned-km columns: use as km[Km.km]."""

    line = auto()
    service_period = auto()
    day_type = auto()
    run = auto()
    date = auto()
    km = auto()
    # derived in load_km
    year = auto()
    unassigned = auto()


INCIDENT_COLUMNS = {
    "Numero d'incident": Inc.incident_id,
    "Type d'incident": Inc.type,
    "Cause primaire": Inc.cause_primary,
    "Cause secondaire": Inc.cause_secondary,
    "Symptome": Inc.symptom,
    "Ligne": Inc.line,
    "Numéro de tournée": Inc.run,
    "Heure de l'incident": Inc.start_clock,
    "Heure de reprise": Inc.resume_clock,
    "Incident en minutes": Inc.duration_bin,
    "Véhicule": Inc.vehicle,
    "Porte de voiture": Inc.car_door,
    "Type de matériel": Inc.rolling_stock,
    "Code de lieu": Inc.location,
    "Dommage matériel": Inc.material_damage,
    "KFS": Inc.emergency_brake,
    "Porte": Inc.door,
    "Urgence métro": Inc.emergency_team,
    "CAT": Inc.power_cut,
    "Évacuation": Inc.evacuation,
    "Jour de la semaine": Inc.weekday,
    "Jour calendaire": Inc.date,
}

FLAG_COLUMNS = [
    Inc.material_damage,
    Inc.emergency_brake,
    Inc.door,
    Inc.emergency_team,
    Inc.power_cut,
]

KM_COLUMNS = {
    "Ligne": Km.line,
    "Période Exploitation": Km.service_period,
    "Type de Jour": Km.day_type,
    "Tournée": Km.run,
    "Jour calendaire": Km.date,
    "KM planifié": Km.km,
}


def parse_service_clock(day: pd.Series, clock: pd.Series) -> pd.Series:
    """Turn a service-day clock into timestamps: '25:20:00' on day D is 01:20 on D+1."""
    hm = clock.str.split(":", expand=True)
    hours = pd.to_timedelta(hm[0].astype(int), unit="h")
    minutes = pd.to_timedelta(hm[1].astype(int), unit="m")
    return day + hours + minutes


def load_incidents(path: Path = INCIDENTS_FILE) -> pd.DataFrame:
    """One row per incident, with timestamps, computed minutes and major-incident targets."""
    raw = pd.read_csv(path, sep=";", encoding="utf-8-sig", na_values="#", dtype=str)
    df = raw[list(INCIDENT_COLUMNS)].rename(columns=INCIDENT_COLUMNS)

    df[Inc.date] = pd.to_datetime(df[Inc.date])
    df[Inc.weekday] = df[Inc.weekday].astype(int)
    df[FLAG_COLUMNS] = df[FLAG_COLUMNS].astype(int)
    df[Inc.duration_bin] = pd.Categorical(
        df[Inc.duration_bin], categories=DURATION_BINS, ordered=True
    )

    df[Inc.start] = parse_service_clock(df[Inc.date], df[Inc.start_clock])
    resume = parse_service_clock(df[Inc.date], df[Inc.resume_clock])
    # a few resumes are written on the plain clock after midnight (e.g. start 23:50, resume 00:10)
    df[Inc.resume] = resume.where(resume >= df[Inc.start], resume + pd.Timedelta(days=1))
    # audit only: resume time is not known at declaration, so never a feature
    df[Inc.minutes] = (df[Inc.resume] - df[Inc.start]).dt.total_seconds() / 60

    df[Inc.year] = df[Inc.date].dt.year
    df[Inc.month] = df[Inc.date].dt.month
    df[Inc.hour] = df[Inc.start].dt.hour
    df[Inc.multi_line] = df[Inc.line].str.contains(",", na=False)

    # targets come from the official bin, and only train incidents carry a real duration
    is_train = df[Inc.type] == "T"
    for threshold in (5, 10, 30):
        first_bin = next(b for b, (low, _) in BIN_MINUTES.items() if low >= threshold)
        df[Inc[f"major_{threshold}"]] = (
            (df[Inc.duration_bin] >= first_bin).astype("boolean").where(is_train)
        )
    return df


def train_incidents(inc: pd.DataFrame) -> pd.DataFrame:
    """Train incidents on one named line: the population of every analysis."""
    return inc[(inc[Inc.type] == "T") & inc[Inc.line].isin(LINES)]


def model_population(inc: pd.DataFrame) -> pd.DataFrame:
    """Rows the prediction models use: train incidents on one named line, up to the last
    full year."""
    df = train_incidents(inc)
    df = df[df[Inc.year] <= LAST_FULL_YEAR].copy()
    targets = [Inc.major_5, Inc.major_10, Inc.major_30]
    df[targets] = df[targets].astype(bool)
    # 0.3% of rows have no symptom: kept as their own value so every model sees the same rows
    df[Inc.symptom] = df[Inc.symptom].fillna("not recorded")
    return df


def load_km(path: Path = KM_FILE) -> pd.DataFrame:
    """Planned km by line, service period, run and day (2019-01 to 2023-09)."""
    raw = pd.read_csv(path, encoding="utf-8-sig", decimal=",", dtype={"Tournée": str})
    df = raw[list(KM_COLUMNS)].rename(columns=KM_COLUMNS)
    df[Km.date] = pd.to_datetime(df[Km.date])
    df[Km.km] = df[Km.km].astype(float)
    df[Km.year] = df[Km.date].dt.year
    # service period '#' / day type 'Non affecté' still carries real km: flagged, not dropped
    df[Km.unassigned] = df[Km.service_period] == "#"
    return df
