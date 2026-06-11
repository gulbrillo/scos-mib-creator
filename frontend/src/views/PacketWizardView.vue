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
  name: string; descr: string; ptc: number; pfc: number; unit: string; is_pi1: boolean
}

const descr = ref('')
const packetName = ref('')
const apid = ref<number | null>(null)
const type = ref(3)
const stype = ref(25)
const pi1Val = ref<number | null>(null)
const dfhSize = ref(10)
const hasTime = ref(true)
const hasPec = ref(true)
const intervalMs = ref<number | null>(8000)
const params = ref<ParamRow[]>([])
const error = ref('')
const busy = ref(false)

const serviceOptions = computed(() =>
  store.pusServices.flatMap((s) =>
    s.tm.map((st) => ({
      value: `${s.service}/${st.subtype}`,
      label: `(${s.service},${st.subtype}) ${s.name} — ${st.name}`,
      service: s.service, subtype: st.subtype,
    }))))
const selectedService = ref('3/25')
function applyService() {
  const opt = serviceOptions.value.find((o) => o.value === selectedService.value)
  if (opt) { type.value = opt.service; stype.value = opt.subtype }
}

const isHk = computed(() => type.value === 3)

function addParam(pi1 = false) {
  params.value.push({
    name: '', descr: '', ptc: 3, pfc: 12, unit: '', is_pi1: pi1,
  })
}
function setPi1(idx: number) {
  params.value.forEach((p, i) => (p.is_pi1 = i === idx))
}
function move(i: number, delta: number) {
  const j = i + delta
  if (j < 0 || j >= params.value.length) return
  const arr = params.value
  ;[arr[i], arr[j]] = [arr[j], arr[i]]
}

// live byte map
const bitWidthOf = (p: ParamRow): number => {
  const entry = store.ptcCatalog.find((e) => e.ptc === p.ptc)
  if (!entry) return 0
  if (entry.pfc) return entry.pfc.find((v) => v.pfc === p.pfc)?.bits ?? 0
  const r = entry.pfc_rule!
  return r.bits === 'pfc*8' ? p.pfc * 8 : p.pfc
}
const layout = computed(() => {
  let cursor = (6 + (dfhSize.value || 0)) * 8
  return params.value.map((p) => {
    const start = cursor
    const bits = bitWidthOf(p)
    cursor += bits
    return { p, start, bits, byte: Math.floor(start / 8), bit: start % 8 }
  })
})
const totalBytes = computed(() => {
  const end = layout.value.length ? layout.value[layout.value.length - 1] : null
  const bits = end ? end.start + end.bits : (6 + (dfhSize.value || 0)) * 8
  return Math.ceil(bits / 8) + (hasPec.value ? 2 : 0)
})

async function submit() {
  error.value = ''
  busy.value = true
  try {
    const res = await post(`/api/projects/${projectId.value}/wizards/tm-packet`, {
      descr: descr.value, apid: apid.value, type: type.value, stype: stype.value,
      pi1_val: pi1Val.value, dfh_size: dfhSize.value, has_time: hasTime.value,
      interval_ms: intervalMs.value, packet_name: packetName.value, has_pec: hasPec.value,
      params: params.value.map((p) => ({
        name: p.name, descr: p.descr, ptc: p.ptc, pfc: p.pfc, unit: p.unit,
        is_pi1: p.is_pi1,
      })),
    })
    toast.add({
      severity: 'success', summary: `Packet created (SPID ${res.spid})`,
      detail: `Created ${res.created.pcf} new parameters, layout for ${res.created.plf} fields.`,
      life: 5000,
    })
    await store.loadProject(projectId.value, true)
    router.push(`/project/${projectId.value}/table/pid`)
  } catch (e: any) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page">
    <h1><i class="pi pi-inbox" /> New TM packet</h1>
    <p class="muted small">
      Creates the packet identification (pid), identification criteria (pic), packet
      characteristics (tpcf) and the byte-exact parameter layout (plf) in one step —
      and defines any new parameters (pcf) on the way. All offsets are computed for you.
    </p>
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <div class="card">
      <h2>1. What kind of packet is it?</h2>
      <div class="grid-2">
        <div class="field-row">
          <label v-tooltip.top="'PUS service / subtype of the packet. Housekeeping reports are (3,25).'">
            PUS service
          </label>
          <Select v-model="selectedService" :options="serviceOptions" option-label="label"
                  option-value="value" filter fluid @change="applyService" />
        </div>
        <div class="field-row">
          <label v-tooltip.top="'The service type and subtype written into the PUS header of the packet. Pre-filled by the service selection on the left — only edit for mission-custom services.'">
            Type / subtype (editable)
          </label>
          <div style="display: flex; gap: 0.5rem">
            <InputNumber v-model="type" :min="0" :max="255" show-buttons style="width: 50%" />
            <InputNumber v-model="stype" :min="0" :max="255" show-buttons style="width: 50%" />
          </div>
        </div>
        <div class="field-row">
          <label v-tooltip.top="'The APID assigned to your unit by the system team (0-2047).'">
            APID <span class="req">*</span>
          </label>
          <InputNumber v-model="apid" :min="0" :max="2047" fluid />
        </div>
        <div class="field-row">
          <label v-tooltip.top="'Shown to operators wherever this packet appears.'">
            Description <span class="req">*</span>
          </label>
          <InputText v-model="descr" placeholder="e.g. XYZ standard HK report" fluid />
        </div>
        <div class="field-row">
          <label v-tooltip.top="'Short mnemonic for displays (tpcf), max 12 characters.'">Packet mnemonic</label>
          <InputText v-model="packetName" maxlength="12" placeholder="e.g. XYZ_HK1" fluid />
        </div>
        <div class="field-row" v-if="isHk">
          <label v-tooltip.top="'The Structure ID distinguishing this HK report from others with the same APID and type. Carried as the first field of the packet body.'">
            SID (PI1 value)
          </label>
          <InputNumber v-model="pi1Val" :min="0" fluid />
        </div>
      </div>
    </div>

    <div class="card">
      <h2>2. Packet structure</h2>
      <div class="grid-2">
        <div class="field-row">
          <label v-tooltip.top="'Bytes of PUS secondary header (incl. time stamp and spare) after the 6-byte CCSDS header. Mission-specific — ask your system team. Common values: 10-16.'">
            Data field header size (bytes)
          </label>
          <InputNumber v-model="dfhSize" :min="0" :max="64" show-buttons fluid />
        </div>
        <div class="field-row" style="justify-content: end; gap: 0.8rem">
          <div style="display: flex; align-items: center; gap: 0.4rem">
            <Checkbox v-model="hasTime" binary input-id="ht" />
            <label for="ht" style="font-weight: 400"
                   v-tooltip.top="'Whether the data field header carries the packet generation time stamp (PID_TIME). Standard PUS housekeeping packets do.'">
              Header contains time stamp
            </label>
          </div>
          <div style="display: flex; align-items: center; gap: 0.4rem">
            <Checkbox v-model="hasPec" binary input-id="hp" />
            <label for="hp" style="font-weight: 400"
                   v-tooltip.top="'Whether the last 2 bytes of the packet are a CRC checksum (Packet Error Control). Standard for PUS packets — only affects the computed total size (tpcf).'">
              Packet ends with CRC (PEC, 2 bytes)
            </label>
          </div>
        </div>
        <div class="field-row">
          <label v-tooltip.top="'For periodic packets: the generation period. Used to flag stale parameters. Empty for event-driven packets.'">
            Generation interval (ms)
          </label>
          <InputNumber v-model="intervalMs" :min="0" fluid />
        </div>
      </div>
    </div>

    <div class="card">
      <h2>3. Parameters in the packet body (in order)</h2>
      <p class="muted small">
        List the fields of the packet body in their on-board order, starting right after the
        data field header. For a HK packet the first field is usually the 16-bit SID —
        mark it as the identification field. New names are created as TM parameters (pcf)
        automatically; existing names are reused.
      </p>
      <table class="param-table" v-if="params.length">
        <thead>
          <tr>
            <th style="width: 5.5rem"
                v-tooltip.top="'Order = position in the packet body. Use the arrows to reorder; all offsets update live in the map below.'">Order</th>
            <th style="width: 9rem"
                v-tooltip.top="'Unique parameter mnemonic, max 8 characters (PCF_NAME). A new name is created as a TM parameter automatically; an existing name reuses its stored type.'">Name *</th>
            <th v-tooltip.top="'Free text shown to operators in displays, max 24 characters (PCF_DESCR).'">Description</th>
            <th style="width: 5rem"
                v-tooltip.top="'Parameter Type Code — the kind of value: 1 boolean, 2 enumerated state, 3 unsigned int, 4 signed int, 5 real, 8 text, 9 time. Use the type picker if unsure.'">PTC</th>
            <th style="width: 5rem"
                v-tooltip.top="'Parameter Format Code — the size variant of the PTC. For integers: PFC 4 = 8 bit, 12 = 16 bit, 14 = 32 bit. Together PTC and PFC fix how many bits the field occupies.'">PFC</th>
            <th style="width: 9rem"></th>
            <th style="width: 5rem"
                v-tooltip.top="'Engineering unit shown next to calibrated values, max 4 characters, e.g. V, degC, mA. Leave empty for counters and states.'">Unit</th>
            <th style="width: 5rem"
                v-tooltip.top="'Mark the field that carries the identification value (the SID for housekeeping packets). Its position is written into the pic table so the ground can tell packets apart.'">ID field</th>
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
            <td><InputText v-model="p.name" maxlength="8" size="small" fluid /></td>
            <td><InputText v-model="p.descr" maxlength="24" size="small" fluid /></td>
            <td><InputNumber v-model="p.ptc" :min="1" :max="13" size="small" fluid /></td>
            <td><InputNumber v-model="p.pfc" :min="0" size="small" fluid /></td>
            <td><PtcPfcPicker side="tm" :ptc="p.ptc" :pfc="p.pfc"
                              @select="(v) => { p.ptc = v.ptc; p.pfc = v.pfc }" /></td>
            <td><InputText v-model="p.unit" maxlength="4" size="small" fluid /></td>
            <td style="text-align: center">
              <input type="radio" name="pi1" :checked="p.is_pi1" @change="setPi1(i)"
                     v-tooltip.top="'This field carries the SID / identification value'" />
            </td>
            <td><Button text size="small" icon="pi pi-trash" severity="danger"
                        v-tooltip.top="'Remove from packet (does not delete the parameter)'"
                        @click="params.splice(i, 1)" /></td>
          </tr>
        </tbody>
      </table>
      <div class="toolbar" style="margin-top: 0.75rem">
        <Button size="small" outlined icon="pi pi-plus" label="Add parameter" @click="addParam()" />
        <Button v-if="isHk && !params.some(p => p.is_pi1)" size="small" outlined severity="secondary"
                icon="pi pi-key" label="Add SID field (16-bit)"
                @click="params.unshift({ name: '', descr: 'Structure ID', ptc: 3, pfc: 12, unit: '', is_pi1: true })" />
      </div>

      <template v-if="params.length">
        <h3 style="margin-top: 1rem">Packet map (byte.bit offsets from packet start)</h3>
        <div class="byte-map">
          <span class="seg hdr">0 · CCSDS header (6 B)</span>
          <span class="seg hdr">6 · Data field header ({{ dfhSize }} B)</span>
          <span v-for="(l, i) in layout" :key="i" class="seg"
                v-tooltip.top="`${l.bits} bits`">
            {{ l.byte }}.{{ l.bit }} · {{ l.p.name || '?' }}
          </span>
          <span v-if="hasPec" class="seg hdr">CRC (2 B)</span>
        </div>
        <p class="muted small">Total packet size: {{ totalBytes }} bytes</p>
      </template>
    </div>

    <div class="toolbar">
      <div class="spacer" />
      <Button label="Create packet" icon="pi pi-check" :loading="busy"
              :disabled="apid == null || !descr.trim() || params.some(p => !p.name.trim())"
              @click="submit" />
    </div>
  </div>
</template>

<style scoped>
.param-table { width: 100%; border-collapse: collapse; }
.param-table th { text-align: left; font-size: 0.8rem; color: var(--p-text-muted-color); padding: 0.25rem; cursor: help; }
.param-table td { padding: 0.2rem 0.25rem; }
.param-table td.reorder { white-space: nowrap; }
.param-table td.reorder .p-button { padding: 0.15rem; width: 1.6rem; }
</style>
