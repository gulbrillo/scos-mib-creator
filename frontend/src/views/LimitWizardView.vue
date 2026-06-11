<script setup lang="ts">
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import { useToast } from 'primevue/usetoast'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { get, post } from '../api'
import type { MibRow } from '../types'
import { useSchema } from '../stores/schema'

const route = useRoute()
const router = useRouter()
const store = useSchema()
const toast = useToast()
const projectId = computed(() => Number(route.params.id))

const param = ref('')
const nbchck = ref(1)
const inter = ref('C')
const codin = ref('I')
const checks = ref<{ type: string; low: string; high: string }[]>(
  [{ type: 'S', low: '', high: '' }])
const error = ref('')
const busy = ref(false)

const pcfRows = ref<MibRow[]>([])
onMounted(async () => {
  pcfRows.value = await get(`/api/projects/${projectId.value}/tables/pcf/rows`)
})
const paramOptions = computed(() => pcfRows.value.map((r) => ({
  value: String(r.data.PCF_NAME),
  label: `${r.data.PCF_NAME} — ${r.data.PCF_DESCR ?? ''}`,
})))

const interOptions = [
  { value: 'C', label: 'Calibrated — limits are engineering values / state texts' },
  { value: 'U', label: 'Uncalibrated — limits are raw values' },
]
const codinOptions = [
  { value: 'I', label: 'Integer limit values' },
  { value: 'R', label: 'Real limit values' },
  { value: 'A', label: 'State text (for status parameters)' },
]
const typeOptions = [
  { value: 'S', label: 'Soft limit / expected state (warning)' },
  { value: 'H', label: 'Hard limit (alarm)' },
  { value: 'D', label: 'Delta check (rate of change)' },
  { value: 'E', label: 'Event only' },
]

async function submit() {
  error.value = ''
  busy.value = true
  try {
    await post(`/api/projects/${projectId.value}/wizards/limit`, {
      param: param.value, nbchck: nbchck.value, inter: inter.value, codin: codin.value,
      checks: checks.value.map((c) => ({ type: c.type, low: c.low, high: c.high })),
    })
    toast.add({ severity: 'success', summary: `Limit checks created for ${param.value}`, life: 4000 })
    await store.loadProject(projectId.value, true)
    router.push(`/project/${projectId.value}/table/ocp`)
  } catch (e: any) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page">
    <h1><i class="pi pi-exclamation-triangle" /> New limit check</h1>
    <p class="muted small">
      Defines ground-side limit monitoring for a TM parameter (ocf + ocp records):
      the EGSE/control system flags the parameter yellow (soft) or red (hard) when a
      limit is violated. For status parameters, define the expected state instead.
    </p>
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <div class="card">
      <div class="grid-2">
        <div class="field-row">
          <label>Parameter <span class="req">*</span></label>
          <Select v-model="param" :options="paramOptions" option-label="label"
                  option-value="value" filter placeholder="Select a TM parameter…" fluid />
        </div>
        <div class="field-row">
          <label v-tooltip.top="'Number of consecutive violating samples before the alarm is raised; >1 filters noise.'">
            Samples before alarm
          </label>
          <InputNumber v-model="nbchck" :min="1" :max="99" show-buttons fluid />
        </div>
        <div class="field-row">
          <label>Limit interpretation</label>
          <Select v-model="inter" :options="interOptions" option-label="label" option-value="value" fluid />
        </div>
        <div class="field-row">
          <label>Limit value format</label>
          <Select v-model="codin" :options="codinOptions" option-label="label" option-value="value" fluid />
        </div>
      </div>
    </div>

    <div class="card">
      <h2>Checks</h2>
      <p class="muted small">
        Typical setup: one soft limit (operating range) and one hard limit (safety range).
        For status parameters one soft check with the expected state in "low".
      </p>
      <div v-for="(c, i) in checks" :key="i" class="toolbar" style="margin-bottom: 0.4rem">
        <Select v-model="c.type" :options="typeOptions" option-label="label"
                option-value="value" size="small" style="width: 18rem" />
        <InputText v-model="c.low" placeholder="low limit / expected state" size="small" style="width: 12rem" />
        <InputText v-model="c.high" placeholder="high limit" size="small" style="width: 12rem" />
        <Button text size="small" icon="pi pi-trash" severity="danger" @click="checks.splice(i, 1)" />
      </div>
      <Button size="small" outlined icon="pi pi-plus" label="Add check"
              @click="checks.push({ type: 'H', low: '', high: '' })" />
    </div>

    <div class="toolbar">
      <div class="spacer" />
      <Button label="Create limit checks" icon="pi pi-check" :loading="busy"
              :disabled="!param || !checks.length" @click="submit" />
    </div>
  </div>
</template>
