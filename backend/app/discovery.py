"""Calendar discovery and snapshot-verified demo requests, without semantic ranking."""
from datetime import date, timedelta
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .catalog import Catalog
from .rules import CheckedProfile, filter_profiles
from .schemas import MAX_BUDGET, MAX_DATE, MIN_DATE, AvailabilityDay, Schema, SearchParams

MAX_AVAILABILITY_DAYS = 31


class AvailabilityRequest(Schema):
    query: SearchParams
    date_from: date | None = Field(default=None, ge=MIN_DATE, le=MAX_DATE)
    date_to: date | None = Field(default=None, ge=MIN_DATE, le=MAX_DATE)
    days_before: int | None = Field(default=None, ge=0, le=30, strict=True,
                                    description='По умолчанию 2 дня для относительного окна')
    days_after: int | None = Field(default=None, ge=0, le=30, strict=True,
                                   description='По умолчанию 2 дня для относительного окна')

    @field_validator('date_from', 'date_to', mode='before')
    @classmethod
    def calendar_date(cls, value: object) -> object:
        return None if value is None else SearchParams.calendar_date(value)

    @model_validator(mode='after')
    def valid_range(self) -> 'AvailabilityRequest':
        explicit = self.date_from is not None or self.date_to is not None
        if explicit:
            if self.date_from is None or self.date_to is None:
                raise ValueError('Укажите обе границы date_from и date_to')
            if self.days_before is not None or self.days_after is not None:
                raise ValueError('Укажите диапазон дат или окно, но не оба варианта')
            if self.date_from > self.date_to:
                raise ValueError('date_from не может быть позже date_to')
            length = (self.date_to - self.date_from).days + 1
        else:
            length = self.before_days() + self.after_days() + 1
        if length > MAX_AVAILABILITY_DAYS:
            raise ValueError('Можно проверить не более 31 календарного дня')
        return self

    def bounds(self) -> tuple[date, date]:
        if self.date_from is not None and self.date_to is not None:
            return self.date_from, self.date_to
        return (max(MIN_DATE, self.query.date - timedelta(days=self.before_days())),
                min(MAX_DATE, self.query.date + timedelta(days=self.after_days())))

    def before_days(self) -> int:
        return 2 if self.days_before is None else self.days_before

    def after_days(self) -> int:
        return 2 if self.days_after is None else self.days_after


class AvailabilityResponse(Schema):
    query: SearchParams
    date_from: date
    date_to: date
    days: list[AvailabilityDay] = Field(max_length=MAX_AVAILABILITY_DAYS)
    recommended_date: date | None
    data_version: str


def find_availability(catalog: Catalog, request: AvailabilityRequest) -> AvailabilityResponse:
    """Count every eligible profile; recommend a positive day other than the selected day.

    Explicit ranges must be inside the known calendar. Relative windows are clipped
    to that calendar. Dates are calendar days, with no timezone conversion.
    """
    query = catalog.canonical_query(request.query)
    first, last = request.bounds()
    days = []
    for offset in range((last - first).days + 1):
        day = first + timedelta(days=offset)
        eligible, _ = filter_profiles(catalog.profiles, query.model_copy(update={'date': day}))
        days.append(AvailabilityDay(date=day, available=len(eligible)))
    alternatives = [day for day in days if day.date != query.date and day.available > 0]
    preferred = min(alternatives, key=lambda day: (
        -day.available, abs((day.date - query.date).days), day.date,
    )) if alternatives else None
    return AvailabilityResponse(query=query, date_from=first, date_to=last, days=days,
                                recommended_date=preferred.date if preferred else None,
                                data_version=catalog.version)
