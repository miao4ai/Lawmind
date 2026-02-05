# 🚀 Getting Started with Mamimind

## 项目概览

Mamimind 是一个基于 Agentic AI 的法律文档智能处理系统，可部署到 GCP。

## 核心特性

✅ **Agentic AI 架构** - 自主的、可组合的 Agent 系统
✅ **云原生部署** - GCP Cloud Functions + Cloud Run
✅ **完整的文档处理流程** - OCR → 分块 → 向量化 → RAG 问答
✅ **可观测性** - OpenTelemetry 追踪 + 结构化日志
✅ **基础设施即代码** - Terraform 管理
✅ **生产就绪** - 重试、超时、错误处理

## 快速开始

### 1. 环境准备

```bash
# 克隆项目 (如果从 Git)
cd /home/mjiang/Documents/Mamimind

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 开发工具 (可选)
pip install -e ".[dev]"
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的配置
nano .env
```

**必须配置的变量**:
- `GCP_PROJECT_ID` - 你的 GCP 项目 ID
- `GCP_STORAGE_BUCKET` - Cloud Storage 桶名
- `OPENAI_API_KEY` - OpenAI API Key
- `QDRANT_URL` - Qdrant 地址 (本地开发: http://localhost:6333)

### 3. 启动本地依赖 (Docker)

```bash
# 启动 Qdrant (向量数据库)
docker run -d -p 6333:6333 -p 6334:6334 \
    --name qdrant \
    qdrant/qdrant

# 或使用 Docker Compose (推荐)
# TODO: 创建 docker-compose.yml
```

### 4. 本地开发服务器

```bash
# 启动开发服务器
python scripts/dev_server.py

# 访问 API 文档
open http://localhost:8000/docs
```

### 5. 测试 API

```bash
# 测试查询端点
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the termination conditions?",
    "user_id": "test_user",
    "top_k": 5
  }'

# 测试上传端点
curl -X POST http://localhost:8000/upload \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "filename": "contract.pdf",
    "file_size": 1024000
  }'
```

## 部署到 GCP

### 前置条件

1. **安装 gcloud CLI**
   ```bash
   # macOS
   brew install google-cloud-sdk

   # Linux
   curl https://sdk.cloud.google.com | bash
   ```

2. **认证**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **启用必要的 API**
   ```bash
   gcloud services enable \
     cloudfunctions.googleapis.com \
     cloudbuild.googleapis.com \
     pubsub.googleapis.com \
     firestore.googleapis.com \
     storage.googleapis.com \
     secretmanager.googleapis.com
   ```

### 部署步骤

#### 方式 1: 使用部署脚本 (推荐)

```bash
# 设置项目 ID
export GCP_PROJECT_ID=your-project-id
export GCP_REGION=us-central1

# 一键部署所有服务
./deployment/deploy.sh
```

#### 方式 2: 使用 Terraform

```bash
cd infra/gcp

# 初始化 Terraform
terraform init

# 预览变更
terraform plan -var="project_id=your-project-id"

# 应用变更
terraform apply -var="project_id=your-project-id"
```

#### 方式 3: 手动部署单个 Function

```bash
# 部署 RAG 查询服务
gcloud functions deploy rag-query \
  --gen2 \
  --runtime python311 \
  --region us-central1 \
  --source services/rag_query \
  --entry-point handle_query \
  --trigger-http \
  --allow-unauthenticated
```

### 配置 Secrets

```bash
# OpenAI API Key
echo -n "sk-your-key" | gcloud secrets create openai-api-key --data-file=-

# Qdrant API Key (如果使用云版本)
echo -n "your-qdrant-key" | gcloud secrets create qdrant-api-key --data-file=-
```

## 开发工作流

### 本地测试 Agent

```python
# test_agent.py
import asyncio
from agents.legal_reasoning_agent import LegalReasoningAgent
from agents.runtime import AgentRuntime

async def test():
    runtime = AgentRuntime()
    agent = LegalReasoningAgent()

    result = await runtime.run(
        agent=agent,
        input_data={
            "query": "What are the payment terms?",
            "user_id": "test_user"
        },
        user_id="test_user"
    )

    print(result)

asyncio.run(test())
```

### 运行测试

```bash
# 单元测试
pytest tests/unit -v

# 集成测试
pytest tests/integration -v

# 带覆盖率
pytest --cov=. --cov-report=html
```

### 代码格式化

```bash
# 格式化代码
black .

# 检查代码质量
ruff check .

# 类型检查
mypy .
```

## 项目结构说明

### 核心模块

- **`agents/`** - Agent 层，实现自主任务执行
- **`tools/`** - Agent 可调用的工具
- **`services/`** - Cloud Functions 处理函数
- **`shared/`** - 共享代码和配置 ⭐ 关键改进

### Agent 架构

每个 Agent 必须实现:
1. `validate_input()` - 输入验证
2. `execute()` - 主要逻辑
3. `before_execute()` / `after_execute()` - 生命周期钩子

```python
@register_agent("my_agent")
class MyAgent(Agent):
    def validate_input(self, input_data):
        return "required_field" in input_data

    async def execute(self, context):
        # 实现逻辑
        return AgentResult(...)
```

### 添加新 Agent

1. 创建目录: `agents/my_agent/`
2. 实现 `agent.py`
3. 定义 `schema.py` (输入/输出模型)
4. 在 `services/` 中使用

## 监控和调试

### 查看日志

```bash
# Cloud Function 日志
gcloud functions logs read rag-query --region=us-central1

# 实时日志
gcloud functions logs tail rag-query --region=us-central1
```

### 查看追踪

```bash
# 访问 Cloud Trace
open https://console.cloud.google.com/traces/list
```

### 性能监控

```bash
# 访问 Cloud Monitoring
open https://console.cloud.google.com/monitoring
```

## 常见问题

### Q: Cloud Function 冷启动慢?
A: 设置 `--min-instances=1` 保持温热

### Q: 如何调试 Agent?
A: 使用 `scripts/dev_server.py` 本地运行，添加断点

### Q: 如何更新依赖?
A: 修改 `requirements.txt` 后重新部署对应的 Cloud Function

### Q: 如何扩展向量数据库?
A: Qdrant 支持集群模式，或切换到 Vertex AI Vector Search

## 下一步

1. ✅ 实现前端 UI (Next.js)
2. ✅ 添加用户认证 (Firebase Auth)
3. ✅ 完善测试覆盖率
4. ✅ 配置 CI/CD (GitHub Actions)
5. ✅ 性能优化 (缓存、批处理)

## 资源链接

- 📚 [架构文档](docs/architecture.md)
- 🤖 [Agent 设计](docs/agents.md)
- 🚀 [部署指南](docs/deployment.md)
- 📖 [API 规范](docs/api_spec.md)

## 需要帮助?

- GitHub Issues: https://github.com/your-repo/issues
- 文档: [docs/](docs/)
- Email: your-email@example.com

---

Happy Coding! 🎉
