# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
# Install
pip install -e .

# Run unified HTTP server (Web + REST API + MCP HTTP on single port)
second-brain --port 8765

# Or directly
python http_server.py --port 8765

# MCP stdio mode (for Claude Code)
python main.py --mode mcp-stdio

# CLI interactive Q&A
python main.py --mode cli

# Add documents to knowledge base
python main.py --add-docs ./data/documents

# Clear knowledge base
python main.py --clear
```

No test suite exists yet.

## Architecture

**KnowledgeBase** (`src/knowledge_base.py`) is the single orchestrator that wires all modules in order:

```
Settings → Loaders (.md/.txt/.html) → Chunker → Embedder → ChromaVectorStore → Retriever → RAGChain
```

**MCP design**: `search_knowledge` only calls `_kb.retriever.retrieve()` — no LLM generation. Raw retrieval results are returned for the consuming AI agent to synthesize. This is intentional.

**Two entry points**:
- `main.py` — CLI and standalone MCP server (stdio/http/sse)
- `http_server.py` — FastAPI + FastMCP unified server (single port)

## FastMCP + FastAPI Integration

The single-port integration in `http_server.py` requires two critical steps:

1. **Pass MCP lifespan to FastAPI**: `FastAPI(lifespan=mcp_app.lifespan)` — without this, FastMCP's task group won't initialize, causing "Task group is not initialized" errors.
2. **Mount MCP app at root path**: `app.mount("/", mcp.http_app(path="/mcp", transport="http"))` — must be registered AFTER all FastAPI routes, since mount acts as a fallback.

## Configuration

- **config.yaml** — primary config (embedding, chroma, llm, rag, mcp sections)
- **Priority**: config.yaml > environment variables > defaults
- **Key env vars**: `OPENAI_API_KEY`, `OPENAI_API_BASE`, `EMBEDDING_API_KEY`, `EMBEDDING_API_BASE`
- **.mcp.json** — MCP client config for Claude Code, points to `main.py --mode mcp-stdio`

## MCP Tool Registration

Tools are registered in `src/mcp_protocol/server.py` via `@_mcp.tool()` decorators inside `init_mcp()`. The module-level `_kb` and `_mcp` globals are set during `init_mcp()`.

The `search_knowledge` return includes a `rule` field that instructs the consuming agent: on success, add source references; on failure, fall back to Context7, MiniMax Search, or official docs.

## Embedding & Retrieval

- **Embedder** (`src/vectorstore/embedder.py`): Wraps `OpenAIEmbeddings` with a custom `UAClient` (injects User-Agent, disables SSL verify). HTTP request URLs are logged in `UAClient.send()`.
- **ChromaVectorStore** (`src/vectorstore/chroma_client.py`): Local Chroma persistence, supports similarity search and MMR.
- **Retriever** (`src/retrieval/retriever.py`): When `use_mmr=False`, returns cosine distance scores (0=identical, 1=orthogonal, 2=opposite). When `use_mmr=True`, scores are not available (set to 0.0).

## Document Processing

Document addition is incremental — `add_document(file_path)` only vectorizes the given file, not the entire knowledge base.
