<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import api from '../api'

const tab = ref<'runs' | 'users' | 'settings'>('runs')
const runs = ref<any[]>([])
const users = ref<any[]>([])
const settingsForm = ref<Record<string, string>>({})
const expandedRun = ref<number | null>(null)
const liveLog = ref<Record<number, string>>({})
const triggering = ref<Record<string, boolean>>({})
const dispatched = ref<Record<string, boolean>>({})
const killing = ref<Record<number, boolean>>({})
const toast = ref<{ msg: string; type: 'success' | 'error' } | null>(null)
const confirm = ref<{ agent: typeof AGENTS[number] } | null>(null)

const AGENTS = [
  { type: 'market_analyst', label: 'Market Analyst', icon: '📋', marketGated: true,
    desc: 'Trend detection · Fundamentals · Technicals · Sentiment → Top 5 picks + PDF' },
  { type: 'paper_trader',   label: 'Paper Trader',   icon: '💱', marketGated: true,
    desc: 'Monitors open positions, books profit/loss, buys new picks from last report' },
  { type: 'retrospective',  label: 'Retrospective',  icon: '🧠', marketGated: false,
    desc: 'Reviews P&L vs SPY and evolves the trading strategy for next month' },
]

// Market hours detection (US Eastern, 9:30 AM–4:00 PM Mon–Fri)
const now = ref(new Date())
let clockInterval: ReturnType<typeof setInterval>

const marketOpen = computed(() => {
  const d = now.value
  const dayOfWeek = d.getDay() // 0=Sun, 6=Sat
  if (dayOfWeek === 0 || dayOfWeek === 6) return false
  // Convert to ET: approximate offset (doesn't handle DST edge days)
  const etOffset = isDST(d) ? -4 : -5
  const etHour = (d.getUTCHours() + etOffset + 24) % 24
  const etMin  = d.getUTCMinutes()
  const etTime = etHour * 60 + etMin
  return etTime >= 9 * 60 + 30 && etTime < 16 * 60
})

function isDST(d: Date): boolean {
  // DST in US: second Sunday of March → first Sunday of November
  const jan = new Date(d.getFullYear(), 0, 1).getTimezoneOffset()
  const jul = new Date(d.getFullYear(), 6, 1).getTimezoneOffset()
  return d.getTimezoneOffset() < Math.max(jan, jul)
}

onMounted(() => {
  fetchRuns()
  clockInterval = setInterval(() => { now.value = new Date() }, 30_000)
})
onUnmounted(() => clearInterval(clockInterval))

async function fetchRuns() {
  const res = await api.get('/agent-runs')
  runs.value = res.data
}

async function fetchUsers() {
  const res = await api.get('/users')
  users.value = res.data
}

async function fetchSettings() {
  const res = await api.get('/settings')
  const map: Record<string, string> = {}
  res.data.forEach((s: any) => { map[s.key] = s.value })
  settingsForm.value = map
}

async function selectTab(t: typeof tab.value) {
  tab.value = t
  if (t === 'users') fetchUsers()
  if (t === 'settings') fetchSettings()
  if (t === 'runs') fetchRuns()
}

function requestTrigger(agent: typeof AGENTS[number]) {
  if (triggering.value[agent.type]) return
  confirm.value = { agent }
}

async function confirmTrigger() {
  const agent = confirm.value?.agent
  confirm.value = null
  if (!agent) return

  triggering.value[agent.type] = true
  try {
    await api.post(`/agent-runs/trigger/${agent.type}`)
    triggering.value[agent.type] = false
    dispatched.value[agent.type] = true
    showToast(`${agent.label} dispatched — GitHub Action starting…`, 'success')

    // Poll every 3s for up to 3 minutes (60 attempts)
    let attempts = 0
    const poll = setInterval(async () => {
      await fetchRuns()
      const hasNew = runs.value.some(
        (r) => r.agent_type === agent.type && ['running', 'pending'].includes(r.status),
      )
      if (hasNew || ++attempts >= 60) {
        clearInterval(poll)
        dispatched.value[agent.type] = false
      }
    }, 3000)
  } catch (err: unknown) {
    triggering.value[agent.type] = false
    const msg = (err as { response?: { data?: { message?: string } } })?.response?.data?.message
    showToast(msg ?? `Failed to trigger ${agent.label}`, 'error')
  }
}

function showToast(msg: string, type: 'success' | 'error') {
  toast.value = { msg, type }
  setTimeout(() => (toast.value = null), 4000)
}

async function expandRun(run: any) {
  if (expandedRun.value === run.id) { expandedRun.value = null; return }
  expandedRun.value = run.id
  liveLog.value[run.id] = run.log || ''
  if (run.status === 'running') streamLog(run.id)
}

function streamLog(id: number) {
  const base = import.meta.env.VITE_API_URL?.replace('/api', '') ?? 'http://localhost:3000'
  const src = new EventSource(`${base}/api/agent-runs/${id}/stream`)
  src.onmessage = (e) => {
    const data = JSON.parse(e.data)
    if (data.log) liveLog.value[id] = (liveLog.value[id] ?? '') + data.log
    if (data.done) { src.close(); fetchRuns() }
  }
  src.onerror = () => src.close()
}

async function killRun(run: any) {
  if (killing.value[run.id]) return
  killing.value[run.id] = true
  try {
    await api.patch(`/agent-runs/${run.id}/kill`)
    showToast(`Run #${run.id} killed`, 'success')
    await fetchRuns()
  } catch {
    showToast(`Failed to kill run #${run.id}`, 'error')
  } finally {
    killing.value[run.id] = false
  }
}

async function approve(id: number) {
  await api.patch(`/users/${id}/approve`)
  showToast('User approved', 'success')
  fetchUsers()
}

async function saveSettings() {
  await api.patch('/settings', settingsForm.value)
  showToast('Settings saved', 'success')
}

function statusColor(s: string) {
  return { completed: '#27ae60', running: '#f39c12', failed: '#e74c3c', pending: '#95a5a6' }[s] ?? '#95a5a6'
}

function lastRunFor(type: string) {
  return runs.value.find((r) => r.agent_type === type)
}
</script>

<template>
  <div class="admin-wrap">
    <!-- Toast -->
    <Transition name="toast">
      <div v-if="toast" :class="['toast', toast.type]">{{ toast.msg }}</div>
    </Transition>

    <!-- Confirm Modal -->
    <Transition name="modal">
      <div v-if="confirm" class="modal-backdrop" @click.self="confirm = null">
        <div class="modal">
          <div class="modal-icon">{{ confirm.agent.icon }}</div>
          <h3 class="modal-title">Force Run {{ confirm.agent.label }}?</h3>
          <p class="modal-body">
            This will dispatch the <strong>{{ confirm.agent.label }}</strong> agent on GitHub Actions immediately
            <span v-if="confirm.agent.marketGated && !marketOpen"> even though the <strong>market is currently closed</strong></span>.
            The run cannot be cancelled once dispatched.
          </p>
          <div class="modal-actions">
            <button class="modal-cancel" @click="confirm = null">Cancel</button>
            <button class="modal-confirm" @click="confirmTrigger">
              ⚡ Yes, Force Run
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <h2 class="page-h">Admin Panel</h2>

    <!-- ── Market Status Banner ─────────────────────────────────── -->
    <div :class="['market-banner', marketOpen ? 'open' : 'closed']">
      <span class="market-dot">●</span>
      <span>US Market: <strong>{{ marketOpen ? 'Open' : 'Closed' }}</strong></span>
      <span class="market-note" v-if="!marketOpen">
        — Market Analyst &amp; Paper Trader will run as Force on the next scheduled slot.
        Admin triggers always force-run.
      </span>
    </div>

    <!-- ── Trigger Bar ──────────────────────────────────────────── -->
    <div class="trigger-bar">
      <div v-for="agent in AGENTS" :key="agent.type" class="trigger-tile"
        :class="{ 'market-gated': !marketOpen, 'tile-dispatched': dispatched[agent.type] }">
        <div class="tile-meta">
          <span class="tile-icon">{{ agent.icon }}</span>
          <div>
            <div class="tile-label">
              {{ agent.label }}
              <span v-if="agent.marketGated" class="market-tag"
                :class="marketOpen ? 'tag-open' : 'tag-closed'">
                {{ marketOpen ? 'Market Open' : 'Market Closed' }}
              </span>
            </div>
            <div class="tile-desc">{{ agent.desc }}</div>
            <div v-if="dispatched[agent.type]" class="tile-waiting">
              <span class="waiting-dot"></span> GitHub Action starting — waiting for run…
            </div>
            <div v-else-if="lastRunFor(agent.type)" class="tile-last">
              Last run:
              <span :style="{ color: statusColor(lastRunFor(agent.type)!.status) }">
                ● {{ lastRunFor(agent.type)!.status }}
              </span>
              &nbsp;{{ lastRunFor(agent.type)!.started_at?.slice(0, 16) }}
            </div>
          </div>
        </div>
        <button
          class="run-btn"
          :class="{ loading: triggering[agent.type] || dispatched[agent.type], 'btn-force': !marketOpen }"
          :disabled="triggering[agent.type] || dispatched[agent.type]"
          @click="requestTrigger(agent)"
        >
          <span v-if="triggering[agent.type]" class="spinner"></span>
          <span v-else-if="dispatched[agent.type]" class="spinner"></span>
          <span v-else-if="!marketOpen">⚡ Force Run</span>
          <span v-else>▶ Run Now</span>
        </button>
      </div>
    </div>

    <!-- ── Tabs ───────────────────────────────────────────────────── -->
    <div class="tabs">
      <button v-for="t in ['runs', 'users', 'settings']" :key="t"
        :class="{ active: tab === t }" @click="selectTab(t as any)">
        {{ t === 'runs' ? 'Agent Run History' : t === 'users' ? 'Users' : 'Settings' }}
      </button>
    </div>

    <!-- Agent Runs -->
    <div v-if="tab === 'runs'" class="panel">
      <div class="panel-toolbar">
        <span class="panel-count">{{ runs.length }} runs</span>
        <button class="refresh-btn" @click="fetchRuns">↻ Refresh</button>
      </div>
      <div v-for="run in runs" :key="run.id" class="run-card">
        <div class="run-header" @click="expandRun(run)">
          <span class="run-type">{{ run.agent_type.replace(/_/g, ' ').toUpperCase() }}</span>
          <span class="run-id">#{{ run.id }}</span>
          <span class="run-status" :style="{ color: statusColor(run.status) }">● {{ run.status }}</span>
          <span class="run-date">{{ run.started_at?.slice(0, 16) }}</span>
          <span class="run-by">{{ run.triggered_by }}</span>
          <span class="duration" v-if="run.finished_at">
            {{ Math.round((new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()) / 1000) }}s
          </span>
          <button
            v-if="['running','pending'].includes(run.status)"
            class="kill-btn"
            :disabled="killing[run.id]"
            @click.stop="killRun(run)"
          >{{ killing[run.id] ? '…' : '✕ Kill' }}</button>
          <span class="chevron">{{ expandedRun === run.id ? '▲' : '▼' }}</span>
        </div>
        <div v-if="expandedRun === run.id" class="run-log">
          <pre>{{ liveLog[run.id] ?? run.log }}</pre>
          <p v-if="run.error" class="run-error">{{ run.error }}</p>
        </div>
      </div>
      <p v-if="!runs.length" class="empty">No agent runs yet — trigger one above.</p>
    </div>

    <!-- Users -->
    <div v-if="tab === 'users'" class="panel">
      <div class="users-table-wrap">
      <table class="users-table">
        <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Since</th><th>Actions</th></tr></thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.name }}</td>
            <td>{{ u.email }}</td>
            <td><span :class="['role-badge', u.role]">{{ u.role }}</span></td>
            <td>{{ u.created_at?.slice(0, 10) }}</td>
            <td>
              <button v-if="u.role === 'pending'" @click="approve(u.id)" class="approve-btn">Approve</button>
              <span v-else class="no-action">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      </div>
    </div>

    <!-- Settings -->
    <div v-if="tab === 'settings'" class="panel">
      <div class="settings-form">
        <div v-for="(val, key) in settingsForm" :key="key" class="setting-row">
          <label>{{ String(key).replace(/_/g, ' ').toUpperCase() }}</label>
          <input v-model="settingsForm[key as string]" type="text" />
        </div>
        <button class="save-btn" @click="saveSettings">Save Settings</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-wrap { position: relative; }
.page-h { font-size: 1.5rem; font-weight: 700; color: #1e3a5f; margin-bottom: 20px; }

/* ── Toast ─────────────────────────────────────────────────────── */
.toast {
  position: fixed; top: 20px; right: 24px; z-index: 999;
  padding: 12px 20px; border-radius: 10px; font-size: 0.875rem; font-weight: 600;
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
}
.toast.success { background: #27ae60; color: #fff; }
.toast.error   { background: #e74c3c; color: #fff; }
.toast-enter-active, .toast-leave-active { transition: all 0.25s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(-10px); }

/* ── Market Banner ─────────────────────────────────────────────── */
.market-banner {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 16px; border-radius: 8px; font-size: 0.82rem;
  margin-bottom: 16px; border: 1px solid;
}
.market-banner.open   { background: #f0fdf4; border-color: #86efac; color: #166534; }
.market-banner.closed { background: #fff7ed; border-color: #fdba74; color: #9a3412; }
.market-dot { font-size: 1rem; }
.market-note { color: inherit; opacity: 0.75; }

/* ── Trigger Bar ───────────────────────────────────────────────── */
.trigger-bar {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px;
  margin-bottom: 24px;
}
@media (max-width: 900px) { .trigger-bar { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .trigger-bar { grid-template-columns: 1fr; } }
.trigger-tile {
  background: #fff; border-radius: 12px; padding: 18px 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06); border: 1px solid #e5e7eb;
  display: flex; flex-direction: column; gap: 14px;
}
.tile-meta { display: flex; gap: 14px; align-items: flex-start; }
.tile-icon { font-size: 1.6rem; flex-shrink: 0; margin-top: 2px; }
.tile-label { font-weight: 700; color: #1e3a5f; margin-bottom: 2px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.market-tag { font-size: 0.65rem; font-weight: 700; padding: 1px 6px; border-radius: 4px; }
.tag-open   { background: #dcfce7; color: #15803d; }
.tag-closed { background: #ffedd5; color: #9a3412; }
.trigger-tile.market-gated { border-color: #fdba74; }
.trigger-tile.tile-dispatched { border-color: #93c5fd; background: #eff6ff; }
.tile-desc { font-size: 0.78rem; color: #9ca3af; line-height: 1.4; margin-bottom: 4px; }
.tile-last { font-size: 0.75rem; color: #6b7280; }
.tile-waiting {
  font-size: 0.75rem; color: #1d4ed8; font-weight: 600;
  display: flex; align-items: center; gap: 6px;
}
.waiting-dot {
  display: inline-block; width: 8px; height: 8px;
  border-radius: 50%; background: #3b82f6;
  animation: pulse 1.2s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.4; transform: scale(0.75); }
}
.run-btn {
  width: 100%; padding: 10px; background: #1e3a5f; color: #fff; border: none;
  border-radius: 8px; font-weight: 600; font-size: 0.875rem; cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  transition: background 0.15s;
}
.run-btn:hover:not(:disabled) { background: #2d4f7c; }
.run-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.run-btn.loading { background: #2d4f7c; }
.run-btn.btn-force { background: #92400e; }
.run-btn.btn-force:hover:not(:disabled) { background: #b45309; }
.spinner {
  width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.4);
  border-top-color: #fff; border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Tabs ─────────────────────────────────────────────────────── */
.tabs { display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 2px solid #e5e7eb; }
.tabs button {
  padding: 10px 20px; background: none; border: none; cursor: pointer;
  font-size: 0.875rem; color: #6b7280; border-bottom: 2px solid transparent; margin-bottom: -2px;
}
.tabs button.active { color: #1e3a5f; font-weight: 700; border-bottom-color: #1e3a5f; }

/* ── Panel ────────────────────────────────────────────────────── */
.panel { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.panel-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.panel-count { font-size: 0.8rem; color: #9ca3af; }
.refresh-btn { padding: 6px 14px; background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 6px; cursor: pointer; font-size: 0.8rem; }
.refresh-btn:hover { background: #e5e7eb; }

/* ── Run Cards ────────────────────────────────────────────────── */
.run-card { border: 1px solid #e5e7eb; border-radius: 10px; margin-bottom: 8px; overflow: hidden; }
.run-header { display: flex; align-items: center; gap: 12px; padding: 12px 16px; cursor: pointer; font-size: 0.85rem; }
.run-header:hover { background: #f9fafb; }
.run-type { font-weight: 700; color: #1e3a5f; min-width: 160px; }
.run-id { color: #d1d5db; font-size: 0.75rem; }
.run-status { font-weight: 600; min-width: 100px; }
.run-date { color: #6b7280; flex: 1; }
.run-by { font-size: 0.72rem; background: #f3f4f6; padding: 2px 8px; border-radius: 4px; color: #6b7280; }
.duration { font-size: 0.72rem; color: #9ca3af; }
.chevron { color: #9ca3af; font-size: 0.75rem; }
.kill-btn {
  padding: 3px 10px; background: #fef2f2; color: #e74c3c;
  border: 1px solid #fecaca; border-radius: 5px; cursor: pointer;
  font-size: 0.75rem; font-weight: 700; white-space: nowrap;
  transition: background 0.15s;
}
.kill-btn:hover:not(:disabled) { background: #e74c3c; color: #fff; border-color: #e74c3c; }
.kill-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.run-log { padding: 0 16px 16px; }
.run-log pre {
  background: #0f172a; color: #e2e8f0; border-radius: 8px; padding: 14px;
  font-size: 0.75rem; max-height: 320px; overflow-y: auto;
  white-space: pre-wrap; word-break: break-all;
}
.run-error { color: #e74c3c; font-size: 0.8rem; margin-top: 8px; padding: 8px 12px; background: #fef2f2; border-radius: 6px; }

/* ── Users ────────────────────────────────────────────────────── */
.users-table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.users-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; min-width: 480px; }
.users-table th { background: #f3f4f6; padding: 10px 12px; text-align: left; font-weight: 600; color: #6b7280; }
.users-table td { padding: 10px 12px; border-bottom: 1px solid #f9fafb; }
.role-badge { padding: 2px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; }
.role-badge.admin   { background: #1e3a5f; color: #fff; }
.role-badge.guest   { background: #dcfce7; color: #15803d; }
.role-badge.pending { background: #fef3c7; color: #92400e; }
.approve-btn { padding: 4px 12px; background: #27ae60; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; }
.no-action { color: #d1d5db; }

/* ── Settings ─────────────────────────────────────────────────── */
.settings-form { max-width: 500px; }
.setting-row { display: flex; align-items: center; gap: 16px; margin-bottom: 14px; flex-wrap: wrap; }
.setting-row label { width: 220px; font-size: 0.8rem; font-weight: 700; color: #374151; flex-shrink: 0; }
.setting-row input { flex: 1; min-width: 0; padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.875rem; }
.save-btn { padding: 10px 24px; background: #1e3a5f; color: #fff; border: none; border-radius: 8px; cursor: pointer; margin-top: 8px; font-weight: 600; }
.save-btn:hover { background: #2d4f7c; }

.empty { color: #9ca3af; text-align: center; padding: 32px 0; font-size: 0.875rem; }

/* ── Confirm Modal ────────────────────────────────────────────── */
.modal-backdrop {
  position: fixed; inset: 0; background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal {
  background: #fff; border-radius: 16px; padding: 32px 28px; max-width: 420px; width: 90%;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2); text-align: center;
}
.modal-icon { font-size: 2.5rem; margin-bottom: 12px; }
.modal-title { font-size: 1.15rem; font-weight: 700; color: #1e3a5f; margin: 0 0 12px; }
.modal-body { font-size: 0.875rem; color: #4b5563; line-height: 1.6; margin: 0 0 24px; }
.modal-actions { display: flex; gap: 12px; justify-content: center; }
.modal-cancel {
  padding: 10px 24px; background: #f3f4f6; border: 1px solid #d1d5db;
  border-radius: 8px; font-size: 0.875rem; font-weight: 600; cursor: pointer; color: #374151;
}
.modal-cancel:hover { background: #e5e7eb; }
.modal-confirm {
  padding: 10px 24px; background: #1e3a5f; color: #fff;
  border: none; border-radius: 8px; font-size: 0.875rem; font-weight: 600; cursor: pointer;
}
.modal-confirm:hover { background: #2d4f7c; }
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-active .modal, .modal-leave-active .modal { transition: transform 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .modal, .modal-leave-to .modal { transform: scale(0.95); }

@media (max-width: 767px) {
  .page-h { font-size: 1.2rem; margin-bottom: 14px; }
  .panel { padding: 14px; }
  .run-header { flex-wrap: wrap; gap: 6px; }
  .run-type { min-width: 0; }
  .run-status { min-width: 0; }
  .tabs button { padding: 8px 14px; font-size: 0.82rem; }
  .setting-row label { width: 100%; }
  .settings-form { max-width: 100%; }
}
</style>
