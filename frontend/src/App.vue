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

            <el-form
                v-if="availableColumns.length > 0"
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
                      v-for="col in availableColumns"
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
                      v-for="col in availableColumns"
                      :key="col"
                      :label="col"
                      :value="col"
                  />
                </el-select>
              </el-form-item>
            </el-form>
            <el-button
                type="primary"
                size="large"
                @click="startAnalysis"
                :disabled="isStartButtonDisabled"
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
// 优化: 将ApiService的调用参数更新为我们新设计的格式
import { analyzeFiles, downloadPdf } from './services/ApiService';
// 优化: 引入xlsx库来读取Excel表头。请确保已安装: npm install xlsx
import * as XLSX from 'xlsx';

// refs for components
const uploadRef = ref<UploadInstance | null>(null);
const reportScrollbar = ref<any>(null);

// 文件状态
const filesToUpload = ref<UploadRawFile[]>([]);
const fileListForDisplay = ref<UploadUserFile[]>([]);

// 应用状态
const isLoading = ref(false);
const reportMarkdown = ref('');

// START: 新增的动态参数状态
const availableColumns = ref<string[]>([]);
const analysisParams = ref({
  keyColumns: [] as string[],
  valueColumn: '',
});
// END: 新增的动态参数状态

// 优化: “开始分析”按钮的禁用逻辑更完善
const isStartButtonDisabled = computed(() => {
  return (
      filesToUpload.value.length < 2 ||
      isLoading.value ||
      analysisParams.value.keyColumns.length === 0 ||
      !analysisParams.value.valueColumn
  );
});

// 将 Markdown 转换为 HTML
const reportHtml = computed(() => {
  if (reportMarkdown.value) {
    marked.setOptions({ breaks: true, gfm: true });
    return marked(reportMarkdown.value);
  }
  return '';
});

// 优化: 文件处理回调，增加读取表头逻辑
const handleFileChange: UploadProps['onChange'] = async (_uploadFile, uploadFiles) => {
  filesToUpload.value = uploadFiles.map(f => f.raw as UploadRawFile);
  fileListForDisplay.value = uploadFiles;

  // 清空旧状态
  availableColumns.value = [];
  analysisParams.value.keyColumns = [];
  analysisParams.value.valueColumn = '';

  if (filesToUpload.value.length > 0) {
    const firstFile = filesToUpload.value[0];
    try {
      const data = await firstFile.arrayBuffer();
      const workbook = XLSX.read(data, { type: 'array' });
      const firstSheetName = workbook.SheetNames[0];
      const worksheet = workbook.Sheets[firstSheetName];
      const headers = XLSX.utils.sheet_to_json(worksheet, { header: 1 })[0] as string[];
      availableColumns.value = headers.filter(h => h); // 过滤掉空表头
    } catch (error) {
      ElMessage.error('解析Excel文件表头失败，请检查文件格式是否正确。');
      console.error(error);
    }
  }
};

// 优化: 文件移除回调，增加清空状态逻辑
const handleFileRemove: UploadProps['onRemove'] = (uploadFile, uploadFiles) => {
  filesToUpload.value = uploadFiles.map(f => f.raw as UploadRawFile);
  fileListForDisplay.value = uploadFiles;
  ElMessage.info(`文件 "${uploadFile.name}" 已被移除。`);

  // 如果所有文件都被移除，则清空列选项和已选参数
  if (filesToUpload.value.length === 0) {
    availableColumns.value = [];
    analysisParams.value.keyColumns = [];
    analysisParams.value.valueColumn = '';
  }
};

// 优化: 开始分析函数，传递动态参数
const startAnalysis = async () => {
  // 此处检查已通过 isStartButtonDisabled 计算属性覆盖，但为保险起见保留
  if (filesToUpload.value.length < 2) {
    ElMessage.warning('请确保已上传至少两个文件。');
    return;
  }
  if (analysisParams.value.keyColumns.length === 0 || !analysisParams.value.valueColumn) {
    ElMessage.warning('请选择关键列和分析值列。');
    return;
  }

  isLoading.value = true;
  reportMarkdown.value = '';

  try {
    // 将动态参数和文件列表一同传递给API服务
    const result = await analyzeFiles(filesToUpload.value, analysisParams.value);
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

// 下载功能 (保持不变)
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

// 监听报告内容更新 (保持不变)
watch(reportMarkdown, async () => {
  await nextTick();
  reportScrollbar.value?.update();
});

// 保留您新增的跳转方法 (保持不变)
const goToReportPage = () => {
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

.upload-area {
  display: flex;
  flex-direction: column;
  flex-grow: 1;
}

/* 新增: 为参数表单添加一些间距 */
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
</style>