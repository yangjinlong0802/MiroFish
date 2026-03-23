import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import MainLayout from '../layout/MainLayout.vue'
import Process from '../views/MainView.vue'
import SimulationView from '../views/SimulationView.vue'
import SimulationRunView from '../views/SimulationRunView.vue'
import ReportView from '../views/ReportView.vue'
import InteractionView from '../views/InteractionView.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/',
    component: MainLayout,
    children: [
      {
        path: 'process/:projectId',
        name: 'Process',
        component: Process,
        props: true,
        meta: { step: 1 }
      },
      {
        path: 'simulation/:simulationId',
        name: 'Simulation',
        component: SimulationView,
        props: true,
        meta: { step: 2 }
      },
      {
        path: 'simulation/:simulationId/start',
        name: 'SimulationRun',
        component: SimulationRunView,
        props: true,
        meta: { step: 3 }
      },
      {
        path: 'report/:reportId',
        name: 'Report',
        component: ReportView,
        props: true,
        meta: { step: 4 }
      },
      {
        path: 'interaction/:reportId',
        name: 'Interaction',
        component: InteractionView,
        props: true,
        meta: { step: 5 }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局前置守卫：从 URL 参数中捕获 himat token 并存入 localStorage
router.beforeEach((to, from, next) => {
  const token = to.query.token
  if (token) {
    localStorage.setItem('himat_token', token)
    // 移除 URL 中的 token 参数，保持地址栏干净
    const query = { ...to.query }
    delete query.token
    next({ path: to.path, query, replace: true })
    return
  }
  next()
})

export default router
