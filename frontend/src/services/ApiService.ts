// frontend/src/services/ApiService.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api', // Vite代理会处理这个前缀
  headers: {
    'Content-Type': 'application/json',
  },
});

export const analyzeFiles = async (files: File[]) => {
  const formData = new FormData();
  files.forEach(file => {
    formData.append('files', file);
  });

  const response = await apiClient.post('/analyze', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const downloadPdf = async (markdown: string) => {
  const response = await apiClient.post('/download/pdf', { markdown }, {
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
  link.parentNode?.removeChild(link);
  window.URL.revokeObjectURL(url);
};