<script setup lang="ts">
import Drawer from 'primevue/drawer'
import { useRoute } from 'vue-router'
import type { HelpTopic } from '../help/wizardHelp'

defineProps<{ topic: HelpTopic | null }>()
const visible = defineModel<boolean>('visible')
const route = useRoute()

function resolve(to: string): string {
  return to.replace('{id}', String(route.params.id ?? ''))
}
</script>

<template>
  <Drawer v-model:visible="visible" position="right" :style="{ width: '460px' }"
          :header="topic?.title ?? 'Help'">
    <template v-if="topic">
      <p v-for="(p, i) in topic.body" :key="i" style="white-space: pre-line">{{ p }}</p>
      <div v-if="topic.example" class="help-text" style="margin-top: 0.75rem">
        <b>Example:</b> {{ topic.example }}
      </div>
      <div v-if="topic.links?.length" style="margin-top: 0.75rem">
        <div v-for="l in topic.links" :key="l.to" style="margin-bottom: 0.35rem">
          <router-link :to="resolve(l.to)" @click="visible = false">
            <i class="pi pi-arrow-right" style="font-size: 0.75rem" /> {{ l.label }}
          </router-link>
        </div>
      </div>
      <p v-if="topic.ref" class="muted small" style="margin-top: 0.75rem">
        <i class="pi pi-book" /> {{ topic.ref }}
      </p>
    </template>
  </Drawer>
</template>
