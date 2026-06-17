<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart, GaugeChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import api from '../api'

use([CanvasRenderer, BarChart, LineChart, PieChart, GaugeChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])

const summary = ref({ total_trades: 0, wins: 0, losses: 0, win_rate_pct: 0, total_pnl: 0 })
const portfolio = ref({ buying_power: 5000, open_positions: [] as any[] })
const monthlyPnl = ref<any[]>([])
const portfolioHistory = ref<any[]>([])
const sectorBreakdown = ref<any[]>([])
const agentStatus = ref<any[]>([])
const recentTx = ref<any[]>([])

onMounted(async () => {
  const [sum, port, pnl, hist, sector, agents, tx] = await Promise.all([
    api.get('/transactions/summary'),
    api.get('/portfolio/current'),
    api.get('/dashboard/monthly-pnl'),
    api.get('/dashboard/portfolio-value'),
    api.get('/dashboard/sector-breakdown'),
    api.get('/dashboard/agent-status'),
    api.get('/transactions?action=SELL'),
  ])
  summary.value = sum.data
  portfolio.value = port.data
  monthlyPnl.value = pnl.data
  portfolioHistory.value = hist.data
  sectorBreakdown.value = sector.data
  agentStatus.value = agents.data || []
  recentTx.value = tx.data.slice(0, 10)
})

const pnlChartOption = () => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['P&L ($)'] },
  xAxis: { type: 'category', data: monthlyPnl.value.map((d: any) => d.month) },
  yAxis: { type: 'value', axisLabel: { formatter: '${value}' } },
  series: [{
    name: 'P&L ($)', type: 'bar',
    data: monthlyPnl.value.map((d: any) => ({
      value: d.realized_pnl,
      itemStyle: { color: d.realized_pnl >= 0 ? '#27ae60' : '#e74c3c' }
    })),
  }],
})

const portfolioChartOption = () => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: portfolioHistory.value.map((d: any) => d.snapshot_at?.slice(0,10)) },
  yAxis: { type: 'value', axisLabel: { formatter: '${value}' } },
  series: [{ name: 'Portfolio Value', type: 'line', smooth: true, data: portfolioHistory.value.map((d: any) => d.total_value), areaStyle: { opacity: 0.1 }, itemStyle: { color: '#1e3a5f' } }],
})

const sectorChartOption = () => ({
  tooltip: { trigger: 'item', formatter: '{b}: ${c}' },
  legend: { orient: 'vertical', right: 10 },
  series: [{
    type: 'pie', radius: ['40%', '70%'],
    data: sectorBreakdown.value.map((d: any) => ({ name: d.symbol, value: Math.abs(d.pnl) })),
  }],
})

const winRateOption = () => ({
  series: [{
    type: 'gauge',
    startAngle: 180, endAngle: 0,
    min: 0, max: 100,
    progress: { show: true, width: 18 },
    axisLine: { lineStyle: { width: 18 } },
    axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false },
    pointer: { show: false },
    detail: { valueAnimation: true, formatter: '{value}%', fontSize: 22, fontWeight: 700, offsetCenter: [0, '-20%'] },
    data: [{ value: summary.value.win_rate_pct, name: 'Win Rate' }],
  }],
})

function statusColor(s: string) {
  return { completed: '#27ae60', running: '#f39c12', failed: '#e74c3c', pending: '#95a5a6' }[s] ?? '#95a5a6'
}
</script>

<template>
  <div>
    <h2 class="page-h">Executive Dashboard</h2>

    <!-- KPI Cards -->
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-label">Buying Power</div>
        <div class="kpi-value green">${{ portfolio.buying_power.toLocaleString() }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Open Positions</div>
        <div class="kpi-value">{{ portfolio.open_positions.length }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Total P&L</div>
        <div class="kpi-value" :class="summary.total_pnl >= 0 ? 'green' : 'red'">
          ${{ summary.total_pnl.toFixed(2) }}
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Win Rate</div>
        <div class="kpi-value">{{ summary.win_rate_pct }}%</div>
      </div>
    </div>

    <!-- Charts Row 1 -->
    <div class="chart-row">
      <div class="chart-card wide">
        <h3>Monthly P&L</h3>
        <VChart v-if="monthlyPnl.length" :option="pnlChartOption()" style="height:240px" autoresize />
        <p v-else class="empty">No trade data yet</p>
      </div>
      <div class="chart-card">
        <h3>Win Rate</h3>
        <VChart :option="winRateOption()" style="height:240px" autoresize />
        <p class="wins-label">{{ summary.wins }}W / {{ summary.losses }}L</p>
      </div>
    </div>

    <!-- Charts Row 2 -->
    <div class="chart-row">
      <div class="chart-card wide">
        <h3>Portfolio Value Over Time</h3>
        <VChart v-if="portfolioHistory.length" :option="portfolioChartOption()" style="height:220px" autoresize />
        <p v-else class="empty">No snapshots yet</p>
      </div>
      <div class="chart-card">
        <h3>P&L by Symbol</h3>
        <VChart v-if="sectorBreakdown.length" :option="sectorChartOption()" style="height:220px" autoresize />
        <p v-else class="empty">No closed trades yet</p>
      </div>
    </div>

    <!-- Agent Status -->
    <div class="section-card">
      <h3>Agent Status</h3>
      <div class="agent-row">
        <div v-for="agent in agentStatus" :key="agent.id" class="agent-card">
          <div class="agent-name">{{ agent.agent_type.replace('_', ' ').toUpperCase() }}</div>
          <div class="agent-status" :style="{ color: statusColor(agent.status) }">● {{ agent.status }}</div>
          <div class="agent-time">{{ agent.finished_at ? new Date(agent.finished_at).toLocaleString() : 'Never' }}</div>
        </div>
        <div v-if="!agentStatus.length" class="empty">No agent runs yet</div>
      </div>
    </div>

    <!-- Recent Transactions -->
    <div class="section-card">
      <h3>Recent Transactions</h3>
      <div class="table-scroll">
      <table class="tx-table" v-if="recentTx.length">
        <thead><tr><th>Symbol</th><th>Action</th><th>Price</th><th>Qty</th><th>P&L</th><th>Date</th></tr></thead>
        <tbody>
          <tr v-for="tx in recentTx" :key="tx.id">
            <td><strong>{{ tx.symbol }}</strong></td>
            <td><span :class="['action-badge', tx.action.toLowerCase()]">{{ tx.action }}</span></td>
            <td>${{ tx.price?.toFixed(2) }}</td>
            <td>{{ tx.quantity }}</td>
            <td :class="tx.realized_pnl > 0 ? 'green' : tx.realized_pnl < 0 ? 'red' : ''">
              {{ tx.realized_pnl != null ? '$' + tx.realized_pnl.toFixed(2) : '—' }}
            </td>
            <td>{{ tx.executed_at?.slice(0,10) }}</td>
          </tr>
        </tbody>
      </table>
      </div>
      <p v-else class="empty">No transactions yet</p>
    </div>
  </div>
</template>

<style scoped>
.page-h { font-size: 1.5rem; font-weight: 700; color: #1e3a5f; margin-bottom: 20px; }
.kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
.kpi-card { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.kpi-label { font-size: 0.8rem; color: #9ca3af; font-weight: 600; text-transform: uppercase; margin-bottom: 8px; }
.kpi-value { font-size: 1.8rem; font-weight: 700; color: #1e3a5f; }
.kpi-value.green { color: #27ae60; }
.kpi-value.red { color: #e74c3c; }
.chart-row { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; margin-bottom: 20px; }
.chart-card { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.chart-card h3 { font-size: 0.95rem; font-weight: 700; color: #374151; margin-bottom: 12px; }
.chart-card.wide { grid-column: span 1; }
.wins-label { text-align: center; font-size: 0.85rem; color: #9ca3af; margin-top: 4px; }
.section-card { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 20px; }
.section-card h3 { font-size: 0.95rem; font-weight: 700; color: #374151; margin-bottom: 16px; }
.agent-row { display: flex; gap: 16px; flex-wrap: wrap; }
.agent-card { background: #f9fafb; border-radius: 8px; padding: 14px 20px; min-width: 180px; }
.agent-name { font-weight: 700; font-size: 0.8rem; color: #374151; margin-bottom: 4px; }
.agent-status { font-size: 0.85rem; font-weight: 600; margin-bottom: 4px; }
.agent-time { font-size: 0.75rem; color: #9ca3af; }
.table-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.tx-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; min-width: 520px; }
.tx-table th { background: #f3f4f6; padding: 8px 12px; text-align: left; font-weight: 600; color: #6b7280; }
.tx-table td { padding: 8px 12px; border-bottom: 1px solid #f3f4f6; }
.action-badge { padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; }
.action-badge.buy { background: #dcfce7; color: #15803d; }
.action-badge.sell { background: #fee2e2; color: #b91c1c; }
.green { color: #27ae60; font-weight: 600; }
.red { color: #e74c3c; font-weight: 600; }
.empty { color: #9ca3af; font-size: 0.875rem; padding: 16px 0; }

@media (max-width: 767px) {
  .page-h { font-size: 1.2rem; margin-bottom: 14px; }
  .kpi-row { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .kpi-card { padding: 14px; }
  .kpi-value { font-size: 1.4rem; }
  .chart-row { grid-template-columns: 1fr; gap: 12px; }
  .section-card { padding: 14px; }
  .agent-card { min-width: 0; flex: 1 1 140px; }
}
</style>
