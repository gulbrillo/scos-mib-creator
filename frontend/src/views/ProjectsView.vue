<script setup lang="ts">
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { get, post } from '../api'
import { useSchema } from '../stores/schema'
import type { Project } from '../types'

const router = useRouter()
const toast = useToast()
const store = useSchema()

const projects = ref<Project[]>([])
const loading = ref(true)
const showCreate = ref(false)
const name = ref('')
const description = ref('')
const profile = ref('ccs5')
const bootstrap = ref(true)
const error = ref('')

const profileOptions = computed(() =>
  Object.entries(store.schema?.profiles ?? {}).map(([value, label]) => ({ value, label })))

async function load() {
  loading.value = true
  projects.value = await get('/api/projects')
  loading.value = false
}

onMounted(async () => {
  await store.load()
  await load()
})

async function create() {
  error.value = ''
  try {
    const p = await post<Project>('/api/projects', {
      name: name.value, description: description.value,
      profile: profile.value, bootstrap: bootstrap.value,
    })
    showCreate.value = false
    toast.add({ severity: 'success', summary: `Project "${p.name}" created`, life: 3000 })
    router.push(`/project/${p.id}`)
  } catch (e: any) {
    error.value = e.message
  }
}
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <h1>Projects</h1>
      <div class="spacer" />
      <Button icon="pi pi-plus" label="New project" @click="showCreate = true; name=''; description=''; error=''" />
    </div>
    <p class="muted small">
      Each project is one MIB database. New here? Read the
      <router-link to="/help">MIB &amp; PUS guide</router-link> first — it explains
      what a MIB is and how the pieces fit together.
    </p>

    <div class="card">
      <DataTable :value="projects" :loading="loading" data-key="id" selection-mode="single"
                 @row-select="(e: any) => router.push(`/project/${e.data.id}`)">
        <Column field="name" header="Name" sortable>
          <template #body="{ data }">
            <router-link :to="`/project/${data.id}`"><b>{{ data.name }}</b></router-link>
          </template>
        </Column>
        <Column field="description" header="Description" />
        <Column field="profile" header="Export profile">
          <template #body="{ data }">
            <Tag :value="store.schema?.profiles[data.profile] ?? data.profile" severity="info" />
          </template>
        </Column>
        <Column field="total_rows" header="Records" sortable />
        <Column field="role" header="Your role" />
        <template #empty>
          <span class="muted">No projects yet — create your first MIB project.</span>
        </template>
      </DataTable>
    </div>

    <Dialog v-model:visible="showCreate" modal header="New MIB project" :style="{ width: '480px' }">
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
      <div class="field-row">
        <label>Project name <span class="req">*</span></label>
        <InputText v-model="name" placeholder="e.g. MySat XYZ Unit MIB" autofocus fluid />
      </div>
      <div class="field-row">
        <label>Description</label>
        <Textarea v-model="description" rows="2" auto-resize fluid />
      </div>
      <div class="field-row">
        <label v-tooltip.top="'Both profiles edit the same data; this only selects the default export format.'">
          Export profile
        </label>
        <Select v-model="profile" :options="profileOptions" option-label="label" option-value="value" fluid />
      </div>
      <div class="field-row" style="flex-direction: row; align-items: center;">
        <Checkbox v-model="bootstrap" binary input-id="bs" />
        <label for="bs" style="font-weight: 400;">
          Create starter content (database version record, standard PUS TC packet
          header, generic verification stages) — recommended
        </label>
      </div>
      <template #footer>
        <Button text label="Cancel" @click="showCreate = false" />
        <Button label="Create project" :disabled="!name.trim()" @click="create" />
      </template>
    </Dialog>
  </div>
</template>
