<template>
  <el-container class="main-container">
    <el-header class="header">
      <div class="logo-title">
        <DataAnalysis class="icon"/>
        <h1>大小模型协同的数据质量链式追溯与智能分析平台</h1>
      </div>
      <div class="header-extra-actions">
        <el-button type="primary" plain @click="goToReportPage">系统评测报告（模型卡片）</el-button>
      </div>
    </el-header>

    <el-main ref="mainRef" class="main-content">
      <el-row :gutter="20" style="height: 100%">
        <el-col :span="8" style="height: 100%">
          <el-card class="box-card control-card" shadow="always">
            <template #header>
              <div class="card-header">
                <span><UploadFilled class="icon"/> 文件上传与控制</span>
                <el-button type="danger" link @click="clearAllFiles" v-if="fileListForDisplay.length > 0 || isDemoMode">
                  <el-icon><Delete /></el-icon>
                  一键清空(分析过程中请勿点击)
                </el-button>
              </div>
            </template>

            <el-scrollbar class="left-scroll-content">
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
                  <div class="el-upload__tip">请按版本顺序上传至少2个 .xlsx 文件进行对比分析（要求上传的文件表格具有完全相同的列名字段）</div>
                </template>
              </el-upload>

              <el-divider content-position="center">
                <span style="color: #909399; font-size: 14px;"></span>
              </el-divider>
              <el-button
                  @click="loadDemoData"
                  :icon="MagicStick"
                  style="width: 100%;"
                  size="large"
                  type="success"
                  plain
              >
                加载评测省份1数据
              </el-button>

              <el-form
                  v-if="columnsForSelection.length > 0"
                  class="param-form"
                  label-position="top"
                  :model="analysisParams"
              >
                <el-form-item label="关键列 (用于唯一识别记录)">
                  <el-select
                      v-model="analysisParams.keyColumns"
                      multiple
                      filterable
                      placeholder="请从文件中选择关键列"
                      style="width: 100%;"
                  >
                    <el-option
                        v-for="col in columnsForSelection"
                        :key="col"
                        :label="col"
                        :value="col"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="分析值列 (需要追踪变化的数值)">
                  <el-select
                      v-model="analysisParams.valueColumn"
                      filterable
                      placeholder="请选择要分析的数值列"
                      style="width: 100%;"
                  >
                    <el-option
                        v-for="col in columnsForSelection"
                        :key="col"
                        :label="col"
                        :value="col"
                    />
                  </el-select>
                </el-form-item>
              </el-form>
            </el-scrollbar>

            <div class="bottom-action-bar">
              <el-button
                  type="primary"
                  size="large"
                  @click="startAnalysis"
                  :disabled="isStartButtonDisabled"
                  :loading="isLoading"
                  style="width: 100%;"
              >
                {{ isLoading ? '分析中...' : '开始分析' }}
              </el-button>
            </div>

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
                  <el-button type="success" :icon="Download" @click="downloadMD" :disabled="isStreaming">下载 Markdown</el-button>
                  <el-button style="margin-left: 12px" type="danger" :icon="Download" @click="downloadPDF" :disabled="isStreaming">下载 PDF</el-button>
                </div>
              </div>
            </template>

            <el-scrollbar
                ref="reportScrollbar"
                class="report-scroll"
                height="100%"
            >
              <div v-if="reportMarkdown" v-html="reportHtml" class="scroll-content markdown-body"></div>
              <el-empty v-else description="请先上传文件或加载示例并开始分析"/>
            </el-scrollbar>
          </el-card>
        </el-col>
      </el-row>
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue';
import type { UploadInstance, UploadProps, UploadRawFile, UploadUserFile, UploadFile } from 'element-plus';
import { ElMessage } from 'element-plus';
import { DataAnalysis, UploadFilled, Document, Download, MagicStick, Delete } from '@element-plus/icons-vue';
import { marked } from 'marked';
import { analyzeFiles, downloadPdf, analyzeDemo } from './services/ApiService';
import * as XLSX from 'xlsx';

const uploadRef = ref<UploadInstance | null>(null);
const reportScrollbar = ref<any>(null);

const filesToUpload = ref<UploadRawFile[]>([]);
const fileListForDisplay = ref<UploadUserFile[]>([]);

const isLoading = ref(false);
const reportMarkdown = ref('');
const isStreaming = ref(false);


const isDemoMode = ref(false);
const demoColumns = ref<string[]>([]);
const DEMO_FILES_DISPLAY = [
  { name: '省份1_数据v1.xlsx' },
  { name: '省份1_数据v2.xlsx' },
  { name: '省份1_数据v3.xlsx' },
];

const availableColumns = ref<string[]>([]);
const analysisParams = ref({
  keyColumns: [] as string[],
  valueColumn: '',
});

const columnsForSelection = computed(() => {
  return isDemoMode.value ? demoColumns.value : availableColumns.value;
});

const isStartButtonDisabled = computed(() => {
  const filesLoaded = isDemoMode.value || filesToUpload.value.length >= 2;
  return (
      !filesLoaded ||
      isLoading.value ||
      analysisParams.value.keyColumns.length === 0 ||
      !analysisParams.value.valueColumn
  );
});

const reportHtml = computed(() => {
  if (reportMarkdown.value) {
    marked.setOptions({ breaks: true, gfm: true });
    return marked(reportMarkdown.value);
  }
  return '';
});

const getHeadersFromFile = async (file: UploadRawFile): Promise<string[]> => {
  try {
    const data = await file.arrayBuffer();
    const workbook = XLSX.read(data, { type: 'array' });
    const firstSheetName = workbook.SheetNames[0];
    if (!firstSheetName) throw new Error('Excel文件中没有找到工作表(Sheet)。');
    const worksheet = workbook.Sheets[firstSheetName];
    const headers = (XLSX.utils.sheet_to_json(worksheet, { header: 1 })[0] as string[]) || [];
    if (headers.length === 0) throw new Error('无法从文件中读取有效的列头。');
    return headers.filter(h => h);
  } catch (error: any) {
    console.error('解析Excel文件失败:', error);
    throw new Error(`解析文件 "${file.name}" 失败: ${error.message || '请检查文件格式。'}`);
  }
};

const areHeaderArraysEqual = (headers1: string[], headers2: string[]): boolean => {
  if (headers1.length !== headers2.length) return false;
  return JSON.stringify(headers1) === JSON.stringify(headers2);
};

const handleFileChange: UploadProps['onChange'] = async (uploadFile: UploadFile) => {
  if (uploadFile.status !== 'ready') {
    return;
  }
  if (isDemoMode.value) {
    isDemoMode.value = false;
    fileListForDisplay.value = [];
    filesToUpload.value = [];
    availableColumns.value = [];
  }
  const rejectFile = (message: string) => {
    ElMessage.error({ message, duration: 5000 });
    uploadRef.value?.handleRemove(uploadFile);
  };
  if (fileListForDisplay.value.some(f => f.name === uploadFile.name)) {
    rejectFile(`文件 "${uploadFile.name}" 已存在，请勿重复上传。`);
    return;
  }
  try {
    const currentHeaders = await getHeadersFromFile(uploadFile.raw as UploadRawFile);
    if (availableColumns.value.length === 0) {
      availableColumns.value = currentHeaders;
      analysisParams.value.keyColumns = [];
      analysisParams.value.valueColumn = '';
    } else {
      if (!areHeaderArraysEqual(availableColumns.value, currentHeaders)) {
        rejectFile(`文件 "${uploadFile.name}" 的列字段与已上传文件不一致，已拒绝。`);
        return;
      }
    }
    fileListForDisplay.value.push(uploadFile);
    filesToUpload.value.push(uploadFile.raw as UploadRawFile);
  } catch (error: any) {
    rejectFile(error.message || `文件 "${uploadFile.name}" 格式错误或无法解析。`);
  }
};

const handleFileRemove: UploadProps['onRemove'] = (removedFile, currentFiles) => {
  ElMessage.info(`文件 "${removedFile.name}" 已被移除。`);
  fileListForDisplay.value = currentFiles;
  filesToUpload.value = currentFiles.map(f => f.raw as UploadRawFile).filter(Boolean);
  if (removedFile.raw) {
    isDemoMode.value = false;
  }
  if (isDemoMode.value && currentFiles.length === 0) {
    isDemoMode.value = false;
    analysisParams.value.keyColumns = [];
    analysisParams.value.valueColumn = '';
  }
  if (filesToUpload.value.length === 0 && !isDemoMode.value) {
    availableColumns.value = [];
    analysisParams.value.keyColumns = [];
    analysisParams.value.valueColumn = '';
  }
};

const loadDemoData = () => {
  clearAllFiles(true);
  isDemoMode.value = true;
  fileListForDisplay.value = [...DEMO_FILES_DISPLAY] as UploadUserFile[];
  demoColumns.value = ['数据日期', '省份', '行业编码', '行业名称', '电量'];
  analysisParams.value = {
    keyColumns: ['数据日期', '省份', '行业编码'],
    valueColumn: '电量',
  };
  ElMessage.success('示例数据已加载！');
};

const clearAllFiles = (isInternalCall = false) => {
  filesToUpload.value = [];
  fileListForDisplay.value = [];
  uploadRef.value?.clearFiles();
  availableColumns.value = [];
  analysisParams.value.keyColumns = [];
  analysisParams.value.valueColumn = '';
  isDemoMode.value = false;
  reportMarkdown.value = '';
  if (!isInternalCall) {
    ElMessage.success('已清空所有文件和设置。');
  }
};

const startAnalysis = async () => {
  if (isStartButtonDisabled.value) return;

  isLoading.value = true;
  isStreaming.value = true;
  reportMarkdown.value = '';
  let isFirstChunk = true;

  const callbacks = {
    onChunk: (chunk: string) => {
      if (isFirstChunk) {
        isLoading.value = false;
        isFirstChunk = false;
      }
      reportMarkdown.value += chunk;
      nextTick(() => {
        if (reportScrollbar.value && reportScrollbar.value.wrapRef) {
          const scrollContainer = reportScrollbar.value.wrapRef;
          scrollContainer.scrollTop = scrollContainer.scrollHeight;
        }
      });
    },
    onClose: () => {
      if(isLoading.value) {
        isLoading.value = false;
        ElMessage.success('分析完成，未生成任何内容。');
      } else {
        ElMessage.success('分析完成！');
        isStreaming.value = false;
      }
    },
    onError: (error: Error) => {
      const errorMessage = error.message || '请求失败，请检查后端服务是否正常';
      ElMessage.error(`分析出错: ${errorMessage}`);
      console.error(error);
      isLoading.value = false;
      isStreaming.value = false;
    }
  };

  try {
    if (isDemoMode.value) {
      await analyzeDemo(analysisParams.value, callbacks);
    } else {
      await analyzeFiles(filesToUpload.value, analysisParams.value, callbacks);
    }
  } catch (error: any) {
    callbacks.onError(error);
  }
};

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

watch(reportMarkdown, async () => {
  await nextTick();
  reportScrollbar.value?.update();
});

const goToReportPage = () => {
  window.open('/evaluation_report.html', '_blank');
};
</script>

<style scoped>
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

.main-content {
  padding: 20px;
  height: calc(100% - 64px);
  box-sizing: border-box;
}

.box-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.control-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 0;
}

.left-scroll-content {
  flex: 1;
  min-height: 0;
  padding: 20px;
  box-sizing: border-box;
}

.bottom-action-bar {
  flex-shrink: 0;
  padding: 16px 20px;
  border-top: 1px solid #e4e7ed;
  background-color: #ffffff;
}

.upload-area {
  display: flex;
  flex-direction: column;
  flex-grow: 1;
}

.param-form {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.report-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.report-scroll {
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

.markdown-body {
  font-family: -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif;
}

.el-button+.el-button {
  margin-left: 0px;
}
</style>