"""
MCP协议服务器模块 - 基于 FastMCP
支持 stdio、http、sse 模式
"""

import os
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import FastMCP

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# 全局 FastMCP 实例和知识库
_mcp: Optional[FastMCP] = None
_kb = None


def init_mcp():
    """初始化 MCP 服务器"""
    global _mcp, _kb

    from src.config.settings import Settings
    from src.knowledge_base import KnowledgeBase

    # 初始化知识库
    _kb = KnowledgeBase()

    # 创建 FastMCP 实例
    _mcp = FastMCP(
        name="local-second-brain",
        instructions="""你有一个本地知识库系统，名为"第二大脑"。

【功能说明】
- search_knowledge: 搜索知识库，返回检索到的文档块（不包含 LLM 生成内容）
- add_document: 添加文档到知识库
- get_stats: 查看知识库统计

【返回格式】
search_knowledge 返回结构化数据，包含:
- query: 原始查询
- results: 检索结果列表，每项包含 content(内容)、source(来源)、score(分数)、rank(排名)
- total: 结果总数

【重要规则】
1. 搜索结果按相关性排序（score 越低越相关）
2. 由你（智能体）负责阅读检索结果并组织答案
3. 如果检索结果为空或未找到相关内容，请依次尝试以下方式补充查询：
   - 使用 Context7 查询相关技术框架的文档
   - 使用 MiniMax Search 搜索网络获取相关信息
   - 直接访问相关技术框架的官方文档网站
4. 优先使用知识库内容回答，外部来源作为补充；当知识库无结果时，必须使用上述方式获取信息后再回答

示例响应格式：
{
    "query": "什么是RAG",
    "results": [
        {"content": "RAG是...", "source": "docs/rag.md", "score": 0.82, "rank": 1}
    ],
    "total": 1
}

可用工具: search_knowledge(搜索), add_document(添加文档), get_stats(查看统计)"""
    )

    # 注册工具
    @_mcp.tool()
    def search_knowledge(
        query: str,
        top_k: Optional[int] = None,
        max_score: float = 1.0,
    ) -> dict:
        """
        搜索本地知识库。返回检索到的文档块及相关信息，不包含 LLM 生成内容。
        由接入的智能体负责阅读检索结果并组织答案。
        当知识库无相关结果时，请依次使用 Context7、MiniMax Search 或直接访问相关技术框架官方文档补充查询。

        Args:
            query: 搜索查询（可以是任意问题或关键词）
            top_k: 返回结果数量（可选，默认5）
            max_score: 最大距离阈值（可选，默认1.0）。score > max_score 的结果会被过滤掉。
                       score 是余弦距离，0=完全相似，2=完全相反。
                       建议阈值: 0.8=高度相关, 1.0=中度相关, 1.2=低相关

        Returns:
            dict: 包含检索结果的字典，格式为:
            {
                "query": str,           # 原始查询
                "results": [           # 检索结果列表
                    {
                        "content": str,    # 文档块内容
                        "source": str,     # 来源文件路径
                        "score": float,   # 距离分数（越低越相似）
                        "rank": int       # 排名
                    },
                    ...
                ],
                "total": int           # 结果总数
            }
        """
        logger.info(f"搜索知识库: {query}, max_score={max_score}")

        try:
            # 直接使用检索器，不调用 LLM
            if top_k:
                original_top_k = _kb.retriever.top_k
                _kb.retriever.top_k = top_k

            results = _kb.retriever.retrieve(query)

            if top_k:
                _kb.retriever.top_k = original_top_k

            # 组装返回结果，并过滤低相关性
            formatted_results = []
            filtered_count = 0
            for r in results:
                if r.score <= max_score:
                    formatted_results.append({
                        "content": r.document.page_content,
                        "source": r.document.metadata.get("source", "unknown"),
                        "score": r.score,
                        "rank": len(formatted_results) + 1,  # 重新编号
                    })
                else:
                    filtered_count += 1

            logger.info(f"检索完成: 返回 {len(formatted_results)} 个结果，过滤 {filtered_count} 个低相关结果")

            # 根据结果是否为空确定 rule
            if not formatted_results:
                result_rule = "检索失败或者无结果，请依次使用 Context7、MiniMax Search 或直接访问相关技术框架官方文档进行查询"
                result_data = {
                    "query": query,
                    "results": [],
                    "total": 0,
                    "rule": result_rule,
                }
            else:
                result_rule = "本次检索内容作为参考，如果内容符合要求，请在最终答案中添加参考来源，参考来源字段为source（使用绝对路径）"
                result_data = {
                    "query": query,
                    "results": formatted_results,
                    "total": len(formatted_results),
                    "rule": result_rule,
                }

            import json
            print("\n========== MCP 检索结果 ==========")
            print(json.dumps(result_data, ensure_ascii=False, indent=2))
            print("==================================\n")

            return result_data
        except Exception as e:
            logger.error(f"检索失败: {e}")
            import json
            print(f"\n========== MCP 检索失败 ==========\n{json.dumps({'error': str(e)}, ensure_ascii=False, indent=2)}\n==================================\n")
            return {
                "query": query,
                "results": [],
                "total": 0,
                "rule": "检索失败或者无结果，请依次使用 Context7、MiniMax Search 或直接访问相关技术框架官方文档进行查询",
                "error": str(e),
            }

    @_mcp.tool()
    def add_document(file_path: str) -> dict:
        """
        添加文档到本地知识库。支持 .md、.txt、.html 格式。

        Args:
            file_path: 文档的完整路径
        """
        logger.info(f"添加文档: {file_path}")
        try:
            doc_id = _kb.add_document(file_path)
            return {
                "status": "success",
                "document_id": doc_id,
                "message": f"Document added: {file_path}",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @_mcp.tool()
    def get_stats() -> dict:
        """查看知识库当前状态，包括文档数量和分块数量"""
        return _kb.get_stats()

    @_mcp.tool()
    def clear_knowledge_base() -> dict:
        """清空知识库（谨慎使用）"""
        _kb.clear()
        return {"status": "success", "message": "知识库已清空"}

    @_mcp.resource("stats://knowledge")
    def stats_resource() -> str:
        """知识库统计信息资源"""
        import json
        stats = _kb.get_stats()
        return json.dumps(stats, ensure_ascii=False, indent=2)

    return _mcp


def get_mcp() -> FastMCP:
    """获取 MCP 实例"""
    global _mcp
    if _mcp is None:
        init_mcp()
    return _mcp


# 便捷函数
def run(mode: str = "stdio"):
    """
    运行 MCP 服务器

    Args:
        mode: 运行模式 - "stdio", "http", "sse"
    """
    mcp = get_mcp()

    if mode == "stdio":
        mcp.run()
    elif mode == "http":
        mcp.run(transport="http", host="127.0.0.1", port=8765)
    elif mode == "sse":
        # SSE 模式
        mcp.run(transport="sse", host="127.0.0.1", port=8765)
    else:
        raise ValueError(f"不支持的运行模式: {mode}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MCP 服务器")
    parser.add_argument(
        "--mode",
        choices=["stdio", "http", "sse"],
        default="stdio",
        help="运行模式",
    )
    args = parser.parse_args()

    print(f"启动 MCP 服务器: {args.mode} 模式")
    run(args.mode)
