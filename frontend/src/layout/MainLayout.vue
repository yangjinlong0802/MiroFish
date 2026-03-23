<template>
  <div class="app-layout">
    <!-- Global Header -->
    <header class="global-header global-header--minimal">
      <div class="header-brand" @click="router.push('/')">
        AI 推演助手
      </div>
    </header>

    <!-- Step Progress Bar -->
    <nav class="stepper-bar">
      <div
        v-for="(step, i) in steps"
        :key="i"
        class="stepper-item"
        :class="{ active: currentStep === i + 1, completed: currentStep > i + 1 }"
      >
        <span class="stepper-num">{{ String(i + 1).padStart(2, '0') }}</span>
        <span class="stepper-label">{{ step }}</span>
        <span v-if="i < steps.length - 1" class="stepper-connector"></span>
      </div>
    </nav>

    <!-- Content -->
    <div class="layout-content">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const steps = ['图谱构建', '环境搭建', '开始模拟', '报告生成', '深度互动']
const currentStep = computed(() => route.meta.step || 1)
</script>

<style scoped>
.app-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
}

/* ===== Global Header ===== */
.global-header {
  height: 56px;
  background: #0F172A;
  color: #FFF;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  flex-shrink: 0;
}

.global-header--minimal {
  height: 40px;
  justify-content: center;
}

.header-brand {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  font-size: 15px;
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.header-brand:hover {
  opacity: 0.85;
}

/* ===== Stepper Bar ===== */
.stepper-bar {
  height: 48px;
  background: #F8FAFC;
  border-bottom: 1px solid #E2E8F0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  padding: 0 40px;
  flex-shrink: 0;
}

.stepper-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 4px;
  position: relative;
}

.stepper-num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #E2E8F0;
  color: #94A3B8;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.stepper-label {
  font-size: 13px;
  font-weight: 500;
  color: #94A3B8;
  transition: color 0.3s ease;
  white-space: nowrap;
}

.stepper-connector {
  width: 32px;
  height: 1px;
  background: #CBD5E1;
  margin: 0 8px;
  transition: background 0.3s ease;
}

/* Active Step */
.stepper-item.active .stepper-num {
  background: #2563EB;
  color: #FFF;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

.stepper-item.active .stepper-label {
  color: #0F172A;
  font-weight: 600;
}

/* Completed Step */
.stepper-item.completed .stepper-num {
  background: #2563EB;
  color: #FFF;
}

.stepper-item.completed .stepper-label {
  color: #475569;
}

.stepper-item.completed .stepper-connector {
  background: #2563EB;
}

/* ===== Content ===== */
.layout-content {
  flex: 1;
  overflow: hidden;
}
</style>
