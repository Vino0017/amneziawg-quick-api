#!/usr/bin/env python3
"""
为多台服务器生成独立的配置文件
每套配置包含唯一的密钥对、端口和网络配置
运维人员可以将生成的配置分发到各个服务器上
"""

import os
import sys
import yaml
import random
import subprocess
import argparse
import base64
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives import serialization

def generate_keypair():
    """生成 WireGuard 密钥对（纯 Python 实现，不依赖 wg 命令）"""
    private_key = X25519PrivateKey.generate()
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    
    private_key_b64 = base64.b64encode(private_key_bytes).decode('ascii')
    public_key_b64 = base64.b64encode(public_key_bytes).decode('ascii')
    
    return private_key_b64, public_key_b64

def generate_random_port(start=50000, end=60000, exclude=None):
    """生成随机端口"""
    if exclude is None:
        exclude = set()
    
    for _ in range(1000):
        port = random.randint(start, end)
        if port not in exclude:
            return port
    
    raise RuntimeError("无法找到可用端口")

def generate_api_key(length=32):
    """生成随机 API Key"""
    import secrets
    return secrets.token_urlsafe(length)

def generate_server_config(server_id, config_template, used_ports=None):
    """为单个服务器生成配置"""
    if used_ports is None:
        used_ports = set()
    
    # 生成唯一密钥对
    private_key, public_key = generate_keypair()
    
    # 分配端口
    port_range = config_template.get('port_range', {'start': 50000, 'end': 60000})
    server_port = generate_random_port(port_range['start'], port_range['end'], used_ports)
    used_ports.add(server_port)
    
    # 生成网络配置（每个服务器使用不同的子网）
    network_octet = (server_id % 250) + 1  # 1-250
    vpn_network = f"10.{network_octet}.0.0/24"
    vpn_network_start = f"10.{network_octet}.0.2"
    
    # 生成 API Key
    api_key = generate_api_key()
    
    # 混淆参数（从模板读取）
    obf = config_template.get('obfuscation', {})
    
    return {
        'server_id': server_id,
        'server_port': server_port,
        'server_private_key': private_key,
        'server_public_key': public_key,
        'vpn_network': vpn_network,
        'vpn_network_start': vpn_network_start,
        'api_key': api_key,
        'obfuscation': obf
    }

def create_env_file(config, output_path):
    """生成 .env 配置文件"""
    obf = config['obfuscation']
    
    env_content = f"""# 服务器配置 - 服务器 {config['server_id']}
# 请将 SERVER_IP 修改为该服务器的公网 IP

SERVER_IP=0.0.0.0
SERVER_PORT={config['server_port']}
SERVER_PRIVATE_KEY={config['server_private_key']}
SERVER_PUBLIC_KEY={config['server_public_key']}

# 网络配置
VPN_NETWORK={config['vpn_network']}
VPN_NETWORK_START={config['vpn_network_start']}

# 混淆参数
JC={obf.get('jc', 6)}
JMIN={obf.get('jmin', 50)}
JMAX={obf.get('jmax', 1000)}
S1={obf.get('s1', 0)}
S2={obf.get('s2', 0)}
S3={obf.get('s3', 0)}
S4={obf.get('s4', 0)}
H1={obf.get('h1', '')}
H2={obf.get('h2', '')}
H3={obf.get('h3', '')}
H4={obf.get('h4', '')}
I1={obf.get('i1', '')}
I2={obf.get('i2', '')}
I3={obf.get('i3', '')}
I4={obf.get('i4', '')}
I5={obf.get('i5', '')}

# API 配置
API_HOST=0.0.0.0
API_PORT=8080
API_KEY={config['api_key']}

# 接口名称
INTERFACE_NAME=awg0
DATA_DIR=/etc/amneziawg
"""
    
    with open(output_path, 'w') as f:
        f.write(env_content)

def create_info_file(config, output_path):
    """生成服务器信息文件（运维参考）"""
    info_content = f"""# 服务器 {config['server_id']} 部署信息

## 基本信息
- 服务器 ID: {config['server_id']}
- VPN 端口: {config['server_port']} (UDP)
- API 端口: 8080 (TCP)
- API Key: {config['api_key']}

## 密钥信息
- 服务器公钥: {config['server_public_key']}
- 服务器私钥: {config['server_private_key']}

## 网络配置
- VPN 网段: {config['vpn_network']}
- 客户端起始 IP: {config['vpn_network_start']}

## 部署步骤
1. 将此目录下的所有文件复制到服务器的 /root/amneziawg-api/
2. 编辑 .env 文件，将 SERVER_IP 修改为该服务器的公网 IP
3. 运行: docker-compose up -d --build
4. 验证: curl http://localhost:8080/health

## 防火墙配置
- 开放 UDP 端口: {config['server_port']}
- 开放 TCP 端口: 8080（API，可选择只内网访问）
"""
    
    with open(output_path, 'w') as f:
        f.write(info_content)

def main():
    parser = argparse.ArgumentParser(description='为多台服务器生成独立配置')
    parser.add_argument('--count', type=int, default=1, help='服务器数量')
    parser.add_argument('--config', type=str, default='deploy-config.yaml', help='配置模板文件')
    parser.add_argument('--output', type=str, default='./server-configs', help='输出目录')
    parser.add_argument('--start-id', type=int, default=1, help='服务器起始编号')
    
    args = parser.parse_args()
    
    # 加载配置模板
    config_file = Path(args.config)
    if config_file.exists():
        with open(config_file, 'r') as f:
            config_template = yaml.safe_load(f)
    else:
        print(f"警告: 配置文件 {args.config} 不存在，使用默认配置")
        config_template = {
            'obfuscation': {
                'jc': 6,
                'jmin': 50,
                'jmax': 1000,
                's1': 0,
                's2': 0,
                's3': 0,
                's4': 0
            },
            'port_range': {
                'start': 50000,
                'end': 60000
            }
        }
    
    # 创建输出目录
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成配置
    used_ports = set()
    all_configs = []
    
    for i in range(args.count):
        server_id = args.start_id + i
        print(f"\n===== 生成服务器 {server_id} 配置 =====")
        
        config = generate_server_config(server_id, config_template, used_ports)
        all_configs.append(config)
        
        # 创建服务器专用目录
        server_dir = output_dir / f"server-{server_id}"
        server_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成配置文件
        create_env_file(config, server_dir / '.env')
        create_info_file(config, server_dir / 'README.md')
        
        # 复制项目文件的符号链接说明
        with open(server_dir / '部署说明.txt', 'w') as f:
            f.write(f"""部署说明 - 服务器 {server_id}

1. 将 amneziawg-api 项目文件复制到服务器
2. 将此目录下的 .env 文件复制到项目根目录
3. 修改 .env 中的 SERVER_IP 为实际公网 IP
4. 运行 docker-compose up -d --build

VPN 端口: {config['server_port']} (UDP)
API 地址: http://服务器IP:8080
API Key: {config['api_key']}
服务器公钥: {config['server_public_key']}
""")
        
        print(f"  VPN 端口: {config['server_port']}")
        print(f"  API Key: {config['api_key']}")
        print(f"  服务器公钥: {config['server_public_key']}")
        print(f"  配置目录: {server_dir}")
    
    # 生成汇总文件
    summary = {
        'total_servers': len(all_configs),
        'servers': [
            {
                'id': c['server_id'],
                'port': c['server_port'],
                'public_key': c['server_public_key'],
                'api_key': c['api_key'],
                'network': c['vpn_network']
            }
            for c in all_configs
        ]
    }
    
    summary_file = output_dir / 'servers-summary.yaml'
    with open(summary_file, 'w') as f:
        yaml.dump(summary, f, default_flow_style=False, allow_unicode=True)
    
    print(f"\n===== 配置生成完成 =====")
    print(f"共生成 {len(all_configs)} 个服务器配置")
    print(f"配置目录: {output_dir}")
    print(f"汇总文件: {summary_file}")
    print(f"\n请将各服务器目录分发给运维人员部署")

if __name__ == '__main__':
    main()
