<script setup lang="ts">
import Button from 'primevue/button'
import ConfirmDialog from 'primevue/confirmdialog'
import Toast from 'primevue/toast'
import { useRouter } from 'vue-router'
import { useSession } from './stores/session'

const session = useSession()
const router = useRouter()

async function logout() {
  await session.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-root">
    <header v-if="session.user" class="app-header">
      <router-link to="/" class="brand">
        <i class="pi pi-database" />
        <span>SCOS MIB Creator</span>
      </router-link>
      <nav>
        <router-link to="/">Projects</router-link>
        <router-link to="/help">MIB &amp; PUS guide</router-link>
        <router-link v-if="session.user.is_admin" to="/users">Users</router-link>
      </nav>
      <div class="spacer" />
      <span class="muted small">{{ session.user.username }}</span>
      <Button text size="small" icon="pi pi-sign-out" label="Sign out" @click="logout" />
    </header>
    <main>
      <router-view />
    </main>
    <Toast position="bottom-right" />
    <ConfirmDialog />
  </div>
</template>

<style scoped>
.app-root { height: 100%; display: flex; flex-direction: column; }
.app-header {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 0.5rem 1.25rem;
  background: var(--p-surface-0);
  border-bottom: 1px solid var(--p-surface-200);
}
.brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 700;
  color: var(--p-text-color);
}
nav { display: flex; gap: 1rem; }
nav a { color: var(--p-text-muted-color); font-size: 0.92rem; }
nav a.router-link-active { color: var(--p-primary-color); font-weight: 600; }
.spacer { flex: 1; }
main { flex: 1; overflow: auto; }
</style>
