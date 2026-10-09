# WexWeather

A local weather app for Co. Wexford, Ireland. Every night it saves the forecasts for the next two days, compares the first with 10 years of history for the same date, and has a language model write one sentence about what stands out, plus one positive event from history on that date.

## How the AI summaries work

**The model is never the source of a fact.** Python reads the forecast and the history, works out where the forecast ranks (including which year holds the record), and hands the model only those finished numbers to phrase. The "on this day" event works the same way: the app fetches real events from Wikipedia and the model only picks one and writes it up.

If the model is unavailable, the forecast is still saved and the API still serves statistics. A bad night costs a sentence, not the pipeline.

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| API | FastAPI, Uvicorn |
| Database | PostgreSQL 18, psycopg 3 |
| AI | Gemini API (`google-genai`, free tier) |
| HTTP client | httpx |
| Tests | pytest |
| Scheduling | Windows Task Scheduler |

## Data

- **History:** daily records from Met Éireann's Johnstown Castle II station (1775), 1 January 2016 to 31 August 2026, 3,896 days. Earlier years are excluded because their wind readings point to a faulty sensor.
- **Forecast:** Met Éireann's open location forecast API, so forecasts and history come from the same source. Hourly readings are reduced to one day in the same shape as the history: max/min temperature, total rain, mean wind and highest gust.
- **Missing readings are `NULL`, never zero.** Zero would claim a dry, calm day. `NULL` means "no reading" and is carried through to the API and the summaries.
- **Units and days:** wind is stored in knots (forecasts are converted from m/s), and days are UTC days, matching Met Éireann's records.

## Database

Five tables, each keyed by `(station_id, date)` apart from `stations`:

- `stations`: station details, stored once
- `daily_weather`: what actually happened
- `forecast_today`: saved the night before a date and shown as that day's forecast; the summary is built from it
- `forecast_tomorrow`: saved two nights before a date and only ever shown as "tomorrow"
- `daily_summary`: the two generated sentences and the model that wrote them

Both forecast tables also store `hours` (readings the day was built from) and `fetched_at`. A tomorrow forecast is never reused as today's: today always comes from the fresher fetch.

Observations and forecasts are kept in separate tables so a prediction can never leak into the historical record that every statistic is built from. All inserts use `ON CONFLICT DO NOTHING`, so every script is safe to rerun.

## The nightly job

`scripts/fetch_forecast.py` runs at 23:00. One fetch covers about 9 days, and the next two days are complete hourly days. Run on the 9th, it saves:

- the 10th to `forecast_today`, then generates the 10th's summary from it
- the 11th to `forecast_tomorrow`

Today itself is never saved, because the feed starts at the current hour.

- **It refuses partial days.** A day with fewer than 24 hourly readings is not saved, the other day still is, and the job exits non-zero.
- **It is idempotent.** Running it twice saves one row and skips the second.

`run_daily.bat` is the wrapper Task Scheduler runs. It logs to `logs/forecast.log` and passes the exit code back. The task itself is version controlled in `task/wexweather_daily.xml`.

## Getting started

1. **Install**

   ```bash
   git clone https://github.com/shanem1033/WexWeather.git
   cd WexWeather
   python -m venv venv
   source venv/Scripts/activate   # Windows (Git Bash); venv/bin/activate on macOS/Linux
   pip install -r requirements.txt
   ```

2. **Create the database** (as the `postgres` superuser). The app uses its own role rather than the superuser.

   ```sql
   CREATE USER wexweather_app WITH PASSWORD 'your-password';
   CREATE DATABASE wexweather OWNER wexweather_app;
   ```

3. **Add a `.env` file** in the project root. The Gemini key is free from [aistudio.google.com/apikey](https://aistudio.google.com/apikey) and only needed for summaries.

   ```
   DATABASE_URL=postgresql://wexweather_app:your-password@localhost:5432/wexweather
   GEMINI_API_KEY=your-key-here
   ```

4. **Create the tables and load the history**

   ```bash
   psql -U wexweather_app -d wexweather -f sql/schema.sql
   python -m scripts.load_data
   ```

Run every script from the project root with `python -m`, so imports from `app/` resolve.

## Usage

| Command | What it does |
|---|---|
| `uvicorn app.main:app --reload` | Run the API (docs at `http://127.0.0.1:8000/docs`) |
| `python -m scripts.fetch_forecast` | Run the nightly job by hand |
| `python -m scripts.report [YYYY-MM-DD]` | Run the nightly job now, then print a day's report (`--show-only` skips the job) |
| `python -m app.summary [YYYY-MM-DD]` | Print the facts given to the model and its output, without saving |
| `pytest` | Run the tests. No network; writes use 1900 dates in the dev database and clean up after |

To schedule the nightly job on Windows:

```bash
schtasks /create /tn "WexWeather daily forecast" /xml task/wexweather_daily.xml /f
```

The `UserId` in the XML is machine specific. On macOS or Linux, use cron to run `python -m scripts.fetch_forecast`.

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/data-range` | First and last day held, and the number of days |
| `GET` | `/stats/{month}/{day}` | A calendar date across all years: average and record temperatures, average rain |
| `GET` | `/today` | Today's forecast and summary (`null` where nothing is saved yet) |
| `GET` | `/tomorrow` | Tomorrow's forecast |

## Project structure

```
app/
  main.py            API endpoints
  config.py          Environment settings and station details
  db.py              All PostgreSQL code
  forecast.py        Met Éireann forecast fetching and parsing
  summary.py         Ranking, fact rendering, model calls
  onthisday.py       Historical events for a date
scripts/
  load_data.py       Load the CSV history
  fetch_forecast.py  Nightly job
  report.py          One-command report
sql/schema.sql       Database schema
tests/               pytest suite
data/                History CSV and a saved forecast for tests
task/                Scheduled task definition
run_daily.bat        Wrapper the scheduler runs
```

Each module owns one outside dependency: SQL lives only in `db.py`, Met Éireann only in `forecast.py`, the model only in `summary.py`, HTTP only in `main.py`.

## Roadmap

- [ ] Deployment
- [ ] Scheduling with Dagster
- [ ] Simple frontend

## Data attribution

Weather data and forecasts © **Met Éireann**, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The history has been filtered (2016 onwards) and restructured. Met Éireann accepts no liability for errors or omissions, and requires any public website displaying its forecasts to also display its weather warnings.

"On this day" events come from Wikipedia via [byabbe.se](https://byabbe.se/on-this-day/), under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
