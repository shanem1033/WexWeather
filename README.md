# WexWeather

A local weather app for Co. Wexford, Ireland. It combines 10 years of historical weather data with today's forecast, and uses the Claude API to highlight anything interesting about today's weather compared with the past decade.

>  **Work in progress.** The database and data pipeline are complete. 

The API, forecast and AI summary are in development. See the [Roadmap](#roadmap).

## What it does

- Stores 10+ years of daily weather records (max/min temperature, rainfall, wind speed and gusts) from Met Éireann's Johnstown Castle II station in Co. Wexford
- *(Planned)* Serves historical statistics through a REST API, such as yearly averages and how a given date has looked across the years
- *(Planned)* Fetches today's forecast and generates a short summary of what's notable about it, e.g. *"Today's high of 21°C would make it the warmest 23rd of September in a decade."*

### How the AI summary works

The app never asks Claude about the weather directly. Instead, it calculates the real statistics itself (today's forecast alongside the historical record for this date) and passes those numbers to Claude to interpret. Claude only describes facts it has been given, so it can't make up weather data.

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python |
| API | FastAPI |
| Database | PostgreSQL 18 |
| Database driver | psycopg 3 |
| AI | Claude API (Anthropic) |
| HTTP client | httpx |

## Data

Historical data comes from **Met Éireann**, Ireland's national meteorological service. It uses daily records from the **Johnstown Castle II** synoptic station (station 1775, near Wexford town).

- **Coverage:** 1 January 2016 to 31 August 2026 (3,896 days, with no missing days)
- **Fields used:** maximum temperature, minimum temperature, rainfall, mean wind speed, highest gust

### Data quality notes

- **Pre-2016 data is excluded.** The station's records begin in 2008, but early rows show a mean wind speed of 0.1 knots and gusts of 0 every day, which suggests a faulty wind sensor. Starting from 2016 gives a clean 10-year window.
- **Missing readings are stored as `NULL`, not zero.** A zero would claim a dry, calm day. `NULL` means "no reading", and SQL averages skip it correctly. The dataset has no missing temperatures and just 2 missing rainfall and wind readings.
- **Sunshine isn't included.** The file's documentation lists a sunshine column, but this station doesn't record it.
- **Wind is stored in knots**, as in the source data, and converted for display.

## Database design

```
stations                      daily_weather
─────────────                 ───────────────────
station_id (PK) ◄──────────── station_id (FK)
name                          date
county                        max_temp
latitude                      min_temp
longitude                     rain_mm
                              wind_speed_kt
                              max_gust_kt
                              PK: (station_id, date)
```

- **Two normalised tables:** station details are stored once, not repeated on every weather row.
- **Composite primary key `(station_id, date)`:** each station has exactly one record per day. This means adding more stations, even all of Ireland, only requires inserting more rows, with no schema changes.
- **Foreign key:** weather rows can't reference a station that doesn't exist.

### Why PostgreSQL over SQLite?

SQLite would comfortably handle this dataset of a few thousand rows that are mostly read. I chose PostgreSQL to gain hands-on experience with a database that's widely used in industry, and because it suits deployment better: many hosting platforms don't keep local files, so a SQLite database file could be wiped.

## Getting started

### Prerequisites

- Python 3.11+
- PostgreSQL

### Setup

1. **Clone the repo and create a virtual environment**

   ```bash
   git clone https://github.com/shanem1033/WexWeather.git
   cd WexWeather
   python -m venv venv
   source venv/Scripts/activate   # Windows (Git Bash)
   # source venv/bin/activate     # macOS / Linux
   pip install -r requirements.txt
   ```

2. **Create the database and a dedicated user** (as the `postgres` superuser)

   ```sql
   CREATE USER wexweather_app WITH PASSWORD 'your-password';
   CREATE DATABASE wexweather OWNER wexweather_app;
   ```

3. **Add a `.env` file** in the project root

   ```
   DATABASE_URL=postgresql://wexweather_app:your-password@localhost:5432/wexweather
   ```

4. **Create the tables and load the data**

   ```bash
   psql -U wexweather_app -d wexweather -f sql/schema.sql
   python scripts/load_data.py
   ```

   The loading script is safe to rerun: it skips days that are already in the database, so updating with newer data only adds the new days.

5. **Run the API**

   ```bash
   uvicorn app.main:app --reload
   ```

   Interactive API docs are available at `http://127.0.0.1:8000/docs`.

## Project structure

```
WexWeather/
├── app/
│   └── main.py           # FastAPI application
├── data/
│   └── wexford_daily.csv # Met Éireann daily data (Johnstown Castle II)
├── scripts/
│   └── load_data.py      # Loads the CSV into PostgreSQL
├── sql/
│   └── schema.sql        # Database schema
├── requirements.txt
└── README.md
```

## Roadmap

- [x] Project setup and PostgreSQL schema
- [x] Data loading script with data validation
- [ ] API endpoints for historical statistics
- [ ] Today's forecast integration
- [ ] Claude-generated "what's interesting today" summary
- [ ] Simple frontend
- [ ] Deployment

## Data attribution

Weather data © **Met Éireann**, licensed under [Creative Commons Attribution 4.0 (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/). The data has been filtered (2016 onwards) and restructured for this project. Met Éireann does not accept any liability for errors or omissions in the data.