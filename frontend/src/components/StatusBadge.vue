<script setup lang="ts">
import { computed } from 'vue'

import type { LinkStatus } from '@/api/types'

const props = defineProps<{ status: LinkStatus }>()

const label = computed(
  () =>
    ({ ok: 'Opérationnel', broken: 'Cassé', unknown: 'Jamais vérifié' })[props.status],
)
</script>

<template>
  <span class="badge" :class="status">{{ label }}</span>
</template>
