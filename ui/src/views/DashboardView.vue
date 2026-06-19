<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { fmtDateTime } from '../utils/format'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart, GaugeChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import api from '../api'

use([CanvasRenderer, BarChart, LineChart, PieChart, GaugeChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])

const summary        = ref({ total_trades: 0, wins: 0, losses: 0, win_rate_pct: 0, total_pnl: 0 })
const portfolio      = ref({ buying_power: 5000, open_positions: [] as any[] })
const openPosPrices  = ref<Record<string, number | null>>({})
const pricesLoading  = ref(true)
const monthlyPnl     = ref<any[]>([])
const portfolioHistory = ref<any[]>([])
const sectorBreakdown  = ref<any[]>([])
const agentStatus      = ref<any[]>([])
const recentTx         = ref<any[]>([])

onMounted(async () => {
  const [sum, port, pnl, hist, sector, agents, tx] = await Promise.all([
    api.get('/transactions/summary'),
    api.get('/portfolio/current'),
    api.get('/dashboard/monthly-pnl'),
    api.get('/dashboard/portfolio-value'),
    api.get('/dashboard/sector-breakdown'),
    api.get('/dashboard/agent-status'),
    api.get('/transactions', { params: { action: 'SELL' } }),
  ])
  summary.value        = sum.data
  portfolio.value      = port.data
  monthlyPnl.value     = pnl.data
  portfolioHistory.value = hist.data
  sectorBreakdown.value  = sector.data
  agentStatus.value      = agents.data || []
  recentTx.value         = tx.data.slice(0, 10)

  const positions = port.data.open_positions as any[]
  if (positions.length) {
    const symbols = [...new Set(positions.map((p: any) => p.symbol as string))].join(',')
    try {
      const priceRes = await api.get('/transactions/market-prices', { params: { symbols } })
      openPosPrices.value = priceRes.data
    } catch { /* prices unavailable outside market hours */ }
  }
  pricesLoading.value = false
})

const unrealizedPnl = computed(() =>
  portfolio.value.open_positions.reduce((sum: number, pos: any) => {
    const mkt = openPosPrices.value[pos.symbol]
    return mkt != null ? sum + (mkt - pos.entry_price) * pos.quantity : sum
  }, 0)
)

const openPositionsValue = computed(() =>
  portfolio.value.open_positions.reduce((sum: number, pos: any) => {
    const mkt = openPosPrices.value[pos.symbol]
    return sum + (mkt != null ? mkt * pos.quantity : (pos.cost_basis ?? pos.entry_price * pos.quantity))
  }, 0)
)

const totalPortfolioValue = computed(() => portfolio.value.buying_power + openPositionsValue.value)

function posPnl(pos: any) {
  const mkt = openPosPrices.value[pos.symbol]
  return mkt != null ? (mkt - pos.entry_price) * pos.quantity : null
}
function posPnlPct(pos: any) {
  const mkt = openPosPrices.value[pos.symbol]
  return mkt != null ? ((mkt - pos.entry_price) / pos.entry_price) * 100 : null
}
function daysSince(d: string | Date) {
  const ms = new Date(
    typeof d === 'string' && !d.includes('Z') && !/[+-]\d{2}:\d{2}$/.test(d)
      ? d.replace(' ', 'T') + 'Z'
      : d,
  ).getTime()
  return Math.max(0, Math.floor((Date.now() - ms) / 86400000))
}

const pnlChartOption = () => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 56, right: 12, top: 12, bottom: 28 },
  xAxis: { type: 'category', data: monthlyPnl.value.map((d: any) => d.month), axisLabel: { fontSize: 11 } },
  yAxis: { type: 'value', axisLabel: { formatter: '${value}', fontSize: 11 } },
  series: [{
    name: 'Realized P&L',
    type: 'bar',
    data: monthlyPnl.value.map((d: any) => ({
      value: d.realized_pnl,
      itemStyle: { color: d.realized_pnl >= 0 ? '#22c55e' : '#ef4444', borderRadius: [4,4,0,0] },
    })),
  }],
})

function dedupedPortfolioHistory() {
  // Keep only the last snapshot per calendar day to avoid a cluttered x-axis
  const byDay: Record<string, { date: string; value: number }> = {}
  for (const d of portfolioHistory.value) {
    const raw: string = d.snapshot_at ?? ''
    const day = raw.slice(0, 10) // "2026-06-19" regardless of T or space separator
    if (day) byDay[day] = { date: day, value: parseFloat(d.total_value) }
  }
  return Object.values(byDay).sort((a, b) => a.date.localeCompare(b.date))
}

const portfolioChartOption = () => {
  const pts = dedupedPortfolioHistory()
  return {
    tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].name}<br/>$${Number(p[0].value).toFixed(2)}` },
    grid: { left: 60, right: 12, top: 12, bottom: 28 },
    xAxis: { type: 'category', data: pts.map((d) => d.date), axisLabel: { fontSize: 10, rotate: pts.length > 10 ? 30 : 0 } },
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => '$' + v.toLocaleString(), fontSize: 10 } },
    series: [{
      name: 'Portfolio Value', type: 'line', smooth: true,
      data: pts.map((d) => d.value),
      areaStyle: { opacity: 0.12, color: '#3b82f6' },
      lineStyle: { color: '#3b82f6', width: 2 },
      itemStyle: { color: '#3b82f6' },
      symbol: pts.length <= 5 ? 'circle' : 'none',
      symbolSize: 6,
    }],
  }
}

const sectorChartOption = () => ({
  tooltip: { trigger: 'item', formatter: '{b}: ${c} ({d}%)' },
  legend: { bottom: 0, textStyle: { fontSize: 11 } },
  series: [{
    type: 'pie', radius: ['40%', '68%'], top: '-10%',
    data: sectorBreakdown.value.map((d: any) => ({ name: d.symbol, value: Math.abs(d.pnl) })),
    label: { show: false },
    emphasis: { label: { show: true, fontSize: 13, fontWeight: 700 } },
  }],
})

const winRateOption = () => ({
  series: [{
    type: 'gauge',
    startAngle: 180, endAngle: 0,
    min: 0, max: 100,
    progress: { show: true, width: 14, itemStyle: { color: summary.value.win_rate_pct >= 50 ? '#22c55e' : '#ef4444' } },
    axisLine: { lineStyle: { width: 14, color: [[1, '#f1f5f9']] } },
    axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false },
    pointer: { show: false },
    detail: { valueAnimation: true, formatter: '{value}%', fontSize: 22, fontWeight: 800, offsetCenter: [0, '-15%'], color: summary.value.win_rate_pct >= 50 ? '#22c55e' : '#ef4444' },
    data: [{ value: summary.value.win_rate_pct }],
  }],
})

function statusColor(s: string) {
  return { completed: '#22c55e', running: '#f59e0b', failed: '#ef4444', pending: '#94a3b8' }[s] ?? '#94a3b8'
}

function fmt$(v: number) {
  return '$' + Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
</script>

<template>
  <div>
    <h2 class="page-h">Executive Dashboard</h2>

    <!-- How It Works banner -->
    <RouterLink to="/how-it-works" class="hiw-banner">
      <span class="hiw-icon">💡</span>
      <span class="hiw-text">
        <strong>New here?</strong> Learn how AlphaForge's AI agents research stocks, trade on your behalf, and continuously improve the strategy.
      </span>
      <span class="hiw-cta">How It Works →</span>
    </RouterLink>

    <!-- KPI Cards — 6 metrics -->
    <div class="kpi-row">
      <!-- Total Portfolio Value -->
      <div class="kpi-card kpi-featured">
        <div class="kpi-icon">💼</div>
        <div class="kpi-body">
          <div class="kpi-label">Portfolio Value</div>
          <div class="kpi-value">{{ fmt$(totalPortfolioValue) }}</div>
          <div class="kpi-sub">Cash + open positions</div>
        </div>
      </div>

      <!-- Unrealized P&L -->
      <div class="kpi-card">
        <div class="kpi-icon">📈</div>
        <div class="kpi-body">
          <div class="kpi-label">Unrealized P&L</div>
          <div class="kpi-value" :class="unrealizedPnl >= 0 ? 'green' : 'red'">
            <span v-if="pricesLoading && portfolio.open_positions.length" class="kpi-shimmer"></span>
            <span v-else>{{ unrealizedPnl >= 0 ? '+' : '-' }}{{ fmt$(unrealizedPnl) }}</span>
          </div>
          <div class="kpi-sub">{{ portfolio.open_positions.length }} open position{{ portfolio.open_positions.length !== 1 ? 's' : '' }}</div>
        </div>
      </div>

      <!-- Realized P&L -->
      <div class="kpi-card">
        <div class="kpi-icon">🏦</div>
        <div class="kpi-body">
          <div class="kpi-label">Realized P&L</div>
          <div class="kpi-value" :class="summary.total_pnl >= 0 ? 'green' : 'red'">
            {{ summary.total_pnl >= 0 ? '+' : '-' }}{{ fmt$(summary.total_pnl) }}
          </div>
          <div class="kpi-sub">{{ summary.total_trades }} closed trade{{ summary.total_trades !== 1 ? 's' : '' }}</div>
        </div>
      </div>

      <!-- Buying Power -->
      <div class="kpi-card">
        <div class="kpi-icon">💵</div>
        <div class="kpi-body">
          <div class="kpi-label">Buying Power</div>
          <div class="kpi-value">{{ fmt$(portfolio.buying_power) }}</div>
          <div class="kpi-sub">Available cash</div>
        </div>
      </div>

      <!-- Win Rate -->
      <div class="kpi-card">
        <div class="kpi-icon">🎯</div>
        <div class="kpi-body">
          <div class="kpi-label">Win Rate</div>
          <div class="kpi-value" :class="summary.win_rate_pct >= 50 ? 'green' : 'red'">{{ summary.win_rate_pct }}%</div>
          <div class="kpi-sub">{{ summary.wins }}W / {{ summary.losses }}L</div>
        </div>
      </div>

      <!-- Open Positions -->
      <div class="kpi-card">
        <div class="kpi-icon">🔭</div>
        <div class="kpi-body">
          <div class="kpi-label">Open Positions</div>
          <div class="kpi-value">{{ portfolio.open_positions.length }}</div>
          <div class="kpi-sub">Actively monitored</div>
        </div>
      </div>
    </div>

    <!-- Open Positions Table -->
    <div v-if="portfolio.open_positions.length" class="section-card pos-section">
      <div class="section-hd">
        <h3>Open Positions</h3>
        <span class="live-dot"><span class="dot-pulse"></span>Live</span>
      </div>
      <div class="table-scroll">
        <table class="pos-table">
          <thead>
            <tr>
              <th>Symbol</th><th>Qty</th><th>Entry</th>
              <th>Current</th><th>Unrealized P&L</th>
              <th>Target</th><th>Stop</th><th>Age</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="pos in portfolio.open_positions" :key="pos.id">
              <td><strong class="sym">{{ pos.symbol }}</strong></td>
              <td>{{ pos.quantity }}</td>
              <td class="num">${{ pos.entry_price?.toFixed(2) }}</td>
              <td class="num">
                <span v-if="pricesLoading" class="price-shimmer"></span>
                <span v-else-if="openPosPrices[pos.symbol] != null"
                  :class="(openPosPrices[pos.symbol] as number) >= pos.entry_price ? 'green' : 'red'">
                  ${{ (openPosPrices[pos.symbol] as number).toFixed(2) }}
                </span>
                <span v-else class="muted">—</span>
              </td>
              <td>
                <span v-if="pricesLoading" class="price-shimmer"></span>
                <span v-else-if="posPnl(pos) != null"
                  :class="['pnl-chip', (posPnl(pos) as number) >= 0 ? 'pnl-green' : 'pnl-red']">
                  {{ (posPnl(pos) as number) >= 0 ? '+' : '' }}${{ (posPnl(pos) as number)!.toFixed(2) }}
                  <span class="pnl-pct">({{ (posPnlPct(pos) as number) >= 0 ? '+' : '' }}{{ (posPnlPct(pos) as number)!.toFixed(1) }}%)</span>
                </span>
                <span v-else class="muted">—</span>
              </td>
              <td class="num green">${{ pos.exit_target_price?.toFixed(2) }}</td>
              <td class="num red">${{ pos.stop_loss_price?.toFixed(2) }}</td>
              <td class="muted">{{ daysSince(pos.opened_at) }}d</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Charts Row 1 -->
    <div class="chart-row">
      <div class="chart-card wide">
        <h3>Monthly Realized P&L</h3>
        <VChart v-if="monthlyPnl.length" :option="pnlChartOption()" style="height:220px" autoresize />
        <div v-else class="chart-empty">No closed trade data yet</div>
      </div>
      <div class="chart-card">
        <h3>Win Rate</h3>
        <VChart :option="winRateOption()" style="height:180px" autoresize />
        <p class="wins-label">{{ summary.wins }} wins · {{ summary.losses }} losses</p>
      </div>
    </div>

    <!-- Charts Row 2 -->
    <div class="chart-row">
      <div class="chart-card wide">
        <h3>Portfolio Value Over Time</h3>
        <VChart v-if="dedupedPortfolioHistory().length" :option="portfolioChartOption()" style="height:200px" autoresize />
        <div v-else class="chart-empty">No snapshots yet</div>
      </div>
      <div class="chart-card">
        <h3>P&L by Symbol</h3>
        <VChart v-if="sectorBreakdown.length" :option="sectorChartOption()" style="height:200px" autoresize />
        <div v-else class="chart-empty">No closed trades yet</div>
      </div>
    </div>

    <!-- Agent Status -->
    <div class="section-card">
      <div class="section-hd"><h3>Agent Status</h3></div>
      <div class="agent-row">
        <div v-for="agent in agentStatus" :key="agent.id" class="agent-card">
          <div class="agent-name">{{ agent.agent_type.replace('_', ' ').toUpperCase() }}</div>
          <div class="agent-status" :style="{ color: statusColor(agent.status) }">● {{ agent.status }}</div>
          <div class="agent-time">{{ agent.finished_at ? fmtDateTime(agent.finished_at) : 'Never' }}</div>
        </div>
        <div v-if="!agentStatus.length" class="chart-empty" style="padding:8px 0">No agent runs yet</div>
      </div>
    </div>

    <!-- Recent Closed Trades -->
    <div class="section-card">
      <div class="section-hd"><h3>Recent Closed Trades</h3></div>
      <div v-if="recentTx.length" class="table-scroll">
        <table class="tx-table">
          <thead><tr><th>Symbol</th><th>Price</th><th>Qty</th><th>Realized P&L</th><th>Date</th></tr></thead>
          <tbody>
            <tr v-for="tx in recentTx" :key="tx.id">
              <td><strong>{{ tx.symbol }}</strong></td>
              <td class="num">${{ tx.price?.toFixed(2) }}</td>
              <td>{{ tx.quantity }}</td>
              <td :class="tx.realized_pnl > 0 ? 'green bold' : tx.realized_pnl < 0 ? 'red bold' : 'muted'">
                {{ tx.realized_pnl != null
                  ? (tx.realized_pnl >= 0 ? '+' : '') + '$' + tx.realized_pnl.toFixed(2)
                  : '—' }}
              </td>
              <td class="muted">{{ fmtDateTime(tx.executed_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="chart-empty">No closed trades yet</div>
    </div>
  </div>
</template>

<style scoped>
.page-h { font-size: 1.5rem; font-weight: 700; color: #1e3a5f; margin-bottom: 16px; }

/* ── How It Works banner ─────────────────────────────────────────── */
.hiw-banner {
  display: flex; align-items: center; gap: 14px;
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  border: 1px solid #bfdbfe; border-radius: 12px;
  padding: 12px 16px; margin-bottom: 18px;
  text-decoration: none; color: inherit; transition: box-shadow 0.15s;
}
.hiw-banner:hover { box-shadow: 0 4px 12px rgba(59,130,246,0.18); }
.hiw-icon { font-size: 1.4rem; flex-shrink: 0; }
.hiw-text { flex: 1; font-size: 0.85rem; color: #374151; line-height: 1.5; }
.hiw-text strong { color: #1d4ed8; }
.hiw-cta { font-size: 0.8rem; font-weight: 700; color: #1d4ed8; white-space: nowrap; }

/* ── KPI Row — 6 cards ───────────────────────────────────────────── */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px; margin-bottom: 16px;
}
.kpi-card {
  background: rgba(255,255,255,0.75);
  backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(255,255,255,0.6);
  border-radius: 14px; padding: 14px 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  display: flex; align-items: flex-start; gap: 10px;
}
.kpi-featured { border-color: rgba(59,130,246,0.3); background: rgba(239,246,255,0.85); }
.kpi-icon { font-size: 1.3rem; flex-shrink: 0; margin-top: 2px; }
.kpi-body { min-width: 0; }
.kpi-label { font-size: 0.65rem; color: #94a3b8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 4px; white-space: nowrap; }
.kpi-value { font-size: 1.25rem; font-weight: 800; color: #1e3a5f; line-height: 1.1; }
.kpi-value.green { color: #16a34a; }
.kpi-value.red   { color: #dc2626; }
.kpi-sub  { font-size: 0.68rem; color: #94a3b8; margin-top: 3px; }
.kpi-shimmer {
  display: inline-block; width: 72px; height: 18px; border-radius: 6px; vertical-align: middle;
  background: linear-gradient(90deg, #e2e8f0 25%, #cbd5e1 50%, #e2e8f0 75%);
  background-size: 400% 100%; animation: shimmer 1.4s infinite;
}

/* ── Section cards ───────────────────────────────────────────────── */
.section-card {
  background: rgba(255,255,255,0.75);
  backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(255,255,255,0.6);
  border-radius: 14px; padding: 16px 18px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  margin-bottom: 16px;
}
.section-hd { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.section-hd h3 { font-size: 0.78rem; font-weight: 700; color: #374151; text-transform: uppercase; letter-spacing: 0.06em; margin: 0; }
.live-dot { display: flex; align-items: center; gap: 5px; font-size: 0.68rem; font-weight: 700; color: #16a34a; }
.dot-pulse {
  width: 7px; height: 7px; border-radius: 50%; background: #22c55e;
  animation: pulse 1.8s ease infinite;
}
@keyframes pulse { 0%,100%{box-shadow:0 0 0 0 rgba(34,197,94,0.6)} 50%{box-shadow:0 0 0 5px rgba(34,197,94,0)} }

/* ── Open Positions table ────────────────────────────────────────── */
.pos-section { border-color: rgba(34,197,94,0.2); background: rgba(240,253,244,0.8); }
.table-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.pos-table {
  width: 100%; border-collapse: collapse; font-size: 0.82rem; min-width: 620px;
}
.pos-table th {
  background: rgba(0,0,0,0.03); padding: 8px 12px;
  text-align: left; font-weight: 700; font-size: 0.68rem;
  color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em;
}
.pos-table td { padding: 9px 12px; border-top: 1px solid rgba(0,0,0,0.04); }
.pos-table tr:hover td { background: rgba(255,255,255,0.6); }
.sym { font-size: 0.95rem; }
.pnl-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 0.8rem;
  white-space: nowrap;
}
.pnl-green { background: #dcfce7; color: #15803d; }
.pnl-red   { background: #fee2e2; color: #b91c1c; }
.pnl-pct   { font-size: 0.72rem; font-weight: 600; opacity: 0.85; }
.price-shimmer {
  display: inline-block; width: 52px; height: 12px; border-radius: 4px;
  background: linear-gradient(90deg, #e2e8f0 25%, #cbd5e1 50%, #e2e8f0 75%);
  background-size: 400% 100%; animation: shimmer 1.2s infinite;
}

/* ── Chart cards ─────────────────────────────────────────────────── */
.chart-row { display: grid; grid-template-columns: 2fr 1fr; gap: 12px; margin-bottom: 16px; }
.chart-card {
  background: rgba(255,255,255,0.75);
  backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(255,255,255,0.6);
  border-radius: 14px; padding: 16px 18px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.chart-card h3 { font-size: 0.78rem; font-weight: 700; color: #374151; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.05em; }
.chart-empty { color: #94a3b8; font-size: 0.82rem; padding: 20px 0; text-align: center; }
.wins-label { text-align: center; font-size: 0.75rem; color: #94a3b8; margin: 0; }

/* ── Agent cards ─────────────────────────────────────────────────── */
.agent-row { display: flex; gap: 10px; flex-wrap: wrap; }
.agent-card {
  background: rgba(255,255,255,0.55); border: 1px solid rgba(255,255,255,0.6);
  border-radius: 10px; padding: 10px 16px; min-width: 150px; flex: 1;
}
.agent-name   { font-weight: 700; font-size: 0.75rem; color: #374151; margin-bottom: 3px; }
.agent-status { font-size: 0.8rem; font-weight: 600; margin-bottom: 3px; }
.agent-time   { font-size: 0.68rem; color: #9ca3af; }

/* ── Recent trades table ─────────────────────────────────────────── */
.tx-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; min-width: 400px; }
.tx-table th { background: rgba(0,0,0,0.03); padding: 8px 12px; text-align: left; font-weight: 700; font-size: 0.68rem; color: #6b7280; text-transform: uppercase; }
.tx-table td { padding: 8px 12px; border-top: 1px solid rgba(0,0,0,0.04); }
.tx-table tr:hover td { background: rgba(255,255,255,0.6); }

/* ── Shared ──────────────────────────────────────────────────────── */
.num   { font-variant-numeric: tabular-nums; text-align: right; }
.green { color: #16a34a; }
.red   { color: #dc2626; }
.bold  { font-weight: 700; }
.muted { color: #94a3b8; font-size: 0.8rem; }
@keyframes shimmer { 0%{background-position:100% 0} 100%{background-position:-100% 0} }

/* ── Mobile ──────────────────────────────────────────────────────── */
@media (max-width: 767px) {
  .page-h { font-size: 1.2rem; margin-bottom: 12px; }
  .hiw-banner { flex-wrap: wrap; gap: 8px; padding: 10px 14px; }
  .hiw-cta    { width: 100%; text-align: right; }

  .kpi-row { grid-template-columns: repeat(2, 1fr); gap: 8px; margin-bottom: 12px; }
  .kpi-card { padding: 10px 12px; gap: 8px; }
  .kpi-icon { font-size: 1.1rem; }
  .kpi-value { font-size: 1.05rem; }

  .chart-row { grid-template-columns: 1fr; gap: 10px; margin-bottom: 12px; }
  .section-card { padding: 12px 14px; margin-bottom: 12px; }
  .agent-card { flex: 1 1 140px; }
}

@media (max-width: 480px) {
  .kpi-row { grid-template-columns: 1fr 1fr; }
}
</style>
