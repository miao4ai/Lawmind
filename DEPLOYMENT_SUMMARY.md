# 🚀 Mamimind 完整部署指南

## 项目概览

完整的 Agentic AI 法律文档智能系统，包含：
- ✅ **后端**: Python + Cloud Functions/Cloud Run
- ✅ **前端**: Next.js + TypeScript + Cloud Run
- ✅ **Agent 框架**: 自主、可组合、可追踪
- ✅ **基础设施**: Terraform + GCP

---

## 📦 已创建的完整结构

```
Mamimind/
├── 📚 文档
│   ├── README.md                      # 项目总览
│   ├── PROJECT_STRUCTURE.md           # 项目结构详解
│   ├── GETTING_STARTED.md             # 后端快速开始
│   ├── FRONTEND_GUIDE.md              # 前端部署指南 ⭐
│   └── DEPLOYMENT_SUMMARY.md          # 本文件
│
├── 🎨 前端 (Next.js) - 26个文件
│   ├── pages/                         # 页面路由
│   │   ├── index.tsx                  # 首页
│   │   ├── upload.tsx                 # 📄 上传页面
│   │   └── search.tsx                 # 🔍 搜索页面
│   │
│   ├── components/                    # UI 组件
│   │   ├── Layout.tsx                 # 布局 + 导航
│   │   ├── UploadBox.tsx              # 拖拽上传
│   │   ├── SearchBox.tsx              # 搜索框
│   │   ├── AnswerPanel.tsx            # 答案展示
│   │   └── CitationList.tsx           # 引用列表
│   │
│   ├── lib/                           # 工具库
│   │   ├── api.ts                     # API 客户端 ⭐
│   │   └── store.ts                   # 状态管理
│   │
│   ├── Dockerfile                     # Cloud Run 部署
│   ├── deploy-cloudrun.sh             # 一键部署 ⭐
│   └── package.json                   # 依赖配置
│
├── 🤖 后端 Agent 系统
│   ├── agents/                        # Agent 层
│   ├── tools/                         # 工具层
│   ├── services/                      # Cloud Functions
│   └── shared/                        # 共享代码 ⭐
│
├── 🏗️  基础设施
│   ├── infra/gcp/main.tf              # Terraform 配置
│   └── deployment/deploy.sh           # 部署脚本
│
└── 🧪 其他模块
    ├── vector_db/                     # 向量数据库抽象
    ├── metadata_db/                   # 元数据库
    └── observability/                 # 可观测性
```

---

## 🚀 完整部署流程

### Step 1: 部署基础设施

```bash
cd infra/gcp
terraform init
terraform apply -var="project_id=YOUR_PROJECT_ID"
```

### Step 2: 部署后端

```bash
export GCP_PROJECT_ID=your-project-id
./deployment/deploy.sh
```

### Step 3: 部署前端

```bash
cd frontend
export API_BASE_URL=https://your-api-url.run.app
./deploy-cloudrun.sh
```

### Step 4: 验证

```bash
# 获取前端 URL
gcloud run services describe mamimind-frontend \
  --region us-central1 --format 'value(status.url)'
```

---

## 📊 核心功能

| 功能 | 页面 | 说明 |
|------|------|------|
| 文档上传 | `/upload` | 拖拽上传 PDF，自动 OCR |
| 法律搜索 | `/search` | AI 问答 + 精确引用 |
| 首页 | `/` | 产品介绍 |

---

## 💡 快速命令

```bash
# 本地开发 - 前端
cd frontend && npm install && npm run dev

# 本地开发 - 后端
python scripts/dev_server.py

# 部署后端
./deployment/deploy.sh

# 部署前端
cd frontend && ./deploy-cloudrun.sh

# 查看日志
gcloud run services logs read mamimind-frontend --region us-central1
```

---

完整指南请查看:
- [FRONTEND_GUIDE.md](FRONTEND_GUIDE.md) - 前端详细指南
- [GETTING_STARTED.md](GETTING_STARTED.md) - 后端快速开始
- [docs/architecture.md](docs/architecture.md) - 架构设计
