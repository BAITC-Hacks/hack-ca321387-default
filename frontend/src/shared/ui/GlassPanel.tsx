import type { HTMLAttributes } from 'react'

type GlassPanelTag = 'div' | 'section' | 'article'

interface GlassPanelProps extends HTMLAttributes<HTMLElement> {
  as?: GlassPanelTag
  interactive?: boolean
}

export function GlassPanel({ as = 'div', interactive = false, className, ...props }: GlassPanelProps) {
  const surfaceClass = ['liquid-glass', interactive && 'liquid-glass-interactive', className]
    .filter(Boolean)
    .join(' ')

  if (as === 'article') return <article {...props} className={surfaceClass} />
  if (as === 'section') return <section {...props} className={surfaceClass} />
  return <div {...props} className={surfaceClass} />
}