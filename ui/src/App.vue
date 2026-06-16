<script setup lang="ts">
import { RouterView, useRoute } from 'vue-router'
import { computed, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from './stores/auth'
import { useNotificationsStore } from './stores/notifications'
import AppLayout from './components/AppLayout.vue'

const route = useRoute()
const auth = useAuthStore()
const notifs = useNotificationsStore()

const isPublicPage = computed(() =>
  route.meta.public === true || !auth.isLoggedIn
)

let pollInterval: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  if (auth.isLoggedIn) {
    notifs.fetchUnreadCount()
    pollInterval = setInterval(() => notifs.fetchUnreadCount(), 60_000)
  }
})
onUnmounted(() => { if (pollInterval) clearInterval(pollInterval) })
</script>

<template>
  <RouterView v-if="isPublicPage" />
  <AppLayout v-else>
    <RouterView />
  </AppLayout>
</template>
