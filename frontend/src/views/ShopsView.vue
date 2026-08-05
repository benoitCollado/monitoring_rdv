<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api } from '@/api/client'
import type { Employee, Shop } from '@/api/types'
import NoCompany from '@/components/NoCompany.vue'
import { useCompaniesStore } from '@/stores/companies'

const companies = useCompaniesStore()
const companyId = computed(() => companies.currentId)

const shops = ref<Shop[]>([])
const employees = ref<Employee[]>([])
const error = ref<string | null>(null)
const saving = ref(false)

const blank = () => ({
  id: '' as string,
  name: '',
  shortcode: '',
  is_active: true,
  employee_ids: [] as string[],
})
const form = ref(blank())
const editing = computed(() => Boolean(form.value.id))

async function load() {
  if (!companyId.value) return
  try {
    ;[shops.value, employees.value] = await Promise.all([
      api.listShops(companyId.value),
      api.listEmployees(companyId.value),
    ])
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

function edit(shop: Shop) {
  form.value = {
    id: shop.id,
    name: shop.name,
    shortcode: shop.shortcode,
    is_active: shop.is_active,
    employee_ids: shop.employees.map((e) => e.id),
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
    employee_ids: form.value.employee_ids,
  }
  try {
    if (editing.value) {
      await api.updateShop(companyId.value, form.value.id, payload)
    } else {
      await api.createShop(companyId.value, payload)
    }
    form.value = blank()
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    saving.value = false
  }
}

async function remove(shop: Shop) {
  if (!companyId.value) return
  if (
    !confirm(
      `Supprimer la boutique « ${shop.name} » ? Ses liens et leur historique seront supprimés.`,
    )
  )
    return
  try {
    await api.deleteShop(companyId.value, shop.id)
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
      <h2>Boutiques</h2>
      <span class="muted small">{{ shops.length }} boutique(s)</span>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div class="panel">
      <h3 style="margin-top: 0">
        {{ editing ? 'Modifier la boutique' : 'Nouvelle boutique' }}
      </h3>
      <form @submit.prevent="save">
        <div class="row">
          <div class="field">
            <label>Nom</label>
            <input v-model="form.name" required placeholder="Blandin & Delloye - Valencia" />
          </div>
          <div class="field">
            <label>Shortcode</label>
            <input v-model="form.shortcode" required placeholder="bdvalencia" />
          </div>
          <div class="field">
            <label>
              <input type="checkbox" v-model="form.is_active" /> Active
            </label>
          </div>
        </div>

        <div class="field">
          <label>Conseillers rattachés</label>
          <div class="checkbox-grid" v-if="employees.length">
            <label v-for="e in employees" :key="e.id">
              <input type="checkbox" :value="e.id" v-model="form.employee_ids" />
              {{ e.name }} <span class="muted mono">({{ e.shortcode }})</span>
            </label>
          </div>
          <p v-else class="muted small">
            Aucun conseiller pour l'instant — créez-les dans l'onglet Conseillers.
          </p>
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
            <th>Shortcode</th>
            <th>Conseillers</th>
            <th>État</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="shop in shops" :key="shop.id">
            <td>{{ shop.name }}</td>
            <td class="mono">{{ shop.shortcode }}</td>
            <td class="small">
              <span v-if="!shop.employees.length" class="muted">—</span>
              <span v-else>
                {{ shop.employees.map((e) => `${e.name} (${e.shortcode})`).join(', ') }}
              </span>
            </td>
            <td>
              <span class="badge" :class="shop.is_active ? 'ok' : 'muted'">
                {{ shop.is_active ? 'Active' : 'Inactive' }}
              </span>
            </td>
            <td>
              <div class="row">
                <button class="small" @click="edit(shop)">Modifier</button>
                <button class="small danger" @click="remove(shop)">Supprimer</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </template>
</template>
