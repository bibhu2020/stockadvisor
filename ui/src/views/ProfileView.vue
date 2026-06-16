<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const auth = useAuthStore()

// Profile form
const name = ref(auth.user?.name ?? '')
const profileMsg = ref<{ text: string; ok: boolean } | null>(null)
const savingProfile = ref(false)

// Password form
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const passwordMsg = ref<{ text: string; ok: boolean } | null>(null)
const savingPassword = ref(false)

const roleColor: Record<string, string> = {
  admin: '#1e3a5f',
  guest: '#15803d',
  pending: '#92400e',
}

const initials = computed(() => {
  const parts = (auth.user?.name ?? '?').trim().split(' ')
  return parts.map((p) => p[0]).join('').slice(0, 2).toUpperCase()
})

async function saveProfile() {
  if (!name.value.trim()) return
  savingProfile.value = true
  profileMsg.value = null
  try {
    const res = await api.patch('/auth/profile', { name: name.value.trim() })
    auth.user = res.data
    profileMsg.value = { text: 'Profile updated.', ok: true }
  } catch (e: any) {
    profileMsg.value = { text: e.response?.data?.message ?? 'Failed to update profile.', ok: false }
  } finally {
    savingProfile.value = false
  }
}

async function savePassword() {
  passwordMsg.value = null
  if (newPassword.value.length < 8) {
    passwordMsg.value = { text: 'New password must be at least 8 characters.', ok: false }
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    passwordMsg.value = { text: 'New passwords do not match.', ok: false }
    return
  }
  savingPassword.value = true
  try {
    const res = await api.patch('/auth/password', {
      currentPassword: currentPassword.value,
      newPassword: newPassword.value,
    })
    passwordMsg.value = { text: res.data.message, ok: true }
    currentPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
  } catch (e: any) {
    passwordMsg.value = { text: e.response?.data?.message ?? 'Failed to change password.', ok: false }
  } finally {
    savingPassword.value = false
  }
}
</script>

<template>
  <div class="profile-page">
    <h2 class="page-h">My Profile</h2>

    <div class="profile-grid">
      <!-- ── Left: Identity card ─────────────────────────────── -->
      <div class="card identity-card">
        <div class="avatar">{{ initials }}</div>
        <div class="identity-name">{{ auth.user?.name }}</div>
        <div class="identity-email">{{ auth.user?.email }}</div>
        <span class="role-badge" :style="{ background: roleColor[auth.user?.role ?? ''] }">
          {{ auth.user?.role }}
        </span>
        <div class="identity-meta">
          <div class="meta-row">
            <span class="meta-label">Member since</span>
            <span class="meta-val">{{ auth.user?.created_at?.slice(0,10) ?? '—' }}</span>
          </div>
        </div>
      </div>

      <!-- ── Right: Forms ───────────────────────────────────── -->
      <div class="forms-col">

        <!-- Edit profile -->
        <div class="card">
          <h3 class="card-h">Edit Profile</h3>
          <div class="field">
            <label>Display Name</label>
            <input v-model="name" type="text" placeholder="Your full name" />
          </div>
          <div class="field">
            <label>Email</label>
            <input :value="auth.user?.email" type="email" disabled class="disabled" />
            <span class="field-hint">Email cannot be changed.</span>
          </div>
          <div v-if="profileMsg" :class="['msg', profileMsg.ok ? 'ok' : 'err']">
            {{ profileMsg.text }}
          </div>
          <button class="btn-primary" :disabled="savingProfile" @click="saveProfile">
            <span v-if="savingProfile" class="spinner"></span>
            {{ savingProfile ? 'Saving…' : 'Save Changes' }}
          </button>
        </div>

        <!-- Change password -->
        <div class="card">
          <h3 class="card-h">Change Password</h3>
          <div class="field">
            <label>Current Password</label>
            <input v-model="currentPassword" type="password" placeholder="••••••••" autocomplete="current-password" />
          </div>
          <div class="field">
            <label>New Password</label>
            <input v-model="newPassword" type="password" placeholder="Min. 8 characters" autocomplete="new-password" />
          </div>
          <div class="field">
            <label>Confirm New Password</label>
            <input v-model="confirmPassword" type="password" placeholder="Repeat new password" autocomplete="new-password" />
            <span v-if="confirmPassword && newPassword !== confirmPassword" class="field-hint err-hint">
              Passwords do not match.
            </span>
          </div>
          <div v-if="passwordMsg" :class="['msg', passwordMsg.ok ? 'ok' : 'err']">
            {{ passwordMsg.text }}
          </div>
          <button
            class="btn-primary"
            :disabled="savingPassword || !currentPassword || !newPassword || !confirmPassword"
            @click="savePassword"
          >
            <span v-if="savingPassword" class="spinner"></span>
            {{ savingPassword ? 'Updating…' : 'Update Password' }}
          </button>
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
.page-h { font-size: 1.5rem; font-weight: 700; color: #1e3a5f; margin-bottom: 24px; }

.profile-grid {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 20px;
  align-items: start;
}

.card {
  background: #fff; border-radius: 14px; padding: 28px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.card-h { font-size: 1rem; font-weight: 700; color: #1e3a5f; margin-bottom: 20px; }

/* Identity card */
.identity-card { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 10px; }
.avatar {
  width: 72px; height: 72px; border-radius: 50%;
  background: #1e3a5f; color: #fff;
  font-size: 1.6rem; font-weight: 800;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 4px;
}
.identity-name  { font-size: 1.1rem; font-weight: 700; color: #111827; }
.identity-email { font-size: 0.82rem; color: #9ca3af; }
.role-badge {
  color: #fff; padding: 3px 14px; border-radius: 99px;
  font-size: 0.78rem; font-weight: 700; text-transform: uppercase;
}
.identity-meta  { width: 100%; margin-top: 8px; border-top: 1px solid #f3f4f6; padding-top: 14px; }
.meta-row       { display: flex; justify-content: space-between; font-size: 0.82rem; margin-bottom: 6px; }
.meta-label     { color: #9ca3af; }
.meta-val       { color: #374151; font-weight: 600; }

/* Forms */
.forms-col { display: flex; flex-direction: column; gap: 20px; }
.field { margin-bottom: 14px; }
.field label { display: block; font-size: 0.82rem; font-weight: 600; color: #374151; margin-bottom: 5px; }
.field input {
  width: 100%; padding: 9px 14px; border: 1px solid #d1d5db;
  border-radius: 8px; font-size: 0.9rem; transition: border-color 0.15s;
}
.field input:focus { outline: none; border-color: #1e3a5f; box-shadow: 0 0 0 3px rgba(30,58,95,0.1); }
.field input.disabled { background: #f9fafb; color: #9ca3af; cursor: not-allowed; }
.field-hint  { display: block; font-size: 0.75rem; color: #9ca3af; margin-top: 4px; }
.err-hint    { color: #e74c3c; }

.msg { padding: 9px 14px; border-radius: 8px; font-size: 0.85rem; margin-bottom: 14px; }
.msg.ok  { background: #eafaf1; color: #27ae60; border: 1px solid #a9dfbf; }
.msg.err { background: #fdedec; color: #e74c3c; border: 1px solid #f5b7b1; }

.btn-primary {
  padding: 10px 24px; background: #1e3a5f; color: #fff;
  border: none; border-radius: 8px; font-weight: 700; font-size: 0.9rem;
  cursor: pointer; display: inline-flex; align-items: center; gap: 8px;
  transition: background 0.15s;
}
.btn-primary:hover:not(:disabled) { background: #2d4f7c; }
.btn-primary:disabled { opacity: 0.55; cursor: not-allowed; }

.spinner {
  width: 13px; height: 13px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff; border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 700px) {
  .profile-grid { grid-template-columns: 1fr; }
}
</style>
