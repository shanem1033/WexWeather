# WexWeather

A local weather app for Co. Wexford, Ireland. It combines 10 years of historical weather data with tomorrow's forecast, and uses a language model to highlight anything interesting about the forecast compared with the past decade.

> **Work in progress.** The database, data pipeline, forecast integration, nightly job and AI summaries are complete. A web endpoint for the summary and a frontend are still to come. See the [Roadmap](#roadmap).

## What it does

- Stores 10+ years of daily weather records (max/min temperature, rainfall, wind speed and gusts) from Met Éireann's Johnstown Castle II station in Co. Wexford
- Serves historical statistics through a REST API, such as how a given date has looked across the years
- Fetches tomorrow's forecast from Met Éireann every night and stores it alongside the historical record
- Generates a one-sentence summary of what's notable about the forecast, e.g. *"Wexford expects a record-breaking max temperature of 17.1C and top gust of 42kt on 29 September 2026."*
- Picks one positive historical event that happened on the same calendar date

### How the AI summaries work

**The model is never asked a question it could answer from memory.** It is only ever handed real data and asked to phrase it.

For the weather, the app does the arithmetic itself. It reads the saved forecast, reads the historical record for that calendar date, and works out in Python where the forecast ranks among those years — including which year holds the record and what it was. Only those finished numbers reach the model, which chooses the words. It cannot get a fact wrong because it is not the source of any fact.

The same applies to the historical event. Rather than asking the model what happened on this date — a well-known way to get confident, wrong answers — the app fetches the real list of events for that date and asks the model to pick one positive entry from it and write it up.

This also means the summary degrades safely. If the model is unavailable, the forecast is still saved and the statistics are still served; you lose a sentence, not the pipeline.

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python |
| API | FastAPI |
| Database | PostgreSQL 18 |
| Database driver | psycopg 3 |
| AI | Gemini API (`google-genai`, free tier) |
| HTTP client | httpx |
| Scheduling | Windows Task Scheduler |

## Data

### History

Historical data comes from **Met Éireann**, Ireland's national meteorological service. It uses daily records from the **Johnstown Castle II** synoptic station (station 1775, near Wexford town).

- **Coverage:** 1 January 2016 to 31 August 2026 (3,896 days, with no missing days)
- **Fields used:** maximum temperature, minimum temperature, rainfall, mean wind speed, highest gust

### Forecast

Forecasts come from Met Éireann's open location forecast API, chosen over other providers so that forecasts and history come from the same organisation and are directly comparable.

```
http://openaccess.pf.api.met.ie/metno-wdb2ts/locationforecast?lat=52.298;long=-6.497
```

The XML contains two kinds of `<time>` element, distinguished by whether `from` equals `to`:

- **Instants** (`from == to`) carry temperature, wind speed and gusts at a point in time.
- **Intervals** (`from != to`) carry accumulated rainfall over a period.

A day's figures are built from these to mirror how the historical fields are defined: mean wind speed across the day's hourly readings (matching `wdsp`), and the highest single gust (matching `hg`). Rain intervals count towards the day they start in.

Because the daily figures are derived from hourly readings, a forecast max or min can be slightly less extreme than a station's true daily max or min, which is measured continuously.

### Data quality notes

- **Pre-2016 data is excluded.** The station's records begin in 2008, but early rows show a mean wind speed of 0.1 knots and gusts of 0 every day, which suggests a faulty wind sensor. Starting from 2016 gives a clean 10-year window.
- **Missing readings are stored as `NULL`, not zero.** A zero would claim a dry, calm day. `NULL` means "no reading", and SQL averages skip it correctly. The dataset has no missing temperatures and just 2 missing rainfall and wind readings.
- **Sunshine isn't included.** The file's documentation lists a sunshine column, but this station doesn't record it.
- **Wind is stored in knots**, as in the source data, and converted for display. Forecast values arrive in m/s and are converted to knots when parsed, so both tables use the same unit.
- **Days are UTC days**, matching how Met Éireann's historical records are defined.

## Database design

```
stations                      daily_weather                 daily_forecast
─────────────                 ───────────────────           ───────────────────
station_id (PK) ◄──────────── station_id (FK)       ◄─────── station_id (FK)
name                          date                          date
county                        max_temp                      max_temp
latitude                      min_temp                      min_temp
longitude                     rain_mm                       rain_mm
                              wind_speed_kt                 wind_speed_kt
                              max_gust_kt                   max_gust_kt
                              PK: (station_id, date)        hours
                                                            fetched_at
                                                            PK: (station_id, date)
```

- **Two normalised tables:** station details are stored once, not repeated on every weather row.
- **Composite primary key `(station_id, date)`:** each station has exactly one record per day. This means adding more stations, even all of Ireland, only requires inserting more rows, with no schema changes.
- **Foreign key:** weather rows can't reference a station that doesn't exist.

### Why observations and forecasts are separate tables

`daily_weather` holds what actually happened; `daily_forecast` holds what was predicted. They're never mixed, because a forecast is a different kind of claim from a measurement and combining them would quietly corrupt the historical record that every statistic is calculated from.

The forecast table carries two extra columns that only make sense for a prediction:

- `hours` — how many hourly readings the day's figures were derived from. A day built from 24 readings is trustworthy; a partial day isn't.
- `fetched_at` — when the forecast was retrieved, since a forecast is only meaningful relative to when it was made.

## The daily job

`scripts/fetch_forecast.py` fetches the forecast, summarises **tomorrow**, and saves it. It runs once a night rather than continuously, because the API only returns forecasts from the current hour onwards, so late evening is the first point at which a complete 24-hour picture of tomorrow is available.

Two properties make it safe to run unattended:

- **It refuses partial days.** If fewer than 24 hourly readings are available, it exits non-zero without saving, rather than storing a max/min derived from half a day.
- **It's idempotent.** The insert uses `ON CONFLICT (station_id, date) DO NOTHING`, so running it twice saves one row and reports that the second run was skipped. A retry can never double-count.

`run_daily.bat` is the wrapper Task Scheduler runs. It changes to its own directory, calls the virtual environment's interpreter directly (no activation needed, since activation mainly just puts that interpreter on `PATH`), appends both output and errors to `logs/forecast.log`, and passes the exit code back so a failed night shows as a non-zero Last Run Result rather than silently looking fine.

The scheduled task itself is committed as `task/wexweather_daily.xml`, so the schedule is version controlled rather than existing only as clicks in a GUI.

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

   The application connects as a dedicated role rather than the `postgres` superuser, so its reach is limited to this one database and it has no power over the wider cluster.

3. **Add a `.env` file** in the project root

   ```
   DATABASE_URL=postgresql://wexweather_app:your-password@localhost:5432/wexweather
   GEMINI_API_KEY=your-key-here
   ```

   The Gemini key comes from [aistudio.google.com/apikey](https://aistudio.google.com/apikey) and needs no card. It is only required for the summaries — everything else runs without it. The free tier allows 20 requests per day per model, against the two per night this app uses.

4. **Create the tables and load the data**

   ```bash
   psql -U wexweather_app -d wexweather -f sql/schema.sql
   python -m scripts.load_data
   ```

   `schema.sql` uses `CREATE TABLE IF NOT EXISTS` throughout and is safe to rerun. The loading script is safe to rerun too: it skips days that are already in the database, so updating with newer data only adds the new days.

   Scripts are run from the project root with `python -m` so that imports from `app/` resolve and relative data paths work.

5. **Run the API**

   ```bash
   uvicorn app.main:app --reload
   ```

   Interactive API docs are available at `http://127.0.0.1:8000/docs`.

6. **Set up the nightly forecast job** (optional)

   Confirm the job works by hand first:

   ```bash
   python -m scripts.fetch_forecast
   ```

   Then register the scheduled task:

   ```bash
   schtasks /create /tn "WexWeather daily forecast" /xml task/wexweather_daily.xml /f
   ```

   The committed task runs daily at 23:00, catches up after a missed start (so a sleeping laptop doesn't leave a permanent gap), and isn't skipped on battery. The `UserId` in the XML is machine specific and needs changing on another machine.

   On macOS or Linux, schedule `python -m scripts.fetch_forecast` with cron instead. The job itself knows nothing about who runs it, so only the scheduler differs.

7. **Generate a summary**

   ```bash
   python -m app.summary              # tomorrow
   python -m app.summary 2026-09-29   # a specific date
   ```

   This prints the facts given to the model, then the two sentences it produced. Seeing the facts first is the point: if a number there is wrong, no amount of prompt wording will fix it.

   Summaries are not yet wired into the nightly job or exposed as an endpoint — `python -m app.summary` is currently the only way to run them.

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/data-range` | First and last day held, and the total number of days |
| `GET` | `/stats/{month}/{day}` | Statistics for a calendar date across all years: number of years, average and highest max temperature, lowest min temperature, average rainfall |

## Project structure

```
WexWeather/
├── app/
│   ├── main.py               # FastAPI endpoints only
│   ├── db.py                 # All PostgreSQL code
│   ├── forecast.py           # All Met Éireann forecast code
│   ├── summary.py            # Ranking, fact rendering, model calls
│   └── onthisday.py          # Historical events for a calendar date
├── data/
│   ├── wexford_daily.csv     # Met Éireann daily history (Johnstown Castle II)
│   └── sample_forecast.xml   # Saved forecast, used as a fixed test file
├── scripts/
│   ├── load_data.py          # Loads the CSV history into PostgreSQL
│   └── fetch_forecast.py     # Nightly job: fetch, summarise tomorrow, save
├── sql/
│   └── schema.sql            # Database schema
├── task/
│   └── wexweather_daily.xml  # Scheduled task definition
├── run_daily.bat             # Wrapper the scheduler runs
├── requirements.txt
└── README.md
```

Code is organised by what it knows about: anything that knows SQL lives in `db.py`, anything that knows about Met Éireann or XML lives in `forecast.py`, anything that knows about the language model lives in `summary.py`, and anything that knows about URLs and HTTP responses lives in `main.py`. A module that knows about a new external source gets its own file, which is why `onthisday.py` is separate.

## Roadmap

- [x] Project setup and PostgreSQL schema
- [x] Data loading script with data validation
- [x] API endpoints for historical statistics
- [x] Today's forecast integration
- [x] Nightly scheduled job
- [x] AI-generated "what's interesting today" summary
- [x] Positive historical event for the date
- [ ] Endpoint to serve the summary
- [ ] Simple frontend
- [ ] Deployment

## Data attribution

Weather data © **Met Éireann**, licensed under [Creative Commons Attribution 4.0 (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/). The data has been filtered (2016 onwards) and restructured for this project. Met Éireann does not accept any liability for errors or omissions in the data.

Forecast data is retrieved from Met Éireann's open location forecast API, also under CC BY 4.0. The service is provided on a best-effort basis with no guarantee of availability. Met Éireann requires that any public website displaying its forecasts also displays its weather warnings.

Historical "on this day" events come from Wikipedia via [byabbe.se](https://byabbe.se/on-this-day/), which serves them as JSON without requiring an API key. Wikipedia text is available under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Neither service offers a guarantee of availability, so the app treats a missing event as an ordinary outcome rather than an error.
