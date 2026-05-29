"""
嵌入模型管理模块
"""

import os
from typing import List, Optional

import httpx
from langchain_openai import OpenAIEmbeddings

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


# 自定义 HTTP 客户端，添加 user-agent
class UAClient(httpx.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        request.headers['user-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0'
        logger.info(f"嵌入模型请求: {request.method} {request.url}")
        return super().send(request, **kwargs)


class Embedder:
    """嵌入模型管理器"""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        batch_size: int = 100,
    ):
        """
        Args:
            model: 嵌入模型名称
            dimensions: 向量维度
            api_base: API基础URL（可选，用于代理或自定义端点）
            api_key: API密钥（可选，默认从环境变量获取）
            batch_size: 批处理大小
        """
        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size

        # 从环境变量获取API密钥
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("EMBEDDING_API_KEY")

        self.embeddings = OpenAIEmbeddings(
            model=model,
            dimensions=dimensions,
            api_key=api_key,
            base_url=api_base,
            http_client=UAClient(verify=False),
        )
        logger.info(f"嵌入模型初始化完成: {model} ({dimensions}维)")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量生成嵌入向量"""
        logger.debug(f"Embedding {len(texts)} texts...")
        result = self.embeddings.embed_documents(texts)
        logger.debug(f"Embedded {len(result)} texts, dim={self.dimensions}")
        return result

    def embed_query(self, query: str) -> List[float]:
        """为查询生成嵌入向量"""
        logger.debug(f"Embedding query: {query[:50]}...")
        result = self.embeddings.embed_query(query)
        logger.debug(f"Query embedding done, dim={len(result)}")
        return result
