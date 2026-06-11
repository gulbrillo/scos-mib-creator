<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Tag from 'primevue/tag'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { post } from '../api'
import type { Finding } from '../types'

const route = useRoute()
const router = useRouter()
const projectId = computed(() => Number(route.params.id))

const findings = ref<Finding[]>([])
const summary = ref({ error: 0, warning: 0, info: 0 })
const loading = ref(false)

async function run() {
  loading.value = true
  const res = await post<{ summary: any; findings: Finding[] }>(
    `/api/projects/${projectId.value}/validate`)
  findings.value = res.findings
  summary.value = res.summary
  loading.value = false
}
onMounted(run)

const sevMap: Record<string, string> = { error: 'danger', warning: 'warn', info: 'secondary' }

function goTo(f: Finding) {
  if (f.table) router.push(`/project/${projectId.value}/table/${f.table}`)
}
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <h1>Validation</h1>
      <Tag :severity="summary.error ? 'danger' : 'success'" :value="`${summary.error} errors`" />
      <Tag severity="warn" :value="`${summary.warning} warnings`" />
      <Tag severity="secondary" :value="`${summary.info} hints`" />
      <div class="spacer" />
      <Button icon="pi pi-refresh" label="Re-validate" :loading="loading" @click="run" />
    </div>
    <p class="muted small">
      Errors must be fixed before the MIB can be imported by SCOS-2000/CCS5.
      Warnings are tolerated by some systems but should be reviewed before a
      delivery to ESA. Click a finding to open the affected table.
    </p>

    <div class="card">
      <DataTable :value="findings" :loading="loading" size="small" paginator :rows="50"
                 selection-mode="single" @row-select="(e: any) => goTo(e.data)" striped-rows>
        <Column header="Severity" style="width: 7rem">
          <template #body="{ data }">
            <Tag :severity="sevMap[data.severity]" :value="data.severity" />
          </template>
        </Column>
        <Column field="table" header="Table" style="width: 5rem">
          <template #body="{ data }"><span class="mono">{{ data.table }}</span></template>
        </Column>
        <Column field="row_key" header="Record" style="width: 11rem">
          <template #body="{ data }">
            <span class="mono small">{{ data.row_key || (data.row != null ? `row ${data.row + 1}` : '') }}</span>
          </template>
        </Column>
        <Column field="column" header="Field" style="width: 9rem">
          <template #body="{ data }"><span class="mono small">{{ data.column }}</span></template>
        </Column>
        <Column header="Problem & how to fix it">
          <template #body="{ data }">
            <div>{{ data.message }}</div>
            <div v-if="data.hint" class="muted small"><i class="pi pi-lightbulb" /> {{ data.hint }}</div>
          </template>
        </Column>
        <template #empty>
          <span class="muted">
            {{ loading ? 'Validating…' : 'No findings — the MIB is consistent. 🎉' }}
          </span>
        </template>
      </DataTable>
    </div>
  </div>
</template>
