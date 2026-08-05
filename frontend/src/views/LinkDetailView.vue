<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { api } from '@/api/client'
import type { LinkCheck, MonitoredLink } from '@/api/types'
import NoCompany from '@/components/NoCompany.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { useCompaniesStore } from '@/stores/companies'
import { formatDateTime, formatDuration, formatReason } from '@/utils/format'

const route = useRoute()
const companies = useCompaniesStore()
const companyId = computed(() => companies.currentId)
const linkId = computed(() => String(route.params.linkId))

const link = ref<MonitoredLink | null>(null)
const history = ref<LinkCheck[]>([])
const error = ref<string | null>(null)
const busy = ref(false)

async function load() {
  if (!companyId.value) return
  error.value = null
  try {
    ;[link.value, history.value] = await Promise.all([
      api.getLink(companyId.value, linkId.value),
      api.linkHistory(companyId.value, linkId.value),
    ])
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function recheck() {
  if (!companyId.value) return
  busy.value = true
  try {
    link.value = await api.checkLink(companyId.value, linkId.value)
    history.value = await api.linkHistory(companyId.value, linkId.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <NoCompany v-if="!companyId" />

  <template v-else>
    <div class="page-header">
      <h2>
        <RouterLink to="/monitor">← Moniteur</RouterLink>
      </h2>
      <button class="primary" :disabled="busy" @click="recheck">
        {{ busy ? 'Vérification…' : 'Revérifier maintenant' }}
      </button>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div class="panel" v-if="link">
      <h3 class="mono" style="margin-top: 0">{{ link.slug }}</h3>
      <p>
        <a :href="link.url" target="_blank" rel="noopener">{{ link.url }}</a>
      </p>
      <table>
        <tbody>
          <tr>
            <th>Statut</th>
            <td><StatusBadge :status="link.status" /></td>
          </tr>
          <tr>
            <th>Boutique</th>
            <td>{{ link.shop_name }}</td>
          </tr>
          <tr>
            <th>Type de RDV</th>
            <td>{{ link.appointment_type_name }}</td>
          </tr>
          <tr>
            <th>Conseiller</th>
            <td>{{ link.employee_name ?? '— (lien boutique seule)' }}</td>
          </tr>
          <tr>
            <th>Dernière vérification</th>
            <td>
              {{ formatDateTime(link.last_checked_at) }} ·
              {{ formatDuration(link.last_response_time_ms) }} ·
              {{ link.last_status_code ? `HTTP ${link.last_status_code}` : '—' }}
            </td>
          </tr>
          <tr v-if="link.status === 'broken'">
            <th>Cause</th>
            <td>
              {{ formatReason(link.last_reason) }} — {{ link.last_error }}<br />
              <span class="muted small">
                {{ link.consecutive_failures }} échec(s) consécutif(s), cassé depuis
                {{ formatDateTime(link.broken_since) }}
              </span>
            </td>
          </tr>
          <tr v-if="!link.is_active">
            <th>Archivé</th>
            <td class="muted">
              Cette combinaison n'existe plus dans le catalogue ; elle n'est plus
              vérifiée mais son historique est conservé.
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="panel">
      <h3 style="margin-top: 0">Historique</h3>
      <p v-if="!history.length" class="muted">Aucune vérification enregistrée.</p>
      <table v-else>
        <thead>
          <tr>
            <th>Date</th>
            <th>Résultat</th>
            <th>HTTP</th>
            <th>Temps</th>
            <th>Cause</th>
            <th>URL finale</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="check in history" :key="check.id">
            <td>{{ formatDateTime(check.checked_at) }}</td>
            <td>
              <span class="badge" :class="check.ok ? 'ok' : 'broken'">
                {{ check.ok ? 'OK' : 'Cassé' }}
              </span>
            </td>
            <td>{{ check.status_code ?? '—' }}</td>
            <td>{{ formatDuration(check.response_time_ms) }}</td>
            <td class="small">
              {{ formatReason(check.reason) }}
              <div class="muted">{{ check.error }}</div>
            </td>
            <td class="small muted">
              <span class="truncate">{{ check.final_url ?? '—' }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </template>
</template>
