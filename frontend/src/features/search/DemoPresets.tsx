import { useQuery } from '@tanstack/react-query'
import { getDemoPresets } from '../../shared/api/discovery.api'
import type { SearchParams } from '../../shared/types/match'

export function DemoPresets({ onSelect, pending }: { onSelect: (query: SearchParams) => void; pending: boolean }) {
  const presets = useQuery({ queryKey: ['demo-presets'], queryFn: getDemoPresets, staleTime: 5 * 60_000, retry: 1 })
  if (presets.isPending) return null

  return <section className="demo-presets" aria-labelledby="demo-presets-title">
    <div className="demo-presets-heading">
      <h2 id="demo-presets-title">Готовые сценарии</h2>
      <span>Примеры из текущего каталога</span>
    </div>
    {presets.isError ? <p className="demo-presets-error" role="alert">Не удалось загрузить сценарии. <button type="button" onClick={() => void presets.refetch()}>Повторить</button></p>
      : <div className="demo-presets-list">
        {presets.data.presets.map((preset) => <div className="demo-preset" key={preset.id} title={preset.description}>
          <button type="button" className="preset-main" disabled={pending} onClick={() => onSelect(preset.query)}>
            <strong>{preset.title}</strong><span>{preset.eligible_count} подходящих</span>
          </button>
          {preset.related_query && <button type="button" className="preset-compare" disabled={pending} onClick={() => onSelect(preset.related_query!)}>Сравнить</button>}
        </div>)}
      </div>}
  </section>
}
