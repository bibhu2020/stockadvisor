<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useNotificationsStore } from '../stores/notifications'
import NotificationBell from './NotificationBell.vue'

const auth = useAuthStore()
const router = useRouter()
const sidebarOpen = ref(true)

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-shell">
    <!-- Sidebar -->
    <aside :class="['sidebar', { collapsed: !sidebarOpen }]">
      <div class="logo">
        <svg v-if="sidebarOpen" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 38" class="logo-full">
          <defs>
            <linearGradient id="ibg" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stop-color="#3b82f6"/>
              <stop offset="100%" stop-color="#1e40af"/>
            </linearGradient>
          </defs>
          <rect width="38" height="38" rx="9" fill="url(#ibg)"/>
          <line x1="10" y1="30" x2="19" y2="10" stroke="white" stroke-width="2.8" stroke-linecap="round"/>
          <line x1="19" y1="10" x2="28" y2="30" stroke="white" stroke-width="2.8" stroke-linecap="round"/>
          <line x1="14" y1="22" x2="24" y2="22" stroke="white" stroke-width="2.3" stroke-linecap="round"/>
          <circle cx="19" cy="10" r="2.8" fill="#f59e0b"/>
          <line x1="19" y1="7" x2="19" y2="4" stroke="#f59e0b" stroke-width="2" stroke-linecap="round"/>
          <polygon points="19,2 17,5.5 21,5.5" fill="#f59e0b"/>
          <text x="46" y="15" font-family="Inter,sans-serif" font-size="12" font-weight="800" fill="white" letter-spacing="-0.2">Alpha</text>
          <text x="46" y="29" font-family="Inter,sans-serif" font-size="11" font-weight="400" fill="rgba(255,255,255,0.65)" letter-spacing="1.8">FORGE</text>
        </svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 38 38" class="logo-icon">
          <defs>
            <linearGradient id="ibg2" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stop-color="#3b82f6"/>
              <stop offset="100%" stop-color="#1e40af"/>
            </linearGradient>
          </defs>
          <rect width="38" height="38" rx="9" fill="url(#ibg2)"/>
          <line x1="10" y1="30" x2="19" y2="10" stroke="white" stroke-width="2.8" stroke-linecap="round"/>
          <line x1="19" y1="10" x2="28" y2="30" stroke="white" stroke-width="2.8" stroke-linecap="round"/>
          <line x1="14" y1="22" x2="24" y2="22" stroke="white" stroke-width="2.3" stroke-linecap="round"/>
          <circle cx="19" cy="10" r="2.8" fill="#f59e0b"/>
          <line x1="19" y1="7" x2="19" y2="4" stroke="#f59e0b" stroke-width="2" stroke-linecap="round"/>
          <polygon points="19,2 17,5.5 21,5.5" fill="#f59e0b"/>
        </svg>
      </div>
      <nav class="sidebar-nav">
        <RouterLink to="/"            class="nav-item"><span class="icon">📊</span><span v-if="sidebarOpen">Dashboard</span></RouterLink>
        <RouterLink to="/transactions" class="nav-item"><span class="icon">💱</span><span v-if="sidebarOpen">Transactions</span></RouterLink>
        <RouterLink to="/reports"     class="nav-item"><span class="icon">📋</span><span v-if="sidebarOpen">Reports</span></RouterLink>
        <RouterLink to="/strategies"  class="nav-item"><span class="icon">🧠</span><span v-if="sidebarOpen">Strategies</span></RouterLink>
        <RouterLink v-if="auth.isAdmin" to="/admin" class="nav-item"><span class="icon">⚙️</span><span v-if="sidebarOpen">Admin</span></RouterLink>
      </nav>
      <button class="toggle-btn" @click="sidebarOpen = !sidebarOpen">
        {{ sidebarOpen ? '◀' : '▶' }}
      </button>
    </aside>

    <!-- Main -->
    <div class="main-area">
      <header class="topbar">
        <div class="topbar-left">
          <span class="mobile-brand">AlphaForge</span>
          <h1 class="page-title"></h1>
        </div>
        <div class="topbar-right">
          <NotificationBell />
          <RouterLink to="/profile" class="user-info">
            <span class="user-avatar">{{ (auth.user?.name ?? '?')[0].toUpperCase() }}</span>
            <span class="user-name">{{ auth.user?.name }} <em>({{ auth.user?.role }})</em></span>
          </RouterLink>
          <button class="logout-btn" @click="logout">Logout</button>
        </div>
      </header>
      <main class="content">
        <slot />
      </main>
    </div>

    <!-- Mobile bottom nav -->
    <nav class="bottom-nav">
      <RouterLink to="/"             class="bn-item"><span class="bn-icon">📊</span><span class="bn-label">Dashboard</span></RouterLink>
      <RouterLink to="/transactions" class="bn-item"><span class="bn-icon">💱</span><span class="bn-label">Trades</span></RouterLink>
      <RouterLink to="/reports"      class="bn-item"><span class="bn-icon">📋</span><span class="bn-label">Reports</span></RouterLink>
      <RouterLink to="/strategies"   class="bn-item"><span class="bn-icon">🧠</span><span class="bn-label">Strategy</span></RouterLink>
      <RouterLink v-if="auth.isAdmin" to="/admin" class="bn-item"><span class="bn-icon">⚙️</span><span class="bn-label">Admin</span></RouterLink>
      <RouterLink to="/profile"      class="bn-item"><span class="bn-icon">👤</span><span class="bn-label">Profile</span></RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.app-shell { display: flex; height: 100vh; overflow: hidden; }

/* ── Sidebar (desktop) ─────────────────────────────────────────── */
.sidebar {
  width: 220px; min-width: 220px; background: #1e3a5f; color: #fff;
  display: flex; flex-direction: column; transition: width 0.2s, min-width 0.2s;
}
.sidebar.collapsed { width: 60px; min-width: 60px; }
.logo {
  padding: 12px 12px 10px; border-bottom: 1px solid rgba(255,255,255,0.1);
  white-space: nowrap; overflow: hidden; display: flex; align-items: center;
}
.logo-full  { height: 38px; width: auto; display: block; }
.logo-icon  { height: 36px; width: 36px; display: block; }
.sidebar-nav { flex: 1; padding-top: 12px; }
.nav-item {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 16px; color: rgba(255,255,255,0.8); text-decoration: none;
  white-space: nowrap; overflow: hidden; transition: background 0.15s;
}
.nav-item:hover, .nav-item.router-link-exact-active {
  background: rgba(255,255,255,0.15); color: #fff;
}
.icon { font-size: 1.1rem; flex-shrink: 0; }
.toggle-btn {
  margin: 12px; padding: 8px; background: rgba(255,255,255,0.1);
  border: none; color: #fff; cursor: pointer; border-radius: 6px;
}

/* ── Main area ─────────────────────────────────────────────────── */
.main-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; height: 60px; background: #fff;
  border-bottom: 1px solid #e5e7eb; flex-shrink: 0;
}
.mobile-brand { display: none; font-weight: 800; color: #1e3a5f; font-size: 1rem; }
.topbar-right { display: flex; align-items: center; gap: 16px; }
.user-info {
  display: flex; align-items: center; gap: 8px;
  font-size: 0.875rem; color: #374151; text-decoration: none;
  padding: 4px 10px; border-radius: 8px; transition: background 0.15s;
}
.user-info:hover { background: #f3f4f6; }
.user-info em { color: #9ca3af; font-style: normal; }
.user-avatar {
  width: 32px; height: 32px; border-radius: 50%;
  background: #1e3a5f; color: #fff;
  font-size: 0.8rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.logout-btn {
  padding: 6px 14px; background: #ef4444; color: #fff; border: none;
  border-radius: 6px; cursor: pointer; font-size: 0.875rem;
}
.logout-btn:hover { background: #dc2626; }
.content { flex: 1; overflow-y: auto; padding: 24px; background: #f9fafb; }

/* ── Mobile bottom nav (hidden on desktop) ─────────────────────── */
.bottom-nav { display: none; }

/* ── Mobile breakpoint ─────────────────────────────────────────── */
@media (max-width: 767px) {
  .sidebar    { display: none; }
  .mobile-brand { display: block; }
  .page-title { display: none; }
  .user-name  { display: none; }

  .topbar { padding: 0 14px; height: 52px; }
  .topbar-right { gap: 10px; }
  .logout-btn { padding: 6px 10px; font-size: 0.8rem; }

  .content { padding: 14px 12px; padding-bottom: 76px; }

  .bottom-nav {
    display: flex;
    position: fixed; bottom: 0; left: 0; right: 0;
    background: #1e3a5f;
    border-top: 1px solid rgba(255,255,255,0.12);
    z-index: 200;
    padding-bottom: env(safe-area-inset-bottom, 0px);
  }
  .bn-item {
    flex: 1; display: flex; flex-direction: column; align-items: center;
    padding: 8px 4px 6px; color: rgba(255,255,255,0.6);
    text-decoration: none; min-width: 0;
  }
  .bn-item.router-link-active { color: #fff; }
  .bn-icon  { font-size: 1.25rem; line-height: 1; }
  .bn-label { font-size: 0.6rem; margin-top: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; text-align: center; }
}
</style>
