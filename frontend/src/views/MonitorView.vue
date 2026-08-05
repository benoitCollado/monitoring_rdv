<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

import { api } from '@/api/client'
import type {
  AppointmentType,
  CompanySummary,
  Employee,
  MonitoredLink,
  Shop,
} from '@/api/types'
import NoCompany from '@/components/NoCompany.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { useCompaniesStore } from '@/stores/companies'
import { formatDateTime, formatDuration, formatReason } from '@/utils/format'

const companies = useCompaniesStore()
const companyId = computed(() => companies.currentId)

const summary = ref<CompanySummary | null>(null)
const links = ref<MonitoredLink[]>([])
const total = ref(0)
const shops = ref<Shop[]>([])
const employees = ref<Employee[]>([])
const types = ref<AppointmentType[]>([])

const filters = ref({
  status: '',
  kind: '',
  shop_id: '',
  appointment_type_id: '',
  employee_id: '',
  q: '',
  include_archived: false,
})
const limit = 100
const offset = ref(0)

const loading = ref(false)
const busy = ref('')
const error = ref<string | null>(null)
const message = ref<string | null>(null)
let poller: number | undefined

const runInProgress = computed(() => summary.value?.last_run?.status === 'running')

async function loadCatalog() {
  if (!companyId.value) return
  ;[shops.value, employees.value, types.value] = await Promise.all([
    api.listShops(companyId.value),
    api.listEmployees(companyId.value),
    api.listAppointmentTypes(companyId.value),
  ])
}

async function loadLinks() {
  if (!companyId.value) return
  loading.value = true
  error.value = null
  try {
    const [page, sum] = await Promise.all([
      api.listLinks(companyId.value, { ...filters.value, limit, offset: offset.value }),
      api.summary(companyId.value),
    ])
    links.value = page.items
    total.value = page.total
    summary.value = sum
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

async function generate() {
  if (!companyId.value) return
  busy.value = 'generate'
  error.value = null
  try {
    const result = await api.generateLinks(companyId.value)
    message.value =
      `${result.created} lien(s) créé(s), ${result.revived} réactivé(s), ` +
      `${result.updated} mis à jour, ${result.archived} archivé(s) — ` +
      `${result.total_active} liens surveillés.`
    offset.value = 0
    await loadLinks()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = ''
  }
}

async function runNow() {
  if (!companyId.value) return
  busy.value = 'run'
  error.value = null
  try {
    await api.runNow(companyId.value)
    message.value = 'Vérification lancée — la page se met à jour automatiquement.'
    await loadLinks()
    startPolling()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = ''
  }
}

async function recheck(link: MonitoredLink) {
  if (!companyId.value) return
  busy.value = link.id
  try {
    const updated = await api.checkLink(companyId.value, link.id)
    const index = links.value.findIndex((l) => l.id === updated.id)
    if (index !== -1) links.value[index] = updated
    summary.value = await api.summary(companyId.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = ''
  }
}

function startPolling() {
  stopPolling()
  poller = window.setInterval(async () => {
    await loadLinks()
    if (!runInProgress.value) stopPolling()
  }, 4000)
}

function stopPolling() {
  if (poller) window.clearInterval(poller)
  poller = undefined
}

function applyFilters() {
  offset.value = 0
  loadLinks()
}

function resetFilters() {
  filters.value = {
    status: '',
    kind: '',
    shop_id: '',
    appointment_type_id: '',
    employee_id: '',
    q: '',
    include_archived: false,
  }
  applyFilters()
}

function changePage(delta: number) {
  offset.value = Math.max(0, offset.value + delta * limit)
  loadLinks()
}

watch(
  companyId,
  async (id) => {
    if (!id) return
    offset.value = 0
    await loadCatalog()
    await loadLinks()
  },
  { immediate: false },
)

onMounted(async () => {
  if (companyId.value) {
    await loadCatalog()
    await loadLinks()
    if (runInProgress.value) startPolling()
  }
})

onUnmounted(stopPolling)
</script>

<template>
  <NoCompany v-if="!companyId" />

  <template v-else>
    <div class="page-header">
      <h2>Moniteur — {{ companies.current?.name }}</h2>
      <div class="row">
        <button :disabled="busy === 'generate'" @click="generate">
          {{ busy === 'generate' ? 'Génération…' : 'Générer les liens' }}
        </button>
        <button
          class="primary"
          :disabled="busy === 'run' || runInProgress"
          @click="runNow"
        >
          {{ runInProgress ? 'Vérification en cours…' : 'Vérifier maintenant' }}
        </button>
      </div>
    </div>

    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="message" class="notice">{{ message }}</div>

    <div class="tiles" v-if="summary">
      <div class="tile">
        <div class="label">Liens surveillés</div>
        <div class="value">{{ summary.total }}</div>
      </div>
      <div class="tile ok">
        <div class="label">Opérationnels</div>
        <div class="value">{{ summary.ok }}</div>
      </div>
      <div class="tile broken">
        <div class="label">Cassés</div>
        <div class="value">{{ summary.broken }}</div>
      </div>
      <div class="tile">
        <div class="label">Jamais vérifiés</div>
        <div class="value">{{ summary.unknown }}</div>
      </div>
      <div class="tile">
        <div class="label">Dernier run</div>
        <div class="value" style="font-size: 15px; padding-top: 8px">
          {{ formatDateTime(summary.last_run?.started_at) }}
        </div>
        <div class="muted small" v-if="summary.last_run">
          {{ summary.last_run.checked_count }} liens ·
          {{ summary.last_run.broken_count }} cassés ·
          {{ summary.last_run.status }}
        </div>
      </div>
      <div class="tile">
        <div class="label">Prochain run</div>
        <div class="value" style="font-size: 15px; padding-top: 8px">
          {{ formatDateTime(summary.next_run_at) }}
        </div>
        <div class="muted small" v-if="companies.current">
          tous les jours à
          {{ String(companies.current.check_hour).padStart(2, '0') }}:{{
            String(companies.current.check_minute).padStart(2, '0')
          }}
          ({{ companies.current.timezone }})
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="row">
        <div>
          <label>Statut</label>
          <select v-model="filters.status" @change="applyFilters">
            <option value="">Tous</option>
            <option value="broken">Cassés</option>
            <option value="ok">Opérationnels</option>
            <option value="unknown">Jamais vérifiés</option>
          </select>
        </div>
        <div>
          <label>Type de lien</label>
          <select v-model="filters.kind" @change="applyFilters">
            <option value="">Tous</option>
            <option value="shop">Boutique seule</option>
            <option value="employee">Avec conseiller</option>
          </select>
        </div>
        <div>
          <label>Boutique</label>
          <select v-model="filters.shop_id" @change="applyFilters">
            <option value="">Toutes</option>
            <option v-for="s in shops" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>
        <div>
          <label>Type de RDV</label>
          <select v-model="filters.appointment_type_id" @change="applyFilters">
            <option value="">Tous</option>
            <option v-for="t in types" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
        </div>
        <div>
          <label>Conseiller</label>
          <select v-model="filters.employee_id" @change="applyFilters">
            <option value="">Tous</option>
            <option v-for="e in employees" :key="e.id" :value="e.id">
              {{ e.name }}
            </option>
          </select>
        </div>
        <div>
          <label>Recherche</label>
          <input
            v-model="filters.q"
            placeholder="slug ou URL"
            @keyup.enter="applyFilters"
          />
        </div>
        <div>
          <label>
            <input
              type="checkbox"
              v-model="filters.include_archived"
              @change="applyFilters"
            />
            Inclure les archivés
          </label>
        </div>
        <button @click="resetFilters">Réinitialiser</button>
      </div>
    </div>

    <div class="panel">
      <p v-if="loading" class="muted">Chargement…</p>
      <p v-else-if="!links.length" class="muted">
        Aucun lien. Vérifiez le catalogue (boutiques, conseillers, types de RDV) puis
        cliquez sur « Générer les liens ».
      </p>

      <table v-else>
        <thead>
          <tr>
            <th>Statut</th>
            <th>Lien</th>
            <th>Boutique</th>
            <th>Type de RDV</th>
            <th>Conseiller</th>
            <th>Dernière vérif.</th>
            <th>Détail</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="link in links" :key="link.id">
            <td>
              <StatusBadge :status="link.status" />
              <div v-if="!link.is_active" class="badge muted" style="margin-top: 4px">
                archivé
              </div>
            </td>
            <td>
              <RouterLink :to="`/links/${link.id}`" class="mono">{{
                link.slug
              }}</RouterLink>
              <div class="muted small">
                <a :href="link.url" target="_blank" rel="noopener" class="truncate">{{
                  link.url
                }}</a>
              </div>
            </td>
            <td>{{ link.shop_name }}</td>
            <td>{{ link.appointment_type_name }}</td>
            <td>{{ link.employee_name ?? '—' }}</td>
            <td class="small">
              {{ formatDateTime(link.last_checked_at) }}
              <div class="muted">{{ formatDuration(link.last_response_time_ms) }}</div>
            </td>
            <td class="small">
              <template v-if="link.status === 'broken'">
                <div>{{ formatReason(link.last_reason) }}</div>
                <div class="muted">{{ link.last_error }}</div>
                <div class="muted">
                  {{ link.consecutive_failures }} échec(s) consécutif(s) depuis
                  {{ formatDateTime(link.broken_since) }}
                </div>
              </template>
              <span v-else class="muted">
                {{ link.last_status_code ? `HTTP ${link.last_status_code}` : '—' }}
              </span>
            </td>
            <td>
              <button
                class="small"
                :disabled="busy === link.id"
                @click="recheck(link)"
              >
                {{ busy === link.id ? '…' : 'Revérifier' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="pagination" v-if="total > limit">
        <button :disabled="offset === 0" @click="changePage(-1)">Précédent</button>
        <span class="muted small">
          {{ offset + 1 }}–{{ Math.min(offset + limit, total) }} sur {{ total }}
        </span>
        <button :disabled="offset + limit >= total" @click="changePage(1)">
          Suivant
        </button>
      </div>
    </div>
  </template>
</template>
