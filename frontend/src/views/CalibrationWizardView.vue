<script setup lang="ts">
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import { useToast } from 'primevue/usetoast'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { get, post } from '../api'
import type { MibRow } from '../types'
import { useSchema } from '../stores/schema'

const route = useRoute()
const router = useRouter()
const store = useSchema()
const toast = useToast()
const projectId = computed(() => Number(route.params.id))

const kindOptions = [
  { value: 'txf', label: 'TM status texts (txf/txp) — e.g. 0=OFF, 1=ON', target: 'pcf' },
  { value: 'caf', label: 'TM numeric curve (caf/cap) — point-pair interpolation', target: 'pcf' },
  { value: 'mcf', label: 'TM polynomial (mcf) — eng = A0 + A1·raw + …', target: 'pcf' },
  { value: 'lgf', label: 'TM logarithmic (lgf) — thermistor style', target: 'pcf' },
  { value: 'paf', label: 'TC alias set (paf/pas) — operator picks ON/OFF', target: 'cpc' },
  { value: 'cca', label: 'TC numeric de-calibration (cca/ccs) — eng → raw', target: 'cpc' },
  { value: 'prf', label: 'TC range set (prf/prv) — allowed value ranges', target: 'cpc' },
]
const kind = ref('txf')
const ident = ref('')
const descrText = ref('')
const unit = ref('')
const engfmt = ref('R')
const rawfmt = ref('U')
const points = ref<{ raw: string; eng: string }[]>([{ raw: '', eng: '' }, { raw: '', eng: '' }])
const texts = ref<{ from: string; to: string; text: string }[]>([{ from: '', to: '', text: '' }])
const ranges = ref<{ min: string; max: string }[]>([{ min: '', max: '' }])
const coeffs = ref(['', '', '', '', ''])
const attachName = ref('')
const error = ref('')
const busy = ref(false)

const fmtOptions = [
  { value: 'I', label: 'Signed integer' }, { value: 'U', label: 'Unsigned integer' },
  { value: 'R', label: 'Real' },
]

const targetTable = computed(() => kindOptions.find((k) => k.value === kind.value)?.target ?? 'pcf')
const targets = ref<MibRow[]>([])
async function loadTargets() {
  targets.value = await get(`/api/projects/${projectId.value}/tables/${targetTable.value}/rows`)
}
onMounted(loadTargets)
watch(targetTable, loadTargets)

const targetOptions = computed(() => {
  const nameCol = targetTable.value === 'pcf' ? 'PCF_NAME' : 'CPC_PNAME'
  const descCol = targetTable.value === 'pcf' ? 'PCF_DESCR' : 'CPC_DESCR'
  return [{ value: '', label: '(do not attach now)' },
    ...targets.value.map((r) => ({
      value: String(r.data[nameCol]),
      label: `${r.data[nameCol]} — ${r.data[descCol] ?? ''}`,
    }))]
})

const isPoints = computed(() => ['caf', 'cca'].includes(kind.value))
const isTexts = computed(() => ['txf', 'paf'].includes(kind.value))
const isCoeffs = computed(() => ['mcf', 'lgf'].includes(kind.value))
const isRanges = computed(() => kind.value === 'prf')

async function submit() {
  error.value = ''
  busy.value = true
  try {
    await post(`/api/projects/${projectId.value}/wizards/calibration`, {
      kind: kind.value, ident: ident.value, descr: descrText.value, unit: unit.value,
      engfmt: engfmt.value, rawfmt: rawfmt.value,
      points: points.value.filter((p) => p.raw !== '' || p.eng !== ''),
      texts: texts.value.filter((t) => t.text !== '').map((t) => ({ from: t.from, to: t.to, text: t.text })),
      ranges: ranges.value.filter((r) => r.min !== ''),
      coeffs: coeffs.value,
      attach: attachName.value
        ? { table: targetTable.value, name: attachName.value }
        : null,
    })
    toast.add({ severity: 'success', summary: `Calibration ${ident.value} created`, life: 4000 })
    await store.loadProject(projectId.value, true)
    router.push(`/project/${projectId.value}/table/${kind.value}`)
  } catch (e: any) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page">
    <h1><i class="pi pi-sliders-h" /> New calibration</h1>
    <p class="muted small">
      Calibrations turn raw numbers into meaningful values. TM calibrations convert
      downlinked raw values to engineering values; TC (de-)calibrations let operators
      enter engineering values or pick named states for command arguments.
    </p>
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <div class="card">
      <div class="grid-2">
        <div class="field-row">
          <label>Calibration kind</label>
          <Select v-model="kind" :options="kindOptions" option-label="label" option-value="value" fluid />
        </div>
        <div class="field-row">
          <label>Name <span class="req">*</span></label>
          <InputText v-model="ident" maxlength="10" placeholder="e.g. UTMODES" fluid />
        </div>
        <div class="field-row">
          <label>Description</label>
          <InputText v-model="descrText" maxlength="24" fluid />
        </div>
        <div class="field-row" v-if="isPoints || kind === 'prf'">
          <label>Engineering unit</label>
          <InputText v-model="unit" maxlength="4" placeholder="e.g. V" fluid />
        </div>
        <div class="field-row" v-if="isPoints">
          <label>Engineering format</label>
          <Select v-model="engfmt" :options="fmtOptions" option-label="label" option-value="value" fluid />
        </div>
        <div class="field-row" v-if="isPoints || isTexts">
          <label>Raw format</label>
          <Select v-model="rawfmt" :options="fmtOptions" option-label="label" option-value="value" fluid />
        </div>
      </div>
    </div>

    <div class="card" v-if="isTexts">
      <h2>State texts</h2>
      <p class="muted small">Leave "to" empty for a single raw value (e.g. 1 = ON).</p>
      <div v-for="(t, i) in texts" :key="i" class="toolbar" style="margin-bottom: 0.4rem">
        <InputText v-model="t.from" placeholder="raw from" size="small" style="width: 8rem" />
        <InputText v-model="t.to" placeholder="raw to (optional)" size="small" style="width: 8rem" />
        <InputText v-model="t.text" placeholder="state text, e.g. ON" size="small" style="width: 12rem" />
        <Button text size="small" icon="pi pi-trash" severity="danger" @click="texts.splice(i, 1)" />
      </div>
      <Button size="small" outlined icon="pi pi-plus" label="Add state"
              @click="texts.push({ from: '', to: '', text: '' })" />
    </div>

    <div class="card" v-if="isPoints">
      <h2>Curve points</h2>
      <p class="muted small">
        {{ kind === 'caf' ? 'Raw (downlinked) value → engineering value. At least 2 points, raw values increasing.'
                          : 'Engineering value entered by the operator → raw value sent on-board. At least 2 points.' }}
      </p>
      <div v-for="(p, i) in points" :key="i" class="toolbar" style="margin-bottom: 0.4rem">
        <InputText v-model="p.raw" placeholder="raw value" size="small" style="width: 10rem" />
        <i class="pi pi-arrow-right-arrow-left muted" />
        <InputText v-model="p.eng" placeholder="engineering value" size="small" style="width: 10rem" />
        <Button text size="small" icon="pi pi-trash" severity="danger" @click="points.splice(i, 1)" />
      </div>
      <Button size="small" outlined icon="pi pi-plus" label="Add point"
              @click="points.push({ raw: '', eng: '' })" />
    </div>

    <div class="card" v-if="isCoeffs">
      <h2>Coefficients</h2>
      <p class="muted small">
        {{ kind === 'mcf' ? 'eng = A0 + A1·raw + A2·raw² + A3·raw³ + A4·raw⁴'
                          : 'eng = 1 / (A0 + A1·ln(raw) + A2·ln(raw)² + A3·ln(raw)³ + A4·ln(raw)⁴)' }}
      </p>
      <div class="toolbar">
        <InputText v-for="(c, i) in coeffs" :key="i" v-model="coeffs[i]"
                   :placeholder="`A${i}${i === 0 ? ' *' : ''}`" size="small" style="width: 9rem" />
      </div>
    </div>

    <div class="card" v-if="isRanges">
      <h2>Allowed ranges</h2>
      <p class="muted small">Leave "max" empty to allow a single value.</p>
      <div v-for="(r, i) in ranges" :key="i" class="toolbar" style="margin-bottom: 0.4rem">
        <InputText v-model="r.min" placeholder="min / value" size="small" style="width: 10rem" />
        <InputText v-model="r.max" placeholder="max (optional)" size="small" style="width: 10rem" />
        <Button text size="small" icon="pi pi-trash" severity="danger" @click="ranges.splice(i, 1)" />
      </div>
      <Button size="small" outlined icon="pi pi-plus" label="Add range"
              @click="ranges.push({ min: '', max: '' })" />
    </div>

    <div class="card">
      <h2>Attach to a parameter (optional)</h2>
      <p class="muted small">
        Immediately assign this calibration to a
        {{ targetTable === 'pcf' ? 'TM parameter (sets PCF_CURTX and the category)' :
           'command parameter (sets the cpc reference and category)' }}.
      </p>
      <Select v-model="attachName" :options="targetOptions" option-label="label"
              option-value="value" filter style="min-width: 24rem" />
    </div>

    <div class="toolbar">
      <div class="spacer" />
      <Button label="Create calibration" icon="pi pi-check" :loading="busy"
              :disabled="!ident.trim()" @click="submit" />
    </div>
  </div>
</template>
