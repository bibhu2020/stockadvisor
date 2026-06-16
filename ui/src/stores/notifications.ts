import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export const useNotificationsStore = defineStore('notifications', () => {
  const unreadCount = ref(0)
  const notifications = ref<any[]>([])

  async function fetchUnreadCount() {
    try {
      const res = await api.get('/notifications/unread-count')
      unreadCount.value = res.data.count
    } catch {}
  }

  async function fetchAll() {
    const res = await api.get('/notifications')
    notifications.value = res.data
    unreadCount.value = res.data.filter((n: any) => !n.is_read).length
  }

  async function markRead(id: number) {
    await api.patch(`/notifications/${id}/read`)
    const n = notifications.value.find((n) => n.id === id)
    if (n) n.is_read = true
    unreadCount.value = notifications.value.filter((n) => !n.is_read).length
  }

  async function markAllRead() {
    await api.patch('/notifications/read-all')
    notifications.value.forEach((n) => (n.is_read = true))
    unreadCount.value = 0
  }

  return { unreadCount, notifications, fetchUnreadCount, fetchAll, markRead, markAllRead }
})
