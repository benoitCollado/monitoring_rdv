<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api } from '@/api/client'
import type { Company } from '@/api/types'
import { useCompaniesStore } from '@/stores/companies'

const store = useCompaniesStore()
const error = ref<string | null>(null)
const saving = ref(false)
const preview = ref<string[]>([])

const blank = () => ({
  id: '',
  name: '',
  base_url: '',
  shop_link_template: 'guichet_{shop}_{type}',
  employee_link_template: '{shop}_{type}_{employee}',
  error_patterns_text: 'page introuvable\npage not found\n404 not found',
  check_hour: 6,
  check_minute: 0,
  timezone: 'Europe/Paris',
  is_active: true,
})
const form = ref(blank())
const editing = computed(() => Boolean(form.value.id))

function edit(company: Company) {
  form.value = {
    id: company.id,
    name: company.name,
    base_url: company.base_url,
    shop_link_template: company.shop_link_template,
    employee_link_template: company.employee_link_template,
    error_patterns_text: company.error_patterns.join('\n'),
    check_hour: company.check_hour,
    check_minute: company.check_minute,
    timezone: company.timezone,
    is_active: company.is_active,
  }
  preview.value = []
  loadPreview(company.id)
}

async function loadPreview(companyId: string) {
  try {
    preview.value = await api.previewLinks(companyId, 8)
  } catch {
    preview.value = []
  }
}

async function save() {
  saving.value = true
  error.value = null
  const payload = {
    name: form.value.name,
    base_url: form.value.base_url,
    shop_link_template: form.value.shop_link_template,
    employee_link_template: form.value.employee_link_template,
    error_patterns: form.value.error_patterns_text
      .split('\n')
      .map((p) => p.trim())
      .filter(Boolean),
    check_hour: Number(form.value.check_hour),
    check_minute: Number(form.value.check_minute),
    timezone: form.value.timezone,
    is_active: form.value.is_active,
  }
  try {
    if (editing.value) {
      await api.updateCompany(form.value.id, payload)
    } else {
      const created = await api.createCompany(payload)
      store.select(created.id)
    }
    form.value = blank()
    preview.value = []
    await store.load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    saving.value = false
  }
}

async function remove(company: Company) {
  if (
    !confirm(
      `Supprimer « ${company.name} » ? Boutiques, conseillers, liens et historique seront supprimés.`,
    )
  )
    return
  try {
    await api.deleteCompany(company.id)
    if (store.currentId === company.id) store.select(null)
    await store.load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
}

onMounted(() => {
  if (!store.companies.length) store.load()
})
</script>

<template>
  <div class="page-header"><h2>Entreprises</h2></div>

  <div v-if="error" class="error">{{ error }}</div>

  <div class="panel">
    <h3 style="margin-top: 0">
      {{ editing ? `Modifier « ${form.name} »` : 'Nouvelle entreprise' }}
    </h3>
    <form @submit.prevent="save">
      <div class="row">
        <div class="field">
          <label>Nom</label>
          <input v-model="form.name" required placeholder="Blandin & Delloye" />
        </div>
        <div class="field" style="flex: 1; min-width: 320px">
          <label>URL de base (le shortcode est concaténé à la fin)</label>
          <input
            v-model="form.base_url"
            required
            style="width: 100%"
            placeholder="https://mon-odoo.example/r/"
          />
        </div>
      </div>

      <div class="row">
        <div class="field">
          <label>Modèle « boutique seule »</label>
          <input v-model="form.shop_link_template" required style="width: 240px" />
        </div>
        <div class="field">
          <label>Modèle « avec conseiller »</label>
          <input v-model="form.employee_link_template" required style="width: 240px" />
        </div>
        <div class="field muted small" style="max-width: 320px">
          Variables disponibles : <code>{shop}</code>, <code>{type}</code>,
          <code>{employee}</code>. Exemple attendu :
          <code>guichet_bdvalencia_3480</code> et <code>bdvalencia_3480_2663</code>.
        </div>
      </div>

      <div class="row">
        <div class="field">
          <label>Heure de vérification</label>
          <input type="number" v-model="form.check_hour" min="0" max="23" style="width: 80px" />
        </div>
        <div class="field">
          <label>Minute</label>
          <input
            type="number"
            v-model="form.check_minute"
            min="0"
            max="59"
            style="width: 80px"
          />
        </div>
        <div class="field">
          <label>Fuseau horaire</label>
          <input v-model="form.timezone" style="width: 180px" />
        </div>
        <div class="field">
          <label><input type="checkbox" v-model="form.is_active" /> Active (cron)</label>
        </div>
      </div>

      <div class="field" style="max-width: 480px">
        <label>
          Motifs de page d'erreur (un par ligne) — un lien qui répond 200 mais dont la
          page contient l'un de ces textes est considéré cassé
        </label>
        <textarea v-model="form.error_patterns_text" rows="4" style="width: 100%"></textarea>
      </div>

      <div v-if="preview.length" class="field">
        <label>Aperçu des liens générés</label>
        <ul class="mono small" style="margin: 0; padding-left: 18px">
          <li v-for="url in preview" :key="url">{{ url }}</li>
        </ul>
      </div>

      <div class="row">
        <button class="primary" type="submit" :disabled="saving">
          {{ editing ? 'Enregistrer' : 'Créer' }}
        </button>
        <button
          v-if="editing"
          type="button"
          @click="
            () => {
              form = blank()
              preview = []
            }
          "
        >
          Annuler
        </button>
      </div>
    </form>
  </div>

  <div class="panel">
    <table>
      <thead>
        <tr>
          <th>Nom</th>
          <th>URL de base</th>
          <th>Cron</th>
          <th>État</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="company in store.companies" :key="company.id">
          <td>
            {{ company.name }}
            <span v-if="company.id === store.currentId" class="badge muted">
              sélectionnée
            </span>
          </td>
          <td class="mono small">{{ company.base_url }}</td>
          <td class="small">
            {{ String(company.check_hour).padStart(2, '0') }}:{{
              String(company.check_minute).padStart(2, '0')
            }}
            <span class="muted">({{ company.timezone }})</span>
          </td>
          <td>
            <span class="badge" :class="company.is_active ? 'ok' : 'muted'">
              {{ company.is_active ? 'Active' : 'Inactive' }}
            </span>
          </td>
          <td>
            <div class="row">
              <button class="small" @click="store.select(company.id)">
                Sélectionner
              </button>
              <button class="small" @click="edit(company)">Modifier</button>
              <button class="small danger" @click="remove(company)">Supprimer</button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
