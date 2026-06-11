<script setup lang="ts">
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import { useToast } from 'primevue/usetoast'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { get, post } from '../api'
import HelpPanel from '../components/HelpPanel.vue'
import PtcPfcPicker from '../components/PtcPfcPicker.vue'
import PusServicePicker from '../components/PusServicePicker.vue'
import { commandHelp, type HelpTopic } from '../help/wizardHelp'
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

const helpVisible = ref(false)
const helpTopic = ref<HelpTopic | null>(null)
function help(key: string) {
  helpTopic.value = commandHelp[key]
  helpVisible.value = true
}

// packet header definition (tcp/pcdf) — used to draw the full packet map
interface HeaderField { desc: string; bit: number; len: number; type: string }
const headerName = ref('')
const headerFields = ref<HeaderField[]>([])
onMounted(async () => {
  const tcps = await get(`/api/projects/${projectId.value}/tables/tcp/rows`)
  if (!tcps.length) return
  headerName.value = String(tcps[0].data.TCP_ID ?? '')
  const pcdf = await get(`/api/projects/${projectId.value}/tables/pcdf/rows`)
  headerFields.value = pcdf
    .filter((r: any) => r.data.PCDF_TCNAME === headerName.value)
    .map((r: any) => ({
      desc: String(r.data.PCDF_DESC || r.data.PCDF_PNAME || 'field'),
      bit: Number(r.data.PCDF_BIT || 0),
      len: Number(r.data.PCDF_LEN || 0),
      type: String(r.data.PCDF_TYPE || 'F'),
    }))
    .sort((a: HeaderField, b: HeaderField) => a.bit - b.bit)
})
const headerBits = computed(() =>
  headerFields.value.reduce((max, f) => Math.max(max, f.bit + f.len), 0))

const fmtOffset = (bits: number) => `${Math.floor(bits / 8)}.${bits % 8}`

const kindOptions = [
  { value: 'editable', label: 'Editable — operator enters the value' },
  { value: 'fixed', label: 'Fixed — parameter with locked value' },
  { value: 'area', label: 'Fixed area — constant baked into the packet' },
]

function addParam() {
  params.value.push({ pname: '', descr: '', ptc: 3, pfc: 12, kind: 'editable',
                      bits: null, value: '', unit: '', defval: '' })
}
function move(i: number, delta: number) {
  const j = i + delta
  if (j < 0 || j >= params.value.length) return
  const arr = params.value
  ;[arr[i], arr[j]] = [arr[j], arr[i]]
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
          <label v-tooltip.top="'Unique mnemonic, max 8 characters.'">
            Command name <span class="req">*</span> <i class="pi pi-question-circle wq" @click="help('cname')" />
          </label>
          <InputText v-model="cname" maxlength="8" placeholder="e.g. XYZMODE" fluid />
        </div>
        <div class="field-row">
          <label>
            Description <span class="req">*</span> <i class="pi pi-question-circle wq" @click="help('descr')" />
          </label>
          <InputText v-model="descr" maxlength="24" placeholder="e.g. Set instrument mode" fluid />
        </div>
        <div class="field-row">
          <label v-tooltip.top="'PUS service type and subtype of the command, e.g. (8,1) Perform function. Use the picker button if unsure.'">
            PUS type / subtype <i class="pi pi-question-circle wq" @click="help('service')" />
          </label>
          <div style="display: flex; gap: 0.5rem; align-items: center">
            <InputNumber v-model="type" :min="0" :max="255" show-buttons style="flex: 1" />
            <InputNumber v-model="stype" :min="0" :max="255" show-buttons style="flex: 1" />
            <PusServicePicker side="tc" icon-only
                              @select="(v) => { type = v.type; stype = v.stype }" />
          </div>
        </div>
        <div class="field-row">
          <label v-tooltip.top="'APID of the on-board application that executes this command — usually the same APID your unit uses for telemetry.'">
            APID <span class="req">*</span> <i class="pi pi-question-circle wq" @click="help('apid')" />
          </label>
          <InputNumber v-model="apid" :min="0" :max="2047" fluid />
        </div>
        <div class="field-row" style="flex-direction: row; align-items: center; margin-top: 1.4rem">
          <Checkbox v-model="critical" binary input-id="crit" />
          <label for="crit" style="font-weight: 400"
                 v-tooltip.top="'Critical commands require a second operator confirmation before release.'">
            Critical / hazardous command
          </label>
          <i class="pi pi-question-circle wq" @click="help('critical')" />
        </div>
      </div>
    </div>

    <div class="card">
      <h2>2. Arguments (application data, in order)
        <i class="pi pi-question-circle wq" @click="help('args')" /></h2>
      <p class="muted small">
        For a (8,1) command the first element is typically a fixed Function ID. New
        parameter names are created in cpc automatically; bit offsets are computed
        from the types.
      </p>
      <table class="param-table" v-if="params.length">
        <thead>
          <tr>
            <th style="width: 5.5rem"
                v-tooltip.top="'Order = position in the application data. Use the arrows to reorder; bit offsets update live in the map below.'">Order</th>
            <th style="width: 8rem"
                v-tooltip.top="'Argument mnemonic, max 8 characters (CPC_PNAME). New names are created as command parameters automatically; existing names are reused. Fixed areas need no name.'">Name</th>
            <th v-tooltip.top="'Free text shown to operators when preparing the command, max 24 characters.'">Description</th>
            <th style="width: 13rem"
                v-tooltip.top="'Editable: the operator enters the value. Fixed: a locked parameter value (visible but unchangeable). Fixed area: constant bits baked into the packet, invisible to operators — typical for function IDs.'">Kind</th>
            <th style="width: 4.5rem"
                v-tooltip.top="'Parameter Type Code — the kind of value: 2 enumerated state, 3 unsigned int, 4 signed int, 5 real, 8 text, 9 absolute time. Use the type picker if unsure.'">PTC</th>
            <th style="width: 7rem"
                v-tooltip.top="'Parameter Format Code — the size variant of the PTC. For integers: PFC 4 = 8 bit, 12 = 16 bit, 14 = 32 bit. The sparkle button opens the type picker.'">PFC</th>
            <th style="width: 7rem" v-tooltip.top="'Raw value for fixed parameters and areas, or the default offered to operators for editable ones. Leave empty to force the operator to enter a value.'">Value</th>
            <th style="width: 3rem"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(p, i) in params" :key="i">
            <td class="reorder">
              <Button text size="small" icon="pi pi-arrow-up" :disabled="i === 0"
                      v-tooltip.top="'Move up (earlier in the packet)'" @click="move(i, -1)" />
              <Button text size="small" icon="pi pi-arrow-down" :disabled="i === params.length - 1"
                      v-tooltip.top="'Move down (later in the packet)'" @click="move(i, 1)" />
            </td>
            <td><InputText v-model="p.pname" maxlength="8" size="small" :disabled="p.kind === 'area'" fluid /></td>
            <td><InputText v-model="p.descr" maxlength="24" size="small" fluid /></td>
            <td><Select v-model="p.kind" :options="kindOptions" option-label="label" option-value="value" size="small" fluid /></td>
            <td v-if="p.kind !== 'area'"><InputNumber v-model="p.ptc" :min="1" :max="13" size="small" fluid /></td>
            <td v-if="p.kind !== 'area'">
              <div class="pfc-cell">
                <InputNumber v-model="p.pfc" :min="0" size="small" fluid />
                <PtcPfcPicker icon-only side="tc" :ptc="p.ptc" :pfc="p.pfc"
                              @select="(v) => { p.ptc = v.ptc; p.pfc = v.pfc }" />
              </div>
            </td>
            <td v-else colspan="2">
              <InputNumber v-model="p.bits" :min="1" :max="4096" size="small" placeholder="bits" fluid />
            </td>
            <td><InputText v-model="p.value" size="small" fluid /></td>
            <td><Button text size="small" icon="pi pi-trash" severity="danger"
                        v-tooltip.top="'Remove this argument from the command'"
                        @click="params.splice(i, 1)" /></td>
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
        <h3 style="margin-top: 1rem">Packet map (byte.bit offsets from packet start)
          <i class="pi pi-question-circle wq" @click="help('map')" /></h3>
        <div class="byte-map">
          <template v-if="headerFields.length">
            <span v-for="(f, i) in headerFields" :key="`h${i}`" class="seg hdr clickable"
                  @click="help('map')"
                  v-tooltip.top="`${f.len} bit(s) — header field from the ${headerName} definition (pcdf). Click for details`">
              {{ fmtOffset(f.bit) }} · {{ f.desc }}
            </span>
          </template>
          <span v-else class="seg hdr clickable" @click="help('map')"
                v-tooltip.top="'No TC packet header defined yet — click for details'">
            packet header (?)
          </span>
          <span v-for="(l, i) in layout" :key="i" class="seg" v-tooltip.top="`${l.bits} bits`">
            {{ fmtOffset(headerBits + l.start) }} · {{ l.p.kind === 'area' ? (l.p.descr || 'area') : (l.p.pname || '?') }}
          </span>
        </div>
        <p class="muted small" v-if="headerFields.length">
          Grey = packet header "{{ headerName }}" ({{ headerBits / 8 }} bytes), defined once in
          tcp/pcpc/pcdf and shared by all commands. Colored = this command's arguments
          (cdf), whose stored offsets are relative to the end of the header.
        </p>
      </template>
    </div>

    <div class="card">
      <h2>3. Verification
        <i class="pi pi-question-circle wq" @click="help('verification')" /></h2>
      <p class="muted small">
        Which PUS service-1 reports the ground should wait for. This sets the command's
        acknowledgement flags (CCF_ACK) and links the matching verification stages.
      </p>
      <div class="toolbar" style="margin: 0">
        <div style="display: flex; align-items: center; gap: 0.4rem">
          <Checkbox v-model="verifAcceptance" binary input-id="va" />
          <label for="va" style="font-weight: 400"
                 v-tooltip.top="'Wait for the report confirming the on-board software accepted the command. Cheap and recommended for every command.'">
            Acceptance (1,1 / 1,2)
          </label>
        </div>
        <div style="display: flex; align-items: center; gap: 0.4rem">
          <Checkbox v-model="verifStart" binary input-id="vs" />
          <label for="vs" style="font-weight: 400"
                 v-tooltip.top="'Wait for the report that execution started. Only useful for long-running activities that report start separately.'">
            Start of execution (1,3 / 1,4)
          </label>
        </div>
        <div style="display: flex; align-items: center; gap: 0.4rem">
          <Checkbox v-model="verifCompletion" binary input-id="vc" />
          <label for="vc" style="font-weight: 400"
                 v-tooltip.top="'Wait for the report that execution finished successfully. Recommended whenever the on-board software supports it.'">
            Completion (1,7 / 1,8)
          </label>
        </div>
      </div>
    </div>

    <div class="toolbar">
      <div class="spacer" />
      <Button label="Create command" icon="pi pi-check" :loading="busy" :disabled="!valid" @click="submit" />
    </div>

    <HelpPanel v-model:visible="helpVisible" :topic="helpTopic" />
  </div>
</template>

<style scoped>
.param-table { width: 100%; border-collapse: collapse; }
.param-table th { text-align: left; font-size: 0.8rem; color: var(--p-text-muted-color); padding: 0.25rem; cursor: help; }
.param-table td { padding: 0.2rem 0.25rem; }
.param-table td.reorder { white-space: nowrap; }
.param-table td.reorder .p-button { padding: 0.15rem; width: 1.6rem; }
.pfc-cell { display: flex; align-items: center; gap: 2px; }
.pfc-cell > :first-child { flex: 1; min-width: 0; }
</style>
