<script setup lang="ts">
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Password from 'primevue/password'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSession } from '../stores/session'

const session = useSession()
const router = useRouter()
const username = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  busy.value = true
  try {
    await session.login(username.value, password.value)
    router.push('/')
  } catch (e: any) {
    error.value = e.message ?? 'Login failed'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <form class="card login-card" @submit.prevent="submit">
      <div class="brand"><i class="pi pi-database" /> SCOS MIB Creator</div>
      <p class="muted small">
        Web-based editor for SCOS-2000 / CCS5 MIB databases (telemetry &amp;
        telecommand definitions for ESA ground systems).
      </p>
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
      <div class="field-row">
        <label>Username</label>
        <InputText v-model="username" autofocus autocomplete="username" fluid />
      </div>
      <div class="field-row">
        <label>Password</label>
        <Password v-model="password" :feedback="false" toggle-mask autocomplete="current-password" fluid />
      </div>
      <Button type="submit" label="Sign in" :loading="busy" fluid />
    </form>
  </div>
</template>

<style scoped>
.login-wrap { height: 100%; display: flex; align-items: center; justify-content: center; }
.login-card { width: 380px; }
.brand { font-size: 1.2rem; font-weight: 700; display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.5rem; }
</style>
