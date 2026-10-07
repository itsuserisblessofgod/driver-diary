from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_serializer, model_validator

from .db import APP_TZ


class TripIn(BaseModel):
    id: str = Field(min_length=1, max_length=64)  # also the idempotency key
    start: AwareDatetime
    end: AwareDatetime
    amount: int = Field(gt=0)
    payment: Literal["cash", "card"]
    commission: int = Field(ge=0)

    @model_validator(mode="after")
    def check_consistency(self):
        if self.end <= self.start:
            raise ValueError("end must be later than start")
        if self.commission > self.amount:
            raise ValueError("commission must not exceed amount")
        return self


class TripOut(TripIn):
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("start", "end")
    def to_local(self, value: datetime) -> str:
        return value.astimezone(APP_TZ).isoformat()


class Totals(BaseModel):
    trips: int
    revenue: int
    commission: int
    net: int


class Summary(Totals):
    by_payment: dict[str, Totals]
