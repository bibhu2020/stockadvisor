<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { fmtDateTime } from '../utils/format'
import api from '../api'

const router = useRouter()
const transactions = ref<any[]>([])
const strategyMap = ref<Record<number, { version: number; name: string }>>({})
const marketPrices = ref<Record<string, number | null>>({})
const loading = ref(false)
const pricesLoading = ref(false)
const filters = ref({ symbol: '', action: '', from: '', to: '', pnl: '' })

async function load() {
  loading.value = true
  const params = Object.fromEntries(Object.entries(filters.value).filter(([_, v]) => v))
  const [txRes, stRes] = await Promise.all([
    api.get('/transactions', { params }),
    api.get('/strategies'),
  ])
  transactions.value = txRes.data
  strategyMap.value = Object.fromEntries(
    stRes.data.map((s: any) => [s.id, { version: s.version, name: s.name }])
  )
  loading.value = false
  fetchMarketPrices()
}

async function fetchMarketPrices() {
  const symbols = [...new Set(transactions.value.map((t: any) => t.symbol as string))]
  if (!symbols.length) return
  pricesLoading.value = true
  try {
    const res = await api.get('/transactions/market-prices', { params: { symbols: symbols.join(',') } })
    marketPrices.value = res.data
  } finally {
    pricesLoading.value = false
  }
}

function priceChange(tx: any) {
  const mkt = marketPrices.value[tx.symbol]
  if (mkt == null || tx.price == null) return null
  return ((mkt - tx.price) / tx.price) * 100
}

function goToStrategy(strategyId: number) {
  router.push({ path: '/strategies', query: { id: strategyId } })
}

function closeReasonLabel(reason: string) {
  return {
    profit_target: '✓ Profit Booked',
    stop_loss:     '✕ Stop Loss Hit',
    expired:       '⏱ Expired (30d)',
    manual:        '✋ Manual Close',
  }[reason] ?? reason
}

onMounted(load)

function exportCsv() {
  const headers = ['ID','Symbol','Action','Exec Price','Mkt Price','Qty','Amount','P&L','Reason','Date']
  const rows = transactions.value.map((t) => [
    t.id, t.symbol, t.action, t.price,
    marketPrices.value[t.symbol] ?? '',
    t.quantity, t.amount,
    t.realized_pnl ?? '', t.reason ?? '', t.executed_at?.slice(0,10),
  ])
  const csv = [headers, ...rows].map((r) => r.join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = 'transactions.csv'; a.click()
}
</script>

<template>
  <div>
    <div class="header-row">
      <h2 class="page-h">Transactions</h2>
      <button class="export-btn" @click="exportCsv">Export CSV</button>
    </div>

    <div class="filters">
      <input v-model="filters.symbol" placeholder="Symbol (e.g. AAPL)" @change="load" />
      <select v-model="filters.action" @change="load">
        <option value="">All Actions</option>
        <option>BUY</option><option>SELL</option>
      </select>
      <input v-model="filters.from" type="date" @change="load" />
      <input v-model="filters.to" type="date" @change="load" />
      <select v-model="filters.pnl" @change="load">
        <option value="">All P&L</option>
        <option value="gain">Gains Only</option>
        <option value="loss">Losses Only</option>
      </select>
      <button @click="filters = { symbol:'',action:'',from:'',to:'',pnl:'' }; load()">Reset</button>
    </div>

    <div class="table-card">
      <div v-if="loading" class="loading">Loading...</div>
      <div v-else-if="transactions.length" class="table-scroll">
      <table class="tx-table">
        <thead>
          <tr>
            <th>Symbol</th><th>Action</th><th>Exec Price</th><th>Mkt Price</th><th>Qty</th>
            <th>Entry</th><th>Target</th><th>Stop Loss</th>
            <th>Trigger</th><th>P&L</th><th>Strategy</th><th>Date</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="tx in transactions" :key="tx.id" :class="['tx-row', tx.action.toLowerCase(), { 'row-closed': tx.pos_status === 'closed' }]">
            <td data-label="Symbol"><strong>{{ tx.symbol }}</strong></td>
            <td data-label="Action"><span :class="['badge', tx.action.toLowerCase()]">{{ tx.action }}</span></td>
            <td data-label="Exec Price" class="num">${{ tx.price?.toFixed(2) }}</td>
            <td data-label="Mkt Price" class="num mkt-cell">
              <template v-if="pricesLoading">
                <span class="price-loading"></span>
              </template>
              <template v-else-if="marketPrices[tx.symbol] != null">
                <span class="mkt-price">${{ (marketPrices[tx.symbol] as number).toFixed(2) }}</span>
                <span
                  v-if="priceChange(tx) != null"
                  :class="['mkt-delta', (priceChange(tx) as number) >= 0 ? 'pos' : 'neg']"
                >{{ (priceChange(tx) as number) >= 0 ? '▲' : '▼' }}{{ Math.abs(priceChange(tx) as number).toFixed(1) }}%</span>
              </template>
              <span v-else class="muted">—</span>
            </td>
            <td data-label="Qty" class="num">{{ tx.quantity }}</td>

            <!-- Position price levels (from linked position) -->
            <td data-label="Entry" class="num muted">
              {{ tx.pos_entry_price != null ? '$' + tx.pos_entry_price.toFixed(2) : '—' }}
            </td>
            <td data-label="Target" class="num green">
              {{ tx.pos_exit_target_price != null ? '$' + tx.pos_exit_target_price.toFixed(2) : '—' }}
            </td>
            <td data-label="Stop Loss" class="num red">
              {{ tx.pos_stop_loss_price != null ? '$' + tx.pos_stop_loss_price.toFixed(2) : '—' }}
            </td>

            <!-- Trigger: what will/did fire the next trade -->
            <td data-label="Trigger">
              <span v-if="tx.pos_close_reason" :class="['trigger-chip', tx.pos_close_reason]">
                {{ closeReasonLabel(tx.pos_close_reason) }}
              </span>
              <span v-else-if="tx.pos_status === 'open'" class="trigger-chip open">
                Watching
              </span>
              <span v-else class="muted">—</span>
            </td>

            <td data-label="P&L" :class="tx.realized_pnl > 0 ? 'green bold' : tx.realized_pnl < 0 ? 'red bold' : 'muted'">
              {{ tx.realized_pnl != null ? (tx.realized_pnl >= 0 ? '+' : '') + '$' + tx.realized_pnl.toFixed(2) : '—' }}
            </td>
            <td data-label="Strategy">
              <button v-if="tx.strategy_id && strategyMap[tx.strategy_id]" class="strat-link" @click="goToStrategy(tx.strategy_id)">
                v{{ strategyMap[tx.strategy_id].version }}
              </button>
              <span v-else class="muted">—</span>
            </td>
            <td data-label="Date" class="muted">{{ fmtDateTime(tx.executed_at) }}</td>
          </tr>
        </tbody>
      </table>
      </div>
      <p v-else class="empty">No transactions match the filters.</p>
    </div>
  </div>
</template>

<style scoped>
.header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
.page-h { font-size: 1.5rem; font-weight: 700; color: #1e3a5f; margin: 0; }
.export-btn { padding: 8px 18px; background: #1e3a5f; color: #fff; border: none; border-radius: 8px; cursor: pointer; }
.filters { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
.filters input, .filters select {
  padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 0.875rem;
}
.filters button { padding: 8px 16px; background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 8px; cursor: pointer; }
.table-card {
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(255,255,255,0.55);
  border-radius: 14px; padding: 18px;
  box-shadow: 0 2px 16px rgba(0,0,0,0.06);
}
.table-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.tx-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; min-width: 860px; }
.tx-table th { background: #f3f4f6; padding: 10px 12px; text-align: left; font-weight: 600; color: #6b7280; }
.tx-table td { padding: 10px 12px; border-bottom: 1px solid #f9fafb; }
.badge { padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; }
.badge.buy { background: #dcfce7; color: #15803d; }
.badge.sell { background: #fee2e2; color: #b91c1c; }
.green { color: #27ae60; font-weight: 600; }
.red { color: #e74c3c; font-weight: 600; }
.reason { color: #6b7280; font-size: 0.8rem; max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.strat-link {
  background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe;
  border-radius: 5px; padding: 2px 9px; font-size: 0.78rem; font-weight: 700;
  cursor: pointer; white-space: nowrap;
}
.strat-link:hover { background: #1d4ed8; color: #fff; }
.num   { font-variant-numeric: tabular-nums; text-align: right; }
.muted { color: #9ca3af; font-size: 0.82rem; }
.green { color: #27ae60; }
.red   { color: #e74c3c; }
.bold  { font-weight: 700; }
.row-closed td { opacity: 0.7; }
.trigger-chip {
  display: inline-block; padding: 2px 8px; border-radius: 5px;
  font-size: 0.72rem; font-weight: 700; white-space: nowrap;
}
.trigger-chip.profit_target { background: #eafaf1; color: #27ae60; }
.trigger-chip.stop_loss     { background: #fdedec; color: #e74c3c; }
.trigger-chip.expired       { background: #fef9e7; color: #f39c12; }
.trigger-chip.manual        { background: #f3f4f6; color: #6b7280; }
.trigger-chip.open          { background: #eff6ff; color: #1d4ed8; }
.empty   { color: #9ca3af; padding: 24px 0; text-align: center; }
.loading { text-align: center; padding: 24px; color: #9ca3af; }
.mkt-cell { white-space: nowrap; }
.mkt-price { font-weight: 600; color: #0f172a; }
.mkt-delta { display: inline-block; margin-left: 4px; font-size: 0.72rem; font-weight: 700; }
.mkt-delta.pos { color: #15803d; }
.mkt-delta.neg { color: #dc2626; }
.price-loading {
  display: inline-block; width: 44px; height: 10px; border-radius: 4px;
  background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
  background-size: 200% 100%; animation: shimmer 1.2s infinite;
}
@keyframes shimmer { 0%{background-position:100% 0} 100%{background-position:-100% 0} }

@media (max-width: 767px) {
  .page-h  { font-size: 1.2rem; }
  .filters { gap: 8px; }
  .filters input, .filters select { font-size: 0.8rem; padding: 7px 10px; flex: 1 1 calc(50% - 4px); }
  .filters button { width: 100%; }

  /* Collapse table into cards */
  .table-card   { padding: 0; background: transparent; box-shadow: none; border: none; }
  .table-scroll { overflow-x: visible; }
  .tx-table     { min-width: 0; }
  .tx-table thead          { display: none; }
  .tx-table, .tx-table tbody { display: block; }

  /* ── Card shell ─────────────────────────────────────── */
  .tx-table tr {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    background: rgba(255,255,255,0.88);
    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(0,0,0,0.07);
    border-left: 4px solid #e2e8f0;
    border-radius: 14px;
    margin-bottom: 10px;
    padding: 12px 14px 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    gap: 0 10px;
  }
  .tx-table tr.buy       { border-left-color: #22c55e; }
  .tx-table tr.sell      { border-left-color: #ef4444; }
  .tx-table tr.row-closed { opacity: 0.62; }

  /* ── All cells ──────────────────────────────────────── */
  .tx-table td {
    display: flex; flex-direction: column;
    padding: 3px 0; border: none; font-size: 0.82rem;
  }
  .tx-table td::before {
    content: attr(data-label);
    font-size: 0.57rem; font-weight: 700; color: #b0bac5;
    text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 2px;
  }

  /* ── Row 1: Symbol (span 2) + Action ─── header ────── */
  .tx-table td[data-label="Symbol"] {
    grid-column: 1 / span 2; grid-row: 1;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(0,0,0,0.06);
    margin-bottom: 6px;
  }
  .tx-table td[data-label="Symbol"] strong {
    font-size: 1.1rem; font-weight: 800; color: #0f172a; letter-spacing: 0.02em;
  }
  .tx-table td[data-label="Action"] {
    grid-column: 3; grid-row: 1;
    align-items: flex-end;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(0,0,0,0.06);
    margin-bottom: 6px;
  }
  .tx-table td[data-label="Action"] .badge {
    font-size: 0.72rem; padding: 3px 10px; border-radius: 6px;
  }

  /* ── Row 2: Exec Price | Qty | Mkt Price ───────────── */
  .tx-table td[data-label="Exec Price"] { grid-column: 1; grid-row: 2; }
  .tx-table td[data-label="Qty"]        { grid-column: 2; grid-row: 2; align-items: center; }
  .tx-table td[data-label="Mkt Price"]  { grid-column: 3; grid-row: 2; align-items: flex-end; }

  /* ── Row 3: P&L | Trigger | Date ─── footer ─────────── */
  .tx-table td[data-label="P&L"] {
    grid-column: 1; grid-row: 3;
    padding-top: 8px; border-top: 1px solid rgba(0,0,0,0.06); margin-top: 6px;
    font-size: 0.9rem; font-weight: 700;
  }
  .tx-table td[data-label="Trigger"] {
    grid-column: 2; grid-row: 3;
    align-items: center;
    padding-top: 8px; border-top: 1px solid rgba(0,0,0,0.06); margin-top: 6px;
  }
  .tx-table td[data-label="Date"] {
    grid-column: 3; grid-row: 3;
    align-items: flex-end;
    padding-top: 8px; border-top: 1px solid rgba(0,0,0,0.06); margin-top: 6px;
  }

  /* ── Hide secondary columns ─────────────────────────── */
  .tx-table td[data-label="Entry"],
  .tx-table td[data-label="Target"],
  .tx-table td[data-label="Stop Loss"],
  .tx-table td[data-label="Strategy"] { display: none; }

  .num { text-align: left; }
}
</style>
