<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useSchema } from '../stores/schema'

const props = defineProps<{ id: string }>()
const route = useRoute()
const store = useSchema()
const ready = ref(false)

const projectId = computed(() => Number(props.id))

onMounted(async () => {
  await store.load()
  await store.loadProject(projectId.value, true)
  ready.value = true
})
watch(projectId, async (id) => {
  await store.loadProject(id, true)
})

const counts = computed(() => store.project?.row_counts ?? {})

function tableCount(t: string): number {
  return counts.value[t] ?? 0
}

const wizards = [
  { to: 'wizard/packet', icon: 'pi-inbox', label: 'New TM packet' },
  { to: 'wizard/command', icon: 'pi-send', label: 'New TC command' },
  { to: 'wizard/calibration', icon: 'pi-sliders-h', label: 'New calibration' },
  { to: 'wizard/limit', icon: 'pi-exclamation-triangle', label: 'New limit check' },
]
</script>

<template>
  <div v-if="ready && store.project" class="shell">
    <aside class="sidebar">
      <div class="proj-name">
        <i class="pi pi-database" />
        <span>{{ store.project.name }}</span>
      </div>

      <router-link class="nav-item" :to="`/project/${id}`" exact-active-class="active">
        <i class="pi pi-home" /> Dashboard
      </router-link>
      <router-link class="nav-item" :to="`/project/${id}/validation`" active-class="active">
        <i class="pi pi-verified" /> Validation
      </router-link>
      <router-link class="nav-item" :to="`/project/${id}/io`" active-class="active">
        <i class="pi pi-arrow-right-arrow-left" /> Import / Export
      </router-link>
      <router-link class="nav-item" :to="`/project/${id}/settings`" active-class="active">
        <i class="pi pi-cog" /> Settings
      </router-link>

      <div class="section">Guided creation</div>
      <router-link v-for="w in wizards" :key="w.to" class="nav-item wizard"
                   :to="`/project/${id}/${w.to}`" active-class="active">
        <i :class="`pi ${w.icon}`" /> {{ w.label }}
      </router-link>

      <div class="section">MIB tables</div>
      <template v-for="dom in store.schema?.domains" :key="dom.id">
        <div class="domain" v-tooltip.right="dom.description">{{ dom.title }}</div>
        <router-link
          v-for="t in dom.tables" :key="t" class="nav-item table"
          :to="`/project/${id}/table/${t}`" active-class="active"
        >
          <span class="mono">{{ t }}</span>
          <span class="tname">{{ store.schema?.tables[t]?.title }}</span>
          <span v-if="tableCount(t)" class="count">{{ tableCount(t) }}</span>
        </router-link>
      </template>
    </aside>
    <section class="content">
      <router-view :key="route.fullPath" />
    </section>
  </div>
</template>

<style scoped>
.shell { display: flex; height: 100%; }
.sidebar {
  width: 270px;
  min-width: 270px;
  overflow-y: auto;
  background: var(--p-surface-0);
  border-right: 1px solid var(--p-surface-200);
  padding: 0.75rem 0.5rem 2rem;
}
.proj-name {
  display: flex; gap: 0.5rem; align-items: center;
  font-weight: 700; padding: 0.5rem 0.75rem 0.75rem;
}
.section {
  margin: 1rem 0.75rem 0.25rem;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--p-text-muted-color);
}
.domain {
  margin: 0.6rem 0.75rem 0.15rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--p-text-muted-color);
}
.nav-item {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.35rem 0.75rem;
  border-radius: 6px;
  color: var(--p-text-color);
  font-size: 0.9rem;
}
.nav-item:hover { background: var(--p-surface-100); }
.nav-item.active { background: var(--p-primary-50); color: var(--p-primary-700); font-weight: 600; }
.nav-item.table .mono { font-size: 0.78rem; width: 2.6rem; color: var(--p-text-muted-color); }
.nav-item.table .tname { flex: 1; font-size: 0.85rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.nav-item.table .count {
  font-size: 0.72rem;
  background: var(--p-surface-200);
  border-radius: 8px;
  padding: 0 0.4rem;
}
.content { flex: 1; overflow-y: auto; }
</style>
