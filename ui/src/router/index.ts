import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/login',    name: 'login',    component: () => import('../views/LoginView.vue'),    meta: { public: true } },
    { path: '/pending',  name: 'pending',  component: () => import('../views/PendingView.vue'),  meta: { public: true } },
    { path: '/',         name: 'dashboard',component: () => import('../views/DashboardView.vue') },
    { path: '/transactions', name: 'transactions', component: () => import('../views/TransactionsView.vue') },
    { path: '/reports',  name: 'reports',  component: () => import('../views/ReportsView.vue') },
    { path: '/strategies',name: 'strategies',component: () => import('../views/StrategiesView.vue') },
    { path: '/admin',    name: 'admin',    component: () => import('../views/AdminView.vue'), meta: { admin: true } },
    { path: '/profile',  name: 'profile',  component: () => import('../views/ProfileView.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.fetchMe()

  if (to.meta.public) return true
  if (!auth.isLoggedIn) return '/login'
  if (auth.isPending) return '/pending'
  if (to.meta.admin && !auth.isAdmin) return '/'
  return true
})

export default router
