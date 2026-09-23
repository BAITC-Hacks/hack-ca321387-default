import { useQuery } from '@tanstack/react-query'
import { getDemoPresets } from '../../shared/api/discovery.api'
import type { SearchParams } from '../../shared/types/match'

export function DemoPresets({ onSelect, pending }: { onSelect: (query: SearchParams) => void; pending: boolean }) {
  const presets = useQuery({ queryKey: ['demo-presets'], queryFn: getDemoPresets, staleTime: 5 * 60_000, retry: 1 })
  if (presets.isPending) return null

  return <section className="demo-presets" aria-labelledby="demo-presets-title">
    <div className="demo-presets-heading">
      <div><p className="eyebrow">Готовые сценарии</p><h2 id="demo-presets-title">Попробуйте поиск на примере</h2></div>
      <p>Сценарии рассчитаны backend по текущему каталогу.</p>
    </div>
    {presets.isError ? <div className="demo-presets-error" role="alert">Не удалось загрузить сценарии. <button type="button" onClick={() => void presets.refetch()}>Повторить</button></div>
      : <div className="demo-presets-list">
        {presets.data.presets.map((preset) => <div className="demo-preset" key={preset.id}>
          <strong>{preset.title}</strong><p>{preset.description}</p>
          <span>{preset.eligible_count} подходящих в каталоге</span>
          <div><button type="button" className="secondary-button" disabled={pending} onClick={() => onSelect(preset.query)}>Показать результат</button>
            {preset.related_query && <button type="button" className="secondary-button" disabled={pending} onClick={() => onSelect(preset.related_query!)}>Сравнить условие</button>}</div>
        </div>)}
      </div>}
  </section>
}
