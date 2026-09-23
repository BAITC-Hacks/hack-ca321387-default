import { Box, Flex, Heading, Text } from '@chakra-ui/react'
import { useState } from 'react'
import type { Contractor } from '../../shared/types/match'
import { formatKZT, percent } from '../../shared/format'
import { useSettings } from '../settings/useSettings'

const evidenceLabels: Record<string, string> = {
  date: 'Дата', city: 'Город', category: 'Категория', budget: 'Бюджет',
  format: 'Формат', language: 'Язык', duration: 'Длительность', semantic: 'Совпадение описания',
}

interface ContractorCardProps {
  contractor: Contractor
  index: number
  lexicalMode: boolean
}

export function ContractorCard({ contractor, index, lexicalMode }: ContractorCardProps) {
  const [expanded, setExpanded] = useState(false)
  const { settings } = useSettings()
  const entries = Object.entries(contractor.evidence).filter(([, item]) => item)
  const headlineEntries = entries.filter(([key]) => ['date', 'budget', 'format', 'language', 'duration'].includes(key))
  const score = percent(contractor.score)

  return (
    <article className={`contractor-card ${settings.compactResults ? 'is-compact' : ''}`} style={{ animationDelay: `${index * 60}ms` }}>
      <Flex className="card-top" justify="space-between" align="start" gap={4}>
        <div>
          <Text className="card-number">{String(index + 1).padStart(2, '0')} / РЕКОМЕНДАЦИЯ</Text>
          <Heading as="h3" className="contractor-name">{contractor.name}</Heading>
          <Flex gap={2} align="center" className="contractor-meta">
            <span>{contractor.categories.join(', ')}</span><span className="meta-dot" aria-hidden="true" /><span>{contractor.city}</span>
          </Flex>
        </div>
        <div className="score-box" aria-label={`Совпадение ${score}`}>
          <strong>{score}</strong><span>совпадение</span>
          <i style={{ width: score }} aria-hidden="true" />
        </div>
      </Flex>

      <Flex className="card-price-row" align="center" justify="space-between" gap={4} wrap="wrap">
        <div><span className="small-label">Стоимость от</span><strong>{formatKZT(contractor.price)}</strong></div>
        {contractor.synthetic && <span className="synthetic-badge" title="Профиль добавлен в тестовый набор данных.">Синтетический профиль</span>}
      </Flex>

      {settings.compactResults ? (
        <Box className="compact-summary">
          <Text className="subsection-label">Кратко о рекомендации</Text>
          <Text>{contractor.explanation}</Text>
        </Box>
      ) : (
        <>
          <div className="evidence-summary">
            <Text className="subsection-label">Проверенные условия</Text>
            <div className="evidence-grid">
              {headlineEntries.map(([key, item]) => (
                <div className="evidence-row" key={key}>
                  <span className="evidence-indicator" aria-hidden="true" />
                  <div><span className="evidence-label">{evidenceLabels[key]}</span><span className="evidence-fact">{item.reason}</span></div>
                </div>
              ))}
            </div>
          </div>
          <div className="semantic-row">
            <div><span className="small-label">{lexicalMode ? 'Текстовое совпадение' : 'Смысловое совпадение'}</span><p>{contractor.evidence.semantic?.reason || 'Оценка описания не предоставлена.'}</p></div>
            <strong>{percent(contractor.semantic_score)}</strong>
          </div>
          <Box className="explanation-block">
            <Text className="subsection-label">Почему этот подрядчик подходит</Text>
            <Text>{contractor.explanation}</Text>
          </Box>
        </>
      )}

      <button
        type="button"
        className="details-trigger"
        aria-expanded={expanded}
        aria-controls={`details-${contractor.id}`}
        onClick={() => setExpanded((current) => !current)}
      >
        {expanded ? 'Скрыть детали' : settings.compactResults ? 'Подробнее' : 'Все доказательства'}
        <span aria-hidden="true">{expanded ? '−' : '+'}</span>
      </button>
      {expanded && (
        <div id={`details-${contractor.id}`} className="card-details">
          <div className="details-grid">
            <div><span className="small-label">ID профиля</span><strong>{contractor.id}</strong></div>
            <div><span className="small-label">Языки</span><strong>{contractor.languages?.join(', ') || 'Не указаны'}</strong></div>
            <div><span className="small-label">Максимум часов</span><strong>{contractor.max_hours == null ? 'Не применяется' : `${contractor.max_hours} ч`}</strong></div>
          </div>
          {contractor.score_breakdown && <div className="breakdown">
            <span className="small-label">Состав оценки</span>
            <div>{Object.entries(contractor.score_breakdown).map(([key, value]) => <span key={key}>{key}: {percent(value)}</span>)}</div>
          </div>}
          <div className="all-evidence"><span className="small-label">Evidence Ledger</span>
            {entries.map(([key, item]) => <p key={key}><strong>{evidenceLabels[key]}:</strong> {item.reason}{item.source_field && <small> · {item.source_field}</small>}</p>)}
          </div>
        </div>
      )}
    </article>
  )
}
