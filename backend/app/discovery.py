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


PresetId = Literal['normal_match', 'strict_budget', 'date_effect', 'rare_category']


class DemoPreset(Schema):
    id: PresetId
    title: str
    description: str
    query: SearchParams
    expected_status: Literal['matched', 'no_match']
    eligible_count: int = Field(ge=0)
    related_query: SearchParams | None = None
    related_eligible_count: int | None = Field(default=None, ge=0)


class OmittedPreset(Schema):
    id: PresetId
    reason: str


class DemoPresetsResponse(Schema):
    data_version: str
    presets: list[DemoPreset]
    omitted: list[OmittedPreset]


def _seed_queries(catalog: Catalog) -> list[SearchParams]:
    """One seed for each observed city/category/format, funded from actual prices."""
    groups: dict[tuple[str, str, str], list[float]] = {}
    for profile in catalog.profiles:
        if profile.price is None or profile.price > MAX_BUDGET:
            continue
        for category in profile.categories:
            for event_format in profile.formats:
                groups.setdefault((profile.city, category, event_format), []).append(profile.price)
    # Start with common observed combinations; the order never depends on CSV order.
    ordered = sorted(groups, key=lambda key: (-len(groups[key]), key))
    return [catalog.canonical_query(SearchParams(city=city, category=category, event_type=event_format,
                                                date=MIN_DATE, budget=max(groups[(city, category, event_format)])))
            for city, category, event_format in ordered]


def build_demo_presets(catalog: Catalog) -> DemoPresetsResponse:
    """Build requests against the current snapshot using the same hard-rule pipeline.

    The caller may retain this result for the immutable catalog lifetime. A new
    snapshot must rebuild it. No precomputed response, ML call or dataset write is
    involved. Work is bounded by observed combinations and the 100-day calendar.
    """
    seeds = _seed_queries(catalog)
    presets: list[DemoPreset] = []
    omitted: list[OmittedPreset] = []
    # Seeds differ only by these fields/date; optional conditions remain None.
    cache: dict[tuple[str, str, str, float, date], list[CheckedProfile]] = {}

    def eligible(query: SearchParams) -> list[CheckedProfile]:
        key = (query.city, query.category, query.event_type, query.budget, query.date)
        if key not in cache:
            cache[key], _ = filter_profiles(catalog.profiles, query)
        return cache[key]

    def add(identifier: PresetId, title: str, description: str, query: SearchParams,
            related: SearchParams | None = None) -> None:
        count = len(eligible(query))
        presets.append(DemoPreset(id=identifier, title=title, description=description,
                                  query=query, eligible_count=count,
                                  expected_status='matched' if count else 'no_match',
                                  related_query=related,
                                  related_eligible_count=len(eligible(related)) if related is not None else None))

    def first_match(queries: list[SearchParams]) -> SearchParams | None:
        for seed in queries:
            for offset in range((MAX_DATE - MIN_DATE).days + 1):
                query = seed.model_copy(update={'date': MIN_DATE + timedelta(days=offset)})
                if eligible(query):
                    return query
        return None

    normal = first_match(seeds)
    if normal is None:
        omitted.append(OmittedPreset(id='normal_match', reason='Нет проверенного запроса с подходящими подрядчиками.'))
        omitted.append(OmittedPreset(id='strict_budget', reason='Нет исходного совпадения для проверки уменьшения бюджета.'))
    else:
        add('normal_match', 'Подходящие подрядчики', 'Запрос подтверждён текущим снимком каталога.', normal)
        prices = [item.profile.price for item in eligible(normal) if item.profile.price is not None]
        budget = min(prices) / 2
        strict = normal.model_copy(update={'budget': budget})
        if budget > 0 and not eligible(strict):
            add('strict_budget', 'Строгий бюджет',
                'Уменьшение бюджета исключает всех; исходный запрос с теми же остальными условиями даёт совпадения.',
                strict, normal)
        else:
            omitted.append(OmittedPreset(id='strict_budget', reason='Не удалось построить допустимый меньший бюджет.'))

    date_pair: tuple[SearchParams, SearchParams] | None = None
    # Availability can change only at a busy-date boundary in this calendar model.
    # Compare adjacent days around those boundaries instead of every pair of dates.
    boundaries = sorted({day + timedelta(days=offset) for profile in catalog.profiles
                         for day in profile.busy_dates or () for offset in (-1, 0)
                         if MIN_DATE <= day + timedelta(days=offset) < MAX_DATE})
    for seed in seeds:
        for day in boundaries:
            left = seed.model_copy(update={'date': day})
            right = seed.model_copy(update={'date': day + timedelta(days=1)})
            left_count, right_count = len(eligible(left)), len(eligible(right))
            if left_count != right_count:
                date_pair = (left, right) if left_count < right_count else (right, left)
                break
        if date_pair is not None:
            break
    if date_pair is None:
        omitted.append(OmittedPreset(id='date_effect', reason='В известном календаре не найдено изменения числа совпадений при смене даты.'))
    else:
        add('date_effect', 'Дата влияет на выбор',
            'На соседней дате больше совпадений при сохранении остальных условий.', date_pair[0], date_pair[1])

    category_sizes = {category: sum(category in profile.categories for profile in catalog.profiles)
                      for category in catalog.metadata().categories}
    rare_categories = sorted((category for category, count in category_sizes.items()
                              if count < max(category_sizes.values(), default=0)),
                             key=lambda category: (category_sizes[category], category))
    rare: SearchParams | None = None
    for category in rare_categories:
        rare = first_match([seed for seed in seeds if seed.category == category])
        if rare is not None:
            break
    if rare is None:
        omitted.append(OmittedPreset(id='rare_category', reason='Нет категории реже самой частой с проверенным совпадением.'))
    else:
        add('rare_category', 'Редкая категория',
            f'Категория «{rare.category}»: профилей в каталоге — {category_sizes[rare.category]}.', rare)

    return DemoPresetsResponse(data_version=catalog.version, presets=presets, omitted=omitted)
