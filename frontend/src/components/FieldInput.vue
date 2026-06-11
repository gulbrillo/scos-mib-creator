<script setup lang="ts">
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import { computed } from 'vue'
import type { ColumnDef, MibRow } from '../types'

const props = defineProps<{
  column: ColumnDef
  modelValue: string
  fkRows?: MibRow[]          // candidate rows of the referenced table
  fkLabelCol?: string        // optional description column to show alongside
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void; (e: 'help'): void }>()

const value = computed({
  get: () => props.modelValue ?? '',
  set: (v: string) => emit('update:modelValue', v ?? ''),
})

const enumOptions = computed(() => {
  if (!props.column.enum) return null
  const opts = props.column.enum.map((e) => ({
    value: e.value,
    label: e.value === '' ? `(empty) — ${e.label}` : `${e.value} — ${e.label}`,
  }))
  if (!props.column.mandatory && !props.column.enum.some((e) => e.value === '')) {
    opts.unshift({ value: '', label: '(empty)' })
  }
  return opts
})

const fkColumn = computed(() => props.column.fk?.split('.')[1] ?? '')
const fkOptions = computed(() => {
  if (!props.column.fk || !props.fkRows) return null
  const seen = new Set<string>()
  const opts: { value: string; label: string }[] = []
  for (const r of props.fkRows) {
    const v = String(r.data[fkColumn.value] ?? '')
    if (!v || seen.has(v)) continue
    seen.add(v)
    const desc = props.fkLabelCol ? String(r.data[props.fkLabelCol] ?? '') : ''
    opts.push({ value: v, label: desc ? `${v} — ${desc}` : v })
  }
  if (!props.column.mandatory) opts.unshift({ value: '', label: '(empty)' })
  // keep a stale/unknown current value selectable so it stays visible
  if (value.value && !seen.has(value.value)) {
    opts.push({ value: value.value, label: `${value.value} (not found!)` })
  }
  return opts
})
</script>

<template>
  <div class="field-row">
    <label>
      <span v-tooltip.top="column.hint || undefined">{{ column.label }}</span>
      <span v-if="column.mandatory" class="req">*</span>
      <i
        v-if="column.help || column.hint"
        class="pi pi-question-circle help-icon"
        @click="emit('help')"
      />
      <span class="muted small mono">{{ column.name }}</span>
    </label>
    <div class="input-line">
      <Select
        v-if="enumOptions"
        v-model="value"
        :options="enumOptions"
        option-label="label"
        option-value="value"
        size="small"
        :placeholder="column.hint"
        fluid
      />
      <Select
        v-else-if="fkOptions"
        v-model="value"
        :options="fkOptions"
        option-label="label"
        option-value="value"
        size="small"
        filter
        :placeholder="`Select from ${column.fk?.split('.')[0]}…`"
        fluid
      />
      <InputText
        v-else
        v-model="value"
        size="small"
        :placeholder="column.hint"
        :maxlength="column.length ?? undefined"
        fluid
      />
      <slot name="append" />
    </div>
  </div>
</template>

<style scoped>
.help-icon {
  font-size: 0.8rem;
  color: var(--p-primary-color);
  cursor: pointer;
}
label .mono { margin-left: auto; font-weight: 400; }
.input-line { display: flex; align-items: center; gap: 0.15rem; }
.input-line > :first-child { flex: 1; min-width: 0; }
</style>
