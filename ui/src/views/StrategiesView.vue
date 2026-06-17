<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'

const route = useRoute()
const strategies = ref<any[]>([])
const expanded = ref<number | null>(null)

onMounted(async () => {
  const res = await api.get('/strategies')
  strategies.value = res.data

  const targetId = route.query.id ? Number(route.query.id) : null
  if (targetId) {
    expanded.value = targetId
    await nextTick()
    const el = document.getElementById(`strategy-${targetId}`)
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
})

function getParams(s: any) {
  try { return typeof s.parameters === 'string' ? JSON.parse(s.parameters) : s.parameters }
  catch { return {} }
}
</script>

<template>
  <div>
    <h2 class="page-h">Strategy History</h2>

    <div v-if="strategies.length">
      <div
        v-for="s in strategies" :key="s.id"
        :id="`strategy-${s.id}`"
        class="strategy-card"
        :class="{ active: s.is_active, highlighted: Number(route.query.id) === s.id }"
      >
        <div class="strategy-header" @click="expanded = expanded === s.id ? null : s.id">
          <div>
            <span class="version">v{{ s.version }}</span>
            <strong>{{ s.name }}</strong>
            <span v-if="s.is_active" class="active-badge">Active</span>
            <span class="source-badge" :class="s.source">{{ s.source }}</span>
          </div>
          <div class="right">
            <span class="date">{{ s.created_at?.slice(0,10) }}</span>
            <span v-if="s.performance_vs_spy != null" :class="s.performance_vs_spy >= 0 ? 'green' : 'red'">
              vs SPY: ${{ s.performance_vs_spy?.toFixed(2) }}
            </span>
            <span class="chevron">{{ expanded === s.id ? '▲' : '▼' }}</span>
          </div>
        </div>

        <div v-if="expanded === s.id" class="strategy-body">
          <div class="desc">
            <h4>Strategy Description</h4>
            <p>{{ s.description }}</p>
          </div>
          <div class="params">
            <h4>Parameters</h4>
            <div class="param-grid">
              <div v-for="(val, key) in getParams(s)" :key="key" class="param-item">
                <span class="param-key">{{ key }}</span>
                <span class="param-val">{{ Array.isArray(val) ? val.join(', ') || 'Any' : val }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <p v-else class="empty">No strategies yet. The seed strategy is created when the first agent runs.</p>
  </div>
</template>

<style scoped>
.page-h { font-size: 1.5rem; font-weight: 700; color: #1e3a5f; margin-bottom: 20px; }
.strategy-card {
  background: #fff; border-radius: 12px; margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06); overflow: hidden;
  border: 2px solid #f3f4f6;
}
.strategy-card.active { border-color: #1e3a5f; }
.strategy-card.highlighted { border-color: #1d4ed8; box-shadow: 0 0 0 3px rgba(29,78,216,0.15); }
.strategy-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding: 16px 20px; cursor: pointer; gap: 8px;
}
.strategy-header:hover { background: #f9fafb; }
.version { background: #eff6ff; color: #1d4ed8; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; margin-right: 10px; }
.active-badge { background: #1e3a5f; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; margin-left: 8px; }
.source-badge { padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; margin-left: 8px; }
.source-badge.initial { background: #fef3c7; color: #92400e; }
.source-badge.retrospective { background: #ede9fe; color: #5b21b6; }
.right { display: flex; align-items: center; gap: 16px; font-size: 0.85rem; flex-shrink: 0; flex-wrap: wrap; justify-content: flex-end; }
.date { color: #9ca3af; }
.green { color: #27ae60; font-weight: 600; }
.red { color: #e74c3c; font-weight: 600; }
.chevron { color: #9ca3af; }
.strategy-body { padding: 0 20px 20px; border-top: 1px solid #f3f4f6; }
.desc, .params { margin-top: 16px; }
.desc h4, .params h4 { font-size: 0.85rem; font-weight: 700; color: #374151; margin-bottom: 8px; }
.desc p { font-size: 0.875rem; color: #6b7280; line-height: 1.6; }
.param-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px; }
.param-item { background: #f9fafb; border-radius: 8px; padding: 10px; }
.param-key { display: block; font-size: 0.75rem; color: #9ca3af; font-weight: 600; margin-bottom: 4px; }
.param-val { font-size: 0.875rem; color: #1e3a5f; font-weight: 600; }
.empty { color: #9ca3af; }

@media (max-width: 767px) {
  .page-h { font-size: 1.2rem; margin-bottom: 14px; }
  .strategy-header { padding: 12px 14px; }
  .strategy-body { padding: 0 14px 14px; }
  .right { gap: 10px; }
}
</style>
