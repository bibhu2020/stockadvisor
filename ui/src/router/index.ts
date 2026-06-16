import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/login',    name: 'login',    component: () => import('../views/LoginView.vue'),    meta: { public: true, title: 'Sign In' } },
    { path: '/pending',  name: 'pending',  component: () => import('../views/PendingView.vue'),  meta: { public: true, title: 'Pending Approval' } },
    { path: '/',         name: 'dashboard',component: () => import('../views/DashboardView.vue'), meta: { title: 'Dashboard' } },
    { path: '/transactions', name: 'transactions', component: () => import('../views/TransactionsView.vue'), meta: { title: 'Transactions' } },
    { path: '/reports',  name: 'reports',  component: () => import('../views/ReportsView.vue'),   meta: { title: 'Reports' } },
    { path: '/strategies',name: 'strategies',component: () => import('../views/StrategiesView.vue'), meta: { title: 'Strategies' } },
    { path: '/admin',    name: 'admin',    component: () => import('../views/AdminView.vue'),     meta: { admin: true, title: 'Admin' } },
    { path: '/profile',  name: 'profile',  component: () => import('../views/ProfileView.vue'),   meta: { title: 'Profile' } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.afterEach((to) => {
  const page = to.meta.title as string | undefined
  document.title = page ? `${page} | AlphaForge` : 'AlphaForge'
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
