"""
纯文本文档加载器
"""

from typing import List

from src.document.loaders.base import BaseLoader, Document


class TextLoader(BaseLoader):
    """纯文本文件加载器"""

    def __init__(self, encoding: str = "utf-8"):
        """
        Args:
            encoding: 文本编码，默认utf-8
        """
        self.encoding = encoding

    def load(self, file_path: str) -> Document:
        """加载文本文件"""
        with open(file_path, "r", encoding=self.encoding) as f:
            content = f.read()

        metadata = self._get_default_metadata(file_path)
        metadata["encoding"] = self.encoding

        return Document(page_content=content, metadata=metadata)

    def load_batch(self, directory: str, pattern: str = "**/*.txt") -> List[Document]:
        """批量加载文本文件"""
        return super().load_batch(directory, pattern)
