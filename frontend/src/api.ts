const API_ERROR = 'api_error'

export class ApiError extends Error {
  status: number
  body: unknown
  constructor(status: number, body: unknown) {
    super(API_ERROR)
    this.status = status
    this.body = body
  }
}

export async function api<T>(path: string, opts: { method?: string; json?: unknown } = {}): Promise<T> {
  const res = await fetch(path, {
    method: opts.method || 'GET',
    credentials: 'include',
    headers: opts.json ? { 'Content-Type': 'application/json' } : undefined,
    body: opts.json ? JSON.stringify(opts.json) : undefined,
  })
  if (res.status === 204) return undefined as T
  const text = await res.text()
  let body: unknown = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = text
    }
  }
  if (!res.ok) throw new ApiError(res.status, body)
  return body as T
}
