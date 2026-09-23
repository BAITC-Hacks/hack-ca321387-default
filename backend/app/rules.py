"""One implementation of each constraint, shared by selection, evidence and diagnostics."""
from dataclasses import dataclass
from collections.abc import Callable
from time import perf_counter_ns

from .catalog import Profile
from .schemas import DiagnosticStep, EvidenceItem, SearchParams, Stage, normalize

STAGES: tuple[tuple[Stage, str], ...] = (
    ('category', 'В категории'), ('city', 'В выбранном городе'), ('date', 'Свободны на дату'),
    ('format', 'Подходят по формату'), ('budget', 'В пределах бюджета'),
    ('language', 'Работают на языке'), ('duration', 'Подходят по длительности'),
)


def money(value: float) -> str:
    return f'{value:,.2f}'.rstrip('0').rstrip('.').replace(',', ' ') + ' ₸'


@dataclass(frozen=True)
class CheckedProfile:
    profile: Profile
    checks: dict[Stage, EvidenceItem]


def evaluate(profile: Profile, query: SearchParams) -> CheckedProfile:
    checks: dict[Stage, EvidenceItem] = {}

    def check(stage: Stage, matched: bool | None, reason: str, field: str, code: str,
              requested: str | float | None, actual: str | float | list[str] | None) -> None:
        checks[stage] = EvidenceItem(matched=matched, reason=reason, source_field=field,
                                    code=code, requested=requested, actual=actual)

    def contains(value: str, options: tuple[str, ...]) -> bool:
        return normalize(value) in {normalize(item) for item in options}

    category = contains(query.category, profile.categories)
    check('category', category, f'Категория «{query.category}» ' + ('указана в профиле' if category else 'не указана'),
          'categories', 'category_match' if category else 'category_mismatch', query.category, list(profile.categories))
    city = normalize(profile.city) == normalize(query.city)
    check('city', city, f'Город профиля: {profile.city}' + (' (восстановлен в датасете)' if profile.city_imputed else ''),
          'city', 'city_match' if city else 'city_mismatch', query.city, profile.city)
    available = profile.busy_dates is not None and query.date not in profile.busy_dates
    check('date', available,
          f'{query.date.isoformat()}: ' + ('свободен по календарю датасета' if available else
          'календарь неизвестен' if profile.busy_dates is None else 'занят по календарю датасета'),
          'busy_dates', 'date_available' if available else 'calendar_unknown' if profile.busy_dates is None else 'date_busy',
          query.date.isoformat(), None if profile.busy_dates is None else ('available' if available else 'busy'))
    event_format = contains(query.event_type, profile.formats)
    check('format', event_format, f'Формат «{query.event_type}» ' + ('поддерживается' if event_format else 'не подтверждён'),
          'event_formats', 'format_match' if event_format else 'format_unconfirmed', query.event_type, list(profile.formats))
    affordable = profile.price is not None and profile.price <= query.budget
    check('budget', affordable,
          'Цена неизвестна' if profile.price is None else
          f'Цена от {money(profile.price)} за мероприятие; бюджет {money(query.budget)}'
          + (' (цена восстановлена в датасете)' if profile.price_imputed else ''),
          'price_from_kzt', 'budget_match' if affordable else 'price_unknown' if profile.price is None else 'over_budget',
          query.budget, profile.price)
    language = None if query.language is None else contains(query.language, profile.languages)
    check('language', language, 'Язык не ограничен запросом' if query.language is None else
          f'Язык «{query.language}» ' + ('поддерживается' if language else 'не подтверждён'),
          'languages', 'not_requested' if language is None else 'language_match' if language else 'language_unconfirmed',
          query.language, list(profile.languages))
    if query.duration is None:
        duration, reason, code = None, 'Длительность не указана в запросе', 'not_requested'
    elif profile.duration_policy == 'not_applicable':
        duration, reason, code = None, 'Услуга не привязана к присутствию; ограничение часов неприменимо', 'not_applicable'
    elif profile.max_hours is None:
        duration, reason, code = False, 'Максимальная длительность неизвестна', 'duration_unknown'
    else:
        duration = profile.max_hours >= query.duration
        reason = f'Максимум {profile.max_hours:g} ч; запрос {query.duration} ч'
        code = 'duration_match' if duration else 'duration_exceeded'
    check('duration', duration, reason, 'max_hours', code, query.duration, profile.max_hours)
    return CheckedProfile(profile, checks)


def filter_profiles(profiles: tuple[Profile, ...], query: SearchParams,
                    observer: Callable[[str, float, int, int], None] | None = None,
                    ) -> tuple[list[CheckedProfile], list[DiagnosticStep]]:
    started = perf_counter_ns() if observer else 0
    pool = [evaluate(profile, query) for profile in profiles]
    if observer:
        observer('constraints.evaluate', (perf_counter_ns() - started) / 1_000_000, len(profiles), len(pool))
    steps = []
    for stage, label in STAGES:
        started = perf_counter_ns() if observer else 0
        before = len(pool)
        pool = [item for item in pool if item.checks[stage].matched is not False]
        steps.append(DiagnosticStep(stage=stage, label=label, before=before, after=len(pool),
                                    excluded=before - len(pool), count=len(pool)))
        if observer:
            observer(f'filter.{stage}', (perf_counter_ns() - started) / 1_000_000, before, len(pool))
    return pool, steps
