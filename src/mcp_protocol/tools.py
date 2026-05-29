"""
MCP工具模块
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class MCPTool:
    """MCP工具定义"""

    name: str
    description: str
    input_schema: dict
    handler: Callable[[dict], Any]

    def to_dict(self) -> dict:
        """转换为MCP协议格式"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


@dataclass
class MCPResponse:
    """MCP响应封装"""

    success: bool = True
    data: Any = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        if self.error:
            return {"success": False, "error": self.error}
        return {"success": True, "data": self.data}


class MCPTools:
    """MCP工具集合"""

    @staticmethod
    def search_knowledge(args: dict, rag_chain) -> dict:
        """知识库搜索工具"""
        query = args.get("query")
        if not query:
            return MCPResponse(success=False, error="query is required").to_dict()

        result = rag_chain.ask(query, return_sources=True)

        return MCPResponse(
            data={
                "answer": result["answer"],
                "sources": result.get("sources", []),
                "query": query,
            }
        ).to_dict()

    @staticmethod
    def add_document(args: dict, knowledge_base) -> dict:
        """添加文档到知识库"""
        file_path = args.get("file_path")
        if not file_path:
            return MCPResponse(success=False, error="file_path is required").to_dict()

        try:
            doc_id = knowledge_base.add_document(file_path)
            return MCPResponse(
                data={
                    "status": "success",
                    "document_id": doc_id,
                    "message": f"Document added: {file_path}",
                }
            ).to_dict()
        except Exception as e:
            return MCPResponse(success=False, error=str(e)).to_dict()

    @staticmethod
    def get_stats(args: dict, knowledge_base) -> dict:
        """获取知识库统计信息"""
        return MCPResponse(
            data={
                "total_chunks": knowledge_base.count_chunks(),
                "total_documents": knowledge_base.count_documents(),
            }
        ).to_dict()


def create_search_tool(rag_chain) -> MCPTool:
    """创建搜索工具"""
    return MCPTool(
        name="search_knowledge",
        description="搜索知识库，根据查询返回相关答案和来源",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索查询"},
            },
            "required": ["query"],
        },
        handler=lambda args: MCPTools.search_knowledge(args, rag_chain),
    )


def create_add_document_tool(knowledge_base) -> MCPTool:
    """创建添加文档工具"""
    return MCPTool(
        name="add_document",
        description="添加文档到知识库",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "文件路径"},
            },
            "required": ["file_path"],
        },
        handler=lambda args: MCPTools.add_document(args, knowledge_base),
    )


def create_get_stats_tool(knowledge_base) -> MCPTool:
    """创建统计工具"""
    return MCPTool(
        name="get_stats",
        description="获取知识库统计信息",
        input_schema={"type": "object", "properties": {}},
        handler=lambda args: MCPTools.get_stats(args, knowledge_base),
    )
