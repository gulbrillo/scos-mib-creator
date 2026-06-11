import { defineStore } from 'pinia'
import { get, post } from '../api'

interface User { id: number; username: string; is_admin: boolean }

export const useSession = defineStore('session', {
  state: () => ({ user: null as User | null, loaded: false }),
  actions: {
    async load() {
      try {
        this.user = await get<User>('/api/auth/me')
      } catch {
        this.user = null
      }
      this.loaded = true
    },
    async login(username: string, password: string) {
      this.user = await post<User>('/api/auth/login', { username, password })
    },
    async logout() {
      await post('/api/auth/logout')
      this.user = null
    },
  },
})
