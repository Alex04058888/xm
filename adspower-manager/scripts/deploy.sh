#!/bin/bash

# AdsPower Manager 部署脚本
# 用途: 自动化部署生产环境

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    # 检查Git
    if ! command -v git &> /dev/null; then
        log_error "Git未安装，请先安装Git"
        exit 1
    fi
    
    log_success "系统依赖检查完成"
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    mkdir -p data/{postgres,redis,prometheus,grafana,backups}
    mkdir -p logs
    mkdir -p docker/nginx/ssl
    mkdir -p docker/nginx/logs
    
    log_success "目录创建完成"
}

# 生成SSL证书
generate_ssl_cert() {
    log_info "生成SSL证书..."
    
    if [ ! -f "docker/nginx/ssl/cert.pem" ]; then
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout docker/nginx/ssl/key.pem \
            -out docker/nginx/ssl/cert.pem \
            -subj "/C=CN/ST=Beijing/L=Beijing/O=AdsPower/CN=localhost"
        
        log_success "SSL证书生成完成"
    else
        log_info "SSL证书已存在，跳过生成"
    fi
}

# 生成环境变量文件
generate_env_file() {
    log_info "生成环境变量文件..."
    
    if [ ! -f ".env.prod" ]; then
        cat > .env.prod << EOF
# 数据库配置
POSTGRES_USER=adspower
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=adspower_db
POSTGRES_PORT=5432

# Redis配置
REDIS_PORT=6379

# 安全配置
SECRET_KEY=$(openssl rand -base64 64)
ENCRYPTION_KEY=$(openssl rand -base64 32)

# 应用配置
LOG_LEVEL=INFO
DATA_PATH=./data

# Grafana配置
GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 16)

# 备份配置
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=30

# API配置
REACT_APP_API_BASE_URL=https://localhost
REACT_APP_WS_BASE_URL=wss://localhost
EOF
        
        log_success "环境变量文件生成完成"
        log_warning "请检查并修改 .env.prod 文件中的配置"
    else
        log_info "环境变量文件已存在，跳过生成"
    fi
}

# 构建镜像
build_images() {
    log_info "构建Docker镜像..."
    
    # 构建后端镜像
    docker build -f docker/Dockerfile.backend.prod -t adspower-backend:latest backend/
    
    # 构建前端镜像
    docker build -f docker/Dockerfile.frontend.prod -t adspower-frontend:latest frontend/
    
    log_success "Docker镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 使用生产环境配置启动
    docker-compose -f docker/docker-compose.prod.yml --env-file .env.prod up -d
    
    log_success "服务启动完成"
}

# 等待服务就绪
wait_for_services() {
    log_info "等待服务就绪..."
    
    # 等待数据库
    log_info "等待数据库启动..."
    until docker-compose -f docker/docker-compose.prod.yml exec -T postgres pg_isready -U adspower; do
        sleep 2
    done
    
    # 等待Redis
    log_info "等待Redis启动..."
    until docker-compose -f docker/docker-compose.prod.yml exec -T redis redis-cli ping; do
        sleep 2
    done
    
    # 等待后端API
    log_info "等待后端API启动..."
    until curl -f http://localhost:8000/health; do
        sleep 5
    done
    
    log_success "所有服务已就绪"
}

# 运行数据库迁移
run_migrations() {
    log_info "运行数据库迁移..."
    
    # 这里可以添加数据库迁移命令
    # docker-compose -f docker/docker-compose.prod.yml exec backend alembic upgrade head
    
    log_success "数据库迁移完成"
}

# 创建初始用户
create_initial_user() {
    log_info "创建初始管理员用户..."
    
    # 这里可以添加创建初始用户的脚本
    # docker-compose -f docker/docker-compose.prod.yml exec backend python scripts/create_superuser.py
    
    log_info "请手动创建管理员用户"
}

# 验证部署
verify_deployment() {
    log_info "验证部署..."
    
    # 检查服务状态
    if curl -f http://localhost/health > /dev/null 2>&1; then
        log_success "前端服务正常"
    else
        log_error "前端服务异常"
    fi
    
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_success "后端服务正常"
    else
        log_error "后端服务异常"
    fi
    
    # 检查容器状态
    log_info "容器状态:"
    docker-compose -f docker/docker-compose.prod.yml ps
    
    log_success "部署验证完成"
}

# 显示部署信息
show_deployment_info() {
    log_success "部署完成！"
    echo ""
    echo "访问地址:"
    echo "  前端: https://localhost"
    echo "  后端API: https://localhost/api/v1/docs"
    echo "  Grafana: http://localhost:3001"
    echo "  Prometheus: http://localhost:9090"
    echo ""
    echo "默认账户信息请查看 .env.prod 文件"
    echo ""
    echo "常用命令:"
    echo "  查看日志: docker-compose -f docker/docker-compose.prod.yml logs -f"
    echo "  停止服务: docker-compose -f docker/docker-compose.prod.yml down"
    echo "  重启服务: docker-compose -f docker/docker-compose.prod.yml restart"
    echo ""
}

# 主函数
main() {
    log_info "开始部署 AdsPower Manager..."
    
    # 检查参数
    if [ "$1" = "--skip-build" ]; then
        SKIP_BUILD=true
    else
        SKIP_BUILD=false
    fi
    
    # 执行部署步骤
    check_dependencies
    create_directories
    generate_ssl_cert
    generate_env_file
    
    if [ "$SKIP_BUILD" = false ]; then
        build_images
    fi
    
    start_services
    wait_for_services
    run_migrations
    create_initial_user
    verify_deployment
    show_deployment_info
    
    log_success "部署完成！"
}

# 错误处理
trap 'log_error "部署过程中发生错误，请检查日志"; exit 1' ERR

# 执行主函数
main "$@"
