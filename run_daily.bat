@echo off
REM Daily forecast job. Run by Task Scheduler around 23:00.
REM Saves tomorrow's Met Eireann forecast to daily_forecast.

REM %~dp0 is this file's own folder, so the job works from any
REM working directory. /d also handles a drive change.
cd /d "%~dp0"

REM Windows defaults Python's stdout to cp1252, which mangles accented output
REM and raises UnicodeEncodeError on anything outside it - enough to kill the
REM job after its real work has already succeeded. Force UTF-8.
set PYTHONUTF8=1

if not exist logs mkdir logs

echo. >> logs\forecast.log
echo ==== %DATE% %TIME% ==== >> logs\forecast.log

REM Call the venv's interpreter directly: no activation needed.
REM 2>&1 sends tracebacks to the log too, not just normal output.
venv\Scripts\python.exe -m scripts.fetch_forecast >> logs\forecast.log 2>&1

REM Save the exit code before echo overwrites it, then hand it back
REM to Task Scheduler as the task's Last Run Result.
set RC=%ERRORLEVEL%
echo exit code: %RC% >> logs\forecast.log
exit /b %RC%
