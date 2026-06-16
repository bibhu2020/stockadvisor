<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const mode = ref<'login' | 'register'>('login')
const email = ref(''), name = ref(''), password = ref(''), error = ref(''), loading = ref(false)

async function submit() {
  error.value = ''; loading.value = true
  try {
    if (mode.value === 'login') {
      await auth.login(email.value, password.value)
      router.push('/')
    } else {
      const res = await auth.register(email.value, name.value, password.value)
      if (res.data.role === 'admin') {
        await auth.login(email.value, password.value)
        router.push('/')
      } else {
        router.push('/pending')
      }
    }
  } catch (e: any) {
    error.value = e.response?.data?.message ?? 'An error occurred'
  } finally { loading.value = false }
}

const features = [
  { icon: '🤖', title: 'AI-Powered Analysis', desc: 'GPT-4o studies trends, fundamentals, technicals & sentiment daily to surface high-confidence picks.' },
  { icon: '📈', title: 'Autonomous Paper Trading', desc: 'Trades execute automatically — buys top picks, monitors positions, books profit & cuts losses.' },
  { icon: '🧠', title: 'Self-Improving Strategy', desc: 'Every month the AI compares performance vs SPY and rewrites its own strategy if it\'s losing.' },
  { icon: '📋', title: 'Daily Research Reports', desc: 'Full PDF analyst reports with entry/exit targets, confidence scores and risk warnings.' },
]

const stats = [
  { value: '6', label: 'AI Sub-Agents' },
  { value: '3×', label: 'Daily Trade Runs' },
  { value: '∞', label: 'Strategy Versions' },
  { value: '0', label: 'Manual Work' },
]

const previewBars = [
  { label: 'Jan', pct: '72%', val: '+8.2%',  color: '#27ae60' },
  { label: 'Feb', pct: '45%', val: '+3.1%',  color: '#27ae60' },
  { label: 'Mar', pct: '20%', val: '−2.4%',  color: '#e74c3c' },
  { label: 'Apr', pct: '90%', val: '+12.4%', color: '#27ae60' },
]

const picks = ['NVDA ▲ 94%', 'MSFT ▲ 87%', 'AMZN ▲ 81%', 'META ▲ 76%', 'AAPL ▲ 72%']
</script>

<template>
  <div class="login-page">
    <!-- ── Left: Feature Showcase ─────────────────────────────── -->
    <div class="showcase">
      <div class="showcase-inner">
        <div class="brand-hero">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" class="brand-svg">
            <defs><linearGradient id="lbg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="rgba(255,255,255,0.25)"/><stop offset="100%" stop-color="rgba(255,255,255,0.08)"/></linearGradient></defs>
            <rect width="48" height="48" rx="12" fill="url(#lbg)" stroke="rgba(255,255,255,0.2)" stroke-width="1"/>
            <line x1="13" y1="38" x2="24" y2="13" stroke="white" stroke-width="3" stroke-linecap="round"/>
            <line x1="24" y1="13" x2="35" y2="38" stroke="white" stroke-width="3" stroke-linecap="round"/>
            <line x1="18" y1="28" x2="30" y2="28" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
            <circle cx="24" cy="13" r="3" fill="#f59e0b"/>
            <line x1="24" y1="9.5" x2="24" y2="6" stroke="#f59e0b" stroke-width="2" stroke-linecap="round"/>
            <polygon points="24,3 21.5,7 26.5,7" fill="#f59e0b"/>
          </svg>
          <h1>AlphaForge</h1>
          <p class="tagline">AI-Powered Trading Intelligence — autonomous market analysis, 24/7.</p>
        </div>

        <!-- Mini dashboard preview -->
        <div class="preview-card">
          <div class="preview-header">
            <span class="preview-dot red"></span>
            <span class="preview-dot yellow"></span>
            <span class="preview-dot green"></span>
            <span class="preview-title">Live Dashboard</span>
          </div>
          <div class="preview-body">
            <div class="preview-kpis">
              <div class="kpi"><div class="kpi-val green-text">+12.4%</div><div class="kpi-lbl">Portfolio Return</div></div>
              <div class="kpi"><div class="kpi-val">$5,842</div><div class="kpi-lbl">Total Value</div></div>
              <div class="kpi"><div class="kpi-val blue-text">68%</div><div class="kpi-lbl">Win Rate</div></div>
              <div class="kpi"><div class="kpi-val orange-text">3</div><div class="kpi-lbl">Open Positions</div></div>
            </div>
            <div class="preview-bars">
              <div class="bar-row" v-for="b in previewBars" :key="b.label">
                <span class="bar-label">{{ b.label }}</span>
                <div class="bar-track"><div class="bar-fill" :style="{ width: b.pct, background: b.color }"></div></div>
                <span class="bar-val" :style="{ color: b.color }">{{ b.val }}</span>
              </div>
            </div>
            <div class="preview-picks">
              <div class="pick-chip" v-for="p in picks" :key="p">{{ p }}</div>
            </div>
          </div>
        </div>

        <!-- Feature list -->
        <div class="features">
          <div class="feature" v-for="f in features" :key="f.title">
            <span class="feature-icon">{{ f.icon }}</span>
            <div>
              <div class="feature-title">{{ f.title }}</div>
              <div class="feature-desc">{{ f.desc }}</div>
            </div>
          </div>
        </div>

        <!-- Stats row -->
        <div class="stats-row">
          <div class="stat" v-for="s in stats" :key="s.label">
            <div class="stat-val">{{ s.value }}</div>
            <div class="stat-label">{{ s.label }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Right: Auth Form ───────────────────────────────────── -->
    <div class="auth-side">
      <div class="auth-card">
        <div class="auth-logo">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 28 28" style="width:28px;height:28px;margin-right:8px">
            <defs><linearGradient id="abg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#1e40af"/><stop offset="100%" stop-color="#1e3a5f"/></linearGradient></defs>
            <rect width="28" height="28" rx="7" fill="url(#abg)"/>
            <line x1="7" y1="22" x2="14" y2="7" stroke="white" stroke-width="2.2" stroke-linecap="round"/>
            <line x1="14" y1="7" x2="21" y2="22" stroke="white" stroke-width="2.2" stroke-linecap="round"/>
            <line x1="10.5" y1="16" x2="17.5" y2="16" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
            <circle cx="14" cy="7" r="2.2" fill="#f59e0b"/>
            <line x1="14" y1="5" x2="14" y2="3" stroke="#f59e0b" stroke-width="1.5" stroke-linecap="round"/>
            <polygon points="14,1.5 12.5,4 15.5,4" fill="#f59e0b"/>
          </svg>
          <span>AlphaForge</span>
        </div>
        <h2 class="auth-title">{{ mode === 'login' ? 'Welcome back' : 'Create account' }}</h2>
        <p class="auth-sub">{{ mode === 'login' ? 'Sign in to your trading dashboard' : 'Get started with AI-powered trading' }}</p>

        <div class="mode-tabs">
          <button :class="{ active: mode === 'login' }" @click="mode = 'login'">Login</button>
          <button :class="{ active: mode === 'register' }" @click="mode = 'register'">Register</button>
        </div>

        <form @submit.prevent="submit">
          <div v-if="mode === 'register'" class="field">
            <label>Full Name</label>
            <input v-model="name" type="text" placeholder="John Doe" required autocomplete="name" />
          </div>
          <div class="field">
            <label>Email</label>
            <input v-model="email" type="email" placeholder="you@example.com" required autocomplete="email" />
          </div>
          <div class="field">
            <label>Password</label>
            <input v-model="password" type="password" placeholder="••••••••" required autocomplete="current-password" />
          </div>
          <p v-if="error" class="error-msg">⚠ {{ error }}</p>
          <button type="submit" class="submit-btn" :disabled="loading">
            <span v-if="loading" class="btn-spinner"></span>
            {{ loading ? 'Please wait…' : mode === 'login' ? 'Sign In' : 'Create Account' }}
          </button>
        </form>

        <p v-if="mode === 'register'" class="auth-note">
          After registration your account requires admin approval before accessing the dashboard.
        </p>

        <div class="auth-switch">
          {{ mode === 'login' ? "Don't have an account?" : 'Already have an account?' }}
          <button @click="mode = mode === 'login' ? 'register' : 'login'">
            {{ mode === 'login' ? 'Register' : 'Sign in' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>


<style scoped>
.login-page {
  display: flex;
  min-height: 100vh;
  width: 100%;
}

/* ── Showcase (left) ──────────────────────────────────────────── */
.showcase {
  flex: 1.1;
  background: linear-gradient(145deg, #0f2744 0%, #1e3a5f 50%, #1a5276 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 40px;
  overflow-y: auto;
}
.showcase-inner {
  max-width: 520px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

/* Brand hero */
.brand-hero { text-align: center; }
.brand-svg  { width: 56px; height: 56px; display: block; margin: 0 auto 12px; }
.brand-hero h1 { font-size: 2rem; font-weight: 800; color: #fff; letter-spacing: -0.5px; }
.tagline { color: rgba(255,255,255,0.65); font-size: 0.95rem; margin-top: 8px; line-height: 1.5; }

/* Mini dashboard preview */
.preview-card {
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 14px;
  overflow: hidden;
  backdrop-filter: blur(6px);
}
.preview-header {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 14px;
  background: rgba(0,0,0,0.2);
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.preview-dot { width: 10px; height: 10px; border-radius: 50%; }
.preview-dot.red    { background: #e74c3c; }
.preview-dot.yellow { background: #f39c12; }
.preview-dot.green  { background: #27ae60; }
.preview-title { font-size: 0.75rem; color: rgba(255,255,255,0.5); margin-left: 6px; }
.preview-body { padding: 16px; display: flex; flex-direction: column; gap: 14px; }

.preview-kpis { display: grid; grid-template-columns: repeat(4,1fr); gap: 8px; }
.kpi { background: rgba(255,255,255,0.06); border-radius: 8px; padding: 10px 6px; text-align: center; }
.kpi-val { font-size: 1rem; font-weight: 700; color: #fff; }
.kpi-lbl { font-size: 0.65rem; color: rgba(255,255,255,0.5); margin-top: 2px; }
.green-text  { color: #2ecc71; }
.blue-text   { color: #5dade2; }
.orange-text { color: #f39c12; }

.preview-bars { display: flex; flex-direction: column; gap: 6px; }
.bar-row { display: flex; align-items: center; gap: 8px; }
.bar-label { width: 26px; font-size: 0.7rem; color: rgba(255,255,255,0.5); }
.bar-track { flex: 1; height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden; }
.bar-fill  { height: 100%; border-radius: 3px; transition: width 0.8s ease; }
.bar-val   { width: 44px; font-size: 0.7rem; font-weight: 600; text-align: right; }

.preview-picks { display: flex; gap: 6px; flex-wrap: wrap; }
.pick-chip {
  background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.15);
  border-radius: 20px; padding: 3px 10px; font-size: 0.72rem; color: #2ecc71; font-weight: 600;
}

/* Features */
.features { display: flex; flex-direction: column; gap: 14px; }
.feature { display: flex; gap: 14px; align-items: flex-start; }
.feature-icon { font-size: 1.5rem; flex-shrink: 0; margin-top: 2px; }
.feature-title { font-size: 0.9rem; font-weight: 700; color: #fff; margin-bottom: 2px; }
.feature-desc  { font-size: 0.78rem; color: rgba(255,255,255,0.55); line-height: 1.5; }

/* Stats */
.stats-row {
  display: grid; grid-template-columns: repeat(4,1fr);
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px; overflow: hidden;
}
.stat { padding: 14px 8px; text-align: center; border-right: 1px solid rgba(255,255,255,0.08); }
.stat:last-child { border-right: none; }
.stat-val   { font-size: 1.4rem; font-weight: 800; color: #5dade2; }
.stat-label { font-size: 0.68rem; color: rgba(255,255,255,0.5); margin-top: 2px; }

/* ── Auth side (right) ────────────────────────────────────────── */
.auth-side {
  width: 420px;
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 32px 32px 32px;
  background: #fff;
  overflow-y: auto;
  height: 100vh;
}
.auth-card { width: 100%; max-width: 360px; padding-top: 8px; }

.auth-logo {
  display: flex; align-items: center; gap: 8px;
  font-size: 1.1rem; font-weight: 700; color: #1e3a5f; margin-bottom: 16px;
}
.auth-logo span { font-size: 1rem; }
.auth-title { font-size: 1.4rem; font-weight: 800; color: #111827; margin-bottom: 2px; }
.auth-sub   { font-size: 0.85rem; color: #6b7280; margin-bottom: 18px; }

.mode-tabs {
  display: flex; border: 1px solid #e5e7eb; border-radius: 8px;
  overflow: hidden; margin-bottom: 18px;
}
.mode-tabs button {
  flex: 1; padding: 8px; border: none; background: none;
  cursor: pointer; font-size: 0.875rem; color: #6b7280; font-weight: 500;
}
.mode-tabs button.active { background: #1e3a5f; color: #fff; font-weight: 700; }

.field { margin-bottom: 12px; }
.field label { display: block; font-size: 0.82rem; font-weight: 600; color: #374151; margin-bottom: 4px; }
.field input {
  width: 100%; padding: 9px 14px;
  border: 1px solid #d1d5db; border-radius: 8px;
  font-size: 0.925rem; transition: border-color 0.15s;
}
.field input:focus { outline: none; border-color: #1e3a5f; box-shadow: 0 0 0 3px rgba(30,58,95,0.1); }

.error-msg {
  font-size: 0.82rem; color: #ef4444;
  background: #fef2f2; border: 1px solid #fecaca;
  border-radius: 6px; padding: 8px 12px; margin-bottom: 14px;
}

.submit-btn {
  width: 100%; padding: 12px; background: #1e3a5f; color: #fff;
  border: none; border-radius: 8px; font-size: 0.95rem; font-weight: 700;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  gap: 8px; transition: background 0.15s;
}
.submit-btn:hover:not(:disabled) { background: #2d4f7c; }
.submit-btn:disabled { opacity: 0.65; cursor: not-allowed; }
.btn-spinner {
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.35);
  border-top-color: #fff; border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.auth-note {
  font-size: 0.78rem; color: #9ca3af; margin-top: 10px;
  line-height: 1.5; text-align: center;
}

.auth-switch {
  margin-top: 14px; text-align: center;
  font-size: 0.82rem; color: #6b7280;
}
.auth-switch button {
  background: none; border: none; color: #1e3a5f; font-weight: 700;
  cursor: pointer; margin-left: 4px; font-size: 0.82rem;
}
.auth-switch button:hover { text-decoration: underline; }

/* ── Responsive ───────────────────────────────────────────────── */
@media (max-width: 900px) {
  .login-page { flex-direction: column; }
  .showcase { padding: 32px 24px; }
  .auth-side { width: 100%; padding: 32px 24px; }
  .preview-kpis { grid-template-columns: repeat(2,1fr); }
  .stats-row { grid-template-columns: repeat(2,1fr); }
  .stat:nth-child(2) { border-right: none; }
}
</style>
