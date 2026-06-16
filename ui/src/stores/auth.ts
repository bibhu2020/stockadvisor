import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<{ id: number; email: string; name: string; role: string } | null>(null)
  const token = ref<string | null>(localStorage.getItem('token'))

  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isPending = computed(() => user.value?.role === 'pending')
  const hasAccess = computed(() => ['admin', 'guest'].includes(user.value?.role ?? ''))

  async function login(email: string, password: string) {
    const res = await api.post('/auth/login', { email, password })
    token.value = res.data.access_token
    user.value = res.data.user
    localStorage.setItem('token', token.value!)
  }

  async function register(email: string, name: string, password: string) {
    return api.post('/auth/register', { email, name, password })
  }

  async function fetchMe() {
    if (!token.value) return
    try {
      const res = await api.get('/auth/me')
      user.value = res.data
    } catch {
      token.value = null
      user.value = null
      localStorage.removeItem('token')
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return { user, token, isLoggedIn, isAdmin, isPending, hasAccess, login, register, fetchMe, logout }
})
