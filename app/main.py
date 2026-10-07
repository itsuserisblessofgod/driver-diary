import datetime as dt
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import service
from .db import SessionLocal
from .schemas import Summary, TripIn, TripOut

app = FastAPI(title="Дневник смен водителя")


def get_db():
    with SessionLocal() as db:
        yield db


DB = Annotated[Session, Depends(get_db)]
Day = Annotated[dt.date, Query(alias="date", description="YYYY-MM-DD, календарный день в APP_TZ")]


@app.get("/api/trips", response_model=list[TripOut])
def list_trips(day: Day, db: DB):
    return service.trips_for_day(db, day)


@app.get("/api/summary", response_model=Summary)
def day_summary(day: Day, db: DB):
    return service.summarize(service.trips_for_day(db, day))


@app.get("/api/days")
def list_days(db: DB) -> list[str]:
    """Days that have trips, newest first — the client opens the latest one."""
    return service.days_with_trips(db)


@app.post("/api/trips", response_model=TripOut, status_code=201)
def create_trip(trip: TripIn, response: Response, db: DB):
    """201 — created; 200 — the same trip was already saved; 409 — same id, different data."""
    try:
        saved, created = service.add_trip(db, trip.model_dump())
    except service.TripConflict:
        raise HTTPException(409, f"Trip {trip.id!r} already exists with different data")
    if not created:
        response.status_code = 200
    return saved


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True))
