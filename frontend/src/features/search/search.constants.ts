export const MIN_DATE = '2026-09-23'
export const MAX_DATE = '2026-12-31'
export const DEFAULT_SEARCH = {
  city: 'Алматы', date: '2026-11-18', event_type: 'корпоратив', category: 'Ведущий',
  budget: 1_000_000, language: 'русский', duration: 6,
} as const

export const FALLBACK_METADATA = {
  cities: ['Алматы', 'Астана', 'Зарубежье'],
  categories: [
    'Ведущий', 'Фотограф', 'Видеограф', 'Флорист', 'Декоратор',
    'Банкетный зал', 'Загородная площадка', 'Отель', 'Ресторан',
    'Инструменталист', 'Лайв-бэнд', 'Национальный ансамбль',
    'Танцевальный коллектив', 'Шоу-программа', 'Подарки и сувениры',
    'Ведущий церемонии', 'Фото и видеобудки',
  ],
  event_types: ['свадьба', 'той', 'корпоратив', 'конференция', 'юбилей', 'день рождения'],
  languages: ['русский', 'казахский', 'английский'],
  min_date: MIN_DATE,
  max_date: MAX_DATE,
  min_budget_exclusive: 0,
  max_budget: 100_000_000,
  min_duration: 1,
  max_duration: 12,
}
