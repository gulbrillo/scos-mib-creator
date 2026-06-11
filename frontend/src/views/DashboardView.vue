<script setup lang="ts">
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { post } from '../api'
import { useSchema } from '../stores/schema'

const route = useRoute()
const store = useSchema()
const projectId = computed(() => Number(route.params.id))
const summary = ref<{ error: number; warning: number; info: number } | null>(null)

onMounted(async () => {
  const v = await post<{ summary: any }>(`/api/projects/${projectId.value}/validate`)
  summary.value = v.summary
})

const counts = computed(() => store.project?.row_counts ?? {})
const c = (t: string) => counts.value[t] ?? 0

const steps = computed(() => [
  {
    label: 'Project basics: database version record (vdf)',
    done: c('vdf') > 0,
    to: `/project/${projectId.value}/table/vdf`,
    hint: 'One record naming this database version. Created automatically with starter content.',
  },
  {
    label: 'Define your TM parameters (pcf)',
    done: c('pcf') > 0,
    to: `/project/${projectId.value}/table/pcf`,
    hint: 'Every value your unit reports: voltages, temperatures, modes, counters.',
  },
  {
    label: 'Build your first TM packet (wizard)',
    done: c('pid') > 0,
    to: `/project/${projectId.value}/wizard/packet`,
    hint: 'The packet wizard creates pid/pic/tpcf/plf records together and computes all offsets.',
  },
  {
    label: 'Add calibrations for status & analog parameters',
    done: c('txf') + c('caf') + c('mcf') + c('lgf') > 0,
    to: `/project/${projectId.value}/wizard/calibration`,
    hint: 'So operators see "ON/OFF" and volts instead of raw numbers.',
  },
  {
    label: 'Define your TC commands (wizard)',
    done: c('ccf') > 0,
    to: `/project/${projectId.value}/wizard/command`,
    hint: 'The command wizard creates ccf/cpc/cdf and verification entries together.',
  },
  {
    label: 'Add limit checks for safety-relevant parameters',
    done: c('ocf') > 0,
    to: `/project/${projectId.value}/wizard/limit`,
    hint: 'Yellow/red limits so the EGSE flags out-of-range housekeeping immediately.',
  },
  {
    label: 'Validate and export the MIB',
    done: (summary.value?.error ?? 1) === 0 && c('pid') > 0,
    to: `/project/${projectId.value}/validation`,
    hint: 'Fix all errors, then download the .dat file set from Import/Export.',
  },
])
</script>

<template>
  <div class="page" v-if="store.project">
    <div class="toolbar">
      <div>
        <h1>{{ store.project.name }}</h1>
        <span class="muted small">{{ store.project.description || 'MIB database project' }}</span>
      </div>
      <div class="spacer" />
      <Tag :value="store.schema?.profiles[store.project.profile]" severity="info" />
    </div>

    <div class="card" v-if="summary">
      <h2>Validation status</h2>
      <div class="status-row">
        <Tag :severity="summary.error ? 'danger' : 'success'"
             :value="`${summary.error} error${summary.error === 1 ? '' : 's'}`" />
        <Tag :severity="summary.warning ? 'warn' : 'secondary'"
             :value="`${summary.warning} warning${summary.warning === 1 ? '' : 's'}`" />
        <Tag severity="secondary" :value="`${summary.info} hints`" />
        <router-link :to="`/project/${projectId}/validation`">View details</router-link>
        <span class="spacer" />
        <span class="muted small">{{ store.project.total_rows }} records in
          {{ Object.keys(store.project.row_counts).length }} tables</span>
      </div>
    </div>

    <div class="card">
      <h2>Getting started checklist</h2>
      <p class="muted small">
        A typical unit-level MIB is built in this order. Each step links to the right
        editor or wizard; you can revisit any step at any time.
      </p>
      <div v-for="(s, i) in steps" :key="i" class="step" :class="{ done: s.done }">
        <i :class="s.done ? 'pi pi-check-circle' : 'pi pi-circle'" />
        <div class="step-body">
          <router-link :to="s.to">{{ i + 1 }}. {{ s.label }}</router-link>
          <div class="muted small">{{ s.hint }}</div>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>Quick actions</h2>
      <div class="toolbar" style="margin: 0">
        <router-link :to="`/project/${projectId}/wizard/packet`">
          <Button icon="pi pi-inbox" label="New TM packet" outlined />
        </router-link>
        <router-link :to="`/project/${projectId}/wizard/command`">
          <Button icon="pi pi-send" label="New TC command" outlined />
        </router-link>
        <router-link :to="`/project/${projectId}/io`">
          <Button icon="pi pi-download" label="Export MIB" outlined />
        </router-link>
        <router-link to="/help">
          <Button icon="pi pi-book" label="MIB & PUS guide" outlined severity="secondary" />
        </router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.status-row { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
.step { display: flex; gap: 0.7rem; padding: 0.5rem 0; align-items: flex-start; }
.step i { margin-top: 0.2rem; color: var(--p-text-muted-color); }
.step.done i { color: var(--p-green-500); }
.step.done a { color: var(--p-text-muted-color); }
</style>
