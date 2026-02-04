import os
import json
import subprocess
import ipaddress
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from config import Config

class AmneziaWGManager:
    """Manages AmneziaWG configuration and users"""
    
    def __init__(self):
        self.config = Config()
        self.interface = self.config.INTERFACE_NAME
        self.data_dir = Path(self.config.DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or initialize users database
        self.users_file = Path(self.config.USERS_FILE)
        self.users = self._load_users()
        
        # Initialize IP pool
        self.network = ipaddress.IPv4Network(self.config.VPN_NETWORK)
        self.used_ips = set(user['ip'] for user in self.users.values())
    
    def _load_users(self) -> Dict:
        """Load users from JSON file"""
        if self.users_file.exists():
            with open(self.users_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_users(self):
        """Save users to JSON file"""
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=2)
    
    def _get_next_ip(self) -> str:
        """Get next available IP from the pool"""
        start_ip = ipaddress.IPv4Address(self.config.VPN_NETWORK_START)
        
        for ip in self.network.hosts():
            if ip < start_ip:
                continue
            ip_str = str(ip)
            if ip_str not in self.used_ips:
                return ip_str
        
        raise RuntimeError("No available IPs in the pool")
    
    def _generate_keypair(self) -> Tuple[str, str]:
        """Generate a WireGuard keypair"""
        # Generate private key
        private_key = subprocess.check_output(
            ['awg', 'genkey'],
            text=True
        ).strip()
        
        # Generate public key from private key
        public_key = subprocess.check_output(
            ['awg', 'pubkey'],
            input=private_key,
            text=True
        ).strip()
        
        return private_key, public_key
    
    def _run_awg_command(self, args: List[str]) -> str:
        """Run awg command and return output"""
        try:
            result = subprocess.run(
                ['awg'] + args,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"awg command failed: {e.stderr}")
    
    def create_user(self, user_id: str, name: Optional[str] = None) -> Dict:
        """Create a new user and add to AmneziaWG"""
        if user_id in self.users:
            raise ValueError(f"User {user_id} already exists")
        
        # Generate keypair for the user
        private_key, public_key = self._generate_keypair()
        
        # Allocate IP
        ip_address = self._get_next_ip()
        
        # Create user record
        user = {
            'id': user_id,
            'name': name or user_id,
            'private_key': private_key,
            'public_key': public_key,
            'ip': ip_address,
            'allowed_ips': f"{ip_address}/32"
        }
        
        # Add peer to interface
        self._add_peer(public_key, ip_address)
        
        # Save user
        self.users[user_id] = user
        self.used_ips.add(ip_address)
        self._save_users()
        
        # Generate client configuration
        client_config = self._generate_client_config(user)
        user['client_config'] = client_config
        
        return user
    
    def _add_peer(self, public_key: str, allowed_ip: str):
        """Add a peer to the AmneziaWG interface"""
        self._run_awg_command([
            'set', self.interface,
            'peer', public_key,
            'allowed-ips', f"{allowed_ip}/32"
        ])
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user from AmneziaWG"""
        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found")
        
        user = self.users[user_id]
        
        # Remove peer from interface
        self._remove_peer(user['public_key'])
        
        # Remove from database
        self.used_ips.discard(user['ip'])
        del self.users[user_id]
        self._save_users()
        
        return True
    
    def _remove_peer(self, public_key: str):
        """Remove a peer from the AmneziaWG interface"""
        self._run_awg_command([
            'set', self.interface,
            'peer', public_key,
            'remove'
        ])
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user information"""
        user = self.users.get(user_id)
        if user:
            user = user.copy()
            user['client_config'] = self._generate_client_config(user)
        return user
    
    def list_users(self) -> List[Dict]:
        """List all users"""
        return [
            {
                'id': user_id,
                'name': user['name'],
                'ip': user['ip'],
                'public_key': user['public_key']
            }
            for user_id, user in self.users.items()
        ]
    
    def _generate_client_config(self, user: Dict) -> str:
        """Generate client configuration file content"""
        config = f"""[Interface]
PrivateKey = {user['private_key']}
Address = {user['ip']}/32
DNS = 1.1.1.1

# 混淆参数 (Obfuscation parameters)
# obfJunkMinCnt -> Jc, obfJunkMin -> Jmin, obfJunkVar -> Jmax-Jmin
# obfCtlPadLen -> S1, obfTrPadLen -> S4
Jc = {self.config.JC}
Jmin = {self.config.JMIN}
Jmax = {self.config.JMAX}
S1 = {self.config.S1}
S2 = {self.config.S2}
S3 = {self.config.S3}
S4 = {self.config.S4}"""

        # Add optional headers if configured
        if self.config.H1:
            config += f"\nH1 = {self.config.H1}"
        if self.config.H2:
            config += f"\nH2 = {self.config.H2}"
        if self.config.H3:
            config += f"\nH3 = {self.config.H3}"
        if self.config.H4:
            config += f"\nH4 = {self.config.H4}"
        
        # Add custom signature packets if configured
        if self.config.I1:
            config += f"\nI1 = {self.config.I1}"
        if self.config.I2:
            config += f"\nI2 = {self.config.I2}"
        if self.config.I3:
            config += f"\nI3 = {self.config.I3}"
        if self.config.I4:
            config += f"\nI4 = {self.config.I4}"
        if self.config.I5:
            config += f"\nI5 = {self.config.I5}"

        config += f"""

[Peer]
PublicKey = {self.config.SERVER_PUBLIC_KEY}
Endpoint = {self.config.SERVER_IP}:{self.config.SERVER_PORT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
        return config
    
    def get_server_status(self) -> Dict:
        """Get server status information"""
        try:
            output = self._run_awg_command(['show', self.interface])
            return {
                'interface': self.interface,
                'status': 'running',
                'total_users': len(self.users),
                'available_ips': len(list(self.network.hosts())) - len(self.used_ips),
                'details': output
            }
        except Exception as e:
            return {
                'interface': self.interface,
                'status': 'error',
                'error': str(e)
            }
