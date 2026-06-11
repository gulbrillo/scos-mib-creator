export interface EnumValue { value: string; label: string; help: string }

export interface ColumnDef {
  name: string
  label: string
  type: 'char' | 'number'
  length: number | null
  key: boolean
  mandatory: boolean
  signed: boolean
  hint: string
  help: string
  default: string | null
  enum: EnumValue[] | null
  enum_strict: boolean
  fk: string | null
  pattern: string | null
  profiles: string[] | null
}

export interface TableDef {
  name: string
  file: string
  title: string
  domain: string
  icd: string
  description: string
  row_label: string
  key_columns: string[]
  columns: ColumnDef[]
}

export interface Domain {
  id: string
  title: string
  icon: string
  description: string
  tables: string[]
}

export interface Schema {
  profiles: Record<string, string>
  default_profile: string
  domains: Domain[]
  tables: Record<string, TableDef>
}

export interface MibRowData { [col: string]: string }
export interface MibRow { id: number; seq: number; version: number; data: MibRowData }

export interface Project {
  id: number
  name: string
  description: string
  profile: string
  role: string | null
  row_counts: Record<string, number>
  total_rows: number
  members: { user_id: number; username: string; role: string }[]
}

export interface Finding {
  severity: 'error' | 'warning' | 'info'
  table: string
  row: number | null
  column: string | null
  code: string
  message: string
  hint: string
  row_key: string
}

export interface PusService {
  service: number
  name: string
  help: string
  tm: { subtype: number; name: string; note?: string }[]
  tc: { subtype: number; name: string; note?: string }[]
}

export interface PtcEntry {
  ptc: number
  name: string
  help: string
  tm: boolean
  tc: boolean
  pfc?: { pfc: number; bits: number; label: string }[]
  pfc_rule?: { min: number; max: number; bits: string; label: string }
}
