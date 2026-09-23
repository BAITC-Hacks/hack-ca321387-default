"""Contract, explanation and trace tests through the real matching pipeline."""
import math
import os
import unittest
from uuid import UUID
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.catalog import Catalog, Profile
from backend.app.feature_schemas import DebugMatchResponse, DetailedMatchResponse
from backend.app.main import create_app
from backend.app.matching import MatchingService
from backend.app.rules import STAGES
from backend.app.schemas import ErrorResponse, SearchParams
from backend.app.semantic import SemanticUnavailable, TextScore

BASE: dict[str, object] = {
    'city': 'Алматы', 'date': '2026-11-18', 'event_type': 'корпоратив',
    'category': 'Ведущий', 'budget': 1_000_000, 'language': 'русский', 'duration': 6,
}


def request(**changes: object) -> SearchParams:
    return SearchParams.model_validate(BASE | changes)


def profile(identifier: str, **changes: object) -> Profile:
    return Profile.model_validate({
        'id': identifier, 'name': f'Подрядчик {identifier}', 'city': 'Алматы',
        'categories': ['Ведущий'], 'price': 500_000, 'formats': ['корпоратив'],
        'languages': ['русский'], 'max_hours': 8, 'duration_policy': 'limited',
        'busy_dates': [], 'description': 'Ведущий корпоратив с импровизацией',
    } | changes)


def catalog(*records: Profile) -> Catalog:
    return Catalog(tuple(records), 'features-test-snapshot')


class CountingSemantic:
    """Replace only the remote score source, never filtering or matching."""

    def __init__(self, scores: dict[str, tuple[float | None, float | None]] | None = None,
                 failure: SemanticUnavailable | None = None) -> None:
        self.scores = scores or {}
        self.failure = failure
        self.calls = 0

    def score(self, query: SearchParams, snapshot: Catalog) -> dict[str, TextScore]:
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        return {
            record.id: TextScore(id=record.id, semantic=self.scores.get(record.id, (.4, .2))[0],
                                 lexical=self.scores.get(record.id, (.4, .2))[1])
            for record in snapshot.profiles
        }


class MatchFeatureTests(unittest.TestCase):
    def setUp(self) -> None:
        environment = patch.dict(os.environ, {'SEMANTIC_MODE': 'disabled', 'ENABLE_MATCH_TRACE': 'false'})
        environment.start()
        self.addCleanup(environment.stop)

    def test_details_and_trace_preserve_normal_response_for_zero_to_top_three(self) -> None:
        for size in (0, 1, 2, 3, 5):
            with self.subTest(size=size):
                # Keep a known category/city when every candidate fails availability.
                records = tuple(profile(str(index)) for index in range(size)) or (
                    profile('busy', busy_dates=['2026-11-18']),)
                service = MatchingService(catalog(*records))
                ordinary = service.match(request())
                detailed = service.details(request())
                traced = service.debug_match(request())
                self.assertEqual(detailed.match, ordinary)
                self.assertEqual(traced.details, detailed)
                self.assertEqual(len(detailed.match.results), min(size, 3))
                self.assertEqual(len(detailed.ranking), min(size, 3))
                self.assertEqual(detailed.match.total_eligible, size)
                self.assertEqual(detailed.comparison.candidate_ids,
                                 [item.id for item in ordinary.results])
                self.assertEqual([item.position for item in detailed.ranking],
                                 list(range(1, min(size, 3) + 1)))
                self.assertEqual(detailed.funnel[-1].after, size)
                self.assertEqual(ordinary.status, 'matched' if size else 'no_match')

    def test_details_preserve_category_not_found_and_empty_comparison(self) -> None:
        service = MatchingService(catalog(profile('host', city='Астана'),
                                          profile('photo', categories=['Фотограф'])))
        result = service.details(request())
        self.assertEqual(result.match, service.match(request()))
        self.assertEqual(result.match.status, 'category_not_found')
        self.assertEqual(result.ranking, [])
        self.assertEqual(result.comparison.candidate_ids, [])
        self.assertEqual(result.comparison.decisions, [])
        self.assertEqual(result.comparison.formats, {})

    def test_each_enhanced_request_executes_pipeline_and_model_only_once(self) -> None:
        for method in ('details', 'debug_match'):
            with self.subTest(method=method):
                provider = CountingSemantic()
                service = MatchingService(catalog(profile('free')), provider)
                with patch.object(service, '_execute', wraps=service._execute) as execution:
                    getattr(service, method)(request())
                self.assertEqual(execution.call_count, 1)
                self.assertEqual(provider.calls, 1)
        provider = CountingSemantic()
        service = MatchingService(catalog(profile('busy', busy_dates=['2026-11-18'])), provider)
        service.debug_match(request())
        self.assertEqual(provider.calls, 0)

    def test_hard_filters_and_funnel_use_same_facts_even_with_maximum_text_scores(self) -> None:
        records = (
            profile('category', categories=['Фотограф']), profile('city', city='Астана'),
            profile('busy', busy_dates=['2026-11-18']), profile('format', formats=['свадьба']),
            profile('budget', price=2_000_000), profile('language', languages=['казахский']),
            profile('duration', max_hours=4), profile('eligible'),
        )
        provider = CountingSemantic({item.id: (1.0, 1.0) for item in records})
        result = MatchingService(catalog(*records), provider).details(request())
        self.assertEqual(result.comparison.candidate_ids, ['eligible'])
        self.assertEqual([item.stage for item in result.funnel], [stage for stage, _ in STAGES])
        self.assertEqual([item.after for item in result.funnel], [7, 6, 5, 4, 3, 2, 1])
        for index, step in enumerate(result.funnel):
            self.assertEqual(step.before, 8 - index)
            self.assertEqual(step.excluded, step.before - step.after)
            self.assertEqual(step.count, step.after)
            self.assertEqual(step.application, 'applied')
            if index:
                self.assertEqual(step.before, result.funnel[index - 1].after)
        for stage, _ in STAGES:
            self.assertTrue(getattr(result.match.results[0].evidence, stage).matched)

    def test_absent_optional_conditions_are_explicit_and_never_invent_contributions(self) -> None:
        result = MatchingService(catalog(profile('one'))).details(request(language=None, duration=None))
        for step in result.funnel:
            self.assertEqual(step.application, 'not_requested' if step.stage in ('language', 'duration') else 'applied')
            if step.application == 'not_requested':
                self.assertEqual(step.before, step.after)
                self.assertEqual(step.excluded, 0)
        components = {item.component: item for item in result.ranking[0].components}
        self.assertEqual(components['duration'].state, 'not_requested')
        for key in ('duration', 'semantic', 'lexical'):
            self.assertIsNone(components[key].value)
            self.assertIsNone(components[key].weight)
            self.assertIsNone(components[key].contribution)
        self.assertEqual(components['semantic'].state, 'unavailable')
        self.assertEqual(components['budget'].weight, 1)
        self.assertIsNone(result.match.results[0].evidence.language.matched)
        self.assertIsNone(result.match.results[0].evidence.duration.matched)

    def test_not_applicable_duration_and_missing_text_scores_have_explicit_states(self) -> None:
        record = profile('no-presence', max_hours=None, duration_policy='not_applicable', synthetic=True)
        provider = CountingSemantic({record.id: (None, None)})
        result = MatchingService(catalog(record), provider).debug_match(request())
        card = result.details.match.results[0]
        components = {item.component: item for item in result.details.ranking[0].components}
        self.assertEqual(components['duration'].state, 'not_applicable')
        for key in ('semantic', 'lexical'):
            self.assertEqual(components[key].state, 'unavailable')
            self.assertIsNone(components[key].contribution)
            self.assertTrue(components[key].reason)
        self.assertIsNone(card.max_hours)
        self.assertIsNone(card.semantic_score)
        self.assertTrue(card.synthetic)
        self.assertIsNone(card.evidence.duration.matched)
        self.assertEqual([notice.code for notice in result.trace.notices], ['text_score_missing'])
        self.assertEqual(result.trace.notices[0].candidate_id, record.id)

    def test_score_contributions_preserve_raw_inputs_at_rounding_boundaries(self) -> None:
        # The rounded public component can produce a different final rounding.
        # Details must retain actual inputs without altering the legacy score.
        for semantic, expected in ((.50000082, .3), (.50000085, .300001)):
            with self.subTest(semantic=semantic):
                provider = CountingSemantic({'one': (semantic, 0)})
                service = MatchingService(catalog(profile('one', price=1_000_000)), provider)
                result = service.details(request(duration=None))
                detail = result.ranking[0]
                card = result.match.results[0]
                components = {item.component: item for item in detail.components}
                self.assertEqual(detail.score, expected)
                self.assertEqual(components['semantic'].value, semantic)
                self.assertEqual(components['budget'].source_fields, ['price_from_kzt', 'budget'])
                self.assertEqual(detail.decomposition, 'weighted_sum')
                self.assertEqual(detail.interpretation, 'fit_not_probability')
                self.assertEqual((detail.scale_min, detail.scale_max), (0, 1))
                total = sum(item.contribution for item in detail.components if item.contribution is not None)
                self.assertEqual(total, detail.unrounded_score)
                self.assertEqual(total + detail.rounding_adjustment, card.score)
                self.assertEqual(round(total, 6), card.score)
                self.assertLessEqual(abs(detail.rounding_adjustment), .0000005)
                if semantic == .50000082:
                    self.assertIsNotNone(card.score_breakdown.semantic)
                    self.assertIsNotNone(card.score_weights.semantic)
                    naive = (card.score_breakdown.semantic or 0) * (card.score_weights.semantic or 0)
                    self.assertNotEqual(round(naive, 6), card.score)

    def test_partial_text_components_renormalize_without_rejecting_float_roundoff(self) -> None:
        for semantic, lexical in ((None, 1.0), (1.0, None), (None, None)):
            with self.subTest(semantic=semantic, lexical=lexical):
                provider = CountingSemantic({'one': (semantic, lexical)})
                record = profile('one', price=1e-12, max_hours=12)
                result = MatchingService(catalog(record), provider).debug_match(request())
                detail = result.details.ranking[0]
                self.assertEqual(detail.score, 1)
                total = sum(item.contribution for item in detail.components if item.contribution is not None)
                self.assertEqual(total, detail.unrounded_score)
                self.assertEqual(total + detail.rounding_adjustment, detail.score)
                self.assertAlmostEqual(sum(item.weight for item in detail.components if item.weight is not None), 1)
                for item in detail.components:
                    absent = (item.component == 'semantic' and semantic is None
                              or item.component == 'lexical' and lexical is None)
                    self.assertEqual(item.state, 'unavailable' if absent else 'active')
                    if absent:
                        self.assertIsNone(item.contribution)
                self.assertEqual([notice.code for notice in result.trace.notices], ['text_score_missing'])

    def test_comparison_explains_score_price_then_identifier_without_inventing_factors(self) -> None:
        # Without duration, these signals compensate differing budget components.
        records = (profile('B', price=400_000), profile('A', price=400_000),
                   profile('C', price=500_000))
        provider = CountingSemantic({'A': (.4, 0), 'B': (.4, 0), 'C': (.4333333333333333, 0)})
        result = MatchingService(catalog(*records), provider).details(request(duration=None))
        self.assertEqual([card.score for card in result.match.results], [.36, .36, .36])
        self.assertEqual(result.comparison.candidate_ids, ['A', 'B', 'C'])
        decisions = {(item.higher_id, item.lower_id): item for item in result.comparison.decisions}
        self.assertEqual(decisions[('A', 'B')].decided_by, 'id')
        self.assertEqual(decisions[('A', 'C')].decided_by, 'price')
        self.assertEqual(decisions[('B', 'C')].decided_by, 'price')
        self.assertTrue(all(item.score_gap == 0 for item in decisions.values()))
        self.assertIsNone(decisions[('A', 'C')].contribution_deltas['duration'])
        self.assertEqual(result.comparison.ordering, ['score_desc', 'price_asc', 'id_asc'])
        self.assertEqual(result.comparison.currency, 'KZT')
        self.assertEqual(result.comparison.price_unit, 'event')
        self.assertEqual(result.comparison.price_basis, 'starting_price')
        self.assertEqual(result.comparison.duration_unit, 'hours')
        self.assertEqual(result.comparison.formats, {item.id: ['корпоратив'] for item in records})
        ranked = MatchingService(catalog(profile('cheap', price=300_000),
                                         profile('costly', price=700_000))).details(request())
        self.assertEqual(ranked.comparison.decisions[0].decided_by, 'score')
        self.assertGreater(ranked.comparison.decisions[0].score_gap, 0)

    def test_trace_timings_funnel_and_identifiers_describe_same_execution(self) -> None:
        service = MatchingService(catalog(profile('busy', busy_dates=['2026-11-18']), profile('free')),
                                  CountingSemantic())
        result = service.debug_match(request(city='  аЛМАТЫ  ', language=' РУССКИЙ '))
        trace = result.trace
        self.assertEqual(str(UUID(trace.request_id)), trace.request_id)
        self.assertEqual(UUID(trace.request_id).version, 4)
        self.assertEqual(trace.normalized_query, request())
        self.assertEqual(trace.model_info, result.details.match.model_info)
        self.assertEqual((trace.catalog_count, trace.total_eligible, trace.returned_count), (2, 1, 1))
        stages = {item.stage: item for item in trace.stages}
        self.assertEqual(len(stages), len(trace.stages))
        for step in result.details.funnel:
            timing = stages[f'filter.{step.stage}']
            self.assertEqual((timing.before, timing.after), (step.before, step.after))
        self.assertIn('ranking.semantic', stages)
        self.assertIn('details.assemble', stages)
        self.assertIn('query.normalize', stages)
        self.assertTrue(math.isfinite(trace.total_ms))
        self.assertGreater(trace.total_ms, 0)
        self.assertTrue(all(math.isfinite(item.elapsed_ms) and 0 <= item.elapsed_ms <= trace.total_ms
                            for item in trace.stages))
        self.assertGreaterEqual(trace.total_ms, sum(item.elapsed_ms for item in trace.stages))
        self.assertNotEqual(service.debug_match(request()).trace.request_id, trace.request_id)

    def test_trace_degradation_is_sanitized_and_preserves_real_fallback(self) -> None:
        secret = 'provider-secret-token-and-internal-stack'
        provider = CountingSemantic(failure=SemanticUnavailable(secret, 'semantic_timeout'))
        service = MatchingService(catalog(profile('good'), profile('busy', busy_dates=['2026-11-18'])), provider)
        ordinary = service.match(request())
        result = service.debug_match(request())
        self.assertEqual(result.details.match, ordinary)
        self.assertEqual(result.trace.model_info.semantic_model, 'unavailable')
        self.assertTrue(result.trace.model_info.fallback_used)
        self.assertEqual(result.trace.notices[0].code, 'semantic_timeout')
        self.assertNotIn(secret, result.model_dump_json())
        self.assertEqual(result.details.comparison.candidate_ids, ['good'])
        for item in result.details.ranking[0].components:
            if item.component in ('semantic', 'lexical'):
                self.assertEqual(item.state, 'unavailable')
                self.assertIsNone(item.value)
                self.assertIsNone(item.contribution)

    def test_details_http_contract_and_validation_keep_ordinary_search_compatible(self) -> None:
        with TestClient(create_app(catalog(profile('one'), profile('two')))) as client:
            ordinary = client.post('/api/match', json=BASE)
            detailed = client.post('/api/match/details', json=BASE)
            self.assertEqual(ordinary.status_code, 200)
            self.assertEqual(detailed.status_code, 200, detailed.text)
            DetailedMatchResponse.model_validate(detailed.json())
            self.assertEqual(detailed.json()['match'], ordinary.json())
            self.assertNotIn('ranking', ordinary.json())
            for changes in ({'category': 'unknown'}, {'duration': 13}, {'date': '2026-11-18T00:00:00Z'}):
                invalid = client.post('/api/match/details', json=BASE | changes)
                self.assertEqual(invalid.status_code, 422)
                ErrorResponse.model_validate(invalid.json())

    def test_debug_http_is_absent_by_default_and_explicitly_enabled(self) -> None:
        with TestClient(create_app(catalog(profile('one')))) as client:
            disabled = client.post('/api/debug/match', json=BASE)
            self.assertEqual(disabled.status_code, 404)
            self.assertEqual(disabled.json()['code'], 'route_not_found')
            self.assertNotIn('/api/debug/match', client.get('/openapi.json').json()['paths'])
        with patch.dict(os.environ, {'ENABLE_MATCH_TRACE': 'true'}):
            with TestClient(create_app(catalog(profile('one')))) as client:
                ordinary = client.post('/api/match', json=BASE)
                traced = client.post('/api/debug/match', json=BASE)
                self.assertEqual(traced.status_code, 200, traced.text)
                DebugMatchResponse.model_validate(traced.json())
                self.assertEqual(traced.json()['details']['match'], ordinary.json())
                self.assertIn('/api/debug/match', client.get('/openapi.json').json()['paths'])
                invalid = client.post('/api/debug/match', json=BASE | {'budget': 0})
                self.assertEqual(invalid.status_code, 422)
                ErrorResponse.model_validate(invalid.json())


if __name__ == '__main__':
    unittest.main()
