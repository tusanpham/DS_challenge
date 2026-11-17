# Data

Both files are unmodified copies of the datasets as provided with the challenge (extract dated 2026-07-07), published by the Société de transport de Montréal on the Ville de Montréal open data portal. Only the file names were changed, to ASCII with a `.csv` extension, because the originals are delimited text despite their `.xls` extension.

| File | Original name | Source |
|---|---|---|
| `raw/incidents_metro_20260707.csv` | `Incidents métro_20260707.xls` | [Incidents du réseau du métro](https://donnees.montreal.ca/dataset/incidents-du-reseau-du-metro) |
| `raw/km_planifie_metro_20260707.csv` | `Kilométrage métro planifé_20260707.xls` | Kilométrage métro des périodes de service (same portal) |

## Reading the files

- Encoding: UTF-8 with BOM (`encoding="utf-8-sig"`).
- Incidents: `;`-delimited. Kilometres: `,`-delimited with decimal commas (`decimal=","`).
- Incident times after midnight use a service-day clock (`24:58:00`, `25:20:00`), which naive time parsing drops; daytime values are `HH:MM`.
- Headers and categorical values are in French.
- `#` marks a missing value in the incidents file.
