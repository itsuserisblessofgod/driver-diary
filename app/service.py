from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import APP_TZ, Trip


class TripConflict(Exception):
    """The id is taken by a trip with different data."""


def day_bounds(day: date) -> tuple[datetime, datetime]:
    """[00:00, 24:00) of a calendar day in APP_TZ, as UTC instants."""
    lo = datetime.combine(day, time.min, tzinfo=APP_TZ)
    hi = datetime.combine(day + timedelta(days=1), time.min, tzinfo=APP_TZ)
    return lo.astimezone(timezone.utc), hi.astimezone(timezone.utc)


def trips_for_day(db: Session, day: date) -> list[Trip]:
    """A trip belongs to the day it started on."""
    lo, hi = day_bounds(day)
    return list(db.scalars(select(Trip).where(Trip.start >= lo, Trip.start < hi).order_by(Trip.start)))


def days_with_trips(db: Session) -> list[str]:
    starts = db.scalars(select(Trip.start))
    return sorted({s.astimezone(APP_TZ).date().isoformat() for s in starts}, reverse=True)


def _totals(trips: list[Trip]) -> dict:
    revenue = sum(t.amount for t in trips)
    commission = sum(t.commission for t in trips)
    return {"trips": len(trips), "revenue": revenue, "commission": commission, "net": revenue - commission}


def summarize(trips: list[Trip]) -> dict:
    by_payment = {p: _totals([t for t in trips if t.payment == p]) for p in ("cash", "card")}
    return {**_totals(trips), "by_payment": by_payment}


def add_trip(db: Session, data: dict) -> tuple[Trip, bool]:
    """Insert a trip -> (trip, created).

    The primary key is the idempotency key. Duplicates are caught by the database
    itself, so two concurrent identical requests cannot both succeed.
    """
    trip = Trip(**data)
    db.add(trip)
    try:
        db.commit()
        return trip, True
    except IntegrityError:
        db.rollback()
        existing = db.get(Trip, data["id"])
        if existing is None:
            raise  # some other constraint failed
        if any(getattr(existing, k) != v for k, v in data.items()):
            raise TripConflict(data["id"])
        return existing, False
