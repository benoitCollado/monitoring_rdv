export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  return new Date(value).toLocaleString('fr-FR', {
    dateStyle: 'short',
    timeStyle: 'short',
  })
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return '—'
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms} ms`
}

const REASONS: Record<string, string> = {
  ok: 'OK',
  http_status: 'Statut HTTP',
  error_pattern: "Page d'erreur",
  network: 'Erreur réseau',
}

export function formatReason(reason: string | null | undefined): string {
  if (!reason) return '—'
  return REASONS[reason] ?? reason
}
