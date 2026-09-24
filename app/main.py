from fastapi import FastAPI

from app import db

app = FastAPI(title="WexWeather")

@app.get("/data-range")
def data_range():
    return db.get_data_range()

@app.get("/stats/{month}/{day}")
def stats(month: int, day: int):
    return db.get_day_stats(month, day)