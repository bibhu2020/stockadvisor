<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationsStore } from '../stores/notifications'

const notifs = useNotificationsStore()
const router = useRouter()
const open = ref(false)
const wrapperRef = ref<HTMLElement | null>(null)

function onDocClick(e: MouseEvent) {
  if (open.value && wrapperRef.value && !wrapperRef.value.contains(e.target as Node)) {
    open.value = false
  }
}
onMounted(() => document.addEventListener('click', onDocClick, true))
onUnmounted(() => document.removeEventListener('click', onDocClick, true))

async function toggle() {
  open.value = !open.value
  if (open.value) await notifs.fetchAll()
}

// Hide read notifications older than 24 hours
const visibleNotifs = computed(() => {
  const cutoff = Date.now() - 24 * 60 * 60 * 1000
  return notifs.notifications.filter((n) => {
    if (!n.is_read) return true                          // always show unread
    return new Date(n.created_at).getTime() > cutoff    // hide read if >24h old
  })
})

const ROUTES: Record<string, string> = {
  report_ready:       '/reports',
  trade_executed:     '/transactions',
  stop_loss:          '/transactions',
  profit_booked:      '/transactions',
  strategy_updated:   '/strategies',
  retrospective_done: '/reports',
}

async function handleClick(n: any) {
  if (!n.is_read) await notifs.markRead(n.id)
  open.value = false
  const target = ROUTES[n.type]
  if (target) router.push(target)
}

function typeIcon(type: string) {
  const map: Record<string, string> = {
    report_ready:       '📋',
    trade_executed:     '💱',
    stop_loss:          '🛑',
    profit_booked:      '✅',
    strategy_updated:   '🧠',
    retrospective_done: '📊',
  }
  return map[type] ?? '🔔'
}

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins  = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  if (mins < 1)   return 'just now'
  if (mins < 60)  return `${mins}m ago`
  if (hours < 24) return `${hours}h ago`
  return new Date(dateStr).toLocaleDateString()
}
</script>

<template>
  <div class="bell-wrapper" ref="wrapperRef">
    <button class="bell-btn" @click="toggle">
      🔔
      <span v-if="notifs.unreadCount > 0" class="badge">{{ notifs.unreadCount }}</span>
    </button>

    <div v-if="open" class="notif-panel">
      <div class="notif-header">
        <span>Notifications</span>
        <button v-if="notifs.unreadCount > 0" @click="notifs.markAllRead()">Mark all read</button>
      </div>

      <div class="notif-list">
        <div
          v-for="n in visibleNotifs"
          :key="n.id"
          :class="['notif-item', { unread: !n.is_read }, ROUTES[n.type] ? 'clickable' : '']"
          @click="handleClick(n)"
        >
          <span class="notif-icon">{{ typeIcon(n.type) }}</span>
          <div class="notif-body">
            <p class="notif-title">{{ n.title }}</p>
            <p class="notif-msg">{{ n.message }}</p>
            <div class="notif-footer">
              <span class="notif-time">{{ timeAgo(n.created_at) }}</span>
              <span v-if="ROUTES[n.type]" class="notif-go">View →</span>
            </div>
          </div>
        </div>

        <p v-if="!visibleNotifs.length" class="empty">
          {{ notifs.notifications.length ? 'All caught up — no recent notifications.' : 'No notifications yet.' }}
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.bell-wrapper { position: relative; }
.bell-btn {
  position: relative; background: none; border: none;
  font-size: 1.3rem; cursor: pointer; padding: 4px 8px;
}
.badge {
  position: absolute; top: -2px; right: -2px;
  background: #ef4444; color: #fff; border-radius: 99px;
  font-size: 0.65rem; padding: 1px 5px; font-weight: 700;
}
.notif-panel {
  position: absolute; right: 0; top: 44px; width: 370px; max-height: 500px;
  background: #fff; border: 1px solid #e5e7eb; border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.13); z-index: 100;
  display: flex; flex-direction: column; overflow: hidden;
}
.notif-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 13px 16px; border-bottom: 1px solid #f3f4f6;
  font-weight: 700; font-size: 0.9rem; color: #1e3a5f; flex-shrink: 0;
}
.notif-header button {
  font-size: 0.75rem; color: #3b82f6; background: none; border: none; cursor: pointer;
}
.notif-list { overflow-y: auto; flex: 1; }
.notif-item {
  display: flex; gap: 12px; padding: 13px 16px;
  border-bottom: 1px solid #f9fafb; transition: background 0.12s;
}
.notif-item.clickable { cursor: pointer; }
.notif-item.clickable:hover { background: #f0f7ff; }
.notif-item.unread { background: #eff6ff; border-left: 3px solid #3b82f6; }
.notif-item.unread:hover { background: #e0effe; }
.notif-icon { font-size: 1.3rem; flex-shrink: 0; margin-top: 1px; }
.notif-body { flex: 1; min-width: 0; }
.notif-title { font-weight: 600; font-size: 0.85rem; margin: 0 0 3px; color: #111827; }
.notif-msg   { font-size: 0.8rem; color: #6b7280; margin: 0 0 5px; line-height: 1.4; }
.notif-footer { display: flex; justify-content: space-between; align-items: center; }
.notif-time  { font-size: 0.7rem; color: #9ca3af; }
.notif-go    { font-size: 0.72rem; color: #3b82f6; font-weight: 600; }
.empty { text-align: center; padding: 28px 16px; color: #9ca3af; font-size: 0.85rem; }
</style>
