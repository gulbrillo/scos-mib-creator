<script setup lang="ts">
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import { computed, ref, watch } from 'vue'
import { useSchema } from '../stores/schema'
import type { PtcEntry } from '../types'

const props = defineProps<{ side: 'tm' | 'tc'; ptc?: number | null; pfc?: number | null }>()
const emit = defineEmits<{ (e: 'select', v: { ptc: number; pfc: number; label: string }): void }>()

const store = useSchema()
const visible = ref(false)
const selectedPtc = ref<PtcEntry | null>(null)
const selectedPfc = ref<number | null>(null)
const customPfc = ref<number>(8)

const catalog = computed(() => store.ptcCatalog.filter((e) => e[props.side]))

watch(visible, (v) => {
  if (v && props.ptc != null) {
    selectedPtc.value = catalog.value.find((e) => e.ptc === props.ptc) ?? null
    if (selectedPtc.value?.pfc) selectedPfc.value = props.pfc ?? null
    else customPfc.value = props.pfc ?? 8
  }
})

const pfcOptions = computed(() =>
  (selectedPtc.value?.pfc ?? []).map((v) => ({ value: v.pfc, label: `PFC ${v.pfc} — ${v.label}` })))

function pickLabel(): string {
  const t = selectedPtc.value!
  if (t.pfc) {
    const v = t.pfc.find((x) => x.pfc === selectedPfc.value)
    return `${t.name}, ${v?.label ?? ''}`
  }
  return `${t.name} (PFC ${customPfc.value})`
}

function apply() {
  if (!selectedPtc.value) return
  const pfc = selectedPtc.value.pfc ? selectedPfc.value : customPfc.value
  if (pfc == null) return
  emit('select', { ptc: selectedPtc.value.ptc, pfc, label: pickLabel() })
  visible.value = false
}
</script>

<template>
  <Button
    text size="small" icon="pi pi-sparkles" label="Type picker"
    v-tooltip.top="'Pick the PTC/PFC pair from a plain-language list'"
    @click="visible = true"
  />
  <Dialog v-model:visible="visible" modal header="Choose a parameter type" :style="{ width: '560px' }">
    <div class="field-row">
      <label>What kind of value is it?</label>
      <Select
        v-model="selectedPtc"
        :options="catalog"
        :option-label="(e: PtcEntry) => `PTC ${e.ptc} — ${e.name}`"
        placeholder="Select a type…"
        fluid
      />
    </div>
    <p v-if="selectedPtc" class="help-text">{{ selectedPtc.help }}</p>
    <div v-if="selectedPtc?.pfc" class="field-row">
      <label>Size / variant</label>
      <Select
        v-model="selectedPfc"
        :options="pfcOptions"
        option-label="label"
        option-value="value"
        placeholder="Select a size…"
        filter
        fluid
      />
    </div>
    <div v-else-if="selectedPtc" class="field-row">
      <label>{{ selectedPtc.pfc_rule?.label }}</label>
      <InputNumber
        v-model="customPfc"
        :min="selectedPtc.pfc_rule?.min"
        :max="selectedPtc.pfc_rule?.max"
        show-buttons
        fluid
      />
    </div>
    <template #footer>
      <Button text label="Cancel" @click="visible = false" />
      <Button label="Use this type" :disabled="!selectedPtc || (selectedPtc.pfc != null && selectedPfc == null)" @click="apply" />
    </template>
  </Dialog>
</template>
