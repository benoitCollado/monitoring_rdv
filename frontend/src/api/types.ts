export interface Company {
  id: string
  name: string
  base_url: string
  shop_link_template: string
  employee_link_template: string
  error_patterns: string[]
  check_hour: number
  check_minute: number
  timezone: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CatalogRef {
  id: string
  name: string
  shortcode: string
  is_active: boolean
}

export interface Shop extends CatalogRef {
  company_id: string
  employees: CatalogRef[]
}

export interface Employee extends CatalogRef {
  company_id: string
  shops: CatalogRef[]
}

export interface AppointmentType extends CatalogRef {
  company_id: string
}

export type LinkStatus = 'ok' | 'broken' | 'unknown'

export interface MonitoredLink {
  id: string
  company_id: string
  kind: 'shop' | 'employee'
  slug: string
  url: string
  is_active: boolean
  status: LinkStatus
  last_checked_at: string | null
  last_status_code: number | null
  last_response_time_ms: number | null
  last_reason: string | null
  last_error: string | null
  consecutive_failures: number
  broken_since: string | null
  shop_id: string
  shop_name: string
  appointment_type_id: string
  appointment_type_name: string
  employee_id: string | null
  employee_name: string | null
}

export interface LinkPage {
  items: MonitoredLink[]
  total: number
  limit: number
  offset: number
}

export interface LinkCheck {
  id: string
  link_id: string
  run_id: string | null
  checked_at: string
  ok: boolean
  status_code: number | null
  response_time_ms: number | null
  final_url: string | null
  reason: string
  error: string | null
}

export interface CheckRun {
  id: string
  company_id: string
  trigger: string
  status: 'running' | 'done' | 'failed'
  started_at: string
  finished_at: string | null
  checked_count: number
  ok_count: number
  broken_count: number
  error: string | null
}

export interface CompanySummary {
  company_id: string
  total: number
  ok: number
  broken: number
  unknown: number
  archived: number
  last_run: CheckRun | null
  next_run_at: string | null
}

export interface GenerateResult {
  created: number
  revived: number
  archived: number
  updated: number
  total_active: number
}
