# AmneziaWG Quick API

**AmneziaWG 快速用户管理 API** | AmneziaWG Quick User Management API

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub](https://img.shields.io/github/stars/Vino0017/amneziawg-quick-api?style=social)](https://github.com/Vino0017/amneziawg-quick-api)

一个基于 Docker 的 AmneziaWG VPN 用户管理系统，通过 RESTful API 实现用户的创建、删除和配置管理。

A Docker-based AmneziaWG VPN user management system with RESTful API for user creation, deletion, and configuration management.

---

> ⚠️ **免责声明 / Disclaimer**
>
> 本项目仅供学习和研究目的使用。**严禁**在任何法律禁止使用 VPN 的国家或地区部署和使用本软件。使用者必须遵守当地法律法规，作者不对任何违规使用承担责任。
>
> This project is for educational and research purposes only. It is **strictly prohibited** to deploy or use this software in any country or region where VPN usage is illegal. Users must comply with local laws and regulations. The author assumes no responsibility for any misuse.

---

## ✨ 功能特性 / Features

- 🚀 **RESTful API** - 完整的用户管理 API 接口
- 🐳 **一键部署** - Docker 容器化，开箱即用
- 🛡️ **DPI 混淆** - 支持 AmneziaWG 抗深度包检测
- 🔑 **自动密钥** - 服务器和客户端密钥自动生成
- 🌐 **IP 分配** - 自动管理客户端 IP 地址池
- 📱 **配置导出** - 一键生成客户端配置文件

## 🚀 快速开始 / Quick Start

### 前置要求 / Prerequisites

- Linux 服务器 (Ubuntu/Debian/CentOS)
- Docker & Docker Compose
- 开放 UDP 端口用于 VPN

### 一键部署 / One-Click Deploy

```bash
git clone https://github.com/Vino0017/amneziawg-quick-api.git
cd amneziawg-quick-api
./install.sh --ip <YOUR_SERVER_IP>
```

### 部署参数 / Parameters

| 参数 | 说明 | 必选 | 默认值 |
|------|------|:----:|--------|
| `--ip` | 服务器公网 IP | ✅ | - |
| `--api-key` | API 认证密钥 | ❌ | 随机生成 |
| `--name` | 实例名称 | ❌ | amneziawg |

### 多实例部署 / Multi-Instance

```bash
./install.sh --ip 1.2.3.4 --name node1
./install.sh --ip 5.6.7.8 --name node2
```

部署完成后会输出 API Key 和端口信息。

## 📖 API 文档 / API Reference

### 认证 / Authentication

所有 API 请求需要在 Header 中携带 API Key：

```
X-API-Key: your-api-key
```

### 接口列表 / Endpoints

#### 创建用户 / Create User

```http
POST /api/users
Content-Type: application/json

{
  "user_id": "alice",
  "name": "Alice"
}
```

**响应 / Response:**
```json
{
  "success": true,
  "user": {
    "id": "alice",
    "ip": "10.8.0.2",
    "client_config": "[Interface]\nPrivateKey = ...\n..."
  }
}
```

#### 获取用户 / Get User

```http
GET /api/users/{user_id}
```

#### 列出所有用户 / List Users

```http
GET /api/users
```

#### 删除用户 / Delete User

```http
DELETE /api/users/{user_id}
```

#### 服务器状态 / Server Status

```http
GET /api/server/status
```

#### 健康检查 / Health Check

```http
GET /health
```

### 使用示例 / Usage Examples

```bash
# 创建用户
curl -X POST http://YOUR_IP:8080/api/users \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"user_id": "user001", "name": "User 1"}'

# 获取客户端配置
curl http://YOUR_IP:8080/api/users/user001 \
  -H "X-API-Key: YOUR_API_KEY" | jq -r '.user.client_config' > user001.conf

# 删除用户
curl -X DELETE http://YOUR_IP:8080/api/users/user001 \
  -H "X-API-Key: YOUR_API_KEY"
```

## 📱 客户端 / Clients

生成的配置文件需要使用 AmneziaWG 兼容客户端：

| 平台 | 客户端 |
|------|--------|
| Windows / macOS / Linux | [AmneziaVPN](https://amnezia.org/) |
| iOS / Android | [AmneziaVPN App](https://amnezia.org/) |

## ⚙️ 配置说明 / Configuration

### 混淆参数 / Obfuscation Parameters

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `JC` | 垃圾包数量 | 6 |
| `JMIN` | 垃圾包最小大小 | 37 |
| `JMAX` | 垃圾包最大大小 | 38 |
| `S1` | 握手初始包填充 | 157 |
| `S4` | 传输包填充 | 109 |
| `H1-H4` | 消息头标识 | 自定义 |

## 🔧 常见问题 / Troubleshooting

**Q: 客户端无法连接？**
- 确认 UDP 端口已开放
- 检查客户端配置的混淆参数是否与服务端一致
- 使用 AmneziaVPN 客户端（非标准 WireGuard）

**Q: API 返回 401？**
- 检查请求头中的 `X-API-Key` 是否正确

**Q: Docker 容器启动失败？**
- 确保 Docker 具有特权模式权限
- 运行 `modprobe tun` 加载内核模块

## 📄 许可证 / License

MIT License

本项目使用以下开源组件：
- [AmneziaWG-go](https://github.com/amnezia-vpn/amneziawg-go)
- [AmneziaWG-tools](https://github.com/amnezia-vpn/amneziawg-tools)

---

**⚠️ 再次提醒：本项目仅供学习研究，请遵守当地法律法规。**
