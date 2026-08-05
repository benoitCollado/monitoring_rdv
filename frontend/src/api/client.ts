import type {
  AppointmentType,
  CheckRun,
  Company,
  CompanySummary,
  Employee,
  GenerateResult,
  LinkCheck,
  LinkPage,
  MonitoredLink,
  Shop,
} from './types'

const BASE = import.meta.env.VITE_API_BASE_URL ?? '/api'
const API_KEY_STORAGE = 'olm.apiKey'

export function getApiKey(): string {
  return localStorage.getItem(API_KEY_STORAGE) ?? ''
}

export function setApiKey(key: string): void {
  if (key) localStorage.setItem(API_KEY_STORAGE, key)
  else localStorage.removeItem(API_KEY_STORAGE)
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  const key = getApiKey()
  if (key) headers.set('X-API-Key', key)

  const response = await fetch(`${BASE}${path}`, { ...init, headers })

  if (!response.ok) {
    throw new ApiError(response.status, await describeError(response))
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

async function describeError(response: Response): Promise<string> {
  try {
    const body = await response.json()
    const detail = body?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      // FastAPI validation errors: "champ : message"
      return detail
        .map((e: { loc?: unknown[]; msg?: string }) => {
          const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : ''
          return field ? `${field} : ${e.msg}` : e.msg
        })
        .join(' — ')
    }
  } catch {
    /* réponse non JSON */
  }
  return `Erreur HTTP ${response.status}`
}

const qs = (params: Record<string, string | number | boolean | undefined | null>) => {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value))
    }
  }
  const s = search.toString()
  return s ? `?${s}` : ''
}

export const api = {
  config: () => request<{ auth_required: boolean }>('/config'),

  // Entreprises
  listCompanies: () => request<Company[]>('/companies'),
  createCompany: (payload: Partial<Company>) =>
    request<Company>('/companies', { method: 'POST', body: JSON.stringify(payload) }),
  updateCompany: (id: string, payload: Partial<Company>) =>
    request<Company>(`/companies/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteCompany: (id: string) =>
    request<void>(`/companies/${id}`, { method: 'DELETE' }),

  // Catalogue
  listShops: (companyId: string) => request<Shop[]>(`/companies/${companyId}/shops`),
  createShop: (companyId: string, payload: Record<string, unknown>) =>
    request<Shop>(`/companies/${companyId}/shops`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateShop: (companyId: string, id: string, payload: Record<string, unknown>) =>
    request<Shop>(`/companies/${companyId}/shops/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteShop: (companyId: string, id: string) =>
    request<void>(`/companies/${companyId}/shops/${id}`, { method: 'DELETE' }),

  listEmployees: (companyId: string) =>
    request<Employee[]>(`/companies/${companyId}/employees`),
  createEmployee: (companyId: string, payload: Record<string, unknown>) =>
    request<Employee>(`/companies/${companyId}/employees`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateEmployee: (companyId: string, id: string, payload: Record<string, unknown>) =>
    request<Employee>(`/companies/${companyId}/employees/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteEmployee: (companyId: string, id: string) =>
    request<void>(`/companies/${companyId}/employees/${id}`, { method: 'DELETE' }),

  listAppointmentTypes: (companyId: string) =>
    request<AppointmentType[]>(`/companies/${companyId}/appointment-types`),
  createAppointmentType: (companyId: string, payload: Record<string, unknown>) =>
    request<AppointmentType>(`/companies/${companyId}/appointment-types`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateAppointmentType: (
    companyId: string,
    id: string,
    payload: Record<string, unknown>,
  ) =>
    request<AppointmentType>(`/companies/${companyId}/appointment-types/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteAppointmentType: (companyId: string, id: string) =>
    request<void>(`/companies/${companyId}/appointment-types/${id}`, {
      method: 'DELETE',
    }),

  // Moniteur
  generateLinks: (companyId: string) =>
    request<GenerateResult>(`/companies/${companyId}/links/generate`, {
      method: 'POST',
    }),
  previewLinks: (companyId: string, limit = 10) =>
    request<string[]>(`/companies/${companyId}/preview${qs({ limit })}`),
  listLinks: (
    companyId: string,
    params: Record<string, string | number | boolean | undefined> = {},
  ) => request<LinkPage>(`/companies/${companyId}/links${qs(params)}`),
  getLink: (companyId: string, linkId: string) =>
    request<MonitoredLink>(`/companies/${companyId}/links/${linkId}`),
  checkLink: (companyId: string, linkId: string) =>
    request<MonitoredLink>(`/companies/${companyId}/links/${linkId}/check`, {
      method: 'POST',
    }),
  linkHistory: (companyId: string, linkId: string, limit = 50) =>
    request<LinkCheck[]>(
      `/companies/${companyId}/links/${linkId}/checks${qs({ limit })}`,
    ),
  summary: (companyId: string) =>
    request<CompanySummary>(`/companies/${companyId}/summary`),
  runNow: (companyId: string) =>
    request<{ status: string }>(`/companies/${companyId}/checks/run`, {
      method: 'POST',
    }),
  listRuns: (companyId: string, limit = 30) =>
    request<CheckRun[]>(`/companies/${companyId}/runs${qs({ limit })}`),
}
