<script setup lang="ts">
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Password from 'primevue/password'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { onMounted, ref } from 'vue'
import { del, get, patch, post } from '../api'

interface UserRow { id: number; username: string; is_admin: boolean }

const users = ref<UserRow[]>([])
const toast = useToast()
const confirm = useConfirm()

const showDialog = ref(false)
const editUser = ref<UserRow | null>(null)
const username = ref('')
const password = ref('')
const isAdmin = ref(false)
const error = ref('')

async function load() {
  users.value = await get('/api/users')
}
onMounted(load)

function openNew() {
  editUser.value = null
  username.value = ''
  password.value = ''
  isAdmin.value = false
  error.value = ''
  showDialog.value = true
}

function openEdit(u: UserRow) {
  editUser.value = u
  username.value = u.username
  password.value = ''
  isAdmin.value = u.is_admin
  error.value = ''
  showDialog.value = true
}

async function save() {
  error.value = ''
  try {
    if (editUser.value) {
      await patch(`/api/users/${editUser.value.id}`, {
        password: password.value || undefined, is_admin: isAdmin.value,
      })
    } else {
      await post('/api/users', {
        username: username.value, password: password.value, is_admin: isAdmin.value,
      })
    }
    showDialog.value = false
    toast.add({ severity: 'success', summary: 'Saved', life: 2000 })
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

function remove(u: UserRow) {
  confirm.require({
    message: `Delete user "${u.username}"?`,
    header: 'Delete user',
    acceptProps: { label: 'Delete', severity: 'danger' },
    rejectProps: { label: 'Cancel', severity: 'secondary', text: true },
    accept: async () => { await del(`/api/users/${u.id}`); await load() },
  })
}
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <h1>Users</h1>
      <div class="spacer" />
      <Button icon="pi pi-user-plus" label="New user" @click="openNew" />
    </div>
    <div class="card">
      <DataTable :value="users" size="small" selection-mode="single"
                 @row-select="(e: any) => openEdit(e.data)">
        <Column field="username" header="Username" sortable />
        <Column field="is_admin" header="Administrator">
          <template #body="{ data }">
            <i v-if="data.is_admin" class="pi pi-check" />
          </template>
        </Column>
        <Column style="width: 4rem">
          <template #body="{ data }">
            <Button text size="small" icon="pi pi-trash" severity="danger" @click.stop="remove(data)" />
          </template>
        </Column>
      </DataTable>
    </div>

    <Dialog v-model:visible="showDialog" modal
            :header="editUser ? `Edit ${editUser.username}` : 'New user'"
            :style="{ width: '420px' }">
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
      <div class="field-row" v-if="!editUser">
        <label>Username</label>
        <InputText v-model="username" fluid />
      </div>
      <div class="field-row">
        <label>{{ editUser ? 'New password (leave empty to keep)' : 'Password' }}</label>
        <Password v-model="password" :feedback="false" toggle-mask fluid />
      </div>
      <div class="field-row" style="flex-direction: row; align-items: center;">
        <Checkbox v-model="isAdmin" binary input-id="adm" />
        <label for="adm" style="font-weight: 400">Administrator (manage users, see all projects)</label>
      </div>
      <template #footer>
        <Button text label="Cancel" @click="showDialog = false" />
        <Button label="Save" @click="save" />
      </template>
    </Dialog>
  </div>
</template>
