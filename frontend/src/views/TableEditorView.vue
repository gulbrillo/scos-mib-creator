<script setup lang="ts">
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import Drawer from 'primevue/drawer'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { del, get, post, put } from '../api'
import FieldInput from '../components/FieldInput.vue'
import PtcPfcPicker from '../components/PtcPfcPicker.vue'
import PusServicePicker from '../components/PusServicePicker.vue'
import { useSchema } from '../stores/schema'
import type { ColumnDef, MibRow, MibRowData } from '../types'

const props = defineProps<{ table: string }>()
const route = useRoute()
const store = useSchema()
const toast = useToast()
const confirm = useConfirm()

const projectId = computed(() => Number(route.params.id))
const tableDef = computed(() => store.schema!.tables[props.table])
const profile = computed(() => store.project?.profile ?? 'ccs5')
const canWrite = computed(() => ['owner', 'editor'].includes(store.project?.role ?? ''))

const rows = ref<MibRow[]>([])
const loading = ref(true)
const editing = ref(false)
const editRow = ref<MibRow | null>(null)   // null = creating new
const draft = ref<MibRowData>({})
const saveError = ref('')

// columns applicable to the current project profile
const profileColumns = computed<ColumnDef[]>(() =>
  tableDef.value.columns.filter((c) => !c.profiles || c.profiles.includes(profile.value)))

// grid shows up to 7 informative columns
const gridColumns = computed(() => profileColumns.value.slice(0, 7))

// help drawer state
const helpVisible = ref(false)
const helpColumn = ref<ColumnDef | null>(null)
function showHelp(col: ColumnDef) {
  helpColumn.value = col
  helpVisible.value = true
}

// FK option rows, fetched lazily per referenced table
const fkRows = ref<Record<string, MibRow[]>>({})
async function loadFkTables() {
  const tables = new Set(
    profileColumns.value.filter((c) => c.fk).map((c) => c.fk!.split('.')[0]))
  for (const t of tables) {
    fkRows.value[t] = await get(`/api/projects/${projectId.value}/tables/${t}/rows`)
  }
}
function fkLabelCol(col: ColumnDef): string | undefined {
  const t = store.schema!.tables[col.fk!.split('.')[0]]
  const second = t?.columns[1]
  return second && second.type === 'char' && !second.key ? second.name : undefined
}

async function load() {
  loading.value = true
  rows.value = await get(`/api/projects/${projectId.value}/tables/${props.table}/rows`)
  await loadFkTables()
  loading.value = false
}

onMounted(load)
watch(() => props.table, load)

function newRow() {
  editRow.value = null
  draft.value = {}
  for (const c of tableDef.value.columns) draft.value[c.name] = c.default ?? ''
  saveError.value = ''
  editing.value = true
}

function openRow(r: MibRow) {
  editRow.value = r
  draft.value = { ...r.data }
  saveError.value = ''
  editing.value = true
}

async function save() {
  saveError.value = ''
  try {
    if (editRow.value) {
      await put(`/api/projects/${projectId.value}/tables/${props.table}/rows/${editRow.value.id}`,
        { data: draft.value, version: editRow.value.version })
    } else {
      await post(`/api/projects/${projectId.value}/tables/${props.table}/rows`,
        { data: draft.value })
    }
    editing.value = false
    toast.add({ severity: 'success', summary: 'Saved', life: 1500 })
    await load()
    await store.loadProject(projectId.value, true)
  } catch (e: any) {
    saveError.value = e.message
  }
}

function removeRow(r: MibRow) {
  confirm.require({
    message: 'Delete this record? References from other tables are not deleted automatically.',
    header: 'Delete record',
    icon: 'pi pi-trash',
    acceptProps: { label: 'Delete', severity: 'danger' },
    rejectProps: { label: 'Cancel', severity: 'secondary', text: true },
    accept: async () => {
      await del(`/api/projects/${projectId.value}/tables/${props.table}/rows/${r.id}`)
      editing.value = false
      await load()
      await store.loadProject(projectId.value, true)
    },
  })
}

const domain = computed(() => store.schema!.domains.find((d) => d.id === tableDef.value.domain))

// "smart picker" buttons rendered next to certain inputs: PTC/PFC fields get
// the type picker, PUS type/subtype fields get the service picker.
interface PickerInfo {
  kind: 'ptc' | 'pus'
  side: 'tm' | 'tc'
  typeCol: string
  secondCol: string
}
const PUS_TABLES: Record<string, [string, string, 'tm' | 'tc']> = {
  pid: ['PID_TYPE', 'PID_STYPE', 'tm'],
  pic: ['PIC_TYPE', 'PIC_STYPE', 'tm'],
  ccf: ['CCF_TYPE', 'CCF_STYPE', 'tc'],
}
function pickerFor(colName: string): PickerInfo | null {
  if (colName.endsWith('_PTC') || colName.endsWith('_PFC')) {
    const prefix = colName.slice(0, -4)
    const cols = tableDef.value.columns.map((c) => c.name)
    if (cols.includes(`${prefix}_PTC`) && cols.includes(`${prefix}_PFC`)) {
      return {
        kind: 'ptc',
        side: tableDef.value.domain.startsWith('tm') ? 'tm' : 'tc',
        typeCol: `${prefix}_PTC`,
        secondCol: `${prefix}_PFC`,
      }
    }
  }
  const pus = PUS_TABLES[tableDef.value.name]
  if (pus && (colName === pus[0] || colName === pus[1])) {
    return { kind: 'pus', side: pus[2], typeCol: pus[0], secondCol: pus[1] }
  }
  return null
}
function applyPtc(p: PickerInfo, v: { ptc: number; pfc: number }) {
  draft.value[p.typeCol] = String(v.ptc)
  draft.value[p.secondCol] = String(v.pfc)
}
function applyPus(p: PickerInfo, v: { type: number; stype: number }) {
  draft.value[p.typeCol] = String(v.type)
  draft.value[p.secondCol] = String(v.stype)
}
</script>

<template>
  <div class="page" v-if="tableDef">
    <div class="toolbar">
      <div>
        <h1>
          {{ tableDef.title }}
          <span class="muted mono small">{{ tableDef.file }}</span>
          <Tag v-if="tableDef.icd" :value="`ICD §${tableDef.icd}`" severity="secondary" />
        </h1>
        <span class="muted small">{{ domain?.title }}</span>
      </div>
      <div class="spacer" />
      <Button v-if="canWrite" icon="pi pi-plus" label="New record" @click="newRow" />
    </div>

    <p class="help-text">{{ tableDef.description }}</p>

    <div class="card">
      <DataTable
        :value="rows" :loading="loading" data-key="id" size="small"
        paginator :rows="25" :rows-per-page-options="[25, 100, 500]"
        selection-mode="single" @row-select="(e: any) => openRow(e.data)"
        striped-rows scrollable
      >
        <Column v-for="c in gridColumns" :key="c.name" :field="`data.${c.name}`" sortable>
          <template #header>
            <span v-tooltip.top="c.hint || c.label" class="mono small">{{ c.name }}</span>
          </template>
          <template #body="{ data }">
            <span :class="{ mono: c.type === 'number' || c.key }">{{ data.data[c.name] }}</span>
          </template>
        </Column>
        <Column v-if="canWrite" style="width: 4rem">
          <template #body="{ data }">
            <Button text size="small" icon="pi pi-trash" severity="danger" @click.stop="removeRow(data)" />
          </template>
        </Column>
        <template #empty>
          <span class="muted">
            No records yet.
            <template v-if="canWrite">Use “New record” — every field has a tooltip and a
            <i class="pi pi-question-circle" style="font-size: 0.8rem" /> help button.</template>
          </span>
        </template>
      </DataTable>
    </div>

    <Dialog
      v-model:visible="editing" modal
      :header="editRow ? `Edit ${tableDef.title} record` : `New ${tableDef.title} record`"
      :style="{ width: '880px', maxWidth: '95vw' }"
    >
      <Message v-if="saveError" severity="error" :closable="false">{{ saveError }}</Message>
      <div class="grid-2">
        <FieldInput
          v-for="c in profileColumns" :key="c.name"
          v-model="draft[c.name]"
          :column="c"
          :fk-rows="c.fk ? fkRows[c.fk.split('.')[0]] : undefined"
          :fk-label-col="c.fk ? fkLabelCol(c) : undefined"
          @help="showHelp(c)"
        >
          <template v-if="pickerFor(c.name)" #append>
            <PtcPfcPicker
              v-if="pickerFor(c.name)!.kind === 'ptc'"
              icon-only
              :side="pickerFor(c.name)!.side"
              :ptc="Number(draft[pickerFor(c.name)!.typeCol]) || null"
              :pfc="Number(draft[pickerFor(c.name)!.secondCol]) || null"
              @select="(v) => applyPtc(pickerFor(c.name)!, v)"
            />
            <PusServicePicker
              v-else
              icon-only
              :side="pickerFor(c.name)!.side"
              @select="(v) => applyPus(pickerFor(c.name)!, v)"
            />
          </template>
        </FieldInput>
      </div>
      <template #footer>
        <Button v-if="editRow && canWrite" text severity="danger" icon="pi pi-trash"
                label="Delete" @click="removeRow(editRow!)" />
        <span style="flex: 1" />
        <Button text label="Cancel" @click="editing = false" />
        <Button v-if="canWrite" label="Save" icon="pi pi-check" @click="save" />
      </template>
    </Dialog>

    <Drawer v-model:visible="helpVisible" position="right" :style="{ width: '420px' }"
            :header="helpColumn ? `${helpColumn.label} (${helpColumn.name})` : 'Help'">
      <template v-if="helpColumn">
        <p v-if="helpColumn.hint"><b>{{ helpColumn.hint }}</b></p>
        <p v-if="helpColumn.help" style="white-space: pre-line">{{ helpColumn.help }}</p>
        <template v-if="helpColumn.enum">
          <h3>Allowed values</h3>
          <ul>
            <li v-for="e in helpColumn.enum" :key="e.value">
              <b class="mono">{{ e.value === '' ? '(empty)' : e.value }}</b> — {{ e.label }}
              <div v-if="e.help" class="muted small">{{ e.help }}</div>
            </li>
          </ul>
        </template>
        <p class="muted small">
          <template v-if="helpColumn.mandatory">Mandatory field. </template>
          <template v-if="helpColumn.length">Maximum length: {{ helpColumn.length }} characters. </template>
          <template v-if="helpColumn.fk">References {{ helpColumn.fk }}. </template>
          Defined in the SCOS-2000 Database Import ICD, section {{ tableDef.icd }}.
        </p>
      </template>
    </Drawer>
  </div>
</template>
