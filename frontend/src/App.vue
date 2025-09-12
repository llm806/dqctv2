<template>
  <el-container class="main-container">
    <el-header class="header">
      <div class="logo-title">
        <DataAnalysis class="icon"/>
        <h1>基于大小模型协同的电力数据智能分析</h1>
      </div>

      <div class="header-extra-actions">
        <el-button type="primary" plain @click="goToReportPage">系统评测报告（模型卡片）</el-button>
      </div>
    </el-header>

    <el-main ref="mainRef" class="main-content">
      <el-row :gutter="20" style="height: 100%">
        <el-col :span="8" style="height: 100%">
          <el-card class="box-card" shadow="always">
            <template #header>
              <div class="card-header">
                <span><UploadFilled class="icon"/> 文件上传与控制</span>
              </div>
            </template>

            <el-upload
                ref="uploadRef"
                class="upload-area"
                drag
                action="#"
                multiple
                :auto-upload="false"
                :file-list="fileListForDisplay"
                :on-change="handleFileChange"
                :on-remove="handleFileRemove"
            >
              <el-icon class="el-icon--upload">
                <upload-filled/>
              </el-icon>
              <div class="el-upload__text">将文件拖到此处, 或 <em>点击上传</em></div>
              <template #tip>
                <div class="el-upload__tip">请按版本顺序上传至少2个 .xlsx 文件进行对比分析</div>
              </template>
            </el-upload>

            <el-button
                type="primary"
                size="large"
                @click="startAnalysis"
                :disabled="filesToUpload.length < 2 || isLoading"
                :loading="isLoading"
                style="width: 100%; margin-top: 20px;"
            >
              {{ isLoading ? '分析中...' : '开始分析' }}
            </el-button>
          </el-card>
        </el-col>

        <el-col :span="16" style="height: 100%">
          <el-card
              class="box-card report-card"
              shadow="always"
              v-loading="isLoading"
              :body-style="{ padding: 0, flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }"
          >
            <template #header>
              <div class="card-header report-card-header">
                <span><Document class="icon"/> 分析报告</span>
                <div v-if="reportMarkdown">
                  <el-button type="success" :icon="Download" @click="downloadMD">下载 Markdown</el-button>
                  <el-button type="danger" :icon="Download" @click="downloadPDF">下载 PDF</el-button>
                </div>
              </div>
            </template>

            <el-scrollbar
                ref="reportScrollbar"
                class="report-scroll"
                height="100%"
            >
              <div v-if="reportMarkdown" v-html="reportHtml" class="scroll-content markdown-body"></div>
              <el-empty v-else description="请先上传文件并开始分析"/>
            </el-scrollbar>
          </el-card>
        </el-col>
      </el-row>
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue';
import type { UploadInstance, UploadProps, UploadRawFile, UploadUserFile } from 'element-plus';
import { ElMessage } from 'element-plus';
import { DataAnalysis, UploadFilled, Document, Download } from '@element-plus/icons-vue';
import { marked } from 'marked';
import { analyzeFiles, downloadPdf } from './services/ApiService';

// refs for components
const uploadRef = ref<UploadInstance | null>(null);
const reportScrollbar = ref<any>(null);

// 文件状态
const filesToUpload = ref<UploadRawFile[]>([]);
const fileListForDisplay = ref<UploadUserFile[]>([]);

// 应用状态
const isLoading = ref(false);
const reportMarkdown = ref('');

// 将 Markdown 转换为 HTML
const reportHtml = computed(() => {
  if (reportMarkdown.value) {
    marked.setOptions({ breaks: true, gfm: true });
    return marked(reportMarkdown.value);
  }
  return '';
});

// 文件处理回调
const handleFileChange: UploadProps['onChange'] = (_uploadFile, uploadFiles) => {
  filesToUpload.value = uploadFiles.map(f => f.raw as UploadRawFile);
  fileListForDisplay.value = uploadFiles;
};

const handleFileRemove: UploadProps['onRemove'] = (uploadFile, uploadFiles) => {
  filesToUpload.value = uploadFiles.map(f => f.raw as UploadRawFile);
  fileListForDisplay.value = uploadFiles;
  ElMessage.info(`文件 "${uploadFile.name}" 已被移除。`);
};

// 开始分析
const startAnalysis = async () => {
  if (filesToUpload.value.length < 2) {
    ElMessage.warning('请确保已上传至少两个文件。');
    return;
  }

  isLoading.value = true;
  reportMarkdown.value = '';

  try {
    const result = await analyzeFiles(filesToUpload.value);
    if (result.success) {
      reportMarkdown.value = result.report;
      ElMessage.success('分析完成！');
    } else {
      ElMessage.error(result.report || '分析失败，未知错误');
    }
  } catch (error: any) {
    const errorMessage = error.response?.data?.detail || error.message || '请求失败，请检查后端服务是否正常';
    ElMessage.error(`分析出错: ${errorMessage}`);
    console.error(error);
  } finally {
    isLoading.value = false;
  }
};

// 下载功能
const downloadMD = () => {
  const blob = new Blob([reportMarkdown.value], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', 'analysis_report.md');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

const downloadPDF = async () => {
  ElMessage.info('正在生成PDF，请稍候...');
  try {
    await downloadPdf(reportMarkdown.value);
  } catch (error: any) {
    ElMessage.error('PDF下载失败: ' + (error?.message ?? String(error)));
  }
};

// 当报告内容更新时，通知滚动条组件更新其内部状态，以确保滚动条正确
watch(reportMarkdown, async () => {
  await nextTick();
  reportScrollbar.value?.update();
});

// START: 新增的跳转方法
const goToReportPage = () => {
  // 使用 window.open 在新标签页中打开报告，不影响当前分析任务
  window.open('/evaluation_report.html', '_blank');
};
</script>

<style scoped>
/* 基础布局 */
.main-container {
  height: 100vh;
  background-color: #f0f2f5;
}

.header {
  background-color: #ffffff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 8px #f0f1f2;
  z-index: 1;
  padding: 0 20px;
  height: 64px;
  box-sizing: border-box;
}

.logo-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;
  color: #007bff;
}

.icon {
  width: 1.2em;
  height: 1.2em;
  vertical-align: middle;
}

/* main，减去 header 高度 */
.main-content {
  padding: 20px;
  height: calc(100% - 64px);
  box-sizing: border-box;
}

/* card 充满列高度，并设置为 flex 容器 */
.box-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.upload-area {
  display: flex;
  flex-direction: column;
  flex-grow: 1;
}

.report-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.report-scroll {
  /* 此样式确保滚动条本身可以收缩，但现在已不再严格需要，因为高度是 100% */
  flex: 1;
  min-height: 0;
}

.scroll-content {
  padding: 20px;
  line-height: 1.8;
  word-wrap: break-word;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* Markdown specific styles */
.markdown-body {
  font-family: -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif;
}
</style>