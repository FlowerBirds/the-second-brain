"""
Chroma向量数据库封装模块
"""

from typing import List, Optional, Tuple

from langchain_chroma import Chroma

from src.document.loaders.base import Document
from src.vectorstore.embedder import Embedder
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ChromaVectorStore:
    """Chroma向量数据库封装"""

    def __init__(
        self,
        persist_directory: str,
        collection_name: str = "knowledge_base",
        embedder: Optional[Embedder] = None,
    ):
        """
        Args:
            persist_directory: 持久化目录
            collection_name: 集合名称
            embedder: 嵌入模型（可选）
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        # 如果没有提供embedder，使用默认配置
        if embedder is None:
            embedder = Embedder()

        self.embedder = embedder

        self.vectorstore = Chroma(
            client=None,
            collection_name=collection_name,
            persist_directory=persist_directory,
            embedding_function=self.embedder.embeddings,
        )
        logger.info(f"Chroma向量库初始化完成: {collection_name}")

    def add_documents(
        self,
        documents: List[Document],
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """添加文档到向量库"""
        result = self.vectorstore.add_documents(documents=documents, ids=ids)
        logger.info(f"添加 {len(documents)} 个文档块到向量库")
        return result

    def delete(self, ids: Optional[List[str]] = None, where: Optional[dict] = None) -> None:
        """删除向量"""
        self.vectorstore.delete(ids=ids, where=where)
        logger.info("向量库删除完成")

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[dict] = None,
    ) -> List[Document]:
        """相似性搜索"""
        return self.vectorstore.similarity_search(
            query=query,
            k=k,
            filter=filter,
        )

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        threshold: Optional[float] = None,
    ) -> List[Tuple[Document, float]]:
        """
        带相似度分数的搜索

        Args:
            query: 查询文本
            k: 返回数量
            threshold: 相似度阈值（可选）

        Returns:
            (文档, 分数) 元组列表
        """
        results = self.vectorstore.similarity_search_with_score(
            query=query,
            k=k,
        )

        if threshold is not None:
            results = [(doc, score) for doc, score in results if score >= threshold]

        return results

    def max_marginal_relevance_search(
        self,
        query: str,
        k: int = 5,
        lambda_mult: float = 0.5,
    ) -> List[Document]:
        """
        最大边际相关性搜索，增加结果多样性

        Args:
            query: 查询文本
            k: 返回数量
            lambda_mult: 多样性参数 (0-1)，越大越多样化

        Returns:
            文档列表
        """
        logger.debug(f"MMR search: query={query[:30]}..., k={k}")
        return self.vectorstore.max_marginal_relevance_search(
            query=query,
            k=k,
            lambda_mult=lambda_mult,
        )

    def count(self) -> int:
        """返回集合中的文档数量"""
        return self.vectorstore._collection.count()

    def get_collection(self) -> dict:
        """获取集合信息"""
        return {
            "name": self.collection_name,
            "count": self.count(),
            "persist_directory": self.persist_directory,
        }
