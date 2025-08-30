<template>
  <el-container class="main-container">
    <el-header class="header">
      <div class="logo-title">
        <DataAnalysis class="icon"/>
        <h1>基于大小模型协同的电力数据智能分析</h1>
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
                <div class="el-upload__tip">请上传至少2个 .xlsx 文件进行对比分析</div>
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
              ref="reportCardRef"
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
                :height="scrollbarHeight"
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
import {ref, computed, watch, nextTick, onMounted, onBeforeUnmount} from 'vue';
import type {ComponentPublicInstance} from 'vue';
import type {UploadInstance, UploadProps, UploadRawFile, UploadUserFile} from 'element-plus';
import {ElMessage} from 'element-plus';
import {DataAnalysis, UploadFilled, Document, Download} from '@element-plus/icons-vue';
import {marked} from 'marked';
// 确保这个路径是正确的，相对于 App.vue 文件
import {analyzeFiles, downloadPdf} from './services/ApiService';

// refs for DOM & components
const mainRef = ref<ComponentPublicInstance | null>(null);
const reportCardRef = ref<ComponentPublicInstance | null>(null);
const uploadRef = ref<UploadInstance | null>(null);
const reportScrollbar = ref<any>(null);

// files
const filesToUpload = ref<UploadRawFile[]>([]);
const fileListForDisplay = ref<UploadUserFile[]>([]);

const isLoading = ref(false);
const reportMarkdown = ref('');

// computed html
const reportHtml = computed(() => {
  if (reportMarkdown.value) {
    marked.setOptions({breaks: true, gfm: true});
    return marked(reportMarkdown.value);
  }
  return '';
});

// height string to pass into el-scrollbar
const scrollbarHeight = ref('600px');

function computeScrollbarHeight() {
  const mainEl = mainRef.value?.$el as HTMLElement;
  const reportCardDomEl = reportCardRef.value?.$el as HTMLElement;

  if (!mainEl || !reportCardDomEl) {
    return;
  }

  const mainRect = mainEl.getBoundingClientRect();

  const cardHeaderEl = reportCardDomEl.querySelector('.report-card-header') as HTMLElement | null;

  // 提供一个默认高度以增加健壮性
  const cardHeaderHeight = cardHeaderEl ? cardHeaderEl.getBoundingClientRect().height : 48;

  // 卡片主体区域有默认的 padding，这里设为0，但保留安全边距
  const safePadding = 24;

  const available = Math.max(120, Math.floor(mainRect.height - cardHeaderHeight - safePadding));
  scrollbarHeight.value = `${available}px`;
}

// resize handling
let ro: ResizeObserver | null = null;

function startResizeObserver() {
    const mainEl = mainRef.value?.$el;
    if (mainEl) {
        ro = new ResizeObserver(() => {
            computeScrollbarHeight();
        });
        ro.observe(mainEl);
    }
    window.addEventListener('resize', computeScrollbarHeight);
}

function stopResizeObserver() {
    const mainEl = mainRef.value?.$el;
    if (ro && mainEl) {
        ro.unobserve(mainEl);
        ro = null;
    }
    window.removeEventListener('resize', computeScrollbarHeight);
}


// file handlers
const handleFileChange: UploadProps['onChange'] = (_uploadFile, uploadFiles) => {
  filesToUpload.value = uploadFiles.map(f => f.raw as UploadRawFile);
  fileListForDisplay.value = uploadFiles;
};

const handleFileRemove: UploadProps['onRemove'] = (uploadFile, uploadFiles) => {
  filesToUpload.value = uploadFiles.map(f => f.raw as UploadRawFile);
  fileListForDisplay.value = uploadFiles;
  ElMessage.info(`文件 "${uploadFile.name}" 已被移除。`);
};

// analysis
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

// downloads
const downloadMD = () => {
  const blob = new Blob([reportMarkdown.value], {type: 'text/markdown;charset=utf-8'});
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

// update scrollbar after markdown content mounts/changes
watch(reportMarkdown, async () => {
  await nextTick();
  try {
    reportScrollbar.value?.update?.();
  } catch (e) {
    // ignore
  }
});

onMounted(() => {
  nextTick(() => {
    computeScrollbarHeight();
    startResizeObserver();
  });
});

onBeforeUnmount(() => {
  stopResizeObserver();
});
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

/* card 充满列高度 */
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
  /* This ensures the scrollbar itself can shrink */
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
  /* Add your markdown styles here */
  /* For example: */
  font-family: -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif;
}
</style>