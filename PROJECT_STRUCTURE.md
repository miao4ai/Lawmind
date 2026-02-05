# Mamimind Project Structure

完整的 Agentic AI 系统文件骨架，可部署到 GCP Cloud Functions/Cloud Run。

## 📁 目录结构

```
mamimind/
├── README.md                     # 项目总览
├── PROJECT_STRUCTURE.md          # 本文件
├── .gitignore                   # Git 忽略配置
├── .env.example                 # 环境变量模板
├── pyproject.toml               # Python 项目配置 (推荐)
├── requirements.txt             # Python 依赖
│
├── frontend/                    # 🎨 Web 前端 (Next.js/React)
│   ├── pages/                   # Next.js 页面
│   ├── components/              # React 组件
│   └── lib/                     # 前端工具库
│
├── services/                    # ☁️  Cloud Functions (HTTP/PubSub)
│   ├── upload_doc/              # 生成上传 URL
│   │   ├── handler.py
│   │   └── requirements.txt
│   │
│   ├── ocr_process/             # OCR 处理 (PubSub 触发)
│   │   ├── handler.py
│   │   └── requirements.txt
│   │
│   ├── index_doc/               # 文档索引 (PubSub 触发)
│   │   ├── handler.py
│   │   └── requirements.txt
│   │
│   ├── rag_query/               # RAG 问答 (HTTP)
│   │   ├── handler.py
│   │   └── requirements.txt
│   │
│   └── doc_status/              # 文档状态查询 (HTTP)
│       ├── handler.py
│       └── requirements.txt
│
├── agents/                      # 🤖 Agent 层 (核心差异化)
│   ├── __init__.py
│   ├── base.py                  # Agent 基类
│   ├── runtime.py               # Agent 运行时 (retry/trace)
│   ├── registry.py              # Agent 注册表
│   │
│   ├── ocr_agent/               # OCR Agent
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   └── schema.py
│   │
│   ├── indexing_agent/          # 索引 Agent
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   └── schema.py
│   │
│   └── legal_reasoning_agent/   # 法律推理 Agent
│       ├── __init__.py
│       ├── agent.py
│       ├── prompts.py
│       └── schema.py
│
├── tools/                       # 🔧 Agent 可调用工具
│   ├── __init__.py
│   ├── ocr.py                   # OCR 工具
│   ├── chunking.py              # 文档切分
│   ├── embeddings.py            # Embedding 生成
│   ├── vector_search.py         # 向量检索
│   └── llm.py                   # LLM 调用
│
├── shared/                      # 📦 共享代码 (重要!)
│   ├── __init__.py
│   ├── config/                  # 配置管理
│   │   ├── __init__.py
│   │   └── settings.py
│   │
│   ├── models/                  # 数据模型
│   │   ├── __init__.py
│   │   ├── document.py
│   │   ├── chunk.py
│   │   └── query.py
│   │
│   └── utils/                   # 工具函数
│       └── __init__.py
│
├── storage/                     # 💾 存储结构 (逻辑)
│   ├── raw/                     # 原始文件
│   └── processed/               # 处理后文件
│
├── vector_db/                   # 🔍 向量数据库抽象
│   ├── __init__.py
│   ├── client.py                # Qdrant/Vertex 客户端
│   └── schema.py
│
├── metadata_db/                 # 📊 元数据库 (Firestore)
│   ├── __init__.py
│   └── repository.py
│
├── observability/               # 👀 可观测性
│   ├── __init__.py
│   ├── tracing.py               # OpenTelemetry 追踪
│   └── logging.py               # 结构化日志
│
├── infra/                       # 🏗️  基础设施即代码
│   └── gcp/
│       └── main.tf              # Terraform 配置
│
├── deployment/                  # 🚀 部署脚本
│   └── deploy.sh                # 一键部署脚本
│
├── scripts/                     # 🛠️  运维/开发脚本
│   ├── dev_server.py            # 本地开发服务器
│   ├── local_ocr_test.py        # 本地 OCR 测试
│   └── reindex_doc.py           # 重建索引
│
├── tests/                       # 🧪 测试
│   ├── unit/                    # 单元测试
│   ├── integration/             # 集成测试
│   └── e2e/                     # 端到端测试
│
└── docs/                        # 📚 文档
    ├── architecture.md          # 架构设计
    ├── agents.md                # Agent 设计说明
    ├── api_spec.md              # API 规范
    ├── deployment.md            # 部署指南
    └── demo.md                  # Demo 演示
```

## 🎯 关键设计亮点

### 1. **Shared 模块** (改进点 ✨)
- 避免各 Cloud Function 重复代码
- 统一的配置管理 (settings.py)
- 共享数据模型 (Pydantic)
- 可跨服务导入使用

### 2. **Agent 架构** (核心差异化 🌟)
- 强类型接口 (base.py)
- 自动重试和追踪 (runtime.py)
- 动态发现和注册 (registry.py)
- 完全可测试和可组合

### 3. **Tools 层** (可复用)
- 独立于 Agent 的工具
- 可被多个 Agent 共享
- 易于 Mock 和测试

### 4. **Services 层** (GCP 部署)
- 每个 service 是独立的 Cloud Function
- 有自己的 requirements.txt
- 可以独立部署和扩缩容
- 通过 sys.path 引用 shared 模块

## 🚀 快速开始

### 本地开发

```bash
# 1. 安装依赖
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的配置

# 3. 启动本地开发服务器
python scripts/dev_server.py

# 访问 http://localhost:8000/docs
```

### 部署到 GCP

```bash
# 1. 部署基础设施 (Terraform)
cd infra/gcp
terraform init
terraform plan
terraform apply

# 2. 部署 Cloud Functions
./deployment/deploy.sh

# 3. 配置 Secret Manager
gcloud secrets versions add openai-api-key --data-file=- <<< "your-key"
```

## 📊 数据流

```
用户上传文档
    ↓
upload_doc (Cloud Function)
    ↓
Cloud Storage (raw/)
    ↓
Pub/Sub: ocr-process
    ↓
ocr_process (Cloud Function)
    → OCRAgent
    → 保存到 processed/
    ↓
Pub/Sub: index-doc
    ↓
index_doc (Cloud Function)
    → IndexingAgent
    → 生成 embedding
    → 存入 Qdrant
    ↓
文档状态: READY

用户查询
    ↓
rag_query (Cloud Function)
    → LegalReasoningAgent
    → 检索相关 chunks
    → LLM 生成答案
    → 返回 answer + citations
```

## 🔧 技术栈

| 组件 | 技术选型 |
|------|---------|
| 前端 | Next.js + React + TypeScript |
| 后端 | Python 3.11 + FastAPI |
| 部署 | GCP Cloud Functions (2nd gen) |
| 消息队列 | Cloud Pub/Sub |
| 存储 | Cloud Storage |
| 元数据库 | Firestore |
| 向量数据库 | Qdrant / Vertex AI Vector Search |
| OCR | Google Cloud Vision API |
| Embedding | OpenAI text-embedding-3 |
| LLM | GPT-4 Turbo / Claude |
| 追踪 | OpenTelemetry + Cloud Trace |
| 日志 | Cloud Logging + structlog |
| IaC | Terraform |

## 📈 相比原始结构的改进

### ✅ 添加了 `shared/` 目录
- 避免代码重复
- 统一配置管理
- 共享数据模型

### ✅ 添加了 `deployment/` 目录
- 一键部署脚本
- CI/CD 配置 (可扩展)

### ✅ 添加了 `tests/` 目录
- 完整测试覆盖
- 单元/集成/E2E 测试

### ✅ 改进了 Agent 架构
- 更强的类型系统
- 自动重试机制
- 分布式追踪
- 易于测试

### ✅ 添加了 `observability/` 模块
- 结构化日志
- 分布式追踪
- 性能监控

### ✅ 优化了 Cloud Functions 结构
- 每个 function 独立 requirements.txt
- 共享代码通过模块导入
- 支持 Cloud Run 迁移

## 🎓 面试加分点

1. **Agent 设计模式**: 展示你理解 agentic AI 架构
2. **云原生**: 完整的 GCP 部署方案
3. **可观测性**: OpenTelemetry + Cloud Trace
4. **IaC**: Terraform 管理基础设施
5. **测试**: 完整的测试策略
6. **文档**: 清晰的架构文档

## 📝 下一步

1. ✅ 完成前端 UI 实现
2. ✅ 实现完整的 IndexingAgent
3. ✅ 添加更多测试
4. ✅ 配置 CI/CD (GitHub Actions)
5. ✅ 性能优化和缓存
6. ✅ 添加用户认证 (Firebase Auth)

## 🤝 贡献

欢迎提交 Issue 和 PR！

## 📄 License

MIT
