# Frontend 部署指南

## 📦 已创建的文件

完整的 Next.js + TypeScript 前端应用，可部署到 GCP Cloud Run。

### 核心文件

```
frontend/
├── package.json                    # 依赖和脚本
├── tsconfig.json                   # TypeScript 配置
├── next.config.js                  # Next.js 配置
├── tailwind.config.ts              # Tailwind CSS 配置
├── Dockerfile                      # Cloud Run 部署
├── deploy-cloudrun.sh              # 一键部署脚本 ⭐
│
├── pages/                          # 页面
│   ├── _app.tsx                    # App 入口
│   ├── _document.tsx               # HTML 文档
│   ├── index.tsx                   # 首页 (Landing)
│   ├── upload.tsx                  # 📄 上传页面
│   └── search.tsx                  # 🔍 搜索页面
│
├── components/                     # 组件
│   ├── Layout.tsx                  # 布局 + 导航
│   ├── UploadBox.tsx               # 拖拽上传组件
│   ├── SearchBox.tsx               # 搜索框
│   ├── AnswerPanel.tsx             # 答案展示
│   └── CitationList.tsx            # 引用列表
│
├── lib/                            # 工具库
│   ├── api.ts                      # API 客户端 ⭐
│   └── store.ts                    # 状态管理 (Zustand)
│
└── styles/
    └── globals.css                 # 全局样式
```

## 🎯 核心功能

### 1. 文档上传 (`/upload`)

- ✅ 拖拽上传 PDF
- ✅ 文件验证（类型、大小）
- ✅ 实时上传进度
- ✅ 自动触发 OCR
- ✅ 文档状态跟踪

**实现细节**:
- 使用 `react-dropzone` 处理拖拽
- 通过 Cloud Storage signed URL 上传
- WebSocket 或轮询获取处理状态

### 2. 文档搜索 (`/search`)

- ✅ 自然语言查询
- ✅ 示例问题推荐
- ✅ 文档过滤选择
- ✅ AI 生成答案
- ✅ 精确引用展示
- ✅ 置信度评分

**实现细节**:
- RAG (Retrieval-Augmented Generation)
- 向量搜索 + LLM 推理
- Citation 追溯到原文档和页码

## 🚀 本地开发

### 快速启动

```bash
cd frontend

# 1. 安装依赖
npm install

# 2. 配置环境变量
cp .env.example .env.local

# 编辑 .env.local:
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# 3. 启动开发服务器
npm run dev

# 访问 http://localhost:3000
```

### 开发脚本

```bash
npm run dev          # 开发服务器 (热重载)
npm run build        # 构建生产版本
npm run start        # 启动生产服务器
npm run lint         # 代码检查
npm run type-check   # TypeScript 类型检查
```

## ☁️  部署到 GCP Cloud Run

### 方式 1: 一键部署脚本 (推荐) ⭐

```bash
cd frontend

# 设置环境变量
export GCP_PROJECT_ID=your-project-id
export GCP_REGION=us-central1
export API_BASE_URL=https://your-api-gateway.run.app

# 部署
./deploy-cloudrun.sh
```

脚本会自动：
1. ✅ 启用所需的 GCP API
2. ✅ 构建 Docker 镜像
3. ✅ 推送到 Container Registry
4. ✅ 部署到 Cloud Run
5. ✅ 配置环境变量

### 方式 2: 手动部署

```bash
# 1. 构建 Docker 镜像
cd frontend
gcloud builds submit --tag gcr.io/PROJECT_ID/mamimind-frontend

# 2. 部署到 Cloud Run
gcloud run deploy mamimind-frontend \
  --image gcr.io/PROJECT_ID/mamimind-frontend \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --set-env-vars "NEXT_PUBLIC_API_BASE_URL=https://your-api.run.app"

# 3. 获取 URL
gcloud run services describe mamimind-frontend \
  --region us-central1 \
  --format 'value(status.url)'
```

### 方式 3: 使用 Cloud Build (CI/CD)

创建 `frontend/cloudbuild.yaml`:

```yaml
steps:
  # Build
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/mamimind-frontend', '.']

  # Push
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/mamimind-frontend']

  # Deploy
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'mamimind-frontend'
      - '--image=gcr.io/$PROJECT_ID/mamimind-frontend'
      - '--region=us-central1'
      - '--platform=managed'
      - '--allow-unauthenticated'

images:
  - 'gcr.io/$PROJECT_ID/mamimind-frontend'
```

部署：

```bash
gcloud builds submit --config cloudbuild.yaml
```

## 🔗 API 集成

前端通过 `lib/api.ts` 调用后端 API：

### API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/upload` | POST | 获取上传 URL |
| `/query` | POST | RAG 查询 |
| `/status/{doc_id}` | GET | 文档状态 |
| `/documents` | GET | 用户文档列表 |

### API 客户端使用

```typescript
import { api } from '@/lib/api';

// 上传文档
const uploadData = await api.getUploadUrl(
  userId,
  filename,
  fileSize
);

await api.uploadFile(uploadData.upload_url, file);

// 查询
const result = await api.query(
  userId,
  "What are the termination conditions?",
  undefined, // docIds (可选)
  5  // top_k
);
```

## 🎨 UI 组件说明

### UploadBox.tsx

拖拽上传组件，支持：
- 文件验证
- 上传进度条
- 状态显示（idle, uploading, success, error）
- 自动重试

### SearchBox.tsx

搜索输入组件，提供：
- 实时搜索
- 示例问题
- 加载状态
- 键盘快捷键

### AnswerPanel.tsx

答案展示组件，包含：
- Markdown 渲染
- 置信度指示器
- 推理过程展开
- 引用列表

### CitationList.tsx

引用列表组件，显示：
- 文档来源
- 页码定位
- 相关度评分
- 原文引用

## 🎭 状态管理

使用 Zustand 进行全局状态管理：

```typescript
import { useStore } from '@/lib/store';

function MyComponent() {
  const {
    userId,           // 当前用户
    documents,        // 文档列表
    selectedDocIds,   // 选中的文档
    toggleDocument    // 切换文档选择
  } = useStore();

  // ...
}
```

## 🔧 配置说明

### next.config.js

```javascript
module.exports = {
  output: 'standalone',  // Docker 优化
  images: {
    unoptimized: true,   // Cloud Run 兼容
  },
}
```

### Dockerfile

多阶段构建：
1. **deps**: 安装依赖
2. **builder**: 构建应用
3. **runner**: 运行时镜像（最小化）

最终镜像大小: ~150MB

## 📊 性能优化

### 已实现

- ✅ Standalone 输出（最小镜像）
- ✅ 代码分割（自动）
- ✅ 图片优化禁用（Cloud Run）
- ✅ 浏览器缓存
- ✅ Gzip 压缩

### 可选优化

```bash
# 1. 使用 Cloud CDN
gcloud compute backend-services update BACKEND_SERVICE \
  --enable-cdn

# 2. 设置最小实例（减少冷启动）
gcloud run services update mamimind-frontend \
  --min-instances 1 \
  --region us-central1

# 3. 增加内存（更快响应）
gcloud run services update mamimind-frontend \
  --memory 1Gi \
  --region us-central1
```

## 🔒 安全性

### 已实现

- ✅ HTTPS 强制
- ✅ CORS 配置
- ✅ 输入验证
- ✅ XSS 防护
- ✅ 环境变量隔离

### 生产配置

```bash
# 1. 启用 Cloud Armor (DDoS 防护)
gcloud compute security-policies create mamimind-policy

# 2. 配置 IAM
gcloud run services add-iam-policy-binding mamimind-frontend \
  --member="allUsers" \
  --role="roles/run.invoker"

# 3. 设置速率限制
# 通过 Cloud Endpoints 或 API Gateway
```

## 🐛 调试

### 查看日志

```bash
# Cloud Run 日志
gcloud run services logs read mamimind-frontend \
  --region us-central1 \
  --limit 50

# 实时日志
gcloud run services logs tail mamimind-frontend \
  --region us-central1
```

### 本地调试

```bash
# 查看网络请求
npm run dev -- --inspect

# 使用 Docker 本地测试
docker build -t mamimind-frontend .
docker run -p 8080:8080 \
  -e NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 \
  mamimind-frontend
```

## 📈 监控

### Cloud Monitoring

```bash
# 创建监控仪表板
gcloud monitoring dashboards create --config-from-file=dashboard.json
```

监控指标：
- Request count
- Latency (p50, p95, p99)
- Error rate
- Container CPU/Memory

### 告警设置

```bash
# 错误率告警
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High Error Rate" \
  --condition-threshold-value=5 \
  --condition-threshold-duration=300s
```

## 🚦 生产检查清单

部署前确认：

- [ ] 环境变量已配置
- [ ] API URL 正确
- [ ] CORS 已设置
- [ ] SSL 证书有效
- [ ] 自定义域名配置（可选）
- [ ] 监控和告警已启用
- [ ] 备份策略已设定
- [ ] 负载测试已完成

## 💡 最佳实践

1. **环境变量**: 生产和开发分离
2. **错误处理**: 友好的用户提示
3. **加载状态**: 所有异步操作都有加载指示
4. **可访问性**: 遵循 WCAG 指南
5. **SEO**: 使用 Next.js 的 SEO 优化功能
6. **分析**: 集成 Google Analytics（可选）

## 🔄 持续集成

### GitHub Actions 示例

创建 `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Cloud SDK
        uses: google-github-actions/setup-gcloud@v1
        with:
          project_id: ${{ secrets.GCP_PROJECT_ID }}
          service_account_key: ${{ secrets.GCP_SA_KEY }}

      - name: Deploy to Cloud Run
        run: |
          cd frontend
          ./deploy-cloudrun.sh
```

## 📚 相关文档

- [Next.js Documentation](https://nextjs.org/docs)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Zustand](https://github.com/pmndrs/zustand)

---

## 快速命令参考

```bash
# 本地开发
cd frontend && npm install && npm run dev

# 构建
npm run build && npm start

# 部署
export GCP_PROJECT_ID=your-id && ./deploy-cloudrun.sh

# 查看日志
gcloud run services logs read mamimind-frontend --region us-central1

# 更新服务
gcloud run services update mamimind-frontend \
  --set-env-vars KEY=VALUE \
  --region us-central1
```

需要帮助？查看 [frontend/README.md](frontend/README.md) 或提交 Issue。
