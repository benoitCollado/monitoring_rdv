<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api } from '@/api/client'
import type { Employee, Shop } from '@/api/types'
import NoCompany from '@/components/NoCompany.vue'
import { useCompaniesStore } from '@/stores/companies'

const companies = useCompaniesStore()
const companyId = computed(() => companies.currentId)

const employees = ref<Employee[]>([])
const shops = ref<Shop[]>([])
const error = ref<string | null>(null)
const saving = ref(false)

const blank = () => ({
  id: '' as string,
  name: '',
  shortcode: '',
  is_active: true,
  shop_ids: [] as string[],
})
const form = ref(blank())
const editing = computed(() => Boolean(form.value.id))

async function load() {
  if (!companyId.value) return
  try {
    ;[employees.value, shops.value] = await Promise.all([
      api.listEmployees(companyId.value),
      api.listShops(companyId.value),
    ])
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

function edit(employee: Employee) {
  form.value = {
    id: employee.id,
    name: employee.name,
    shortcode: employee.shortcode,
    is_active: employee.is_active,
    shop_ids: employee.shops.map((s) => s.id),
  }
}

async function save() {
  if (!companyId.value) return
  saving.value = true
  error.value = null
  const payload = {
    name: form.value.name,
    shortcode: form.value.shortcode,
    is_active: form.value.is_active,
    shop_ids: form.value.shop_ids,
  }
  try {
    if (editing.value) {
      await api.updateEmployee(companyId.value, form.value.id, payload)
    } else {
      await api.createEmployee(companyId.value, payload)
    }
    form.value = blank()
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    saving.value = false
  }
}

async function remove(employee: Employee) {
  if (!companyId.value) return
  if (!confirm(`Supprimer « ${employee.name} » et ses liens ?`)) return
  try {
    await api.deleteEmployee(companyId.value, employee.id)
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

onMounted(load)
</script>

<template>
  <NoCompany v-if="!companyId" />

  <template v-else>
    <div class="page-header">
      <h2>Conseillers</h2>
      <span class="muted small">{{ employees.length }} conseiller(s)</span>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div class="panel">
      <h3 style="margin-top: 0">
        {{ editing ? 'Modifier le conseiller' : 'Nouveau conseiller' }}
      </h3>
      <p class="muted small">
        Un conseiller peut être rattaché à plusieurs boutiques : un lien sera généré
        pour chaque couple (boutique rattachée × type de RDV).
      </p>
      <form @submit.prevent="save">
        <div class="row">
          <div class="field">
            <label>Nom</label>
            <input v-model="form.name" required placeholder="Maxime Pozuelo" />
          </div>
          <div class="field">
            <label>Code</label>
            <input v-model="form.shortcode" required placeholder="2663" />
          </div>
          <div class="field">
            <label><input type="checkbox" v-model="form.is_active" /> Actif</label>
          </div>
        </div>

        <div class="field">
          <label>Boutiques</label>
          <div class="checkbox-grid" v-if="shops.length">
            <label v-for="s in shops" :key="s.id">
              <input type="checkbox" :value="s.id" v-model="form.shop_ids" />
              {{ s.name }} <span class="muted mono">({{ s.shortcode }})</span>
            </label>
          </div>
          <p v-else class="muted small">Créez d'abord au moins une boutique.</p>
        </div>

        <div class="row">
          <button class="primary" type="submit" :disabled="saving">
            {{ editing ? 'Enregistrer' : 'Créer' }}
          </button>
          <button v-if="editing" type="button" @click="form = blank()">Annuler</button>
        </div>
      </form>
    </div>

    <div class="panel">
      <table>
        <thead>
          <tr>
            <th>Nom</th>
            <th>Code</th>
            <th>Boutiques</th>
            <th>État</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="employee in employees" :key="employee.id">
            <td>{{ employee.name }}</td>
            <td class="mono">{{ employee.shortcode }}</td>
            <td class="small">
              <span v-if="!employee.shops.length" class="muted">—</span>
              <span v-else>{{ employee.shops.map((s) => s.name).join(', ') }}</span>
            </td>
            <td>
              <span class="badge" :class="employee.is_active ? 'ok' : 'muted'">
                {{ employee.is_active ? 'Actif' : 'Inactif' }}
              </span>
            </td>
            <td>
              <div class="row">
                <button class="small" @click="edit(employee)">Modifier</button>
                <button class="small danger" @click="remove(employee)">
                  Supprimer
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </template>
</template>
