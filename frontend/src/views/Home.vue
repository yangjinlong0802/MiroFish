<template>
  <div class="home-container">
    <!-- 顶部导航栏 -->
    <nav class="navbar navbar--minimal">
      <div class="nav-brand">AI 推演助手</div>
    </nav>

    <div class="main-content">
      <!-- 新建项目卡片 -->
      <section class="create-card">
        <div class="card-header">
          <div class="card-title-row">
            <h2 class="card-title">新建推演预测项目</h2>
            <span class="engine-badge">引擎: V1.0</span>
          </div>
          <p class="card-desc">上传数据文件并输入预测需求，系统将自动构建知识图谱并启动多智能体推演</p>
        </div>

        <div class="card-body">
          <div class="form-grid">
            <!-- 左列：上传区域 -->
            <div class="form-section">
              <div class="section-label">
                <span class="label-num">01</span>
                <span>上传数据文件</span>
                <span class="label-hint">PDF / MD / TXT</span>
              </div>
              <div
                class="upload-zone"
                :class="{ 'drag-over': isDragOver, 'has-files': files.length > 0 }"
                @dragover.prevent="handleDragOver"
                @dragleave.prevent="handleDragLeave"
                @drop.prevent="handleDrop"
                @click="triggerFileInput"
              >
                <input
                  ref="fileInput"
                  type="file"
                  multiple
                  accept=".pdf,.md,.txt"
                  @change="handleFileSelect"
                  style="display: none"
                  :disabled="loading"
                />

                <div v-if="files.length === 0" class="upload-placeholder">
                  <div class="upload-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="17 8 12 3 7 8"/>
                      <line x1="12" y1="3" x2="12" y2="15"/>
                    </svg>
                  </div>
                  <div class="upload-text">拖拽文件到此处，或点击上传</div>
                </div>

                <div v-else class="file-list">
                  <div v-for="(file, index) in files" :key="index" class="file-item">
                    <span class="file-icon">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                      </svg>
                    </span>
                    <span class="file-name">{{ file.name }}</span>
                    <button @click.stop="removeFile(index)" class="remove-btn">×</button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 右列：输入区域 -->
            <div class="form-section">
              <div class="section-label">
                <span class="label-num">02</span>
                <span>模拟提示词</span>
              </div>
              <textarea
                v-model="formData.simulationRequirement"
                class="requirement-input"
                placeholder="用自然语言输入模拟或预测需求（例：武大若发布撤销肖某处分的公告，会引发什么舆情走向）"
                rows="6"
                :disabled="loading"
              ></textarea>
            </div>
          </div>

          <!-- 启动按钮 -->
          <button
            class="start-btn"
            @click="startSimulation"
            :disabled="!canSubmit || loading"
          >
            <span v-if="!loading">启动推演引擎</span>
            <span v-else>初始化中...</span>
            <span class="btn-arrow">→</span>
          </button>
        </div>
      </section>

      <!-- 历史项目数据库 -->
      <HistoryDatabase />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import HistoryDatabase from '../components/HistoryDatabase.vue'

const router = useRouter()

// 表单数据
const formData = ref({
  simulationRequirement: ''
})

// 文件列表
const files = ref([])

// 状态
const loading = ref(false)
const error = ref('')
const isDragOver = ref(false)

// 文件输入引用
const fileInput = ref(null)

// 计算属性:是否可以提交
const canSubmit = computed(() => {
  return formData.value.simulationRequirement.trim() !== '' && files.value.length > 0
})

// 触发文件选择
const triggerFileInput = () => {
  if (!loading.value) {
    fileInput.value?.click()
  }
}

// 处理文件选择
const handleFileSelect = (event) => {
  const selectedFiles = Array.from(event.target.files)
  addFiles(selectedFiles)
}

// 处理拖拽相关
const handleDragOver = (e) => {
  if (!loading.value) {
    isDragOver.value = true
  }
}

const handleDragLeave = (e) => {
  isDragOver.value = false
}

const handleDrop = (e) => {
  isDragOver.value = false
  if (loading.value) return

  const droppedFiles = Array.from(e.dataTransfer.files)
  addFiles(droppedFiles)
}

// 添加文件
const addFiles = (newFiles) => {
  const validFiles = newFiles.filter(file => {
    const ext = file.name.split('.').pop().toLowerCase()
    return ['pdf', 'md', 'txt'].includes(ext)
  })
  files.value.push(...validFiles)
}

// 移除文件
const removeFile = (index) => {
  files.value.splice(index, 1)
}

// 滚动到底部
const scrollToBottom = () => {
  window.scrollTo({
    top: document.body.scrollHeight,
    behavior: 'smooth'
  })
}

// 开始模拟 - 立即跳转，API调用在Process页面进行
const startSimulation = () => {
  if (!canSubmit.value || loading.value) return

  // 存储待上传的数据
  import('../store/pendingUpload.js').then(({ setPendingUpload }) => {
    setPendingUpload(files.value, formData.value.simulationRequirement)

    // 立即跳转到Process页面（使用特殊标识表示新建项目）
    router.push({
      name: 'Process',
      params: { projectId: 'new' }
    })
  })
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  background: #F8FAFC;
  font-family: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
  color: #0F172A;
}

/* 顶部导航 */
.navbar {
  height: 56px;
  background: #0F172A;
  color: #FFF;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 28px;
}

.navbar--minimal {
  height: 40px;
  justify-content: center;
}

.nav-brand {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  letter-spacing: 0.5px;
  font-size: 15px;
}

/* 主要内容区 */
.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 24px;
}

/* 新建项目卡片 */
.create-card {
  background: #FFF;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 4px 12px rgba(0, 0, 0, 0.02);
  margin-bottom: 32px;
  overflow: hidden;
}

.card-header {
  padding: 24px 28px 0;
}

.card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: #0F172A;
}

.engine-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #64748B;
  background: #F1F5F9;
  padding: 3px 10px;
  border-radius: 4px;
  font-weight: 500;
}

.card-desc {
  font-size: 13px;
  color: #64748B;
  margin: 0;
  line-height: 1.5;
}

.card-body {
  padding: 20px 28px 28px;
}

/* 表单网格 */
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 20px;
}

.form-section {
  display: flex;
  flex-direction: column;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 10px;
}

.label-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  color: #2563EB;
  background: #EFF6FF;
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.label-hint {
  font-size: 11px;
  font-weight: 400;
  color: #94A3B8;
  margin-left: auto;
}

/* 上传区域 */
.upload-zone {
  flex: 1;
  min-height: 180px;
  border: 1.5px dashed #CBD5E1;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #FAFBFC;
}

.upload-zone:hover {
  border-color: #2563EB;
  background: #F8FAFF;
}

.upload-zone.drag-over {
  border-color: #2563EB;
  background: #EFF6FF;
}

.upload-zone.has-files {
  align-items: flex-start;
  padding: 12px;
}

.upload-placeholder {
  text-align: center;
  color: #94A3B8;
}

.upload-icon {
  margin-bottom: 10px;
  color: #94A3B8;
  display: flex;
  justify-content: center;
}

.upload-text {
  font-size: 13px;
  font-weight: 500;
}

.file-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #F8FAFC;
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid #E2E8F0;
  font-size: 13px;
}

.file-icon {
  color: #64748B;
  display: flex;
  align-items: center;
}

.file-name {
  flex: 1;
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.remove-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  color: #94A3B8;
  padding: 0 4px;
  line-height: 1;
  transition: color 0.15s;
}

.remove-btn:hover {
  color: #EF4444;
}

/* 输入区域 */
.requirement-input {
  flex: 1;
  min-height: 180px;
  width: 100%;
  border: 1.5px solid #CBD5E1;
  border-radius: 8px;
  padding: 14px 16px;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.6;
  resize: vertical;
  outline: none;
  background: #FAFBFC;
  color: #0F172A;
  transition: border-color 0.2s;
}

.requirement-input:focus {
  border-color: #2563EB;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}

.requirement-input::placeholder {
  color: #94A3B8;
}

/* 启动按钮 */
.start-btn {
  width: 100%;
  background: #2563EB;
  color: #FFF;
  border: none;
  padding: 14px 24px;
  font-family: inherit;
  font-weight: 600;
  font-size: 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 8px;
}

.start-btn:hover:not(:disabled) {
  background: #1D4ED8;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
}

.start-btn:active:not(:disabled) {
  transform: translateY(0);
}

.start-btn:disabled {
  background: #E2E8F0;
  color: #94A3B8;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.btn-arrow {
  font-size: 16px;
}

/* 响应式 */
@media (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .main-content {
    padding: 20px 16px;
  }
}
</style>
