#!/usr/bin/env python3
"""
本地知识库系统—第二大脑
入口文件
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.config.settings import Settings
from src.knowledge_base import KnowledgeBase
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="本地知识库系统—第二大脑")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--mode", choices=["cli", "mcp-stdio", "mcp-http", "mcp-sse"], default="cli", help="运行模式")
    parser.add_argument("--add-docs", metavar="DIR", help="添加文档目录")
    parser.add_argument("--clear", action="store_true", help="清空知识库")

    args = parser.parse_args()

    # 检查配置文件是否存在
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"错误: 配置文件不存在: {args.config}")
        sys.exit(1)

    # 初始化知识库（CLI 和 MCP 模式都需要）
    logger.info("初始化知识库...")
    try:
        kb = KnowledgeBase(config_path=args.config)
    except Exception as e:
        logger.error(f"知识库初始化失败: {e}")
        sys.exit(1)

    # 清空知识库
    if args.clear:
        logger.info("清空知识库...")
        kb.clear()
        print("知识库已清空")
        return

    # 添加文档
    if args.add_docs:
        logger.info(f"添加文档: {args.add_docs}")
        doc_path = Path(args.add_docs)
        if not doc_path.exists():
            print(f"错误: 目录不存在: {args.add_docs}")
            sys.exit(1)

        ids = kb.add_documents(args.add_docs)
        print(f"已添加 {len(ids)} 个文档块")
        print(f"知识库统计: {kb.get_stats()}")
        return

    if args.mode == "cli":
        # CLI交互模式
        print("=" * 50)
        print("本地知识库系统—第二大脑")
        print("=" * 50)
        print(f"知识库: {kb.count_chunks()} 个文档块")
        print("输入 'exit' 退出，输入 'stats' 查看统计")
        print()

        while True:
            try:
                query = input("你: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if query.lower() in ["exit", "quit", "退出"]:
                break

            if not query:
                continue

            if query.lower() == "stats":
                stats = kb.get_stats()
                print(f"文档数: {stats['total_documents']}")
                print(f"分块数: {stats['total_chunks']}")
                print()
                continue

            try:
                result = kb.search(query)
                print()

                answer = result["answer"]
                if isinstance(answer, str):
                    try:
                        print(f"答案: {answer}")
                    except UnicodeEncodeError:
                        print("答案: [内容包含无法显示的字符]")
                else:
                    print(f"答案: {answer}")

                print()

                if result.get("sources"):
                    print("参考来源:")
                    for i, src in enumerate(result["sources"], 1):
                        print(f"  [{i}] {src['source']} (score: {src['score']:.4f})")
                    print()

            except Exception as e:
                logger.error(f"搜索失败: {e}")
                print(f"错误: {e}")
                print()

    elif args.mode == "mcp-stdio":
        # MCP stdio 模式
        from src.mcp_protocol.server import get_mcp
        print("启动 MCP 服务器 (stdio 模式)...")
        print("按 Ctrl+C 停止")
        mcp = get_mcp()
        mcp.run()

    elif args.mode == "mcp-http":
        # MCP HTTP 模式
        from src.mcp_protocol.server import get_mcp
        settings = Settings(args.config)
        host = settings.get("mcp.host", "127.0.0.1")
        port = settings.get("mcp.port", 8765)
        print(f"启动 MCP 服务器 (HTTP 模式: http://{host}:{port})")
        print("按 Ctrl+C 停止")
        mcp = get_mcp()
        mcp.run(transport="http", host=host, port=port)

    elif args.mode == "mcp-sse":
        # MCP SSE 模式
        from src.mcp_protocol.server import get_mcp
        settings = Settings(args.config)
        host = settings.get("mcp.host", "127.0.0.1")
        port = settings.get("mcp.port", 8765)
        print(f"启动 MCP 服务器 (SSE 模式: http://{host}:{port})")
        print("按 Ctrl+C 停止")
        mcp = get_mcp()
        mcp.run(transport="sse", host=host, port=port)


if __name__ == "__main__":
    main()
