# AdsPower Manager Backend

AdsPower环境管理与RPA自动化平台后端服务

## 快速开始

### 1. 环境要求
- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### 2. 安装依赖
```bash
cd backend
pip install -r requirements.txt
```

### 3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库和其他参数
```

### 4. 数据库初始化
```bash
# 创建数据库
createdb adspower_db

# 运行迁移（如果有）
alembic upgrade head
```

### 5. 启动服务
```bash
python main.py
```

服务将在 http://localhost:8000 启动

### 6. API文档
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## 项目结构

```
backend/
├── app/
│   ├── api/           # API路由
│   ├── core/          # 核心配置
│   ├── models/        # 数据模型
│   ├── services/      # 业务服务
│   └── utils/         # 工具函数
├── tests/             # 测试文件
├── alembic/           # 数据库迁移
├── main.py            # 应用入口
└── requirements.txt   # 依赖列表
```

## 开发指南

### 代码格式化
```bash
black app/
isort app/
flake8 app/
```

### 运行测试
```bash
pytest
```

### 类型检查
```bash
mypy app/
```

## API概览

### 认证
- POST `/api/v1/auth/register` - 用户注册
- POST `/api/v1/auth/login` - 用户登录
- POST `/api/v1/auth/refresh` - 刷新令牌
- GET `/api/v1/auth/me` - 获取当前用户信息

### 环境管理
- GET `/api/v1/profiles` - 获取环境列表
- POST `/api/v1/profiles` - 创建环境
- GET `/api/v1/profiles/{id}` - 获取环境详情
- PUT `/api/v1/profiles/{id}` - 更新环境
- DELETE `/api/v1/profiles/{id}` - 删除环境

### RPA流程
- GET `/api/v1/rpa/flows` - 获取流程列表
- POST `/api/v1/rpa/flows` - 创建流程
- GET `/api/v1/rpa/flows/{id}` - 获取流程详情
- PUT `/api/v1/rpa/flows/{id}` - 更新流程
- DELETE `/api/v1/rpa/flows/{id}` - 删除流程

### 任务管理
- GET `/api/v1/tasks` - 获取任务列表
- POST `/api/v1/tasks` - 创建任务
- GET `/api/v1/tasks/{id}` - 获取任务详情
- PUT `/api/v1/tasks/{id}` - 更新任务
- DELETE `/api/v1/tasks/{id}` - 删除任务
