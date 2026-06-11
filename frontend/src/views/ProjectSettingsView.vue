<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { del, patch, post } from '../api'
import { useSchema } from '../stores/schema'

const route = useRoute()
const router = useRouter()
const store = useSchema()
const toast = useToast()
const confirm = useConfirm()
const projectId = computed(() => Number(route.params.id))

const name = ref('')
const description = ref('')
const profile = ref('ccs5')
const error = ref('')
const isOwner = computed(() => store.project?.role === 'owner')

const newMember = ref('')
const newRole = ref('editor')
const roleOptions = [
  { value: 'owner', label: 'Owner (manage project & members)' },
  { value: 'editor', label: 'Editor (edit MIB content)' },
  { value: 'viewer', label: 'Viewer (read-only)' },
]
const profileOptions = computed(() =>
  Object.entries(store.schema?.profiles ?? {}).map(([value, label]) => ({ value, label })))

onMounted(() => {
  name.value = store.project?.name ?? ''
  description.value = store.project?.description ?? ''
  profile.value = store.project?.profile ?? 'ccs5'
})

async function save() {
  error.value = ''
  try {
    await patch(`/api/projects/${projectId.value}`,
      { name: name.value, description: description.value, profile: profile.value })
    await store.loadProject(projectId.value, true)
    toast.add({ severity: 'success', summary: 'Project updated', life: 2000 })
  } catch (e: any) {
    error.value = e.message
  }
}

async function addMember() {
  error.value = ''
  try {
    await post(`/api/projects/${projectId.value}/members`,
      { username: newMember.value, role: newRole.value })
    newMember.value = ''
    await store.loadProject(projectId.value, true)
  } catch (e: any) {
    error.value = e.message
  }
}

async function removeMember(userId: number) {
  await del(`/api/projects/${projectId.value}/members/${userId}`)
  await store.loadProject(projectId.value, true)
}

function deleteProject() {
  confirm.require({
    message: `Delete project "${store.project?.name}" and ALL its MIB content? This cannot be undone.`,
    header: 'Delete project',
    icon: 'pi pi-trash',
    acceptProps: { label: 'Delete project', severity: 'danger' },
    rejectProps: { label: 'Cancel', severity: 'secondary', text: true },
    accept: async () => {
      await del(`/api/projects/${projectId.value}`)
      router.push('/')
    },
  })
}
</script>

<template>
  <div class="page" v-if="store.project">
    <h1>Project settings</h1>
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <div class="card">
      <h2>General</h2>
      <div class="field-row">
        <label>Name</label>
        <InputText v-model="name" :disabled="!isOwner" fluid />
      </div>
      <div class="field-row">
        <label>Description</label>
        <Textarea v-model="description" rows="2" :disabled="!isOwner" auto-resize fluid />
      </div>
      <div class="field-row">
        <label v-tooltip.top="'Selects which columns are exported and how strictly field lengths are checked.'">
          Export profile
        </label>
        <Select v-model="profile" :options="profileOptions" option-label="label"
                option-value="value" :disabled="!isOwner" fluid />
      </div>
      <Button v-if="isOwner" label="Save" icon="pi pi-check" @click="save" />
    </div>

    <div class="card">
      <h2>Members</h2>
      <DataTable :value="store.project.members" size="small">
        <Column field="username" header="User" />
        <Column field="role" header="Role" />
        <Column v-if="isOwner" style="width: 4rem">
          <template #body="{ data }">
            <Button text size="small" icon="pi pi-trash" severity="danger"
                    @click="removeMember(data.user_id)" />
          </template>
        </Column>
      </DataTable>
      <div v-if="isOwner" class="toolbar" style="margin-top: 1rem">
        <InputText v-model="newMember" placeholder="Username" size="small" />
        <Select v-model="newRole" :options="roleOptions" option-label="label"
                option-value="value" size="small" />
        <Button size="small" icon="pi pi-user-plus" label="Add member"
                :disabled="!newMember.trim()" @click="addMember" />
      </div>
      <p class="muted small">Users are created by an administrator on the Users page.</p>
    </div>

    <div class="card" v-if="isOwner">
      <h2>Danger zone</h2>
      <Button severity="danger" outlined icon="pi pi-trash" label="Delete project"
              @click="deleteProject" />
    </div>
  </div>
</template>
