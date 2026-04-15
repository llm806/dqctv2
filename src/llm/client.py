# -*- coding: utf-8 -*-

import os
from openai import OpenAI
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

def get_llm_client() -> OpenAI:
    """
    初始化并返回一个配置好的OpenAI客户端，用于调用兼容服务（如DashScope）。

    Raises:
        ValueError: 如果环境变量未设置。
        Exception: 客户端初始化失败。
    """
    try:
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("环境变量 DASHSCOPE_API_KEY 未设置或为空。")

        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", # 如果用本地部署的大模型服务，修改为对应的URL
        )
        return client
    except Exception as e:
        print(f"❌ LLM客户端初始化失败: {e}")
        raise


# 函数修改为生成器函数
def request_llm_analysis(client: OpenAI, model: str, system_prompt: str, user_prompt: str):
    """
    向大语言模型发送分析请求并以流式方式返回结果。
    """
    try:
        # 增加 stream=True 参数
        stream = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ], # type: ignore
            stream=True, # 关键改动
            extra_body={'enable_thinking': False}
        )
        # 遍历返回的数据流
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                # 使用 yield 返回每一块内容
                yield content
    except Exception as e:
        print(f"❌ 请求大模型分析时发生错误: {e}")
        # 可以在这里 yield 一个错误信息，或者直接 raise
        yield f"ERROR: 请求大模型分析时出错: {str(e)}"
        raise

# def request_llm_analysis(client: OpenAI, model: str, system_prompt: str, user_prompt: str) -> str:
#     """
#     向大语言模型发送分析请求并返回结果。
#     """
#     try:
#         completion = client.chat.completions.create(
#             model=model,
#             messages=[
#                 {'role': 'system', 'content': system_prompt},
#                 {'role': 'user', 'content': user_prompt}
#             ],
#             stream=True,
#             extra_body={'enable_thinking': False}
#         ) # 如果用本地部署的大模型服务，可能需要调整参数
#         return completion.choices[0].message.content
#     except Exception as e:
#         print(f"❌ 请求大模型分析时发生错误: {e}")
#         raise