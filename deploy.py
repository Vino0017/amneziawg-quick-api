#!/usr/bin/env python3
"""
Batch deployment script for AmneziaWG API instances
"""

import os
import sys
import yaml
import random
import subprocess
import argparse
from pathlib import Path

def generate_keypair():
    """Generate a WireGuard keypair"""
    private_key = subprocess.check_output(['docker', 'run', '--rm', 'alpine', 'sh', '-c',
        'apk add -q wireguard-tools && wg genkey'], text=True).strip()
    public_key = subprocess.check_output(['docker', 'run', '--rm', 'alpine', 'sh', '-c',
        f'apk add -q wireguard-tools && echo "{private_key}" | wg pubkey'], text=True).strip()
    return private_key, public_key

def find_available_port(start_port=50000, end_port=60000, used_ports=None):
    """Find an available port in the given range"""
    if used_ports is None:
        used_ports = set()
    
    for _ in range(1000):  # Try up to 1000 random ports
        port = random.randint(start_port, end_port)
        if port not in used_ports:
            return port
    
    raise RuntimeError("Could not find an available port")

def generate_instance_config(instance_id, config_template, base_port=50000):
    """Generate configuration for a single instance"""
    
    # Generate unique keypair
    private_key, public_key = generate_keypair()
    
    # Allocate unique port
    server_port = base_port + instance_id
    api_port = 8080 + instance_id
    
    # Generate unique network
    network_third_octet = 8 + instance_id
    vpn_network = f"10.{network_third_octet}.0.0/24"
    vpn_network_start = f"10.{network_third_octet}.0.2"
    
    config = {
        'instance_id': instance_id,
        'container_name': f'amneziawg-api-{instance_id}',
        'server_port': server_port,
        'api_port': api_port,
        'server_private_key': private_key,
        'server_public_key': public_key,
        'vpn_network': vpn_network,
        'vpn_network_start': vpn_network_start,
        'server_ip': config_template.get('server_ip', '0.0.0.0'),
        'obfuscation': config_template.get('obfuscation', {})
    }
    
    return config

def create_docker_compose(instance_config, output_dir):
    """Create docker-compose file for an instance"""
    
    obf = instance_config['obfuscation']
    
    compose_content = f"""version: '3.8'

services:
  {instance_config['container_name']}:
    image: amneziawg-api:latest
    container_name: {instance_config['container_name']}
    privileged: true
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    sysctls:
      - net.ipv4.ip_forward=1
      - net.ipv4.conf.all.src_valid_mark=1
    ports:
      - "{instance_config['api_port']}:8080"
      - "{instance_config['server_port']}:{instance_config['server_port']}/udp"
    environment:
      - SERVER_IP={instance_config['server_ip']}
      - SERVER_PORT={instance_config['server_port']}
      - SERVER_PRIVATE_KEY={instance_config['server_private_key']}
      - SERVER_PUBLIC_KEY={instance_config['server_public_key']}
      - VPN_NETWORK={instance_config['vpn_network']}
      - VPN_NETWORK_START={instance_config['vpn_network_start']}
      - JC={obf.get('jc', 6)}
      - JMIN={obf.get('jmin', 50)}
      - JMAX={obf.get('jmax', 1000)}
      - S1={obf.get('s1', 0)}
      - S2={obf.get('s2', 0)}
      - S3={obf.get('s3', 0)}
      - S4={obf.get('s4', 0)}
      - H1={obf.get('h1', '')}
      - H2={obf.get('h2', '')}
      - H3={obf.get('h3', '')}
      - H4={obf.get('h4', '')}
      - I1={obf.get('i1', '')}
      - I2={obf.get('i2', '')}
      - I3={obf.get('i3', '')}
      - I4={obf.get('i4', '')}
      - I5={obf.get('i5', '')}
      - API_HOST=0.0.0.0
      - API_PORT=8080
      - API_KEY={obf.get('api_key', '')}
      - INTERFACE_NAME=awg0
      - DATA_DIR=/etc/amneziawg
    volumes:
      - ./instance-{instance_config['instance_id']}-data:/etc/amneziawg
    restart: unless-stopped
    networks:
      - amneziawg-net-{instance_config['instance_id']}

networks:
  amneziawg-net-{instance_config['instance_id']}:
    driver: bridge
"""
    
    output_file = output_dir / f"docker-compose-instance-{instance_config['instance_id']}.yml"
    with open(output_file, 'w') as f:
        f.write(compose_content)
    
    return output_file

def deploy_instance(compose_file):
    """Deploy a single instance using docker-compose"""
    print(f"Deploying instance with {compose_file}...")
    result = subprocess.run(
        ['docker-compose', '-f', str(compose_file), 'up', '-d'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error deploying instance: {result.stderr}")
        return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Deploy multiple AmneziaWG API instances')
    parser.add_argument('--count', type=int, default=1, help='Number of instances to deploy')
    parser.add_argument('--config', type=str, default='deploy-config.yaml', help='Configuration file')
    parser.add_argument('--output-dir', type=str, default='./deployments', help='Output directory for compose files')
    parser.add_argument('--build', action='store_true', help='Build the Docker image first')
    parser.add_argument('--start-port', type=int, default=50000, help='Starting port for VPN servers')
    
    args = parser.parse_args()
    
    # Load configuration template
    config_file = Path(args.config)
    if config_file.exists():
        with open(config_file, 'r') as f:
            config_template = yaml.safe_load(f)
    else:
        print(f"Warning: Config file {args.config} not found, using defaults")
        config_template = {
            'server_ip': '0.0.0.0',
            'obfuscation': {
                'jc': 6,
                'jmin': 50,
                'jmax': 1000,
                's1': 0,
                's2': 0,
                's3': 0,
                's4': 0
            }
        }
    
    # Build Docker image if requested
    if args.build:
        print("Building Docker image...")
        result = subprocess.run(['docker', 'build', '-t', 'amneziawg-api:latest', '.'])
        if result.returncode != 0:
            print("Error building Docker image")
            sys.exit(1)
        print("Docker image built successfully")
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate and deploy instances
    instances = []
    for i in range(args.count):
        instance_id = i + 1
        print(f"\n===== Configuring Instance {instance_id} =====")
        
        instance_config = generate_instance_config(instance_id, config_template, args.start_port)
        compose_file = create_docker_compose(instance_config, output_dir)
        
        print(f"Instance {instance_id} Configuration:")
        print(f"  Container Name: {instance_config['container_name']}")
        print(f"  VPN Port: {instance_config['server_port']}")
        print(f"  API Port: {instance_config['api_port']}")
        print(f"  Server Public Key: {instance_config['server_public_key']}")
        print(f"  VPN Network: {instance_config['vpn_network']}")
        print(f"  Compose File: {compose_file}")
        
        instances.append(instance_config)
        
        # Deploy instance
        if deploy_instance(compose_file):
            print(f"✓ Instance {instance_id} deployed successfully")
        else:
            print(f"✗ Failed to deploy instance {instance_id}")
    
    # Save deployment summary
    summary_file = output_dir / 'deployment-summary.yaml'
    with open(summary_file, 'w') as f:
        yaml.dump({
            'instances': instances,
            'total_count': len(instances)
        }, f, default_flow_style=False)
    
    print(f"\n===== Deployment Summary =====")
    print(f"Total instances deployed: {len(instances)}")
    print(f"Summary saved to: {summary_file}")
    print("\nTo stop all instances:")
    print(f"  cd {output_dir} && for f in docker-compose-*.yml; do docker-compose -f $f down; done")

if __name__ == '__main__':
    main()
