<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'

const route = useRoute()
const strategies = ref<any[]>([])
const expanded = ref<number | null>(null)
const expandedPrompt = ref<string | null>(null)

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

function numericParams(s: any) {
  const p = getParams(s)
  return Object.fromEntries(Object.entries(p).filter(([k]) => k !== 'prompts'))
}

function prompts(s: any): Record<string, string> {
  return getParams(s).prompts || {}
}

const AGENT_LABELS: Record<string, string> = {
  fundamental_analyst: 'Fundamental Analyst',
  technical_analyst:   'Technical Analyst',
  sentiment_analyst:   'Sentiment Analyst',
  synthesizer:         'Synthesizer',
  trade_decision:      'Trade Decision',
}

function formatValue(val: any): string {
  if (Array.isArray(val)) return val.join(', ') || 'Any'
  return String(val)
}

function togglePrompt(key: string) {
  expandedPrompt.value = expandedPrompt.value === key ? null : key
}
</script>

<template>
  <div>
    <h2 class="page-h">Strategy History</h2>

    <div class="notice">
      Strategy parameters and prompts are managed autonomously by the Retrospective Agent.
      A new strategy version is created whenever portfolio returns lag the S&P 500.
    </div>

    <div v-if="strategies.length">
      <div
        v-for="s in strategies" :key="s.id"
        :id="`strategy-${s.id}`"
        class="strategy-card"
        :class="{ active: s.is_active, highlighted: Number(route.query.id) === s.id }"
      >
        <!-- Header -->
        <div class="strategy-header" @click="expanded = expanded === s.id ? null : s.id">
          <div class="header-left">
            <span class="version">v{{ s.version }}</span>
            <strong>{{ s.name }}</strong>
            <span v-if="s.is_active" class="active-badge">Active</span>
            <span class="source-badge" :class="s.source">{{ s.source }}</span>
          </div>
          <div class="header-right">
            <span class="date">{{ s.created_at?.slice(0,10) }}</span>
            <span v-if="s.performance_vs_spy != null" :class="s.performance_vs_spy >= 0 ? 'green' : 'red'">
              vs SPY: ${{ s.performance_vs_spy?.toFixed(2) }}
            </span>
            <span class="chevron">{{ expanded === s.id ? '▲' : '▼' }}</span>
          </div>
        </div>

        <!-- Body -->
        <div v-if="expanded === s.id" class="strategy-body">
          <!-- Description -->
          <div class="section">
            <h4 class="section-title">Strategy Description</h4>
            <p class="desc-text">{{ s.description }}</p>
          </div>

          <!-- Parameters as formatted JSON -->
          <div class="section">
            <h4 class="section-title">Parameters <span class="readonly-tag">read-only</span></h4>
            <pre class="json-body">{{ JSON.stringify(numericParams(s), null, 2) }}</pre>
          </div>

          <!-- Agent Prompts — full-width, edge-to-edge -->
          <div class="section prompts-section">
            <h4 class="section-title px">Agent Prompts <span class="readonly-tag">read-only · tuned by retrospective agent</span></h4>
            <div class="prompts-list">
              <div
                v-for="(text, key) in prompts(s)" :key="key"
                class="prompt-block"
              >
                <div class="prompt-header" @click="togglePrompt(`${s.id}-${key}`)">
                  <span class="prompt-agent">{{ AGENT_LABELS[key] ?? key }}</span>
                  <span class="prompt-len">{{ text.length }} chars</span>
                  <span class="chevron-sm">{{ expandedPrompt === `${s.id}-${key}` ? '▲' : '▼' }}</span>
                </div>
                <pre v-if="expandedPrompt === `${s.id}-${key}`" class="prompt-body">{{ text }}</pre>
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
.page-h { font-size: 1.5rem; font-weight: 700; color: #1e3a5f; margin-bottom: 12px; }

.notice {
  background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px;
  padding: 10px 16px; font-size: 0.82rem; color: #1e40af; margin-bottom: 20px;
}

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
.header-left { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.header-right { display: flex; align-items: center; gap: 16px; font-size: 0.85rem; flex-shrink: 0; flex-wrap: wrap; justify-content: flex-end; }

.version { background: #eff6ff; color: #1d4ed8; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; }
.active-badge { background: #1e3a5f; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }
.source-badge { padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }
.source-badge.initial { background: #fef3c7; color: #92400e; }
.source-badge.retrospective { background: #ede9fe; color: #5b21b6; }
.date { color: #9ca3af; }
.green { color: #27ae60; font-weight: 600; }
.red { color: #e74c3c; font-weight: 600; }
.chevron { color: #9ca3af; }

.strategy-body { padding: 0 20px 20px; border-top: 1px solid #f3f4f6; }

.section { margin-top: 20px; }
/* prompts-section breaks out of the body's side padding to go edge-to-edge */
.prompts-section { margin-left: -20px; margin-right: -20px; margin-bottom: -20px; margin-top: 20px; }
.px { padding-left: 20px; padding-right: 20px; }

.section-title {
  font-size: 0.82rem; font-weight: 700; color: #374151;
  margin-bottom: 10px; display: flex; align-items: center; gap: 8px;
}
.readonly-tag {
  background: #f3f4f6; color: #6b7280; padding: 1px 6px;
  border-radius: 4px; font-size: 0.7rem; font-weight: 500;
}
.desc-text { font-size: 0.875rem; color: #6b7280; line-height: 1.6; }

/* Formatted JSON block for parameters */
.json-body {
  margin: 0;
  padding: 14px 16px;
  background: #1e293b;
  color: #e2e8f0;
  font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
  font-size: 0.78rem;
  line-height: 1.6;
  white-space: pre;
  overflow-x: auto;
  border-radius: 8px;
  box-sizing: border-box;
}

/* Prompts */
.prompts-list { display: flex; flex-direction: column; gap: 0; border-top: 1px solid #e5e7eb; }

.prompt-block { border-bottom: 1px solid #e5e7eb; }
.prompt-header {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 20px; cursor: pointer; background: #f9fafb;
  user-select: none;
}
.prompt-header:hover { background: #f3f4f6; }
.prompt-agent { font-size: 0.82rem; font-weight: 700; color: #1e3a5f; flex: 1; }
.prompt-len { font-size: 0.75rem; color: #9ca3af; }
.chevron-sm { font-size: 0.7rem; color: #9ca3af; }

.prompt-body {
  margin: 0;
  padding: 16px 20px;
  background: #1e293b;
  color: #e2e8f0;
  font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
  font-size: 0.78rem;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
  width: 100%;
  box-sizing: border-box;
  border-top: 1px solid #334155;
}

.empty { color: #9ca3af; }

@media (max-width: 767px) {
  .page-h { font-size: 1.2rem; margin-bottom: 10px; }
  .strategy-header { padding: 12px 14px; }
  .strategy-body { padding: 0 14px 14px; }
  .prompts-section { margin-left: -14px; margin-right: -14px; margin-bottom: -14px; }
  .px { padding-left: 14px; padding-right: 14px; }
  .header-right { gap: 10px; }
  .prompt-body { font-size: 0.72rem; padding: 12px 14px; }
  .prompt-header { padding: 10px 14px; }
  .json-body { font-size: 0.72rem; }
}
</style>
