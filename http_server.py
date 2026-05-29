#!/usr/bin/env python3
"""
HTTP 服务器 - FastAPI + FastMCP 单端口同时提供 Web、REST API 和 MCP HTTP 服务
参考: https://gofastmcp.com/integrations/fastapi
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.mcp_protocol.server import init_mcp
from src.knowledge_base import KnowledgeBase
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_app(config_path: str = "config.yaml") -> FastAPI:
    """创建 FastAPI 应用，同时支持 Web、REST API 和 MCP HTTP"""

    # 初始化 MCP，创建 ASGI 子应用
    mcp = init_mcp()
    mcp_app = mcp.http_app(path="/mcp", transport="http")

    # 关键：将 mcp_app 的 lifespan 传给 FastAPI，确保 session manager 正确初始化
    app = FastAPI(title="第二大脑 - 本地知识库", lifespan=mcp_app.lifespan)

    # 初始化知识库
    kb = KnowledgeBase(config_path=config_path)

    # ========== Web 界面 ==========

    template_path = Path(__file__).parent / "templates" / "index.html"

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return template_path.read_text(encoding="utf-8")

    # ========== REST API ==========

    @app.get("/api/stats")
    async def get_stats():
        try:
            stats = kb.get_stats()
            return JSONResponse({"status": "success", "data": stats})
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

    @app.get("/api/search")
    async def search(q: str, top_k: int = None, max_score: float = None):
        if not q:
            return JSONResponse({"status": "error", "message": "缺少查询参数 q"}, status_code=400)

        try:
            results = kb.retriever.retrieve(q)
            if max_score is not None:
                results = [r for r in results if r.score <= max_score]

            formatted = []
            for r in results:
                formatted.append({
                    "content": r.document.page_content,
                    "source": r.document.metadata.get("source", "unknown"),
                    "score": r.score,
                    "rank": r.rank,
                })

            return JSONResponse({
                "status": "success",
                "data": {
                    "query": q,
                    "results": formatted,
                    "total": len(formatted),
                }
            })
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

    @app.post("/api/documents")
    async def add_document(request: Request):
        data = await request.json()
        if not data or "path" not in data:
            return JSONResponse({"status": "error", "message": "缺少文档路径"}, status_code=400)

        try:
            doc_id = kb.add_document(data["path"])
            return JSONResponse({
                "status": "success",
                "document_id": doc_id,
                "message": f"文档已添加: {data['path']}"
            })
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

    @app.delete("/api/documents")
    async def clear_knowledge_base():
        try:
            kb.clear()
            return JSONResponse({"status": "success", "message": "知识库已清空"})
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

    # ========== 挂载 MCP HTTP 子应用 (必须放最后) ==========
    # mcp_app 内部路由为 /mcp，挂载后实际路径为 /mcp
    app.mount("/", mcp_app)

    # 静态文件
    static_path = Path(__file__).parent / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    return app


def main():
    parser = argparse.ArgumentParser(description="HTTP 服务器 (Web + MCP + REST)")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--host", default="127.0.0.1", help="主机地址")
    parser.add_argument("--port", type=int, default=8765, help="端口号")

    args = parser.parse_args()

    app = create_app(config_path=args.config)

    print(f"\n{'='*50}")
    print(f"第二大脑 - 本地知识库服务")
    print(f"{'='*50}")
    print(f"  Web:       http://{args.host}:{args.port}/")
    print(f"  MCP HTTP:  http://{args.host}:{args.port}/mcp")
    print(f"  REST API:  http://{args.host}:{args.port}/api/*")
    print(f"{'='*50}\n")

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
