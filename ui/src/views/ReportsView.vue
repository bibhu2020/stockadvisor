<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api'

const reports   = ref<any[]>([])
const selected  = ref<any | null>(null)
const loading   = ref(true)

onMounted(async () => {
  try {
    const res = await api.get('/reports')
    reports.value = res.data
  } finally {
    loading.value = false
  }
})

async function openReport(r: any) {
  const res = await api.get(`/reports/${r.id}`)
  selected.value = res.data
}

function pdfUrl(id: number) {
  const base  = import.meta.env.VITE_API_URL ?? 'http://localhost:3000/api'
  const token = localStorage.getItem('token') ?? ''
  return `${base}/reports/${id}/pdf?token=${encodeURIComponent(token)}`
}

function getPicks(report: any): any[] {
  try { return typeof report.picks === 'string' ? JSON.parse(report.picks) : report.picks || [] }
  catch { return [] }
}

function avgConfidence(report: any) {
  const picks = getPicks(report)
  if (!picks.length) return 0
  return Math.round(picks.reduce((a: number, p: any) => a + (p.confidence_pct || 0), 0) / picks.length)
}

function vixLabel(v: number | null): { label: string; color: string; bg: string; dot: string } {
  if (!v)      return { label: 'N/A',      color: '#6b7280', bg: '#f3f4f6', dot: '#9ca3af' }
  if (v < 15)  return { label: 'Calm',     color: '#15803d', bg: '#dcfce7', dot: '#22c55e' }
  if (v < 25)  return { label: 'Moderate', color: '#92400e', bg: '#fef3c7', dot: '#f59e0b' }
  return        { label: 'Volatile',        color: '#b91c1c', bg: '#fee2e2', dot: '#ef4444' }
}

function confColor(pct: number) {
  if (pct >= 80) return '#15803d'
  if (pct >= 70) return '#d97706'
  return '#dc2626'
}

function formatDate(d: string) {
  const dt = new Date(d + 'T12:00:00')
  return {
    weekday: dt.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase(),
    month:   dt.toLocaleDateString('en-US', { month: 'short' }),
    day:     dt.getDate(),
    year:    dt.getFullYear(),
  }
}

const CHIP_COLORS = [
  { bg: '#ede9fe', color: '#5b21b6', border: '#c4b5fd' },
  { bg: '#dbeafe', color: '#1d4ed8', border: '#93c5fd' },
  { bg: '#fce7f3', color: '#9d174d', border: '#f9a8d4' },
  { bg: '#d1fae5', color: '#065f46', border: '#6ee7b7' },
  { bg: '#ffedd5', color: '#9a3412', border: '#fed7aa' },
]

function gain(p: any) {
  if (!p.entry_price || !p.exit_price) return null
  return (((p.exit_price - p.entry_price) / p.entry_price) * 100).toFixed(0)
}
</script>

<template>
  <div class="page">
    <!-- ── Header ──────────────────────────────────────────────────── -->
    <div class="page-header">
      <div>
        <h2 class="page-h">Analyst Reports</h2>
        <p class="page-sub">AI-generated market analysis and stock picks</p>
      </div>
      <span v-if="reports.length" class="report-count">{{ reports.length }} reports</span>
    </div>

    <!-- ── Loading ─────────────────────────────────────────────────── -->
    <div v-if="loading" class="loading-rows">
      <div v-for="i in 4" :key="i" class="skeleton-row"></div>
    </div>

    <!-- ── Grid ────────────────────────────────────────────────────── -->
    <div v-else-if="reports.length" class="report-grid">

      <!-- Column headers -->
      <div class="grid-header">
        <div class="col-date">Date</div>
        <div class="col-market">Market</div>
        <div class="col-picks">Top Picks</div>
        <div class="col-conf">Confidence</div>
        <div class="col-gain">Avg Target</div>
        <div class="col-actions">Actions</div>
      </div>

      <!-- Data rows -->
      <div class="grid-body">
        <div
          v-for="r in reports"
          :key="r.id"
          class="report-row"
          @click="openReport(r)"
        >
          <!-- Date cell -->
          <div class="col-date">
            <div class="date-pill" :class="{ 'date-today': r.report_date === new Date().toISOString().slice(0,10) }">
              <span class="d-weekday">{{ formatDate(r.report_date).weekday }}</span>
              <span class="d-num">{{ formatDate(r.report_date).day }}</span>
              <span class="d-month">{{ formatDate(r.report_date).month }} {{ formatDate(r.report_date).year }}</span>
            </div>
          </div>

          <!-- Market / VIX cell -->
          <div class="col-market">
            <div class="vix-cell">
              <span class="vix-dot" :style="{ background: vixLabel(r.vix_level).dot }"></span>
              <span class="vix-label" :style="{ color: vixLabel(r.vix_level).color }">{{ vixLabel(r.vix_level).label }}</span>
            </div>
            <span class="vix-num" v-if="r.vix_level">VIX {{ r.vix_level.toFixed(1) }}</span>
          </div>

          <!-- Picks cell -->
          <div class="col-picks">
            <div class="chips-row">
              <span
                v-for="(p, i) in getPicks(r).slice(0, 5)"
                :key="p.symbol"
                class="sym-chip"
                :style="{ background: CHIP_COLORS[i % CHIP_COLORS.length].bg,
                          color:      CHIP_COLORS[i % CHIP_COLORS.length].color,
                          border:     '1px solid ' + CHIP_COLORS[i % CHIP_COLORS.length].border }"
              >{{ p.symbol }}</span>
            </div>
          </div>

          <!-- Confidence cell -->
          <div class="col-conf">
            <div class="conf-wrap">
              <div class="conf-track">
                <div class="conf-fill"
                  :style="{ width: avgConfidence(r) + '%',
                            background: confColor(avgConfidence(r)) }">
                </div>
              </div>
              <span class="conf-val" :style="{ color: confColor(avgConfidence(r)) }">
                {{ avgConfidence(r) }}%
              </span>
            </div>
          </div>

          <!-- Avg target gain cell -->
          <div class="col-gain">
            <span class="gain-badge" v-if="getPicks(r).some((p:any) => gain(p))">
              +{{ Math.round(getPicks(r).reduce((a:number,p:any) => { const g = gain(p); return a + (g ? +g : 0) }, 0) / getPicks(r).filter((p:any) => gain(p)).length || 0) }}%
            </span>
            <span v-else class="gain-na">—</span>
          </div>

          <!-- Actions cell -->
          <div class="col-actions" @click.stop>
            <a v-if="r.pdf_path" :href="pdfUrl(r.id)" target="_blank" class="btn-pdf" title="Download PDF">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              PDF
            </a>
            <button class="btn-view" @click.stop="openReport(r)">View →</button>
          </div>

          <!-- Hover glow accent -->
          <div class="row-accent"></div>
        </div>
      </div>
    </div>

    <!-- ── Empty ────────────────────────────────────────────────────── -->
    <div v-else class="empty-state">
      <div class="empty-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="1.5" stroke-linecap="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
      </div>
      <p>No analyst reports yet.</p>
      <span>Trigger the Market Analyst agent from the Admin panel to generate the first report.</span>
    </div>

    <!-- ── Detail Modal ─────────────────────────────────────────────── -->
    <Transition name="modal">
      <div v-if="selected" class="modal-overlay" @click.self="selected = null">
        <div class="modal">

          <div class="modal-head">
            <div class="modal-title-group">
              <div class="modal-date-badge">
                <span>{{ formatDate(selected.report_date).weekday }}</span>
                <strong>{{ formatDate(selected.report_date).day }}</strong>
                <span>{{ formatDate(selected.report_date).month }}</span>
              </div>
              <div>
                <h3>Analyst Report — {{ selected.report_date }}</h3>
                <p class="modal-meta">{{ getPicks(selected).length }} picks · VIX {{ selected.vix_level?.toFixed(1) ?? 'N/A' }} · {{ vixLabel(selected.vix_level).label }}</p>
              </div>
            </div>
            <div class="modal-head-actions">
              <a v-if="selected.pdf_path" :href="pdfUrl(selected.id)" target="_blank" class="modal-pdf-btn">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Download PDF
              </a>
              <button class="modal-close" @click="selected = null">✕</button>
            </div>
          </div>

          <div class="modal-body">
            <!-- Market summary -->
            <div v-if="selected.market_summary" class="summary-banner">
              <span class="sum-icon">🌐</span>
              <p>{{ selected.market_summary }}</p>
            </div>

            <!-- Picks grid -->
            <div class="picks-grid">
              <div
                v-for="(p, i) in getPicks(selected)"
                :key="p.symbol"
                class="pick-card"
                :style="{ '--accent': CHIP_COLORS[i % CHIP_COLORS.length].color }"
              >
                <!-- Pick header -->
                <div class="pc-head">
                  <div class="pc-identity">
                    <span class="pc-rank" :style="{ background: CHIP_COLORS[i % CHIP_COLORS.length].bg, color: CHIP_COLORS[i % CHIP_COLORS.length].color }">#{{ i+1 }}</span>
                    <strong class="pc-sym">{{ p.symbol }}</strong>
                    <span class="pc-company">{{ p.company }}</span>
                  </div>
                  <div class="pc-tags">
                    <span class="pc-sector">{{ p.sector }}</span>
                    <span class="pc-conf" :style="{ background: confColor(p.confidence_pct) + '18', color: confColor(p.confidence_pct) }">
                      {{ p.confidence_label }} {{ p.confidence_pct }}%
                    </span>
                  </div>
                </div>

                <!-- Price ribbon -->
                <div class="price-ribbon">
                  <div class="pr-cell">
                    <span class="pr-label">Current</span>
                    <span class="pr-val">${{ (p.current_price ?? p.entry_price)?.toFixed(2) }}</span>
                  </div>
                  <div class="pr-cell">
                    <span class="pr-label">Entry</span>
                    <span class="pr-val">${{ p.entry_price?.toFixed(2) }}</span>
                  </div>
                  <div class="pr-cell pr-stop">
                    <span class="pr-label">Stop Loss</span>
                    <span class="pr-val">${{ p.stop_loss?.toFixed(2) }}</span>
                  </div>
                  <div class="pr-cell pr-target">
                    <span class="pr-label">Target</span>
                    <span class="pr-val">${{ p.exit_price?.toFixed(2) }}</span>
                  </div>
                  <div class="pr-cell pr-gain" v-if="gain(p)">
                    <span class="pr-label">Expected Gain</span>
                    <span class="pr-val">+{{ gain(p) }}%</span>
                  </div>
                  <div class="pr-cell pr-earn">
                    <span class="pr-label">Earnings</span>
                    <span class="pr-val">{{ p.earnings_date || 'N/A' }}</span>
                  </div>
                </div>

                <!-- Analysis -->
                <div v-if="p.thesis || p.reason" class="ab thesis">
                  <div class="ab-label">💡 Thesis</div>
                  <p>{{ p.thesis || p.reason }}</p>
                </div>
                <div class="ab-pair" v-if="p.fundamental_analysis || p.technical_analysis">
                  <div v-if="p.fundamental_analysis" class="ab fund">
                    <div class="ab-label">📊 Fundamentals</div>
                    <p>{{ p.fundamental_analysis }}</p>
                  </div>
                  <div v-if="p.technical_analysis" class="ab tech">
                    <div class="ab-label">📈 Technicals</div>
                    <p>{{ p.technical_analysis }}</p>
                  </div>
                </div>
                <div v-if="p.risks || p.risk_warning" class="ab risk">
                  <div class="ab-label">⚠ Risks</div>
                  <p>{{ p.risks || p.risk_warning }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
/* ── Page ──────────────────────────────────────────────────────────── */
.page { display: flex; flex-direction: column; height: 100%; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 28px; }
.page-h  { font-size: 1.5rem; font-weight: 800; color: #0f172a; margin: 0 0 4px; }
.page-sub { font-size: 0.85rem; color: #94a3b8; margin: 0; }
.report-count {
  padding: 5px 14px; background: #f1f5f9; border-radius: 99px;
  font-size: 0.8rem; font-weight: 700; color: #475569; margin-top: 4px;
}

/* ── Skeleton loader ───────────────────────────────────────────────── */
.loading-rows { display: flex; flex-direction: column; gap: 10px; }
.skeleton-row {
  height: 68px; border-radius: 14px;
  background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
  background-size: 400% 100%;
  animation: shimmer 1.4s infinite;
}
@keyframes shimmer { 0%{background-position:100% 0} 100%{background-position:-100% 0} }

/* ── Grid container ────────────────────────────────────────────────── */
.report-grid { display: flex; flex-direction: column; gap: 0; }

/* Column layout shared by header + rows */
.grid-header,
.report-row {
  display: grid;
  grid-template-columns: 140px 120px 1fr 130px 100px 160px;
  align-items: center;
  gap: 0;
}

/* ── Grid header ───────────────────────────────────────────────────── */
.grid-header {
  padding: 0 16px 10px;
  border-bottom: 2px solid #e2e8f0;
  margin-bottom: 6px;
}
.grid-header > div {
  font-size: 0.68rem; font-weight: 700; color: #94a3b8;
  text-transform: uppercase; letter-spacing: 0.08em;
  padding: 0 8px;
}

/* ── Report row — floating card effect ─────────────────────────────── */
.report-row {
  position: relative;
  background: #fff;
  border: 1px solid #e8edf5;
  border-radius: 14px;
  margin: 5px 0;
  padding: 14px 8px;
  cursor: pointer;
  transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1),
              box-shadow 0.22s ease,
              border-color 0.18s ease,
              background 0.18s ease;
  overflow: hidden;
}
.report-row:hover {
  transform: translateY(-5px);
  box-shadow:
    0 2px 0 0 var(--accent-col, #1e3a5f),
    0 8px 32px rgba(30, 58, 95, 0.13),
    0 2px 8px rgba(30, 58, 95, 0.06);
  border-color: #c7d7f0;
  background: #fafcff;
  z-index: 5;
}
/* Gold accent left bar that slides in on hover */
.row-accent {
  position: absolute; left: 0; top: 10%; bottom: 10%;
  width: 3px; border-radius: 2px;
  background: linear-gradient(180deg, #f59e0b, #f97316);
  transform: scaleY(0);
  transform-origin: center;
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.report-row:hover .row-accent { transform: scaleY(1); }

/* ── Date cell ─────────────────────────────────────────────────────── */
.col-date { padding: 0 8px; }
.date-pill {
  display: flex; flex-direction: column; align-items: flex-start;
  gap: 1px;
}
.d-weekday { font-size: 0.62rem; font-weight: 700; color: #94a3b8; letter-spacing: 0.06em; }
.d-num     { font-size: 1.25rem; font-weight: 800; color: #0f172a; line-height: 1.1; }
.d-month   { font-size: 0.7rem; color: #64748b; }
.date-today .d-num     { color: #1d4ed8; }
.date-today .d-weekday { color: #3b82f6; }

/* ── Market cell ───────────────────────────────────────────────────── */
.col-market { padding: 0 8px; }
.vix-cell { display: flex; align-items: center; gap: 6px; margin-bottom: 3px; }
.vix-dot  { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.vix-label { font-size: 0.78rem; font-weight: 700; }
.vix-num  { font-size: 0.68rem; color: #94a3b8; padding-left: 14px; }

/* ── Picks cell ────────────────────────────────────────────────────── */
.col-picks  { padding: 0 8px; }
.chips-row  { display: flex; flex-wrap: wrap; gap: 5px; }
.sym-chip   {
  padding: 3px 9px; border-radius: 99px;
  font-size: 0.72rem; font-weight: 700;
  transition: transform 0.12s, box-shadow 0.12s;
}
.report-row:hover .sym-chip { transform: scale(1.04); }

/* ── Confidence cell ───────────────────────────────────────────────── */
.col-conf { padding: 0 8px; }
.conf-wrap { display: flex; align-items: center; gap: 8px; }
.conf-track {
  flex: 1; height: 5px; background: #e2e8f0; border-radius: 3px; overflow: hidden;
}
.conf-fill { height: 100%; border-radius: 3px; transition: width 0.8s ease; }
.conf-val  { font-size: 0.78rem; font-weight: 700; min-width: 34px; text-align: right; }

/* ── Gain cell ─────────────────────────────────────────────────────── */
.col-gain { padding: 0 8px; }
.gain-badge {
  display: inline-block; padding: 4px 10px;
  background: #dcfce7; color: #15803d;
  border-radius: 99px; font-size: 0.78rem; font-weight: 800;
  border: 1px solid #bbf7d0;
}
.gain-na { color: #cbd5e1; font-size: 0.85rem; }

/* ── Actions cell ──────────────────────────────────────────────────── */
.col-actions { padding: 0 8px; display: flex; gap: 8px; align-items: center; }
.btn-pdf {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 6px 12px; background: #0f172a; color: #fff;
  border-radius: 8px; font-size: 0.72rem; font-weight: 700;
  text-decoration: none; border: none; cursor: pointer;
  transition: background 0.15s, transform 0.12s;
}
.btn-pdf:hover { background: #1e3a5f; transform: scale(1.05); }
.btn-view {
  padding: 6px 12px; background: #eff6ff; color: #1d4ed8;
  border: 1px solid #bfdbfe; border-radius: 8px;
  font-size: 0.72rem; font-weight: 700; cursor: pointer;
  transition: background 0.15s, transform 0.12s;
}
.btn-view:hover { background: #dbeafe; transform: scale(1.05); }

/* ── Empty ─────────────────────────────────────────────────────────── */
.empty-state { text-align: center; padding: 80px 20px; color: #94a3b8; }
.empty-icon  { margin-bottom: 16px; }
.empty-state p    { font-size: 1rem; font-weight: 600; color: #64748b; margin: 0 0 6px; }
.empty-state span { font-size: 0.85rem; }

/* ── Modal overlay ─────────────────────────────────────────────────── */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(2,6,23,0.6);
  z-index: 200; display: flex; align-items: center; justify-content: center;
  padding: 20px; backdrop-filter: blur(3px);
}
.modal {
  background: #fff; border-radius: 20px;
  width: 100%; max-width: 820px; max-height: 92vh;
  display: flex; flex-direction: column; overflow: hidden;
  box-shadow: 0 32px 80px rgba(0,0,0,0.3);
}
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s, transform 0.2s; }
.modal-enter-from, .modal-leave-to       { opacity: 0; transform: translateY(16px) scale(0.97); }

.modal-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20px 24px; flex-shrink: 0;
  background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
}
.modal-title-group { display: flex; align-items: center; gap: 16px; }
.modal-date-badge  {
  display: flex; flex-direction: column; align-items: center;
  background: rgba(255,255,255,0.12); border-radius: 10px; padding: 8px 12px;
  color: #fff; line-height: 1;
}
.modal-date-badge span  { font-size: 0.62rem; font-weight: 700; letter-spacing: 0.06em; opacity: 0.7; }
.modal-date-badge strong { font-size: 1.6rem; font-weight: 900; margin: 2px 0; }
.modal-head h3   { margin: 0; color: #fff; font-size: 1.1rem; font-weight: 700; }
.modal-meta      { margin: 4px 0 0; color: rgba(255,255,255,0.6); font-size: 0.8rem; }
.modal-head-actions { display: flex; gap: 10px; align-items: center; }
.modal-pdf-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 14px; background: rgba(255,255,255,0.12);
  color: #fff; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px;
  font-size: 0.78rem; font-weight: 700; text-decoration: none;
  transition: background 0.15s;
}
.modal-pdf-btn:hover { background: rgba(255,255,255,0.22); }
.modal-close {
  width: 34px; height: 34px; border-radius: 50%;
  background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.2);
  color: #fff; cursor: pointer; font-size: 0.9rem;
  display: flex; align-items: center; justify-content: center;
  transition: background 0.15s;
}
.modal-close:hover { background: rgba(255,255,255,0.25); }

.modal-body  { overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 16px; }

/* Summary banner */
.summary-banner {
  display: flex; gap: 12px; align-items: flex-start;
  background: #f0f7ff; border: 1px solid #bfdbfe; border-radius: 12px; padding: 14px 16px;
}
.sum-icon { font-size: 1.2rem; flex-shrink: 0; margin-top: 1px; }
.summary-banner p { margin: 0; font-size: 0.85rem; color: #334155; line-height: 1.6; }

/* Picks grid in modal */
.picks-grid { display: flex; flex-direction: column; gap: 16px; }
.pick-card  {
  border: 1px solid #e2e8f0; border-radius: 14px; overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  transition: box-shadow 0.15s;
}
.pick-card:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.08); }

.pc-head {
  padding: 14px 18px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-left: 4px solid var(--accent, #1e3a5f);
  display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px;
}
.pc-identity { display: flex; align-items: center; gap: 8px; }
.pc-rank    {
  font-size: 0.68rem; font-weight: 800; padding: 3px 8px; border-radius: 99px;
}
.pc-sym     { font-size: 1.15rem; font-weight: 800; color: #0f172a; }
.pc-company { font-size: 0.82rem; color: #64748b; }
.pc-tags    { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.pc-sector  { font-size: 0.7rem; background: #f1f5f9; color: #64748b; padding: 3px 9px; border-radius: 99px; border: 1px solid #e2e8f0; }
.pc-conf    { font-size: 0.7rem; font-weight: 700; padding: 3px 10px; border-radius: 99px; }

/* Price ribbon */
.price-ribbon {
  display: flex; border-top: 1px solid #f1f5f9; border-bottom: 1px solid #f1f5f9;
}
.pr-cell {
  flex: 1; min-width: 0; display: flex; flex-direction: column;
  align-items: center; padding: 10px 8px;
  border-right: 1px solid #f1f5f9; background: #fff;
}
.pr-cell:last-child { border-right: none; }
.pr-label { font-size: 0.6rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
.pr-val   { font-size: 0.92rem; font-weight: 800; color: #0f172a; }
.pr-stop   { background: #fff8f8; }
.pr-stop .pr-val { color: #dc2626; }
.pr-target { background: #f0fdf4; }
.pr-target .pr-val { color: #15803d; }
.pr-gain   { background: linear-gradient(135deg, #ecfdf5, #d1fae5); }
.pr-gain .pr-val { color: #15803d; font-size: 1rem; }
.pr-earn .pr-val { font-size: 0.78rem; color: #d97706; font-weight: 700; }

/* Analysis blocks */
.ab { padding: 14px 18px; border-top: 1px solid #f1f5f9; }
.ab-label { font-size: 0.68rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 7px; color: #475569; }
.ab p { margin: 0; font-size: 0.83rem; color: #374151; line-height: 1.7; }
.ab-pair { display: grid; grid-template-columns: 1fr 1fr; }
.ab-pair .ab:first-child { border-right: 1px solid #f1f5f9; }
.thesis { background: #fafbff; }
.thesis .ab-label { color: #1d4ed8; }
.fund   { background: #fafff8; }
.fund .ab-label { color: #15803d; }
.tech   { background: #fafcff; }
.tech .ab-label { color: #0369a1; }
.risk   { background: #fffbf0; }
.risk .ab-label { color: #92400e; }
.risk p { color: #78716c; }

/* ── Tablet (< 900px) ──────────────────────────────────────────── */
@media (max-width: 900px) {
  .grid-header { display: none; }
  .report-row {
    grid-template-columns: 130px 1fr;
    grid-template-rows: auto auto auto;
    grid-template-areas:
      "date    market"
      "picks   picks"
      "conf    actions";
    gap: 8px;
    padding: 14px;
  }
  .col-date    { grid-area: date; }
  .col-market  { grid-area: market; }
  .col-picks   { grid-area: picks; }
  .col-conf    { grid-area: conf; }
  .col-gain    { display: none; }
  .col-actions { grid-area: actions; justify-content: flex-end; }
}

/* ── Mobile (< 768px) ──────────────────────────────────────────── */
@media (max-width: 767px) {
  .report-row { grid-template-columns: auto 1fr; gap: 6px 10px; padding: 12px; }
  .page-h { font-size: 1.2rem; }

  /* Modal: bottom sheet */
  .modal-overlay { padding: 0; align-items: flex-end; }
  .modal         { border-radius: 24px 24px 0 0; max-height: 95vh; }
  .modal-head    { flex-direction: column; gap: 10px; align-items: flex-start; padding: 16px 18px; }
  .modal-head-actions { align-self: flex-end; }
  .modal-title-group  { gap: 12px; }
  .modal-head h3      { font-size: 0.95rem; }
  .modal-body         { padding: 14px 16px; gap: 12px; }

  /* Price ribbon: 3 cells per row */
  .price-ribbon       { flex-wrap: wrap; }
  .pr-cell            { flex: 0 0 33.333%; border-right: none; border-bottom: 1px solid #f1f5f9; }

  /* Modal close button — larger tap target */
  .modal-close { width: 40px; height: 40px; font-size: 1rem; }
}

/* ── Small mobile (< 600px) ────────────────────────────────────── */
@media (max-width: 600px) {
  .ab-pair { grid-template-columns: 1fr; }
  .ab-pair .ab:first-child { border-right: none; }
}
</style>
