import unittest
from datetime import date, datetime

from pydantic import ValidationError

from backend.app.catalog import Catalog, DEFAULT_DATASET, Profile, UnknownOption, load_catalog
from backend.app.discovery import AvailabilityRequest, find_availability
from backend.app.matching import MatchingService
from backend.app.rules import filter_profiles
from backend.app.schemas import MAX_DATE, MIN_DATE, SearchParams


def query(**changes: object) -> SearchParams:
    return SearchParams.model_validate(dict(city='Алматы', date='2026-11-18', event_type='корпоратив',
                                           category='Ведущий', budget=1_000_000,
                                           language='русский', duration=6) | changes)


def profile(identifier: str, **changes: object) -> Profile:
    return Profile.model_validate(dict(id=identifier, name=identifier, city='Алматы',
                                       categories=['Ведущий'], price=500000, formats=['корпоратив'],
                                       languages=['русский'], max_hours=8, duration_policy='limited',
                                       busy_dates=[]) | changes)


class AvailabilityTests(unittest.TestCase):
    def test_counts_keep_every_other_condition_and_match_real_search(self) -> None:
        snapshot = Catalog(tuple(profile(str(i)) for i in range(5)) + (
            profile('busy', busy_dates=['2026-11-18']), profile('category', categories=['Фотограф']),
            profile('city', city='Астана'), profile('format', formats=['свадьба']),
            profile('budget', price=1_000_001), profile('language', languages=['казахский']),
            profile('short', max_hours=2), profile('unknown_calendar', busy_dates=None),
            profile('unknown_price', price=None),
            profile('unknown_hours', max_hours=None, duration_policy='unknown'),
        ), 'all-conditions')
        request = AvailabilityRequest(query=query(), days_before=1, days_after=1)
        result = find_availability(snapshot, request)
        self.assertEqual([day.available for day in result.days], [6, 5, 6])
        self.assertEqual(result.recommended_date, date(2026, 11, 17))
        self.assertEqual(result.data_version, snapshot.version)
        for day in result.days:
            actual = MatchingService(snapshot).match(query(date=day.date))
            self.assertEqual(day.available, actual.total_eligible)
            self.assertEqual(len(actual.results), 3)
        self.assertEqual(result.query, request.query)

    def test_recommendation_maximum_then_distance_then_earlier(self) -> None:
        snapshot = Catalog((profile('1', busy_dates=['2026-11-17', '2026-11-19']),
                            profile('2', busy_dates=['2026-11-19'])), 'rank-days')
        result = find_availability(snapshot, AvailabilityRequest(query=query()))
        # The selected date also has two matches but cannot be an alternative.
        self.assertEqual(result.recommended_date, date(2026, 11, 16))
        closer = find_availability(snapshot, AvailabilityRequest(query=query(), days_before=0, days_after=2))
        self.assertEqual(closer.recommended_date, date(2026, 11, 20))

    def test_empty_and_unknown_calendars_never_create_availability(self) -> None:
        snapshot = Catalog((profile('unknown', busy_dates=None),), 'unknown')
        result = find_availability(snapshot, AvailabilityRequest(query=query()))
        self.assertEqual([day.available for day in result.days], [0] * 5)
        self.assertIsNone(result.recommended_date)
        selected_only = find_availability(Catalog((profile('known'),), 'known'),
                                          AvailabilityRequest(query=query(), days_before=0, days_after=0))
        self.assertEqual(selected_only.days[0].available, 1)
        self.assertIsNone(selected_only.recommended_date)

    def test_bounds_ranges_clipping_and_invalid_inputs(self) -> None:
        snapshot = Catalog((profile('1'),), 'bounds')
        for day, first, last in ((MIN_DATE, MIN_DATE, date(2026, 9, 25)),
                                 (MAX_DATE, date(2026, 12, 29), MAX_DATE)):
            result = find_availability(snapshot, AvailabilityRequest(query=query(date=day)))
            self.assertEqual((result.date_from, result.date_to), (first, last))
        maximum = AvailabilityRequest(query=query(), date_from='2026-11-01', date_to='2026-12-01')
        self.assertEqual(len(find_availability(snapshot, maximum).days), 31)
        for request in (maximum, AvailabilityRequest(query=query())):
            self.assertEqual(AvailabilityRequest.model_validate(request.model_dump()), request)
        for change in (
            {'date_from': '2026-11-20', 'date_to': '2026-11-19'},
            {'date_from': '2026-11-01', 'date_to': '2026-12-02'},
            {'date_from': '2026-09-22', 'date_to': '2026-09-24'},
            {'date_from': '2026-12-31', 'date_to': '2027-01-01'},
            {'date_from': '2026-11-18'},
            {'date_from': '2026-11-18', 'date_to': '2026-11-19', 'days_after': 2},
            {'date_from': '2026-11-18T00:00:00Z', 'date_to': '2026-11-19'},
            {'date_from': datetime(2026, 11, 18), 'date_to': '2026-11-19'},
            {'date_from': '2026-11-31', 'date_to': '2026-12-01'},
            {'days_before': 15, 'days_after': 16}, {'days_before': -1},
            {'days_after': True}, {'days_after': 2.5}, {'days_after': '2'},
        ):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                AvailabilityRequest.model_validate({'query': query(), **change})

    def test_normalization_unknown_vocabulary_and_optional_conditions(self) -> None:
        snapshot = Catalog((profile('1', languages=[], max_hours=None, duration_policy='unknown'),), 'optional')
        result = find_availability(snapshot, AvailabilityRequest(query=query(
            city='  аЛмАтЫ ', language='Не важно', duration=None)))
        self.assertEqual(result.query.city, 'Алматы')
        self.assertTrue(all(day.available == 1 for day in result.days))
        with self.assertRaises(UnknownOption):
            find_availability(snapshot, AvailabilityRequest(query=query(category='Неизвестно')))
