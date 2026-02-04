#!/bin/bash
# AmneziaWG API 一键部署脚本
# 用法: ./install.sh --ip <SERVER_IP> [--api-key <KEY>] [--name <NAME>]

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 显示帮助
show_help() {
    echo "用法: $0 --ip <SERVER_IP> [选项]"
    echo ""
    echo "必选参数:"
    echo "  --ip <IP>        服务器公网 IP 地址"
    echo ""
    echo "可选参数:"
    echo "  --api-key <KEY>  API 认证密钥 (默认: 随机生成)"
    echo "  --name <NAME>    实例名称 (默认: amneziawg)"
    echo "  --help           显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 --ip 1.2.3.4"
    echo "  $0 --ip 1.2.3.4 --api-key mysecretkey --name vpn-node1"
    echo ""
    echo "多实例部署:"
    echo "  $0 --ip 1.2.3.4 --name node1"
    echo "  $0 --ip 5.6.7.8 --name node2"
    exit 0
}

# 生成随机 API Key
generate_api_key() {
    openssl rand -hex 32 2>/dev/null || \
    cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1
}

# 查找可用端口
find_available_port() {
    local start_port=$1
    local port=$start_port
    while true; do
        if ! ss -tuln | grep -q ":$port "; then
            echo $port
            return
        fi
        port=$((port + 1))
        if [ $port -gt 65000 ]; then
            port=10000
        fi
        if [ $port -eq $start_port ]; then
            log_error "无法找到可用端口"
            exit 1
        fi
    done
}

# 解析参数
SERVER_IP=""
API_KEY=""
INSTANCE_NAME="amneziawg"

while [[ $# -gt 0 ]]; do
    case $1 in
        --ip)
            SERVER_IP="$2"
            shift 2
            ;;
        --api-key)
            API_KEY="$2"
            shift 2
            ;;
        --name)
            INSTANCE_NAME="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            ;;
        *)
            log_error "未知参数: $1"
            show_help
            ;;
    esac
done

# 验证必选参数
if [ -z "$SERVER_IP" ]; then
    log_error "必须指定 --ip 参数"
    echo ""
    show_help
fi

# 生成默认值
[ -z "$API_KEY" ] && API_KEY=$(generate_api_key)

log_info "=========================================="
log_info "   AmneziaWG API 部署 - ${INSTANCE_NAME}"
log_info "=========================================="
log_info "服务器 IP: $SERVER_IP"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装，请先安装: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# 查找可用端口
log_info "正在查找可用端口..."
VPN_PORT=$(find_available_port 51820)
API_PORT=$(find_available_port 8080)
log_info "VPN 端口: $VPN_PORT"
log_info "API 端口: $API_PORT"

# 创建项目目录
PROJECT_DIR="/opt/${INSTANCE_NAME}"
log_info "项目目录: $PROJECT_DIR"
mkdir -p "$PROJECT_DIR"

# 复制项目文件
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/docker-compose.yml" ]; then
    cp -r "$SCRIPT_DIR"/{Dockerfile,docker-compose.yml,*.py,*.sh,requirements.txt,.env.example} "$PROJECT_DIR/" 2>/dev/null || true
fi
cd "$PROJECT_DIR"

# 创建 .env 配置
log_info "生成配置文件..."
cat > .env << EOF
# AmneziaWG API 配置 - ${INSTANCE_NAME}
# 生成时间: $(date)

# 服务器配置
SERVER_PUBLIC_KEY=
SERVER_PRIVATE_KEY=
SERVER_IP=${SERVER_IP}
SERVER_PORT=${VPN_PORT}

# 网络配置 (每个实例使用不同的网段)
VPN_NETWORK=10.$((RANDOM % 200 + 10)).0.0/24
VPN_NETWORK_START=10.$((RANDOM % 200 + 10)).0.2

# 混淆参数
JC=6
JMIN=37
JMAX=38
S1=157
S2=0
S3=0
S4=109
H1=1020304050
H2=1020304051
H3=1020304052
H4=1020304053

# API 配置
API_HOST=0.0.0.0
API_PORT=${API_PORT}
API_KEY=${API_KEY}

# 接口名称
INTERFACE_NAME=awg0
EOF

# 更新 docker-compose.yml 端口和容器名
if [ -f "docker-compose.yml" ]; then
    sed -i "s/amneziawg-api/${INSTANCE_NAME}/g" docker-compose.yml
    sed -i "s/51820:51820/${VPN_PORT}:${VPN_PORT}/g" docker-compose.yml
    sed -i "s/8080:8080/${API_PORT}:${API_PORT}/g" docker-compose.yml
fi

# 构建并启动
log_info "构建 Docker 镜像..."
docker compose build --quiet 2>/dev/null || docker-compose build --quiet

log_info "启动服务..."
docker compose up -d 2>/dev/null || docker-compose up -d

# 等待启动
sleep 5

# 获取服务器公钥
SERVER_PUBLIC_KEY=$(docker compose logs 2>&1 | grep "Server Public Key:" | tail -1 | awk '{print $NF}')

# 验证服务
if curl -s http://localhost:${API_PORT}/health 2>/dev/null | grep -q "ok"; then
    echo ""
    echo -e "${GREEN}=========================================="
    echo -e "   ✅ 部署成功！"
    echo -e "==========================================${NC}"
    echo ""
    echo -e "${CYAN}实例名称:${NC} ${INSTANCE_NAME}"
    echo -e "${CYAN}项目目录:${NC} ${PROJECT_DIR}"
    echo ""
    echo -e "${CYAN}服务器信息:${NC}"
    echo "  公网 IP:    ${SERVER_IP}"
    echo "  VPN 端口:   ${VPN_PORT}/udp"
    echo "  API 端口:   ${API_PORT}/tcp"
    echo "  公钥:       ${SERVER_PUBLIC_KEY}"
    echo ""
    echo -e "${CYAN}API 认证:${NC}"
    echo "  API Key:    ${API_KEY}"
    echo ""
    echo -e "${CYAN}使用示例:${NC}"
    echo "  # 创建用户"
    echo "  curl -X POST http://${SERVER_IP}:${API_PORT}/api/users \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -H 'X-API-Key: ${API_KEY}' \\"
    echo "    -d '{\"user_id\": \"user001\", \"name\": \"用户1\"}'"
    echo ""
    
    # 保存部署信息
    cat > "${PROJECT_DIR}/deploy-info.txt" << EOF
# AmneziaWG API 部署信息
# 实例: ${INSTANCE_NAME}
# 时间: $(date)

SERVER_IP=${SERVER_IP}
VPN_PORT=${VPN_PORT}
API_PORT=${API_PORT}
API_KEY=${API_KEY}
SERVER_PUBLIC_KEY=${SERVER_PUBLIC_KEY}
PROJECT_DIR=${PROJECT_DIR}
EOF
    log_info "部署信息已保存到: ${PROJECT_DIR}/deploy-info.txt"
else
    log_error "服务启动失败，请检查日志: docker compose logs"
    exit 1
fi
