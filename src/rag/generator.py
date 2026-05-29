"""
答案生成模块
"""

import os
from typing import Optional

import httpx
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


# 自定义 HTTP 客户端，添加 user-agent
class UAClient(httpx.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        request.headers['user-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0'
        return super().send(request, **kwargs)


class RAGPromptTemplate:
    """RAG提示词模板"""

    DEFAULT_TEMPLATE = """你是一个知识库助手。请根据以下参考文档回答用户问题。

参考文档：
{context}

用户问题：{question}

请根据参考文档回答，如果文档中没有相关信息，请如实说明。"""

    def __init__(self, template: Optional[str] = None):
        self.template = template or self.DEFAULT_TEMPLATE
        self.prompt = PromptTemplate(
            template=self.template,
            input_variables=["context", "question"],
        )

    def format(self, context: str, question: str) -> str:
        return self.prompt.format(context=context, question=question)


class AnswerGenerator:
    """答案生成器"""

    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Args:
            model: LLM模型名称
            temperature: 生成温度
            max_tokens: 最大令牌数
            api_base: API基础URL
            api_key: API密钥（可选）
        """
        # 从环境变量获取API密钥
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")

        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            base_url=api_base,
            http_client=UAClient(verify=False),
            http_async_client=httpx.AsyncClient(verify=False),
        )
        self.prompt_template = RAGPromptTemplate()
        self._model = model
        self._api_base = api_base
        logger.info(f"答案生成器初始化完成: {model}")

    def generate(self, question: str, context: str) -> str:
        """生成答案"""
        logger.info(f"开始生成答案 - model: {self._model}, api_base: {self._api_base}")
        logger.debug(f"Context length: {len(context)}, Question: {question[:50]}...")

        prompt = self.prompt_template.format(context=context, question=question)
        logger.debug(f"Prompt length: {len(prompt)}")

        try:
            logger.info("调用 LLM API...")
            response = self.llm.invoke(prompt)
            content = response.content
            logger.info(f"LLM API 调用成功, response length: {len(content) if content else 0}")

            # 安全处理可能的编码问题
            if isinstance(content, str):
                # 移除代理字符
                content = content.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')

            return content
        except Exception as e:
            logger.error(f"LLM API 调用失败: {type(e).__name__}: {e}")
            raise
