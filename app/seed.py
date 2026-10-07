"""Load trips from a JSON file: python -m app.seed [path]. Safe to re-run."""
import sys
from pathlib import Path

from pydantic import TypeAdapter

from . import service
from .db import SessionLocal
from .schemas import TripIn

path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/trips.json")
trips = TypeAdapter(list[TripIn]).validate_json(path.read_text(encoding="utf-8"))
with SessionLocal() as db:
    created = sum(service.add_trip(db, t.model_dump())[1] for t in trips)
print(f"{path}: {created} added, {len(trips) - created} already present")
