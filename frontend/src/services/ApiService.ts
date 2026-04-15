// DQCTv2/frontend/src/services/ApiService.ts

import axios from 'axios';
import type { UploadRawFile } from 'element-plus';

// 为非流式请求（如PDF下载）保留axios客户端
const apiClient = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5分钟超时
});

/**
 * 定义流式分析所需的回调函数类型签名
 */
export interface StreamAnalysisCallbacks {
  onChunk: (chunk: string) => void;
  onError: (error: Error) => void;
  onClose: () => void;
}

/**
 * 通用的流式分析处理函数
 * @param url API端点 (例如 'analyze' 或 'analyze-demo')
 * @param body 请求体 (可以是 FormData 或 JSON 字符串)
 * @param callbacks 包含 onChunk, onError, onClose 的回调对象
 */
const streamAnalyze = async (
  url: string,
  body: BodyInit,
  callbacks: StreamAnalysisCallbacks
) => {
  try {
    const response = await fetch(`/api/${url}`, {
      method: 'POST',
      body: body,
      // 如果发送的是JSON，需要设置请求头
      headers: body instanceof FormData ? {} : { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
      // 如果服务器返回错误状态码，读取错误信息并抛出
      const errorText = await response.text();
      throw new Error(`请求失败 (${response.status}): ${errorText || '未知服务器错误'}`);
    }

    if (!response.body) {
      throw new Error('响应体为空，无法读取数据流。');
    }

    // 获取响应体的读取器和解码器
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');

    // 循环读取数据流直到结束
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break; // 数据流已读取完毕
      }
      // 解码数据块并调用onChunk回调
      const chunk = decoder.decode(value, { stream: true });
      callbacks.onChunk(chunk);
    }

    // 数据流正常关闭时调用onClose回调
    callbacks.onClose();

  } catch (error) {
    // 捕获任何在fetch或流处理中发生的错误，并调用onError回调
    callbacks.onError(error as Error);
  }
};

/**
 * 分析文件服务（流式版本）
 * @param files 文件对象数组
 * @param params 包含关键列和分析值列的对象
 * @param callbacks 流式处理的回调函数
 */
export const analyzeFiles = async (
  files: UploadRawFile[],
  params: { keyColumns: string[]; valueColumn: string },
  callbacks: StreamAnalysisCallbacks
) => {
  const formData = new FormData();
  files.forEach(file => {
    formData.append('files', file);
  });
  formData.append('params', JSON.stringify(params));

  await streamAnalyze('analyze', formData, callbacks);
};

/**
 * 示例分析服务（流式版本）
 * @param params 包含关键列和分析值列的对象
 * @param callbacks 流式处理的回调函数
 */
export const analyzeDemo = async (
  params: { keyColumns: string[]; valueColumn: string },
  callbacks: StreamAnalysisCallbacks
) => {
  const body = JSON.stringify(params);
  await streamAnalyze('analyze-demo', body, callbacks);
};


/**
 * 下载 PDF 报告服务 (此函数保持不变)
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