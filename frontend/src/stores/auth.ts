import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api, getApiKey, setApiKey } from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  const authRequired = ref(false)
  const apiKey = ref(getApiKey())
  const checked = ref(false)

  async function init() {
    try {
      const config = await api.config()
      authRequired.value = config.auth_required
    } catch {
      // /api/config never requires a key: a failure here means the API is down,
      // which the views surface on their own.
      authRequired.value = false
    } finally {
      checked.value = true
    }
  }

  function save(key: string) {
    setApiKey(key)
    apiKey.value = key
  }

  function clear() {
    setApiKey('')
    apiKey.value = ''
  }

  return { authRequired, apiKey, checked, init, save, clear }
})
