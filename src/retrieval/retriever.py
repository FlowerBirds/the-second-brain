"""
检索模块
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from src.document.loaders.base import Document
from src.vectorstore.chroma_client import ChromaVectorStore
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class RetrievalResult:
    """检索结果封装"""

    document: Document
    score: float
    rank: int


class Retriever:
    """语义检索器"""

    def __init__(
        self,
        vectorstore: ChromaVectorStore,
        top_k: int = 5,
        min_similarity: float = 0.6,
        use_mmr: bool = True,
        mmr_lambda: float = 0.5,
    ):
        """
        Args:
            vectorstore: 向量存储
            top_k: 返回结果数量
            min_similarity: 最小相似度阈值
            use_mmr: 是否使用最大边际相关性
            mmr_lambda: MMR参数 (0-1之间，越大越多样性)
        """
        self.vectorstore = vectorstore
        self.top_k = top_k
        self.min_similarity = min_similarity
        self.use_mmr = use_mmr
        self.mmr_lambda = mmr_lambda

    def retrieve(
        self,
        query: str,
        filter_metadata: Optional[dict] = None,
    ) -> List[RetrievalResult]:
        """
        执行检索

        Args:
            query: 查询文本
            filter_metadata: 元数据过滤条件

        Returns:
            检索结果列表，按相关性排序
        """
        if self.use_mmr:
            docs = self.vectorstore.max_marginal_relevance_search(
                query=query,
                k=self.top_k,
                lambda_mult=self.mmr_lambda,
            )
            results = [
                RetrievalResult(document=doc, score=0.0, rank=i + 1)
                for i, doc in enumerate(docs)
            ]
        else:
            doc_scores = self.vectorstore.similarity_search_with_score(
                query=query,
                k=self.top_k,
            )
            results = [
                RetrievalResult(document=doc, score=score, rank=i + 1)
                for i, (doc, score) in enumerate(doc_scores)
                if score >= self.min_similarity
            ]

        logger.info(f"检索完成: query='{query[:50]}...', 返回 {len(results)} 个结果")
        return results

    def retrieve_with_context(
        self,
        query: str,
        max_context_length: int = 3000,
    ) -> Tuple[str, List[RetrievalResult]]:
        """
        检索并组装上下文文本

        Args:
            query: 查询文本
            max_context_length: 最大上下文长度（字符数）

        Returns:
            (组装后的上下文字符串, 检索结果列表)
        """
        results = self.retrieve(query)

        context_parts = []
        current_length = 0

        for result in results:
            chunk = result.document.page_content
            chunk_length = len(chunk)

            if current_length + chunk_length > max_context_length:
                break

            context_parts.append(chunk)
            current_length += chunk_length

        context = "\n\n---\n\n".join(context_parts)
        return context, results
