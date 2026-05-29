"""
文档分块模块
"""

from typing import List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.document.loaders.base import Document
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class DocumentChunker:
    """文档分块器"""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None,
    ):
        """
        Args:
            chunk_size: 每块目标字符数
            chunk_overlap: 块间重叠字符数
            separators: 分隔符列表，按优先级排序
        """
        if separators is None:
            separators = ["\n\n", "\n", "。", "！", "？", ". ", " ", ""]

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            length_function=len,
            is_separator_regex=False,
        )

    def chunk_documents(
        self,
        documents: List[Document],
        add_metadata: bool = True,
    ) -> List[Document]:
        """
        对文档列表进行分块

        Args:
            documents: 原始文档列表
            add_metadata: 是否在分块元数据中记录来源和块索引

        Returns:
            分块后的文档列表
        """
        chunked_docs = self.splitter.split_documents(documents)

        if add_metadata:
            for i, doc in enumerate(chunked_docs):
                doc.metadata["chunk_index"] = i

        logger.info(f"分块完成: {len(documents)} 文档 -> {len(chunked_docs)} 块")
        return chunked_docs

    def chunk_text(
        self,
        text: str,
        metadata: Optional[dict] = None,
    ) -> List[Document]:
        """对单段文本进行分块"""
        chunks = self.splitter.split_text(text)
        return [
            Document(page_content=chunk, metadata=metadata or {})
            for chunk in chunks
        ]
