<script setup lang="ts">
import Drawer from 'primevue/drawer'
import type { HelpTopic } from '../help/wizardHelp'

defineProps<{ topic: HelpTopic | null }>()
const visible = defineModel<boolean>('visible')
</script>

<template>
  <Drawer v-model:visible="visible" position="right" :style="{ width: '460px' }"
          :header="topic?.title ?? 'Help'">
    <template v-if="topic">
      <p v-for="(p, i) in topic.body" :key="i" style="white-space: pre-line">{{ p }}</p>
      <div v-if="topic.example" class="help-text" style="margin-top: 0.75rem">
        <b>Example:</b> {{ topic.example }}
      </div>
      <p v-if="topic.ref" class="muted small" style="margin-top: 0.75rem">
        <i class="pi pi-book" /> {{ topic.ref }}
      </p>
    </template>
  </Drawer>
</template>
