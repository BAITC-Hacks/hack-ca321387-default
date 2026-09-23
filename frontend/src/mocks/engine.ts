import catalog from './catalog.json'
import type { AvailabilityDay, Contractor, DiagnosticStep, MatchResponse, SearchParams } from '../shared/types/match'
import { MAX_DATE, MIN_DATE } from '../features/search/search.constants'
import { formatDate, formatKZT } from '../shared/format'

interface Profile {
  id: string
  name: string
  categories: string[]
  city: string
  price: number
  formats: string[]
  languages: string[]
  max_hours: number | null
  busy_dates: string[]
  description: string
  synthetic: boolean
}

const profiles: Profile[] = catalog as Profile[]
const labels: Record<string, string> = {
  category: 'В категории', city: 'В выбранном городе', date: 'Свободны на дату',
  format: 'Подходят по формату', budget: 'В пределах бюджета',
  language: 'Работают на языке', duration: 'Подходят по длительности',
}

function eligible(input: SearchParams) {
  let pool = profiles.filter((profile) => profile.categories.includes(input.category))
  const steps: DiagnosticStep[] = [{ stage: 'category', label: labels.category, count: pool.length }]
  const apply = (stage: string, predicate: (profile: Profile) => boolean) => {
    pool = pool.filter(predicate)
    steps.push({ stage, label: labels[stage], count: pool.length })
  }
  apply('city', (profile) => profile.city === input.city)
  apply('date', (profile) => !profile.busy_dates.includes(input.date))
  apply('format', (profile) => profile.formats.includes(input.event_type))
  apply('budget', (profile) => profile.price <= input.budget)
  if (input.language) apply('language', (profile) => profile.languages.includes(input.language!))
  if (input.duration) apply('duration', (profile) => profile.max_hours === null || profile.max_hours >= input.duration!)
  return { pool, steps }
}

function availability(input: SearchParams): AvailabilityDay[] {
  const day = new Date(`${input.date}T12:00:00Z`)
  return [-2, -1, 0, 1, 2].map((offset) => {
    const candidate = new Date(day)
    candidate.setUTCDate(day.getUTCDate() + offset)
    const date = candidate.toISOString().slice(0, 10)
    return date >= MIN_DATE && date <= MAX_DATE
      ? { date, available: eligible({ ...input, date }).pool.length }
      : null
  }).filter((item): item is AvailabilityDay => item !== null)
}

function overlap(query: string, description: string): number {
  const tokens = (text: string) => new Set(text.toLocaleLowerCase('ru-RU').match(/[а-яёa-z]{4,}/g) || [])
  const terms = tokens(query)
  if (!terms.size) return 0
  const words = tokens(description)
  return [...terms].filter((term) => words.has(term)).length / terms.size
}

function descriptionHighlights(description: string): string[] {
  const patterns: [RegExp, string][] = [
    [/импровизац/iu, 'импровизация'],
    [/сценари/iu, 'авторский сценарий'],
    [/юмор/iu, 'юмор'],
    [/двуязыч/iu, 'двуязычное ведение'],
    [/телевидени|телеведущ/iu, 'опыт на телевидении'],
    [/акт[её]р/iu, 'актёрский опыт'],
    [/репортаж/iu, 'репортажная съёмка'],
    [/оформлени/iu, 'оформление мероприятий'],
    [/живые эмоции/iu, 'живые эмоции'],
    [/интерактив/iu, 'интерактив'],
  ]
  return patterns.filter(([pattern]) => pattern.test(description)).map(([, label]) => label).slice(0, 2)
}

function toContractor(profile: Profile, input: SearchParams): Contractor {
  const semantic = Math.min(1, overlap(`${input.category} ${input.event_type}`, profile.description))
  const budgetFit = Math.max(0, 1 - profile.price / input.budget)
  const durationFit = input.duration && profile.max_hours !== null
    ? Math.max(0, Math.min(1, (profile.max_hours - input.duration) / input.duration)) : 0
  const score = Number((0.5 * semantic + 0.2 * semantic + 0.2 * budgetFit + 0.1 * durationFit).toFixed(6))
  const budgetReason = `${formatKZT(profile.price)} входит в бюджет ${formatKZT(input.budget)}`
  const formatReason = `Работает с форматом «${input.event_type}»`
  const languageReason = input.language ? `Работает на языке: ${input.language}` : 'Язык не ограничен запросом'
  const durationReason = !input.duration
    ? 'Длительность не указана в запросе'
    : profile.max_hours === null
      ? 'Ограничение длительности для этой услуги не применяется'
      : `Работает до ${profile.max_hours} ч при запросе ${input.duration} ч`
  const highlights = descriptionHighlights(profile.description)
  const semanticReason = highlights.length
    ? `В описании отмечены ${highlights.join(' и ')}`
    : semantic > 0 ? 'Описание содержит слова из параметров запроса' : 'Дополнительного текстового совпадения не обнаружено'
  const evidence = {
    date: { matched: true, reason: `Свободен ${formatDate(input.date)}`, source_field: 'busy_dates' },
    city: { matched: true, reason: `Работает в городе ${profile.city}`, source_field: 'city' },
    category: { matched: true, reason: `Категория: ${input.category}`, source_field: 'categories' },
    budget: { matched: true, reason: budgetReason, source_field: 'price_from_kzt' },
    format: { matched: true, reason: formatReason, source_field: 'event_formats' },
    language: { matched: true, reason: languageReason, source_field: 'languages' },
    duration: { matched: true, reason: durationReason, source_field: 'max_hours' },
    semantic: { matched: semantic > 0, reason: semanticReason, score: semantic, source_field: 'description' },
  }
  const detail = highlights.length
    ? `В профиле указаны ${highlights.join(' и ')}`
    : profile.description.split(/[.!?]/).find((sentence) => sentence.trim().length > 30)?.trim()
  return {
    id: profile.id, name: profile.name, categories: profile.categories, city: profile.city,
    price: profile.price, score, semantic_score: semantic, synthetic: profile.synthetic,
    max_hours: profile.max_hours, languages: profile.languages, description: profile.description,
    evidence, score_breakdown: { semantic, lexical: semantic, budget: budgetFit, duration: durationFit },
    explanation: `${budgetReason}; ${formatReason.toLowerCase()}. ${detail ? `${detail}.` : ''}`.trim(),
  }
}

export function mockMatch(input: SearchParams): MatchResponse {
  const { pool, steps } = eligible(input)
  const cityCount = steps.find((step) => step.stage === 'city')?.count || 0
  const status = cityCount === 0 ? 'category_not_found' : pool.length === 0 ? 'no_match' : 'matched'
  const primary = steps.find((step, index) => index > 0 && step.count === 0)?.stage
  const last = steps[steps.length - 1]
  const results = pool.map((profile) => toContractor(profile, input))
    .sort((a, b) => b.score - a.score || a.price - b.price || a.id.localeCompare(b.id))
    .slice(0, 3)
  return {
    status, results,
    total_eligible: pool.length,
    diagnostics: {
      steps, counts: Object.fromEntries(steps.map((step) => [step.stage, step.count])),
      primary_blocker: primary,
      summary: status === 'category_not_found'
        ? `В городе ${input.city} нет подрядчиков категории «${input.category}».`
        : status === 'no_match'
          ? `После условия «${labels[primary || last.stage]}» подходящих подрядчиков не осталось.`
          : pool.length < 3 ? `Подходящих вариантов только ${pool.length}: остальные не прошли обязательные условия.` : undefined,
    },
    availability: availability(input),
    model_info: { ranking_version: 'mock-lexical-v1', semantic_model: 'lexical-mock', fallback_used: true },
  }
}
