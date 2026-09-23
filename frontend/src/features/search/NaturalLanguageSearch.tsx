import { useState, type FormEvent } from 'react'
import type { SearchParams } from '../../shared/types/match'
import { extractSearch, type ExtractionResponse } from './extract.api'

const labels: Record<string, string> = {
  city: 'город', date: 'дата', event_type: 'формат', category: 'подрядчик',
  budget: 'бюджет', language: 'язык', duration: 'длительность',
}

export function NaturalLanguageSearch({ onApply, pending }: {
  onApply: (query: SearchParams, complete: boolean) => void
  pending: boolean
}) {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ExtractionResponse>()
  const [error, setError] = useState('')

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!text.trim() || loading || pending) return
    setLoading(true)
    setError('')
    setResult(undefined)
    try {
      const extracted = await extractSearch(text.trim())
      setResult(extracted)
      const fields = extracted.fields
      const query: SearchParams = {
        city: fields.city ?? '', date: fields.date ?? '', event_type: fields.event_type ?? '',
        category: fields.category ?? '', budget: fields.budget ?? 0,
        language: fields.language, duration: fields.duration,
      }
      onApply(query, extracted.missing.length === 0)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не удалось разобрать запрос. Заполните форму вручную.')
    } finally {
      setLoading(false)
    }
  }

  return <section className="natural-search" aria-labelledby="natural-search-title">
    <div className="natural-search-heading">
      <div><span className="eyebrow">Поиск по описанию</span><h2 id="natural-search-title">Опишите мероприятие своими словами</h2></div>
      <p>Укажем только то, что действительно есть в вашем тексте.</p>
    </div>
    <form className="natural-search-form" onSubmit={(event) => void submit(event)}>
      <label className="sr-only" htmlFor="natural-search-input">Описание мероприятия</label>
      <textarea id="natural-search-input" value={text} onChange={(event) => setText(event.target.value)}
        maxLength={1500} rows={2} disabled={loading || pending}
        placeholder="Например: Нужен ведущий на корпоратив в Алматы 15 ноября 2026, бюджет до 800 000 ₸, на 6 часов, на русском языке" />
      <button className="primary-button" type="submit" disabled={!text.trim() || loading || pending}>
        {loading ? 'Разбираем запрос…' : 'Найти по описанию'}
      </button>
    </form>
    {error && <p className="natural-search-error" role="alert">{error}</p>}
    {result && <div className="natural-search-result" role="status">
      <p>{result.missing.length ? 'Заполнили найденные поля. Дополните недостающие и нажмите «Найти подрядчиков».' : 'Параметры извлечены из текста. Запускаем подбор.'}</p>
      <div className="natural-search-tags">{Object.entries(result.evidence).map(([field, quote]) =>
        <span key={field} title={`Из текста: ${quote}`}>{labels[field]}: {String(result.fields[field as keyof typeof result.fields])}</span>)}</div>
      {result.missing.length > 0 && <p>Не указано: {result.missing.map((field) => labels[field]).join(', ')}. Мы не подставляем значения из примера.</p>}
    </div>}
  </section>
}
