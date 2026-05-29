"""
RAG链模块
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.rag.generator import AnswerGenerator
from src.retrieval.retriever import Retriever
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class SourceDocument:
    """来源文档封装"""

    content: str
    source: str
    score: float


class RAGChain:
    """RAG链整合"""

    def __init__(
        self,
        retriever: Retriever,
        generator: AnswerGenerator,
    ):
        """
        Args:
            retriever: 检索器
            generator: 答案生成器
        """
        self.retriever = retriever
        self.generator = generator

    def ask(
        self,
        question: str,
        return_sources: bool = False,
    ) -> Dict[str, Any]:
        """
        问答接口

        Args:
            question: 用户问题
            return_sources: 是否返回来源文档

        Returns:
            包含answer的字典，optionally包含sources
        """
        # 1. 检索相关文档
        context, results = self.retriever.retrieve_with_context(question)

        # 2. 生成答案
        answer = self.generator.generate(question, context)

        response = {"answer": answer}

        if return_sources:
            sources = [
                {
                    "content": (
                        r.document.page_content[:200] + "..."
                        if len(r.document.page_content) > 200
                        else r.document.page_content
                    ),
                    "source": r.document.metadata.get("source", "unknown"),
                    "score": r.score,
                }
                for r in results
            ]
            response["sources"] = sources

        return response

    def chat(self, message: str, history: Optional[List[Dict]] = None) -> str:
        """
        对话模式（带历史记录）

        Args:
            message: 用户消息
            history: 对话历史

        Returns:
            助手回复
        """
        # 简化实现，可扩展为ConversationalRetrievalChain
        return self.ask(message)["answer"]
