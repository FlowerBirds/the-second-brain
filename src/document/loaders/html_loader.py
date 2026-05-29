"""
HTML文档加载器
"""

from typing import List

from langchain_community.document_loaders import UnstructuredHTMLLoader

from src.document.loaders.base import BaseLoader, Document


class HTMLLoader(BaseLoader):
    """HTML文档加载器"""

    def __init__(self, mode: str = "elements"):
        """
        Args:
            mode: 加载模式，"elements"保留结构信息，"single"返回单一文本
        """
        self.mode = mode

    def load(self, file_path: str) -> Document:
        """加载HTML文件"""
        loader = UnstructuredHTMLLoader(file_path, mode=self.mode)
        docs = loader.load()

        if not docs:
            return Document(page_content="", metadata=self._get_default_metadata(file_path))

        # 合并所有元素的内容
        content = "\n".join([doc.page_content for doc in docs])
        metadata = docs[0].metadata if docs else {}
        metadata.update(self._get_default_metadata(file_path))

        return Document(page_content=content, metadata=metadata)

    def load_batch(self, directory: str, pattern: str = "**/*.html") -> List[Document]:
        """批量加载HTML文件"""
        return super().load_batch(directory, pattern)
