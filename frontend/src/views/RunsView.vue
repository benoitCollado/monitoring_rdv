<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api } from '@/api/client'
import type { CheckRun } from '@/api/types'
import NoCompany from '@/components/NoCompany.vue'
import { useCompaniesStore } from '@/stores/companies'
import { formatDateTime } from '@/utils/format'

const companies = useCompaniesStore()
const companyId = computed(() => companies.currentId)
const runs = ref<CheckRun[]>([])
const error = ref<string | null>(null)

function duration(run: CheckRun): string {
  if (!run.finished_at) return '—'
  const ms = new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()
  return `${(ms / 1000).toFixed(1)} s`
}

onMounted(async () => {
  if (!companyId.value) return
  try {
    runs.value = await api.listRuns(companyId.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
})
</script>

<template>
  <NoCompany v-if="!companyId" />

  <template v-else>
    <div class="page-header"><h2>Historique des runs</h2></div>
    <div v-if="error" class="error">{{ error }}</div>

    <div class="panel">
      <p v-if="!runs.length" class="muted">
        Aucun run enregistré. Le cron s'exécute une fois par jour ; vous pouvez aussi
        lancer une vérification depuis le moniteur.
      </p>
      <table v-else>
        <thead>
          <tr>
            <th>Démarré</th>
            <th>Déclencheur</th>
            <th>État</th>
            <th>Liens</th>
            <th>OK</th>
            <th>Cassés</th>
            <th>Durée</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="run in runs" :key="run.id">
            <td>{{ formatDateTime(run.started_at) }}</td>
            <td>{{ run.trigger === 'cron' ? 'Cron quotidien' : 'Manuel' }}</td>
            <td>
              <span
                class="badge"
                :class="{
                  ok: run.status === 'done',
                  broken: run.status === 'failed',
                  unknown: run.status === 'running',
                }"
              >
                {{
                  { running: 'En cours', done: 'Terminé', failed: 'Échec' }[run.status]
                }}
              </span>
              <div v-if="run.error" class="muted small">{{ run.error }}</div>
            </td>
            <td>{{ run.checked_count }}</td>
            <td>{{ run.ok_count }}</td>
            <td>{{ run.broken_count }}</td>
            <td>{{ duration(run) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </template>
</template>
