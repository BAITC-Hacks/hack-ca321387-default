"""Load and validate one immutable CSV snapshot at startup; never fall back to mocks."""
import csv
import hashlib
import io
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .schemas import MAX_DATE, MIN_DATE, Metadata, SearchParams, normalize

NOT_PRESENT = {'флорист', 'декоратор', 'подарки и сувениры'}
DEFAULT_DATASET = Path(__file__).resolve().parents[2] / 'docs' / 'hackathon dataset anonymized .csv'


class Profile(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    categories: tuple[str, ...] = Field(min_length=1)
    city: str = Field(min_length=1)
    price: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    formats: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    max_hours: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    duration_policy: Literal['limited', 'not_applicable', 'unknown'] = 'unknown'
    busy_dates: frozenset[date] | None = None
    description: str = ''
    synthetic: bool = False
    city_imputed: bool = False
    price_imputed: bool = False

    @model_validator(mode='after')
    def valid_duration(self) -> 'Profile':
        if (self.duration_policy == 'limited') != (self.max_hours is not None):
            raise ValueError('max_hours and duration_policy disagree')
        return self


class CatalogError(RuntimeError):
    pass


class UnknownOption(ValueError):
    def __init__(self, field: str):
        self.field = field
        super().__init__(f'Неизвестное значение справочника: {field}')


@dataclass(frozen=True)
class Catalog:
    profiles: tuple[Profile, ...]
    version: str

    def metadata(self) -> Metadata:
        return Metadata(
            cities=sorted({p.city for p in self.profiles}),
            categories=sorted({c for p in self.profiles for c in p.categories}),
            event_types=sorted({f for p in self.profiles for f in p.formats}),
            languages=sorted({l for p in self.profiles for l in p.languages}),
        )

    def canonical_query(self, query: SearchParams) -> SearchParams:
        metadata = self.metadata()
        values = query.model_dump()
        for field, options in [('city', metadata.cities), ('category', metadata.categories),
                               ('event_type', metadata.event_types), ('language', metadata.languages)]:
            if values[field] is None:
                continue
            canonical = {normalize(option): option for option in options}.get(normalize(values[field]))
            if canonical is None:
                raise UnknownOption(field)
            values[field] = canonical
        return SearchParams.model_validate(values)


def load_catalog(path: Path) -> Catalog:
    try:
        content = path.read_bytes()
        rows = csv.DictReader(io.StringIO(content.decode('utf-8-sig')))
        required = {'id', 'anon_name', 'categories', 'city', 'price_from_kzt', 'event_formats',
                    'languages', 'max_hours', 'busy_dates', 'description', 'synthetic',
                    'city_imputed', 'price_imputed'}
        if not required.issubset(rows.fieldnames or []):
            raise ValueError('Missing CSV columns')
        profiles: list[Profile] = []
        for row in rows:
            def split(field: str) -> tuple[str, ...]:
                return tuple(dict.fromkeys(' '.join(v.split()) for v in row[field].split('|') if v.strip()))

            def flag(field: str) -> bool:
                if row[field] not in ('True', 'False'):
                    raise ValueError(f'Invalid flag: {field}')
                return row[field] == 'True'

            categories = split('categories')
            hours = float(row['max_hours']) if row['max_hours'].strip() else None
            dates = frozenset(date.fromisoformat(d) for d in split('busy_dates')) if row['busy_dates'].strip() else None
            if dates is not None and any(d < MIN_DATE or d > MAX_DATE for d in dates):
                raise ValueError('Busy date outside documented calendar')
            profiles.append(Profile(
                id=row['id'].strip(), name=row['anon_name'].strip(), categories=categories,
                city=row['city'].strip(), price=float(row['price_from_kzt']) if row['price_from_kzt'].strip() else None,
                formats=split('event_formats'), languages=split('languages'), max_hours=hours,
                duration_policy='limited' if hours is not None else 'not_applicable'
                if {normalize(c) for c in categories}.issubset(NOT_PRESENT) else 'unknown',
                busy_dates=dates, description=row['description'].strip(), synthetic=flag('synthetic'),
                city_imputed=flag('city_imputed'), price_imputed=flag('price_imputed'),
            ))
        if not profiles or len({p.id for p in profiles}) != len(profiles):
            raise ValueError('Empty catalog or duplicate IDs')
        return Catalog(tuple(sorted(profiles, key=lambda p: p.id)), hashlib.sha256(content).hexdigest()[:16])
    except (OSError, ValueError, KeyError, TypeError, csv.Error) as exc:
        raise CatalogError('Не удалось загрузить каталог подрядчиков') from exc
