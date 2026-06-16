<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

let poll: ReturnType<typeof setInterval>
onMounted(() => {
  poll = setInterval(async () => {
    await auth.fetchMe()
    if (auth.hasAccess) { clearInterval(poll); router.push('/') }
  }, 30_000)
})
onUnmounted(() => clearInterval(poll))
</script>

<template>
  <div class="pending-page">
    <div class="card">
      <div class="icon">⏳</div>
      <h2>Approval Pending</h2>
      <p>Your registration is successful! An admin needs to approve your account before you can access the dashboard.</p>
      <p class="sub">This page will automatically redirect you once approved. Checking every 30 seconds...</p>
      <button @click="auth.logout(); $router.push('/login')" class="logout-btn">Logout</button>
    </div>
  </div>
</template>

<style scoped>
.pending-page {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #1e3a5f 0%, #2d6a4f 100%);
}
.card {
  background: #fff; border-radius: 16px; padding: 48px; max-width: 440px;
  text-align: center; box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}
.icon { font-size: 3rem; margin-bottom: 16px; }
h2 { color: #1e3a5f; margin-bottom: 12px; }
p { color: #6b7280; margin-bottom: 12px; }
.sub { font-size: 0.85rem; color: #9ca3af; }
.logout-btn {
  margin-top: 20px; padding: 10px 24px; background: #ef4444; color: #fff;
  border: none; border-radius: 8px; cursor: pointer;
}
</style>
