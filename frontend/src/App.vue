<template>
  <el-container class="main-container">
    <el-header ref="headerRef" class="header">
      <div class="logo-title">
        <DataAnalysis class="icon"/>
        <h1>基于大小模型协同的电力数据智能分析</h1>
      </div>
    </el-header>

    <el-main ref="mainRef" class="main-content">
      <el-row :gutter="20" style="height: 100%">
        <!-- 上传区 -->
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

        <!-- 报告区 -->
        <el-col :span="16" style="height: 100%">
          <el-card
              class="box-card report-card"
              shadow="always"
              v-loading="isLoading"
              :body-class="'report-body'"
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

            <!-- 关键：把 height 设为计算出的 px 字符串 -->
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
import type {UploadInstance, UploadProps, UploadRawFile, UploadUserFile} from 'element-plus';
import {ElMessage} from 'element-plus';
import {DataAnalysis, UploadFilled, Document, Download} from '@element-plus/icons-vue';
import {marked} from 'marked';
import {analyzeFiles, downloadPdf} from './services/ApiService';

// refs for DOM & components
const headerRef = ref<HTMLElement | null>(null);
const mainRef = ref<HTMLElement | null>(null);
const reportCardRef = ref<HTMLElement | null>(null);
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
    marked.setOptions({breaks: true});
    return marked(reportMarkdown.value);
  }
  return '';
});

// height string to pass into el-scrollbar, default to some px to be safe
const scrollbarHeight = ref('640px');

// helper to compute available height for scrollbar in pixels
function computeScrollbarHeight() {
  // ensure required refs exist
  const mainEl = mainRef.value;
  const headerEl = headerRef.value;
  const reportCardEl = reportCardRef.value;
  if (!mainEl || !headerEl || !reportCardEl) {
    return;
  }

  // main area height (already subtracts header since main is below header)
  const mainRect = mainEl.getBoundingClientRect();

  // find the card header (title + buttons) height inside the report card
  const cardHeaderEl = reportCardEl.querySelector('.report-card-header') as HTMLElement | null;
  const cardHeaderHeight = cardHeaderEl ? cardHeaderEl.getBoundingClientRect().height : 0;

  // account for report-card body paddings if any; we set none, but keep a small margin safe area
  const safePadding = 24; // px

  // available height for el-scrollbar = mainRect.height - cardHeaderHeight - safePadding
  const available = Math.max(120, Math.floor(mainRect.height - cardHeaderHeight - safePadding));
  scrollbarHeight.value = `${available}px`;
}

// resize handling
let ro: ResizeObserver | null = null;

function startResizeObserver() {
  if (mainRef.value) {
    ro = new ResizeObserver(() => {
      computeScrollbarHeight();
    });
    ro.observe(mainRef.value);
  }
  // also listen window resize as fallback
  window.addEventListener('resize', computeScrollbarHeight);
}

function stopResizeObserver() {
  if (ro && mainRef.value) {
    ro.unobserve(mainRef.value);
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
  // compute initial size after DOM paint
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

/* 上传区 */
.upload-area {
  display: flex;
  flex-direction: column;
  flex-grow: 1;
}


/* 报告区关键样式：card body 作为可收缩 flex 项 */
.report-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* el-scrollbar 外层：flex 子项，可收缩 */
.report-scroll {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* 真正滚动的内容层 */
.scroll-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 20px;
  box-sizing: border-box;
  line-height: 1.8;
}

/* 卡片头部（含按钮）的样式，便于测量高度 */
.report-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  box-sizing: border-box;
}

</style>
