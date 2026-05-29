"""
文档加载器基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class Document:
    """文档数据结构"""

    page_content: str
    metadata: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return f"Document(content_length={len(self.page_content)}, metadata={self.metadata})"


class BaseLoader(ABC):
    """文档加载器抽象基类"""

    @abstractmethod
    def load(self, file_path: str) -> Document:
        """
        加载单个文件

        Args:
            file_path: 文件路径

        Returns:
            Document对象
        """
        pass

    def load_batch(self, directory: str, pattern: str = "*") -> List[Document]:
        """
        批量加载目录下的文件

        Args:
            directory: 目录路径
            pattern: 文件匹配模式

        Returns:
            Document列表
        """
        path = Path(directory)
        documents = []

        for file_path in path.glob(pattern):
            if file_path.is_file():
                try:
                    doc = self.load(str(file_path))
                    documents.append(doc)
                except Exception as e:
                    logger.warning(f"加载文件失败 {file_path}: {e}")

        return documents

    def _get_default_metadata(self, file_path: str) -> dict:
        """获取默认元数据"""
        path = Path(file_path)
        return {
            "source": str(path.absolute()),
            "filename": path.name,
            "format": path.suffix.lower(),
        }
