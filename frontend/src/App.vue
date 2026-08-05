<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useAuthStore } from '@/stores/auth'
import { useCompaniesStore } from '@/stores/companies'

const auth = useAuthStore()
const companies = useCompaniesStore()
const keyInput = ref('')

const locked = computed(() => auth.authRequired && !auth.apiKey)

onMounted(async () => {
  await auth.init()
  if (!locked.value) await companies.load()
})

async function unlock() {
  auth.save(keyInput.value.trim())
  keyInput.value = ''
  await companies.load()
}

async function logout() {
  auth.clear()
  companies.companies = []
}
</script>

<template>
  <div v-if="!auth.checked" class="content muted">Chargement…</div>

  <div v-else-if="locked" class="gate panel">
    <h2>Moniteur de liens Odoo</h2>
    <p class="muted small">
      Cette instance est protégée. Saisissez la clé d'API configurée côté serveur.
    </p>
    <form @submit.prevent="unlock">
      <div class="field">
        <label for="key">Clé d'API</label>
        <input id="key" v-model="keyInput" type="password" autofocus style="width: 100%" />
      </div>
      <button class="primary" type="submit">Entrer</button>
    </form>
  </div>

  <div v-else class="layout">
    <aside class="sidebar">
      <h1>Moniteur de liens<br /><span class="muted small">Odoo</span></h1>

      <div>
        <div class="section-title">Entreprise</div>
        <select
          :value="companies.currentId ?? ''"
          style="width: 100%"
          @change="companies.select(($event.target as HTMLSelectElement).value || null)"
        >
          <option value="" disabled>— choisir —</option>
          <option v-for="c in companies.companies" :key="c.id" :value="c.id">
            {{ c.name }}
          </option>
        </select>
      </div>

      <nav>
        <div class="section-title">Surveillance</div>
        <RouterLink to="/monitor">Moniteur</RouterLink>
        <RouterLink to="/runs">Historique des runs</RouterLink>
      </nav>

      <nav>
        <div class="section-title">Configuration</div>
        <RouterLink to="/shops">Boutiques</RouterLink>
        <RouterLink to="/employees">Conseillers</RouterLink>
        <RouterLink to="/appointment-types">Types de RDV</RouterLink>
        <RouterLink to="/companies">Entreprises</RouterLink>
      </nav>

      <div v-if="auth.authRequired" style="margin-top: auto">
        <button class="small" @click="logout">Se déconnecter</button>
      </div>
    </aside>

    <main class="content">
      <div v-if="companies.error" class="error">{{ companies.error }}</div>
      <RouterView :key="companies.currentId ?? 'none'" />
    </main>
  </div>
</template>
