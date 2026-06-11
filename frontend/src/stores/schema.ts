import { defineStore } from 'pinia'
import { get } from '../api'
import type { Project, PtcEntry, PusService, Schema } from '../types'

export const useSchema = defineStore('schema', {
  state: () => ({
    schema: null as Schema | null,
    pusServices: [] as PusService[],
    ptcCatalog: [] as PtcEntry[],
    project: null as Project | null,
  }),
  actions: {
    async load() {
      if (!this.schema) {
        const [schema, services, types] = await Promise.all([
          get<Schema>('/api/schema'),
          get<PusService[]>('/api/pus/services'),
          get<PtcEntry[]>('/api/pus/types'),
        ])
        this.schema = schema
        this.pusServices = services
        this.ptcCatalog = types
      }
    },
    async loadProject(id: number, force = false) {
      if (force || !this.project || this.project.id !== id) {
        this.project = await get<Project>(`/api/projects/${id}`)
      }
      return this.project
    },
  },
})
