import axios from 'axios';
import type { UploadRawFile } from 'element-plus';

// 创建 Axios 实例
const apiClient = axios.create({
  // baseURL 保持不变，它定义了所有请求的公共前缀
  baseURL: '/api',
  // 移除这里的默认 headers，让 axios 根据请求内容自动设置
  // 默认超时时间设置为5分钟，以防大文件分析耗时过长
  timeout: 300000,
});

/**
 * 分析文件服务
 * @param files 文件对象数组
 * @returns Promise，包含分析成功与否及报告内容
 */
export const analyzeFiles = async (files: UploadRawFile[]) => {
  const formData = new FormData();
  files.forEach(file => {
    // 这里的 key "files" 必须与 FastAPI 后端参数名 `files: List[UploadFile]` 完全匹配
    formData.append('files', file);
  });

  // 【修复 1】: 将请求路径 '/analyze' 改为 'analyze' (去掉开头的'/')
  // 这样 axios 才能正确地将它和 baseURL 拼接为 '/api/analyze'
  // 【修复 2】: 移除手动设置的 headers 配置
  // 让 axios 自动为 FormData 生成正确的 'Content-Type: multipart/form-data' 和 boundary
  const response = await apiClient.post('analyze', formData);

  return response.data;
};

/**
 * 下载 PDF 服务
 * @param markdown 报告的 Markdown 文本
 */
export const downloadPdf = async (markdown: string) => {
  // 【修复 1】: 同样地，将 '/download/pdf' 改为 'download/pdf'
  const response = await apiClient.post('download/pdf', { markdown }, {
    responseType: 'blob', // 告诉axios期望接收一个二进制文件
  });

  // 创建一个URL指向返回的blob数据
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', 'analysis_report.pdf');
  document.body.appendChild(link);
  link.click();

  // 清理
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};
