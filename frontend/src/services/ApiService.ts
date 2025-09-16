import axios from 'axios';
import type { UploadRawFile } from 'element-plus';

// 创建 Axios 实例 (保持不变)
const apiClient = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5分钟超时
});

/**
 * 优化: 分析文件服务
 * @param files 文件对象数组
 * @param params 包含关键列和分析值列的对象
 * @returns Promise，包含分析成功与否及报告内容
 */
export const analyzeFiles = async (
  files: UploadRawFile[],
  // 新增: 接收一个包含分析参数的对象
  params: { keyColumns: string[]; valueColumn: string }
) => {
  const formData = new FormData();

  // 1. 附加文件 (保持不变)
  files.forEach(file => {
    formData.append('files', file);
  });

  // 2. 新增: 附加分析参数
  // 将JavaScript对象转换为JSON字符串，以便通过FormData传输
  // 后端将接收这个字符串并解析回对象
  formData.append('params', JSON.stringify(params));

  // 请求将自动使用 multipart/form-data 类型
  const response = await apiClient.post('analyze', formData);

  return response.data;
};

// START: 新增的示例分析API函数
/**
 * 示例分析服务
 * @param params 包含关键列和分析值列的对象
 * @returns Promise，包含分析成功与否及报告内容
 */
export const analyzeDemo = async (
  params: { keyColumns: string[]; valueColumn: string }
) => {
  // 注意：这里不再使用 FormData，因为我们不上传文件
  // axios 会自动将 params 对象序列化为 JSON 并发送
  const response = await apiClient.post('analyze-demo', params);
  return response.data;
};


/**
 * 下载 PDF 报告服务
 * @param markdown 报告的 Markdown 文本
 */
export const downloadPdf = async (markdown: string) => {
  const response = await apiClient.post('download/pdf', { markdown }, {
    responseType: 'blob',
  });

  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', 'analysis_report.pdf');
  document.body.appendChild(link);
  link.click();

  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};