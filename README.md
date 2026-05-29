# 本地知识库系统—第二大脑

基于 RAG (Retrieval-Augmented Generation) 的本地知识库系统，支持文档加载、语义搜索和智能问答。

## 技术栈

- **嵌入模型**: text-embedding-3-small (1536维)
- **向量数据库**: Chroma (持久化存储)
- **LLM框架**: LangChain
- **MCP框架**: FastMCP (支持 stdio/http/sse)
- **Web框架**: FastAPI + Uvicorn
- **协议层**: MCP (Model Context Protocol)

## 支持的文档格式

- Markdown (.md)
- 纯文本 (.txt)
- HTML (.html)

## 项目结构

```
local-second-brain/
├── main.py                      # 应用入口
├── mcp_server.py                # MCP stdio 模式入口
├── http_server.py               # HTTP 服务器 (FastAPI + MCP HTTP)
├── pyproject.toml               # 打包配置（含 second-brain 命令入口）
├── requirements.txt             # 依赖清单
├── config.yaml                  # 配置文件
├── .mcp.json                   # MCP 客户端配置
├── templates/
│   └── index.html               # Web 界面模板
├── static/                      # 静态资源
├── src/
│   ├── config/settings.py       # 配置管理
│   ├── document/
│   │   ├── loaders/            # 文档加载器
│   │   └── chunker.py          # 文本分块
│   ├── vectorstore/            # 向量存储
│   │   ├── embedder.py        # 嵌入模型
│   │   └── chroma_client.py   # Chroma封装
│   ├── retrieval/              # 检索模块
│   │   └── retriever.py        # 语义检索
│   ├── mcp_protocol/          # MCP协议
│   │   └── server.py          # FastMCP服务器
│   └── knowledge_base.py       # 主类
└── data/
    ├── documents/              # 源文档
    └── chroma_db/             # 向量数据库
```

## 安装

```bash
pip install -e .
```

或仅安装依赖：

```bash
pip install -r requirements.txt
```

## 配置

编辑 `config.yaml` 配置文件：

```yaml
# LLM配置（支持OpenAI兼容模型）
llm:
  model: "gpt-5.5"                    # 模型名称
  api_base: "https://unity2.ai/v1"    # API地址
  api_key: ""                          # API密钥
  temperature: 0.7
  max_tokens: 2000

# 嵌入模型配置（支持OpenAI兼容模型）
embedding:
  model: "text-embedding-3-small"
  dimensions: 1536
  api_base: "https://xiaohumini.site/v1"  # API地址
  api_key: ""                              # API密钥

# RAG配置
rag:
  top_k: 5
  use_mmr: false    # false=返回相似度分数，true=使用MMR多样性检索
```

### 支持的模型

所有兼容 OpenAI API 格式的模型均可使用：

| 类型 | 示例 |
|------|------|
| OpenAI | GPT-4o, GPT-4-turbo, GPT-3.5-turbo |
| 本地模型 | Ollama, LocalAI |
| 云厂商 | Groq, together.ai, unity2.ai, MiniMax |

### 环境变量

| 变量名 | 说明 |
|--------|------|
| `OPENAI_API_KEY` | LLM API密钥 |
| `OPENAI_API_BASE` | LLM API地址 |
| `EMBEDDING_API_KEY` | 嵌入模型API密钥 |
| `EMBEDDING_API_BASE` | 嵌入模型API地址 |

配置优先级：`config.yaml` > 环境变量 > 默认值

## 使用方法

### MCP 模式（推荐）

通过 MCP 协议连接 AI 助手，工具自动调用。

```bash
# stdio 模式（Claude Code 默认）
python main.py --mode mcp-stdio

# HTTP 模式
python main.py --mode mcp-http

# SSE 模式
python main.py --mode mcp-sse
```

在 Claude Code 中首次使用需要启用 MCP 服务器。

**MCP 工具：**

| 工具 | 说明 |
|------|------|
| `search_knowledge` | 搜索知识库（返回原始检索结果，不含LLM生成内容） |
| `add_document` | 添加文档到知识库 |
| `get_stats` | 查看知识库统计 |
| `clear_knowledge_base` | 清空知识库 |

**search_knowledge 参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 搜索查询 |
| `top_k` | integer | 否 | 返回结果数量（默认5） |
| `max_score` | float | 否 | 最大距离阈值，默认1.0（0=完全相似，2=完全相反） |

**返回格式：**

```json
{
  "query": "搜索关键词",
  "results": [
    {
      "content": "文档内容",
      "source": "文档路径",
      "score": 0.82,
      "rank": 1
    }
  ],
  "total": 1,
  "rule": "本次检索内容作为参考，如果内容符合要求，请在最终答案中添加参考来源，参考来源字段为source（使用绝对路径）"
}
```

**特点：**
- MCP 仅提供检索结果，不调用 LLM 生成内容
- 由接入的智能体负责阅读检索结果并组织答案
- 检索失败或无结果时，rule 字段提示使用其他搜索方式
- 支持 `max_score` 过滤低相关性结果

### CLI 模式

```bash
# 添加文档到知识库
python main.py --add-docs ./data/documents

# 启动交互式问答
python main.py --mode cli

# 清空知识库
python main.py --clear
```

### HTTP 服务器模式

FastAPI + FastMCP 单端口同时提供 Web 界面、REST API 和 MCP HTTP 服务。

```bash
# 使用命令行脚本启动（推荐）
second-brain

# 带参数启动
second-brain --port 8765 --host 127.0.0.1

# 或使用 python 直接启动
python http_server.py --port 8765
```

**服务地址：**

| 服务 | 地址 |
|------|------|
| Web 界面 | `http://127.0.0.1:8765/` |
| MCP HTTP | `http://127.0.0.1:8765/mcp` |
| REST API | `http://127.0.0.1:8765/api/*` |

**REST API 端点：**

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/stats` | 获取统计信息 |
| GET | `/api/search?q=关键词` | 搜索知识库 |
| POST | `/api/documents` | 添加文档 |
| DELETE | `/api/documents` | 清空知识库 |

**启动参数：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--config` | config.yaml | 配置文件路径 |
| `--host` | 127.0.0.1 | 主机地址 |
| `--port` | 8765 | 端口号 |

## 核心流程

### 文档处理流程

```
文档 → Loader → Document → Chunker → 分块
      → Embedder → 向量 → Chroma向量库
```

### MCP 问答流程

```
用户问题 → AI判断是否需要搜索
        → search_knowledge工具
        → 检索相关文档（不含LLM生成）
        → 返回检索结果 + rule
        → 由智能体阅读结果并组织答案
```

### 文档增量添加

添加单文件时，仅对该文件进行分块和向量化，不会重新处理整个知识库。

### RAG 检索策略

| 模式 | 说明 |
|------|------|
| `use_mmr: false` | 相似度检索，返回相关度分数 |
| `use_mmr: true` | MMR多样性检索，增加结果多样性 |

## 常见问题

**Q: MCP 连接失败？**
确保 MCP 服务器已启动，端口未被占用。

**Q: API 请求被阻止？**
某些 API 需要添加 User-Agent，检查配置是否正确。

**Q: 如何切换模型？**
修改 `config.yaml` 中的 `llm.model` 和 `llm.api_base`。

**Q: HTTP 服务器 MCP 报错 "Task group is not initialized"？**
确保 `mcp_app.lifespan` 已传递给 FastAPI，参考 `http_server.py` 中的集成方式。
