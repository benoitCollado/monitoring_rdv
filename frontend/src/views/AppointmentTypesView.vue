<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api } from '@/api/client'
import type { AppointmentType } from '@/api/types'
import NoCompany from '@/components/NoCompany.vue'
import { useCompaniesStore } from '@/stores/companies'

const companies = useCompaniesStore()
const companyId = computed(() => companies.currentId)

const types = ref<AppointmentType[]>([])
const error = ref<string | null>(null)
const saving = ref(false)

const blank = () => ({ id: '' as string, name: '', shortcode: '', is_active: true })
const form = ref(blank())
const editing = computed(() => Boolean(form.value.id))

async function load() {
  if (!companyId.value) return
  try {
    types.value = await api.listAppointmentTypes(companyId.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

function edit(type: AppointmentType) {
  form.value = {
    id: type.id,
    name: type.name,
    shortcode: type.shortcode,
    is_active: type.is_active,
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
  }
  try {
    if (editing.value) {
      await api.updateAppointmentType(companyId.value, form.value.id, payload)
    } else {
      await api.createAppointmentType(companyId.value, payload)
    }
    form.value = blank()
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    saving.value = false
  }
}

async function remove(type: AppointmentType) {
  if (!companyId.value) return
  if (!confirm(`Supprimer le type « ${type.name} » et ses liens ?`)) return
  try {
    await api.deleteAppointmentType(companyId.value, type.id)
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
      <h2>Types de RDV</h2>
      <span class="muted small">{{ types.length }} type(s)</span>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <div class="panel">
      <h3 style="margin-top: 0">
        {{ editing ? 'Modifier le type' : 'Nouveau type de RDV' }}
      </h3>
      <form @submit.prevent="save">
        <div class="row">
          <div class="field">
            <label>Nom</label>
            <input v-model="form.name" required placeholder="Atelier Découverte" />
          </div>
          <div class="field">
            <label>Code RDV</label>
            <input v-model="form.shortcode" required placeholder="3480" />
          </div>
          <div class="field">
            <label><input type="checkbox" v-model="form.is_active" /> Actif</label>
          </div>
          <div class="field">
            <button class="primary" type="submit" :disabled="saving">
              {{ editing ? 'Enregistrer' : 'Créer' }}
            </button>
          </div>
          <div class="field" v-if="editing">
            <button type="button" @click="form = blank()">Annuler</button>
          </div>
        </div>
      </form>
    </div>

    <div class="panel">
      <table>
        <thead>
          <tr>
            <th>Nom</th>
            <th>Code</th>
            <th>État</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="type in types" :key="type.id">
            <td>{{ type.name }}</td>
            <td class="mono">{{ type.shortcode }}</td>
            <td>
              <span class="badge" :class="type.is_active ? 'ok' : 'muted'">
                {{ type.is_active ? 'Actif' : 'Inactif' }}
              </span>
            </td>
            <td>
              <div class="row">
                <button class="small" @click="edit(type)">Modifier</button>
                <button class="small danger" @click="remove(type)">Supprimer</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </template>
</template>
