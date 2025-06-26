# AdsPower Manager

🚀 AdsPower环境管理与RPA自动化平台

## 项目概述

AdsPower Manager是一个基于AdsPower指纹浏览器的环境管理和RPA自动化平台，提供：

- **环境管理**: 18项核心功能，包括创建、复制、批量导入浏览器环境等
- **RPA自动化**: 53个动作节点，支持网页操作、数据处理、第三方服务调用
- **任务调度**: 支持批量执行、并发控制、实时监控

## 技术栈

- **前端**: React + TypeScript + Vite
- **后端**: Python FastAPI + SQLAlchemy  
- **数据库**: PostgreSQL + Redis
- **部署**: Docker + Kubernetes

## 快速开始

### 1. 环境要求

- Docker & Docker Compose
- Node.js 18+ (开发环境)
- Python 3.11+ (开发环境)
- AdsPower客户端

### 2. 使用Docker启动（推荐）

```bash
# 克隆项目
git clone https://github.com/Alex04058888/xm
cd xm/adspower-manager

# 启动所有服务
cd docker
docker-compose up -d

# 查看服务状态
docker-compose ps
```

服务地址：
- 前端: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/api/v1/docs
- 数据库: localhost:5432
- Redis: localhost:6379

### 3. 开发环境启动

#### 后端开发
```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 启动服务
python main.py
```

#### 前端开发
```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm start
```

## 项目结构

```
adspower-manager/
├── frontend/                 # React前端
│   ├── src/
│   │   ├── components/      # 可复用组件
│   │   ├── pages/          # 页面组件
│   │   ├── services/       # API调用
│   │   ├── store/          # 状态管理
│   │   └── utils/          # 工具函数
│   ├── package.json
│   └── vite.config.ts
├── backend/                  # Python后端
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   └── utils/          # 工具函数
│   ├── tests/              # 测试文件
│   ├── requirements.txt
│   └── main.py
├── docker/                   # Docker配置
├── docs/                     # 文档
└── scripts/                  # 部署脚本
```

## 核心功能

### 环境管理（18项功能）

| 功能 | 描述 | API端点 |
|------|------|---------|
| 新建环境 | 创建新的浏览器环境 | POST /api/v1/profiles |
| 批量创建 | 批量创建多个环境 | POST /api/v1/profiles/batch |
| 启动浏览器 | 启动指定环境的浏览器 | POST /api/v1/profiles/{id}/start |
| 关闭浏览器 | 关闭指定环境的浏览器 | POST /api/v1/profiles/{id}/stop |
| 编辑指纹 | 修改环境指纹配置 | PUT /api/v1/profiles/{id}/fingerprint |
| 检测代理 | 检测代理连接状态 | GET /api/v1/profiles/{id}/proxy/check |
| ... | ... | ... |

### RPA自动化（53个节点）

#### 页面操作 (16个)
- newPage, gotoUrl, click, input, hover, screenshot, scrollPage...

#### 数据处理 (4个)  
- extractTxt, convertToJson, extractField, randomExtraction

#### 流程控制 (11个)
- ifCondition, whileLoop, exitLoop, breakpoint...

#### 第三方工具 (6个)
- openai, captcha2, googleSheets, slackWebhook...

## API文档

完整的API文档可在以下地址查看：
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## 开发指南

### 代码规范
```bash
# 后端代码格式化
cd backend
black app/
isort app/
flake8 app/

# 前端代码格式化
cd frontend
npm run lint
npm run format
```

### 运行测试
```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm test
```

### 数据库迁移
```bash
cd backend
alembic revision --autogenerate -m "描述"
alembic upgrade head
```

## 部署

### 生产环境部署
```bash
# 使用生产配置启动
docker-compose --profile production up -d

# 启用监控
docker-compose --profile monitoring up -d
```

### Kubernetes部署
```bash
# 应用Kubernetes配置
kubectl apply -f k8s/
```

## 监控

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin123)

## 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 支持

- 📧 邮箱: alex04058888@icloud.com
- 🐛 问题反馈: [GitHub Issues](https://github.com/Alex04058888/xm/issues)
- 📖 文档: [项目文档](https://github.com/Alex04058888/xm/docs)

## 更新日志

### v1.0.0 (2025-06-26)
- ✨ 初始版本发布
- 🚀 基础架构搭建完成
- 📝 完整的项目文档
- 🐳 Docker容器化支持
