"""
知识库主类
整合所有模块的统一接口
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config.settings import Settings
from src.document.chunker import DocumentChunker
from src.document.loaders.html_loader import HTMLLoader
from src.document.loaders.markdown_loader import MarkdownLoader
from src.document.loaders.text_loader import TextLoader
from src.rag.chain import RAGChain
from src.rag.generator import AnswerGenerator
from src.retrieval.retriever import Retriever
from src.vectorstore.chroma_client import ChromaVectorStore
from src.vectorstore.embedder import Embedder
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class KnowledgeBase:
    """知识库主类，整合所有功能"""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Args:
            config_path: 配置文件路径
        """
        # 1. 加载配置
        self.config = Settings(config_path)
        self.config.validate()

        # 2. 初始化文档加载器
        self.loaders = {
            ".md": MarkdownLoader(),
            ".txt": TextLoader(),
            ".html": HTMLLoader(),
        }

        # 3. 初始化分块器
        self.chunker = DocumentChunker(
            chunk_size=self.config.get("document.chunk_size"),
            chunk_overlap=self.config.get("document.chunk_overlap"),
        )

        # 4. 初始化嵌入模型
        self.embedder = Embedder(
            model=self.config.get("embedding.model"),
            dimensions=self.config.get("embedding.dimensions"),
            api_base=self.config.get("embedding.api_base"),
            api_key=self.config.get("embedding.api_key"),
        )

        # 5. 初始化向量存储
        self.vectorstore = ChromaVectorStore(
            persist_directory=self.config.get("chroma.persist_directory"),
            collection_name=self.config.get("chroma.collection_name"),
            embedder=self.embedder,
        )

        # 6. 初始化检索器
        self.retriever = Retriever(
            vectorstore=self.vectorstore,
            top_k=self.config.get("rag.top_k"),
            min_similarity=self.config.get("rag.min_similarity"),
            use_mmr=self.config.get("rag.use_mmr"),
            mmr_lambda=self.config.get("rag.mmr_lambda"),
        )

        # 7. 初始化生成器
        self.generator = AnswerGenerator(
            model=self.config.get("llm.model"),
            temperature=self.config.get("llm.temperature"),
            max_tokens=self.config.get("llm.max_tokens"),
            api_base=self.config.get("llm.api_base"),
            api_key=self.config.get("llm.api_key"),
        )

        # 8. 初始化RAG链
        self.rag_chain = RAGChain(
            retriever=self.retriever,
            generator=self.generator,
        )

        logger.info("知识库初始化完成")

    def add_document(self, file_path: str) -> Optional[str]:
        """
        添加单个文档

        Args:
            file_path: 文件路径

        Returns:
            文档ID
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix not in self.loaders:
            raise ValueError(f"不支持的格式: {suffix}")

        # 加载文档
        doc = self.loaders[suffix].load(str(path))
        logger.info(f"加载文档: {file_path}")

        # 分块
        chunks = self.chunker.chunk_documents([doc])
        logger.info(f"文档分块: {len(chunks)} 块")

        # 添加到向量库
        ids = self.vectorstore.add_documents(chunks)
        logger.info(f"文档已添加到向量库: {file_path}")

        return ids[0] if ids else None

    def add_documents(self, directory: str, pattern: str = "**/*") -> List[str]:
        """
        批量添加目录下的文档

        Args:
            directory: 目录路径
            pattern: 文件匹配模式

        Returns:
            添加的文档ID列表
        """
        path = Path(directory)
        ids = []

        for file_path in path.glob(pattern):
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                if suffix in self.loaders:
                    try:
                        doc_id = self.add_document(str(file_path))
                        if doc_id:
                            ids.append(doc_id)
                    except Exception as e:
                        logger.warning(f"添加文档失败 {file_path}: {e}")

        logger.info(f"批量添加完成: {len(ids)} 个文档")
        return ids

    def search(self, query: str, top_k: Optional[int] = None) -> Dict[str, Any]:
        """
        语义搜索

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            包含答案和来源的字典
        """
        if top_k:
            original_top_k = self.retriever.top_k
            self.retriever.top_k = top_k

        result = self.rag_chain.ask(query, return_sources=True)

        if top_k:
            self.retriever.top_k = original_top_k

        return result

    def ask(self, question: str) -> str:
        """
        RAG问答

        Args:
            question: 用户问题

        Returns:
            自然语言答案
        """
        return self.rag_chain.ask(question)["answer"]

    def count_documents(self) -> int:
        """返回原始文档数（通过去重source计算）"""
        try:
            all_data = self.vectorstore.vectorstore.get()
            sources = set()
            for metadata in all_data.get("metadatas", []):
                if metadata and "source" in metadata:
                    sources.add(metadata["source"])
            return len(sources)
        except Exception:
            return 0

    def count_chunks(self) -> int:
        """返回分块总数"""
        return self.vectorstore.count()

    def clear(self) -> None:
        """清空知识库"""
        self.vectorstore.delete()
        logger.info("知识库已清空")

    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        return {
            "total_documents": self.count_documents(),
            "total_chunks": self.count_chunks(),
            "collection": self.vectorstore.get_collection(),
        }
