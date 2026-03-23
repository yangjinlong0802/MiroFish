<template>
  <div class="main-view">
    <!-- Content Toolbar -->
    <div class="content-toolbar">
      <div class="segmented-control">
        <button
          v-for="mode in ['graph', 'split', 'workbench']"
          :key="mode"
          class="segment-btn"
          :class="{ active: viewMode === mode }"
          @click="viewMode = mode"
        >
          {{ { graph: '图谱', split: '双栏', workbench: '工作台' }[mode] }}
        </button>
      </div>
      <span class="status-indicator" :class="statusClass">
        <span class="dot"></span>
        {{ statusText }}
      </span>
    </div>

    <!-- Main Content Area -->
    <main class="content-area">
      <!-- Left Panel: Graph -->
      <div class="panel-wrapper left" :style="leftPanelStyle">
        <GraphPanel
          :graphData="graphData"
          :loading="graphLoading"
          :currentPhase="3"
          :isSimulating="isSimulating"
          @refresh="refreshGraph"
          @toggle-maximize="toggleMaximize('graph')"
        />
      </div>

      <!-- Right Panel: Step3 开始模拟 -->
      <div class="panel-wrapper right" :style="rightPanelStyle">
        <Step3Simulation
          :simulationId="currentSimulationId"
          :maxRounds="maxRounds"
          :minutesPerRound="minutesPerRound"
          :projectData="projectData"
          :graphData="graphData"
          :systemLogs="systemLogs"
          @go-back="handleGoBack"
          @next-step="handleNextStep"
          @add-log="addLog"
          @update-status="updateStatus"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import GraphPanel from '../components/GraphPanel.vue'
import Step3Simulation from '../components/Step3Simulation.vue'
import { getProject, getGraphData } from '../api/graph'
import { getSimulation, getSimulationConfig, stopSimulation, closeSimulationEnv, getEnvStatus } from '../api/simulation'

const route = useRoute()
const router = useRouter()

// Props
const props = defineProps({
  simulationId: String
})

// Layout State
const viewMode = ref('split')

// Data State
const currentSimulationId = ref(route.params.simulationId)
const maxRounds = ref(route.query.maxRounds ? parseInt(route.query.maxRounds) : null)
const minutesPerRound = ref(30)
const projectData = ref(null)
const graphData = ref(null)
const graphLoading = ref(false)
const systemLogs = ref([])
const currentStatus = ref('processing')

// --- Computed Layout Styles ---
const leftPanelStyle = computed(() => {
  if (viewMode.value === 'graph') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'workbench') return { width: '0%', opacity: 0, transform: 'translateX(-20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})

const rightPanelStyle = computed(() => {
  if (viewMode.value === 'workbench') return { width: '100%', opacity: 1, transform: 'translateX(0)' }
  if (viewMode.value === 'graph') return { width: '0%', opacity: 0, transform: 'translateX(20px)' }
  return { width: '50%', opacity: 1, transform: 'translateX(0)' }
})

// --- Status Computed ---
const statusClass = computed(() => {
  return currentStatus.value
})

const statusText = computed(() => {
  if (currentStatus.value === 'error') return 'Error'
  if (currentStatus.value === 'completed') return 'Completed'
  return 'Running'
})

const isSimulating = computed(() => currentStatus.value === 'processing')

// --- Helpers ---
const addLog = (msg) => {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) + '.' + new Date().getMilliseconds().toString().padStart(3, '0')
  systemLogs.value.push({ time, msg })
  if (systemLogs.value.length > 200) {
    systemLogs.value.shift()
  }
}

const updateStatus = (status) => {
  currentStatus.value = status
}

// --- Layout Methods ---
const toggleMaximize = (target) => {
  if (viewMode.value === target) {
    viewMode.value = 'split'
  } else {
    viewMode.value = target
  }
}

const handleGoBack = async () => {
  addLog('准备返回 Step 2，正在关闭模拟...')

  stopGraphRefresh()

  try {
    const envStatusRes = await getEnvStatus({ simulation_id: currentSimulationId.value })

    if (envStatusRes.success && envStatusRes.data?.env_alive) {
      addLog('正在关闭模拟环境...')
      try {
        await closeSimulationEnv({
          simulation_id: currentSimulationId.value,
          timeout: 10
        })
        addLog('✓ 模拟环境已关闭')
      } catch (closeErr) {
        addLog(`关闭模拟环境失败，尝试强制停止...`)
        try {
          await stopSimulation({ simulation_id: currentSimulationId.value })
          addLog('✓ 模拟已强制停止')
        } catch (stopErr) {
          addLog(`强制停止失败: ${stopErr.message}`)
        }
      }
    } else {
      if (isSimulating.value) {
        addLog('正在停止模拟进程...')
        try {
          await stopSimulation({ simulation_id: currentSimulationId.value })
          addLog('✓ 模拟已停止')
        } catch (err) {
          addLog(`停止模拟失败: ${err.message}`)
        }
      }
    }
  } catch (err) {
    addLog(`检查模拟状态失败: ${err.message}`)
  }

  router.push({ name: 'Simulation', params: { simulationId: currentSimulationId.value } })
}

const handleNextStep = () => {
  addLog('进入 Step 4: 报告生成')
}

// --- Data Logic ---
const loadSimulationData = async () => {
  try {
    addLog(`加载模拟数据: ${currentSimulationId.value}`)

    const simRes = await getSimulation(currentSimulationId.value)
    if (simRes.success && simRes.data) {
      const simData = simRes.data

      try {
        const configRes = await getSimulationConfig(currentSimulationId.value)
        if (configRes.success && configRes.data?.time_config?.minutes_per_round) {
          minutesPerRound.value = configRes.data.time_config.minutes_per_round
          addLog(`时间配置: 每轮 ${minutesPerRound.value} 分钟`)
        }
      } catch (configErr) {
        addLog(`获取时间配置失败，使用默认值: ${minutesPerRound.value}分钟/轮`)
      }

      if (simData.project_id) {
        const projRes = await getProject(simData.project_id)
        if (projRes.success && projRes.data) {
          projectData.value = projRes.data
          addLog(`项目加载成功: ${projRes.data.project_id}`)

          if (projRes.data.graph_id) {
            await loadGraph(projRes.data.graph_id)
          }
        }
      }
    } else {
      addLog(`加载模拟数据失败: ${simRes.error || '未知错误'}`)
    }
  } catch (err) {
    addLog(`加载异常: ${err.message}`)
  }
}

const loadGraph = async (graphId) => {
  if (!isSimulating.value) {
    graphLoading.value = true
  }

  try {
    const res = await getGraphData(graphId)
    if (res.success) {
      graphData.value = res.data
      if (!isSimulating.value) {
        addLog('图谱数据加载成功')
      }
    }
  } catch (err) {
    addLog(`图谱加载失败: ${err.message}`)
  } finally {
    graphLoading.value = false
  }
}

const refreshGraph = () => {
  if (projectData.value?.graph_id) {
    loadGraph(projectData.value.graph_id)
  }
}

// --- Auto Refresh Logic ---
let graphRefreshTimer = null

const startGraphRefresh = () => {
  if (graphRefreshTimer) return
  addLog('开启图谱实时刷新 (30s)')
  graphRefreshTimer = setInterval(refreshGraph, 30000)
}

const stopGraphRefresh = () => {
  if (graphRefreshTimer) {
    clearInterval(graphRefreshTimer)
    graphRefreshTimer = null
    addLog('停止图谱实时刷新')
  }
}

watch(isSimulating, (newValue) => {
  if (newValue) {
    startGraphRefresh()
  } else {
    stopGraphRefresh()
  }
}, { immediate: true })

onMounted(() => {
  addLog('SimulationRunView 初始化')

  if (maxRounds.value) {
    addLog(`自定义模拟轮数: ${maxRounds.value}`)
  }

  loadSimulationData()
})

onUnmounted(() => {
  stopGraphRefresh()
})
</script>

<style scoped>
.main-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #FFF;
  overflow: hidden;
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
}

/* Content Toolbar */
.content-toolbar {
  height: 44px;
  border-bottom: 1px solid #EAEAEA;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: #FFF;
  flex-shrink: 0;
}

/* Segmented Control */
.segmented-control {
  display: inline-flex;
  background: #F1F5F9;
  border-radius: 8px;
  padding: 3px;
  gap: 2px;
}

.segment-btn {
  border: none;
  background: transparent;
  padding: 5px 18px;
  font-size: 12px;
  font-weight: 600;
  color: #64748B;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.25s ease;
  font-family: inherit;
}

.segment-btn:hover {
  color: #334155;
}

.segment-btn.active {
  background: #2563EB;
  color: #FFF;
  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.3);
}

/* Status */
.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #CCC;
}

.status-indicator.processing .dot { background: #2563EB; animation: pulse 1s infinite; }
.status-indicator.completed .dot { background: #4CAF50; }
.status-indicator.error .dot { background: #F44336; }

@keyframes pulse { 50% { opacity: 0.5; } }

/* Content */
.content-area {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
}

.panel-wrapper {
  height: 100%;
  overflow: hidden;
  transition: width 0.4s cubic-bezier(0.25, 0.8, 0.25, 1), opacity 0.3s ease, transform 0.3s ease;
  will-change: width, opacity, transform;
}

.panel-wrapper.left {
  border-right: 1px solid #EAEAEA;
}
</style>
