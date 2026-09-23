export function normalizeApiBase(value: string): string {
  const base = value.trim().replace(/\/+$/, '')
  return base.endsWith('/api') ? base : `${base}/api`
}

export const apiBase = normalizeApiBase(import.meta.env.VITE_API_URL || '/api')
export const mockMode = import.meta.env.DEV && import.meta.env.VITE_USE_MOCK_API === 'true'

export class ApiError extends Error {
  constructor(message: string, public readonly status: number, public readonly code = 'api_error',
    public readonly fields: Array<{ field: string | null; code: string; message: string }> = []) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function apiClient<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${apiBase}${path}`, {
      ...options,
      signal: options?.signal ?? AbortSignal.timeout(12_000),
      headers: { 'Content-Type': 'application/json', ...options?.headers },
    })
  } catch {
    throw new ApiError('Не удалось связаться с сервером. Проверьте соединение и повторите запрос.', 0, 'network_error')
  }

  if (!response.ok) {
    const details = await response.json().catch(() => null) as {
      detail?: unknown; message?: string; code?: string
    } | null
    const readable = typeof details?.detail === 'string' ? details.detail : details?.message
    const fallback = response.status === 422 || response.status === 400
      ? 'Проверьте параметры поиска и попробуйте снова.'
      : response.status === 404
        ? 'Запрошенный маршрут недоступен.'
        : 'Сервис временно недоступен. Попробуйте ещё раз.'
    const fields = Array.isArray(details?.detail) ? details.detail.filter((item): item is {
      field: string | null; code: string; message: string
    } => typeof item === 'object' && item !== null && (typeof item.field === 'string' || item.field === null)
      && typeof item.code === 'string' && typeof item.message === 'string') : []
    throw new ApiError(readable || fallback, response.status, details?.code, fields)
  }
  try {
    return await response.json() as T
  } catch {
    throw new ApiError('Сервер вернул некорректный JSON.', 502, 'invalid_response')
  }
}
