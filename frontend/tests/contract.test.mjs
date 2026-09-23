import { test, after } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import ts from 'typescript'
import { createServer } from 'vite'

const bundle = JSON.parse(readFileSync(new URL('../src/mocks/fixtures.json', import.meta.url), 'utf8'))
const vite = await createServer({ server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' })
after(() => vite.close())
const { normalizeResponse, matchContractors } = await vite.ssrLoadModule('/src/shared/api/match.api.ts')
const { apiClient, normalizeApiBase, ApiError, mockMode } = await vite.ssrLoadModule('/src/shared/api/client.ts')

test('all recorded backend responses satisfy generated TypeScript contract', () => {
  const file = path.resolve('tests/fixture-contract.ts')
  const source = `import type { Metadata, MatchResponse, SearchParams } from '../src/shared/types/match';\nconst fixture: { metadata: Metadata; fixtures: { request: SearchParams; response: MatchResponse }[] } = ${JSON.stringify(bundle)};`
  const options = { strict: true, noEmit: true, skipLibCheck: true, target: ts.ScriptTarget.ES2022,
    module: ts.ModuleKind.ESNext, moduleResolution: ts.ModuleResolutionKind.Bundler }
  const host = ts.createCompilerHost(options)
  const isFixture = name => path.resolve(name).toLowerCase() === file.toLowerCase()
  const originalFileExists = host.fileExists
  host.fileExists = name => isFixture(name) || originalFileExists(name)
  const original = host.getSourceFile
  host.getSourceFile = (name, version, onError, create) => isFixture(name)
    ? ts.createSourceFile(file, source, version, true) : original(name, version, onError, create)
  const program = ts.createProgram([file], options, host)
  const diagnostics = ts.getPreEmitDiagnostics(program)
  assert.equal(diagnostics.length, 0, diagnostics.map(d => ts.flattenDiagnosticMessageText(d.messageText, '\n')).join('\n'))
})

test('adapter preserves backend order and null semantic values', () => {
  assert.equal(mockMode, false)
  for (const fixture of bundle.fixtures) {
    assert.deepEqual(normalizeResponse(fixture.response), fixture.response)
  }
  const valid = bundle.fixtures.find(f => f.response.status === 'matched').response
  assert.throws(() => normalizeResponse({ ...valid, status: 'surprise' }), ApiError)
  assert.throws(() => normalizeResponse({ ...valid, results: [...valid.results, ...valid.results] }), ApiError)
  assert.throws(() => normalizeResponse({ ...valid, results: [{ ...valid.results[0], score: 2 }] }), ApiError)
})

test('API origin normalization avoids /api/api and submit preserves calendar day', async () => {
  assert.equal(normalizeApiBase('/api/'), '/api')
  assert.equal(normalizeApiBase('http://localhost:8000'), 'http://localhost:8000/api')
  assert.equal(normalizeApiBase('http://localhost:8000/api/'), 'http://localhost:8000/api')
  const previous = globalThis.fetch
  const fixture = bundle.fixtures[0]
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/match')
    const request = JSON.parse(options.body)
    assert.equal(request.date, fixture.request.date)
    assert.equal(request.language, null)
    assert.equal(request.duration, null)
    return Response.json(fixture.response)
  }
  try { await matchContractors({ ...fixture.request, language: undefined, duration: undefined }) }
  finally { globalThis.fetch = previous }
})

test('HTTP, validation, malformed JSON and network errors stay errors; retry works', async () => {
  const previous = globalThis.fetch
  try {
    globalThis.fetch = async () => Response.json({ code: 'validation_error', message: 'Проверьте бюджет',
      detail: [{ field: 'budget', code: 'greater_than', message: 'Бюджет должен быть положительным' }] }, { status: 422 })
    await assert.rejects(apiClient('/match'), error => error instanceof ApiError && error.status === 422 && error.fields[0].field === 'budget')
    globalThis.fetch = async () => { throw new TypeError('Failed to fetch') }
    await assert.rejects(apiClient('/match'), error => error instanceof ApiError && error.status === 0)
    globalThis.fetch = async () => new Response('oops', { status: 200 })
    await assert.rejects(apiClient('/match'), error => error.code === 'invalid_response')
    globalThis.fetch = async () => Response.json(bundle.fixtures[0].response)
    assert.equal((await apiClient('/match')).status, bundle.fixtures[0].response.status)
  } finally { globalThis.fetch = previous }
})

test('components render real result, evidence, no-match, retry and alternative dates', async () => {
  globalThis.window = { localStorage: { getItem: () => null }, matchMedia: () => ({ matches: false }) }
  const { ResultsSection } = await vite.ssrLoadModule('/src/features/matching/ResultsSection.tsx')
  const { AppProviders } = await vite.ssrLoadModule('/src/app/providers.tsx')
  const props = { pending: false, error: null, onRetry() {}, onFocusField() {}, onDateSelect() {} }
  const render = (extra) => renderToStaticMarkup(createElement(AppProviders, null, createElement(ResultsSection, { ...props, ...extra })))
  const matched = bundle.fixtures.find(f => f.response.status === 'matched' && f.response.results.length === 3)
  const html = render({ response: matched.response, query: matched.request })
  for (const card of matched.response.results) {
    assert.ok(html.includes(card.name))
    assert.ok(html.includes(card.evidence.date.reason))
  }
  assert.ok(html.includes('Не рассчитано'))
  assert.ok(html.includes('Все доказательства'))
  assert.ok(html.includes('Доступность по датам'))
  const empty = bundle.fixtures.find(f => f.response.status === 'no_match')
  const noMatch = render({ response: empty.response, query: empty.request })
  assert.ok(noMatch.includes('Что ограничило поиск'))
  assert.ok(noMatch.includes('исключено'))
  const absent = bundle.fixtures.find(f => f.response.status === 'category_not_found')
  assert.ok(render({ response: absent.response }).includes('Изменить город'))
  assert.ok(render({ error: 'Сервис временно недоступен' }).includes('Повторить запрос'))
})

test('production build refuses accidentally enabled mock mode', () => {
  const result = spawnSync(process.execPath, ['node_modules/vite/bin/vite.js', 'build'], {
    encoding: 'utf8', env: { ...process.env, VITE_USE_MOCK_API: 'true' },
  })
  assert.notEqual(result.status, 0)
  assert.ok(result.stderr.includes('development-only'), result.stderr)
})

test('dev fixtures are exact backend recordings and unknown scenarios stay explicit errors', async () => {
  const { mockMatch, mockMetadata } = await vite.ssrLoadModule('/src/mocks/engine.ts')
  assert.deepEqual(mockMetadata, bundle.metadata)
  for (const fixture of bundle.fixtures) assert.deepEqual(mockMatch(fixture.request), fixture.response)
  assert.throws(() => mockMatch({ ...bundle.fixtures[0].request, budget: 123 }), error => error.code === 'fixture_not_found')
})

test('server field errors render next to the corresponding form field; metadata errors do not fall back', async () => {
  globalThis.window = { localStorage: { getItem: () => null }, matchMedia: () => ({ matches: false }) }
  const { SearchForm } = await vite.ssrLoadModule('/src/features/search/SearchForm.tsx')
  const { AppProviders } = await vite.ssrLoadModule('/src/app/providers.tsx')
  const html = renderToStaticMarkup(createElement(AppProviders, null, createElement(SearchForm, {
    value: bundle.fixtures[0].request, metadata: bundle.metadata, pending: false, onChange() {}, onSubmit() {},
    serverErrors: [{ field: 'budget', code: 'validation_error', message: 'Проверьте бюджет на сервере' }],
  })))
  assert.ok(html.includes('id="error-budget"'))
  assert.ok(html.includes('Проверьте бюджет на сервере'))
  const { getMetadata } = await vite.ssrLoadModule('/src/shared/api/metadata.api.ts')
  const previous = globalThis.fetch
  globalThis.fetch = async () => Response.json({ message: 'Маршрут не найден', code: 'route_not_found' }, { status: 404 })
  try { assert.equal((await getMetadata()).min_date, bundle.metadata.min_date) }
  finally { globalThis.fetch = previous }
})
