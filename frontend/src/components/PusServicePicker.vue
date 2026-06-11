<script setup lang="ts">
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import { computed, ref } from 'vue'
import { useSchema } from '../stores/schema'

const props = defineProps<{ side: 'tm' | 'tc'; iconOnly?: boolean }>()
const emit = defineEmits<{
  (e: 'select', v: { type: number; stype: number; label: string }): void
}>()

const store = useSchema()
const visible = ref(false)
const selected = ref<string | null>(null)

const options = computed(() =>
  store.pusServices.flatMap((s) =>
    (props.side === 'tm' ? s.tm : s.tc).map((st) => ({
      value: `${s.service}/${st.subtype}`,
      label: `(${s.service},${st.subtype}) ${s.name} — ${st.name}`,
      service: s.service, subtype: st.subtype,
      help: s.help, note: (st as any).note ?? '',
    }))))

const current = computed(() => options.value.find((o) => o.value === selected.value))

function apply() {
  if (!current.value) return
  emit('select', {
    type: current.value.service, stype: current.value.subtype, label: current.value.label,
  })
  visible.value = false
}
</script>

<template>
  <Button
    text size="small" icon="pi pi-sparkles" :label="iconOnly ? undefined : 'PUS picker'"
    v-tooltip.top="'PUS picker — choose the service/subtype from the catalog; OK fills the fields'"
    @click="visible = true"
  />
  <Dialog v-model:visible="visible" modal header="Choose a PUS service" :style="{ width: '600px' }">
    <div class="field-row">
      <label>{{ side === 'tm' ? 'What kind of report is it?' : 'What kind of request is it?' }}</label>
      <Select v-model="selected" :options="options" option-label="label" option-value="value"
              filter placeholder="Select a service/subtype…" fluid />
    </div>
    <template v-if="current">
      <p class="help-text">{{ current.help }}</p>
      <p v-if="current.note" class="muted small"><i class="pi pi-lightbulb" /> {{ current.note }}</p>
    </template>
    <template #footer>
      <Button text label="Cancel" @click="visible = false" />
      <Button label="Use this service" :disabled="!current" @click="apply" />
    </template>
  </Dialog>
</template>
