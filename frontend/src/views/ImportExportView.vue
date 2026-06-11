<script setup lang="ts">
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { postForm } from '../api'
import { useSchema } from '../stores/schema'

const route = useRoute()
const store = useSchema()
const toast = useToast()
const projectId = computed(() => Number(route.params.id))

// ---- export ----
const profile = ref(store.project?.profile ?? 'ccs5')
const includeEmpty = ref(true)
const profileOptions = computed(() =>
  Object.entries(store.schema?.profiles ?? {}).map(([value, label]) => ({ value, label })))

function download() {
  window.location.href =
    `/api/projects/${projectId.value}/export?profile=${profile.value}&include_empty=${includeEmpty.value}`
}

// ---- import ----
const file = ref<File | null>(null)
const mode = ref('replace-tables')
const dryRun = ref(true)
const result = ref<any | null>(null)
const importing = ref(false)
const modeOptions = [
  { value: 'replace-tables', label: 'Replace tables contained in the archive' },
  { value: 'replace-all', label: 'Replace the entire project content' },
  { value: 'append', label: 'Append to existing tables' },
]

function pick(e: Event) {
  file.value = (e.target as HTMLInputElement).files?.[0] ?? null
  result.value = null
}

async function doImport() {
  if (!file.value) return
  importing.value = true
  try {
    const form = new FormData()
    form.append('file', file.value)
    form.append('mode', mode.value)
    form.append('dry_run', String(dryRun.value))
    result.value = await postForm(`/api/projects/${projectId.value}/import`, form)
    if (result.value.imported) {
      toast.add({ severity: 'success', summary: 'MIB imported', life: 3000 })
      await store.loadProject(projectId.value, true)
    }
  } catch (e: any) {
    toast.add({ severity: 'error', summary: 'Import failed', detail: e.message, life: 6000 })
  } finally {
    importing.value = false
  }
}
</script>

<template>
  <div class="page">
    <h1>Import / Export</h1>

    <div class="card">
      <h2><i class="pi pi-download" /> Export MIB</h2>
      <p class="muted small">
        Generates the complete set of tab-separated <span class="mono">.dat</span> files
        as a zip archive — ready for the SIS/EGSE configuration or the MIB delivery to ESA.
      </p>
      <div class="toolbar" style="margin: 0">
        <Select v-model="profile" :options="profileOptions" option-label="label" option-value="value" />
        <div style="display: flex; align-items: center; gap: 0.4rem">
          <Checkbox v-model="includeEmpty" binary input-id="ie" />
          <label for="ie" class="small">Include empty tables (recommended — importers expect the full file set)</label>
        </div>
        <div class="spacer" />
        <Button icon="pi pi-download" label="Download MIB (zip)" @click="download" />
      </div>
    </div>

    <div class="card">
      <h2><i class="pi pi-upload" /> Import MIB</h2>
      <p class="muted small">
        Load an existing MIB (zip of .dat files) into this project — e.g. a previous
        delivery or a database exported from another tool. Unknown columns are preserved
        and re-exported untouched. Start with a dry run to see what would happen.
      </p>
      <div class="field-row">
        <label>MIB archive (.zip)</label>
        <input type="file" accept=".zip" @change="pick" />
      </div>
      <div class="field-row">
        <label>Mode</label>
        <Select v-model="mode" :options="modeOptions" option-label="label" option-value="value" />
      </div>
      <div style="display: flex; align-items: center; gap: 0.4rem; margin-bottom: 1rem">
        <Checkbox v-model="dryRun" binary input-id="dr" />
        <label for="dr" class="small">Dry run (analyse only, change nothing)</label>
      </div>
      <Button :label="dryRun ? 'Analyse archive' : 'Import now'" icon="pi pi-upload"
              :disabled="!file" :loading="importing" @click="doImport" />

      <template v-if="result">
        <Message :severity="result.imported ? 'success' : (result.dry_run ? 'info' : 'warn')"
                 :closable="false" style="margin-top: 1rem">
          <template v-if="result.imported">Imported successfully.</template>
          <template v-else-if="result.dry_run">Dry run — nothing was changed.</template>
          <template v-else>Import was not applied (see issues below).</template>
        </Message>
        <h3 style="margin-top: 1rem">Tables found</h3>
        <div class="tags">
          <Tag v-for="(n, t) in result.counts" :key="t" severity="secondary"
               :value="`${t}: ${n} rows`" />
        </div>
        <template v-if="result.issues?.length">
          <h3 style="margin-top: 1rem">Notes</h3>
          <ul class="small">
            <li v-for="(i, idx) in result.issues" :key="idx" :class="`severity-${i.severity}`">
              {{ i.message }}
            </li>
          </ul>
        </template>
      </template>
    </div>
  </div>
</template>

<style scoped>
.tags { display: flex; flex-wrap: wrap; gap: 0.4rem; }
</style>
