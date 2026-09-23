export const apiBase = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')
export const mockMode = import.meta.env.VITE_USE_MOCK_API === 'true' ||
  (import.meta.env.DEV && import.meta.env.VITE_USE_MOCK_API !== 'false')

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function apiClient<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${apiBase}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options?.headers },
    })
  } catch {
    throw new ApiError('Не удалось связаться с сервером. Проверьте соединение.', 0)
  }

  if (!response.ok) {
    const details = await response.json().catch(() => null) as { detail?: unknown; message?: string } | null
    const readable = typeof details?.detail === 'string' ? details.detail : details?.message
    const fallback = response.status === 422 || response.status === 400
      ? 'Проверьте параметры поиска и попробуйте снова.'
      : response.status === 404
        ? 'Запрошенные данные пока недоступны.'
        : 'Сервис временно недоступен. Попробуйте ещё раз.'
    throw new ApiError(readable || fallback, response.status)
  }
  return response.json() as Promise<T>
}
