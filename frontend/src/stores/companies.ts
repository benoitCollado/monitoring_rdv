import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api } from '@/api/client'
import type { Company } from '@/api/types'

const CURRENT_KEY = 'olm.currentCompanyId'

export const useCompaniesStore = defineStore('companies', () => {
  const companies = ref<Company[]>([])
  const currentId = ref<string | null>(localStorage.getItem(CURRENT_KEY))
  const loading = ref(false)
  const error = ref<string | null>(null)

  const current = computed(
    () => companies.value.find((c) => c.id === currentId.value) ?? null,
  )

  async function load() {
    loading.value = true
    error.value = null
    try {
      companies.value = await api.listCompanies()
      if (!current.value) select(companies.value[0]?.id ?? null)
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  function select(id: string | null) {
    currentId.value = id
    if (id) localStorage.setItem(CURRENT_KEY, id)
    else localStorage.removeItem(CURRENT_KEY)
  }

  return { companies, currentId, current, loading, error, load, select }
})
