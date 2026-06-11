<script setup lang="ts">
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import { useToast } from 'primevue/usetoast'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { post } from '../api'
import PtcPfcPicker from '../components/PtcPfcPicker.vue'
import { useSchema } from '../stores/schema'

const route = useRoute()
const router = useRouter()
const store = useSchema()
const toast = useToast()
const projectId = computed(() => Number(route.params.id))

interface ParamRow {
  pname: string; descr: string; ptc: number; pfc: number
  kind: 'editable' | 'fixed' | 'area'; bits: number | null; value: string; unit: string
  defval: string
}

const cname = ref('')
const descr = ref('')
const descr2 = ref('')
const apid = ref<number | null>(null)
const type = ref(8)
const stype = ref(1)
const critical = ref(false)
const params = ref<ParamRow[]>([])
const verifAcceptance = ref(true)
const verifStart = ref(false)
const verifCompletion = ref(true)
const error = ref('')
const busy = ref(false)

const serviceOptions = computed(() =>
  store.pusServices.flatMap((s) =>
    s.tc.map((st) => ({
      value: `${s.service}/${st.subtype}`,
      label: `(${s.service},${st.subtype}) ${s.name} — ${st.name}`,
      service: s.service, subtype: st.subtype,
    }))))
const selectedService = ref('8/1')
function applyService() {
  const opt = serviceOptions.value.find((o) => o.value === selectedService.value)
  if (opt) { type.value = opt.service; stype.value = opt.subtype }
}

const kindOptions = [
  { value: 'editable', label: 'Editable — operator enters the value' },
  { value: 'fixed', label: 'Fixed — parameter with locked value' },
  { value: 'area', label: 'Fixed area — constant baked into the packet' },
]

function addParam() {
  params.value.push({ pname: '', descr: '', ptc: 3, pfc: 12, kind: 'editable',
                      bits: null, value: '', unit: '', defval: '' })
}

const bitWidthOf = (p: ParamRow): number => {
  if (p.kind === 'area') return p.bits ?? 0
  const entry = store.ptcCatalog.find((e) => e.ptc === p.ptc)
  if (!entry) return 0
  if (entry.pfc) return entry.pfc.find((v) => v.pfc === p.pfc)?.bits ?? 0
  const r = entry.pfc_rule!
  return r.bits === 'pfc*8' ? p.pfc * 8 : p.pfc
}
const layout = computed(() => {
  let cursor = 0
  return params.value.map((p) => {
    const start = cursor
    const bits = bitWidthOf(p)
    cursor += bits
    return { p, start, bits }
  })
})

const valid = computed(() =>
  cname.value.trim() && descr.value.trim() && apid.value != null &&
  params.value.every((p) =>
    p.kind === 'area' ? (p.bits && p.value) : p.pname.trim() && (p.kind !== 'fixed' || p.value || p.defval)))

async function submit() {
  error.value = ''
  busy.value = true
  try {
    const res = await post(`/api/projects/${projectId.value}/wizards/tc-command`, {
      cname: cname.value, descr: descr.value, descr2: descr2.value,
      apid: apid.value, type: type.value, stype: stype.value, critical: critical.value,
      params: params.value.map((p) => ({
        pname: p.pname, descr: p.descr, ptc: p.ptc, pfc: p.pfc, kind: p.kind,
        bits: p.bits, value: p.value, unit: p.unit, defval: p.defval, inter: 'R',
      })),
      verification: {
        acceptance: verifAcceptance.value, start: verifStart.value,
        completion: verifCompletion.value,
      },
    })
    toast.add({
      severity: 'success', summary: `Command ${res.cname} created`,
      detail: `Ack flags ${res.ack}, ${res.app_data_bits} application-data bits.`,
      life: 5000,
    })
    await store.loadProject(projectId.value, true)
    router.push(`/project/${projectId.value}/table/ccf`)
  } catch (e: any) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page">
    <h1><i class="pi pi-send" /> New TC command</h1>
    <p class="muted small">
      Creates the command (ccf), its argument types (cpc), the bit-exact argument layout
      (cdf) and PUS service-1 verification assignments (cvp/cvs) in one step.
    </p>
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <div class="card">
      <h2>1. The command</h2>
      <div class="grid-2">
        <div class="field-row">
          <label v-tooltip.top="'Unique mnemonic, max 8 characters.'">Command name <span class="req">*</span></label>
          <InputText v-model="cname" maxlength="8" placeholder="e.g. XYZMODE" fluid />
        </div>
        <div class="field-row">
          <label>Description <span class="req">*</span></label>
          <InputText v-model="descr" maxlength="24" placeholder="e.g. Set instrument mode" fluid />
        </div>
        <div class="field-row">
          <label v-tooltip.top="'Most unit commands are (8,1) Perform function — the first argument is then a function ID.'">
            PUS service
          </label>
          <Select v-model="selectedService" :options="serviceOptions" option-label="label"
                  option-value="value" filter fluid @change="applyService" />
        </div>
        <div class="field-row">
          <label>Type / subtype (editable)</label>
          <div style="display: flex; gap: 0.5rem">
            <InputNumber v-model="type" :min="0" :max="255" show-buttons style="width: 50%" />
            <InputNumber v-model="stype" :min="0" :max="255" show-buttons style="width: 50%" />
          </div>
        </div>
        <div class="field-row">
          <label>APID <span class="req">*</span></label>
          <InputNumber v-model="apid" :min="0" :max="2047" fluid />
        </div>
        <div class="field-row" style="flex-direction: row; align-items: center; margin-top: 1.4rem">
          <Checkbox v-model="critical" binary input-id="crit" />
          <label for="crit" style="font-weight: 400"
                 v-tooltip.top="'Critical commands require a second operator confirmation before release.'">
            Critical / hazardous command
          </label>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>2. Arguments (application data, in order)</h2>
      <p class="muted small">
        For a (8,1) command the first element is typically a fixed Function ID. New
        parameter names are created in cpc automatically; bit offsets are computed
        from the types.
      </p>
      <table class="param-table" v-if="params.length">
        <thead>
          <tr>
            <th style="width: 8rem">Name</th><th>Description</th>
            <th style="width: 13rem">Kind</th>
            <th style="width: 4.5rem">PTC</th><th style="width: 4.5rem">PFC</th>
            <th style="width: 8.5rem"></th>
            <th style="width: 7rem" v-tooltip.top="'Raw value for fixed parameters/areas, or default for editable ones'">Value</th>
            <th style="width: 3rem"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(p, i) in params" :key="i">
            <td><InputText v-model="p.pname" maxlength="8" size="small" :disabled="p.kind === 'area'" fluid /></td>
            <td><InputText v-model="p.descr" maxlength="24" size="small" fluid /></td>
            <td><Select v-model="p.kind" :options="kindOptions" option-label="label" option-value="value" size="small" fluid /></td>
            <td v-if="p.kind !== 'area'"><InputNumber v-model="p.ptc" :min="1" :max="13" size="small" fluid /></td>
            <td v-if="p.kind !== 'area'"><InputNumber v-model="p.pfc" :min="0" size="small" fluid /></td>
            <td v-if="p.kind !== 'area'">
              <PtcPfcPicker side="tc" :ptc="p.ptc" :pfc="p.pfc"
                            @select="(v) => { p.ptc = v.ptc; p.pfc = v.pfc }" />
            </td>
            <td v-else colspan="3">
              <InputNumber v-model="p.bits" :min="1" :max="4096" size="small" placeholder="bits" fluid />
            </td>
            <td><InputText v-model="p.value" size="small" fluid /></td>
            <td><Button text size="small" icon="pi pi-trash" severity="danger" @click="params.splice(i, 1)" /></td>
          </tr>
        </tbody>
      </table>
      <div class="toolbar" style="margin-top: 0.75rem">
        <Button size="small" outlined icon="pi pi-plus" label="Add argument" @click="addParam" />
        <Button v-if="type === 8 && !params.length" size="small" outlined severity="secondary"
                icon="pi pi-key" label="Add Function ID (16-bit, fixed)"
                @click="params.push({ pname: '', descr: 'Function ID', ptc: 3, pfc: 12, kind: 'fixed', bits: null, value: '', unit: '', defval: '' })" />
      </div>
      <template v-if="params.length">
        <h3 style="margin-top: 1rem">Application data map (bit offsets after packet header)</h3>
        <div class="byte-map">
          <span v-for="(l, i) in layout" :key="i" class="seg" v-tooltip.top="`${l.bits} bits`">
            {{ l.start }} · {{ l.p.kind === 'area' ? (l.p.descr || 'area') : (l.p.pname || '?') }}
          </span>
        </div>
      </template>
    </div>

    <div class="card">
      <h2>3. Verification</h2>
      <p class="muted small">
        Which PUS service-1 reports the ground should wait for. This sets the command's
        acknowledgement flags (CCF_ACK) and links the matching verification stages.
      </p>
      <div class="toolbar" style="margin: 0">
        <div style="display: flex; align-items: center; gap: 0.4rem">
          <Checkbox v-model="verifAcceptance" binary input-id="va" />
          <label for="va" style="font-weight: 400">Acceptance (1,1 / 1,2)</label>
        </div>
        <div style="display: flex; align-items: center; gap: 0.4rem">
          <Checkbox v-model="verifStart" binary input-id="vs" />
          <label for="vs" style="font-weight: 400">Start of execution (1,3 / 1,4)</label>
        </div>
        <div style="display: flex; align-items: center; gap: 0.4rem">
          <Checkbox v-model="verifCompletion" binary input-id="vc" />
          <label for="vc" style="font-weight: 400">Completion (1,7 / 1,8)</label>
        </div>
      </div>
    </div>

    <div class="toolbar">
      <div class="spacer" />
      <Button label="Create command" icon="pi pi-check" :loading="busy" :disabled="!valid" @click="submit" />
    </div>
  </div>
</template>

<style scoped>
.param-table { width: 100%; border-collapse: collapse; }
.param-table th { text-align: left; font-size: 0.8rem; color: var(--p-text-muted-color); padding: 0.25rem; }
.param-table td { padding: 0.2rem 0.25rem; }
</style>
