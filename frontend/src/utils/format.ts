const currency = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 })

export function formatKZT(value: number): string {
  return `${currency.format(value).replace(/\u00a0|\u202f/g, ' ')} ₸`
}

export function formatDate(value: string, short = false): string {
  const [year, month, day] = value.split('-').map(Number)
  const date = new Date(year, month - 1, day)
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric', month: short ? 'short' : 'long',
    ...(short ? {} : { year: 'numeric' }),
  }).format(date)
}

export function percent(value: number): string {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`
}

export function pluralVariants(value: number): string {
  const mod10 = value % 10
  const mod100 = value % 100
  if (mod10 === 1 && mod100 !== 11) return 'вариант'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 'варианта'
  return 'вариантов'
}
