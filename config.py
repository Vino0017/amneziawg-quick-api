import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    
    # Server Configuration
    SERVER_PUBLIC_KEY = os.getenv('SERVER_PUBLIC_KEY', '')
    SERVER_PRIVATE_KEY = os.getenv('SERVER_PRIVATE_KEY', '')
    SERVER_IP = os.getenv('SERVER_IP', '0.0.0.0')
    SERVER_PORT = int(os.getenv('SERVER_PORT', '51820'))
    
    # Network Configuration
    VPN_NETWORK = os.getenv('VPN_NETWORK', '10.8.0.0/24')
    VPN_NETWORK_START = os.getenv('VPN_NETWORK_START', '10.8.0.2')
    
    # Obfuscation Parameters
    JC = int(os.getenv('JC', '6'))  # Junk packet count
    JMIN = int(os.getenv('JMIN', '50'))  # Junk packet min size
    JMAX = int(os.getenv('JMAX', '1000'))  # Junk packet max size
    
    S1 = int(os.getenv('S1', '0'))  # Init packet padding
    S2 = int(os.getenv('S2', '0'))  # Response packet padding
    S3 = int(os.getenv('S3', '0'))  # Cookie packet padding
    S4 = int(os.getenv('S4', '0'))  # Transport packet padding
    
    H1 = os.getenv('H1', '')  # Init packet header
    H2 = os.getenv('H2', '')  # Response packet header
    H3 = os.getenv('H3', '')  # Cookie packet header
    H4 = os.getenv('H4', '')  # Transport packet header
    
    I1 = os.getenv('I1', '')  # Custom signature packet 1
    I2 = os.getenv('I2', '')  # Custom signature packet 2
    I3 = os.getenv('I3', '')  # Custom signature packet 3
    I4 = os.getenv('I4', '')  # Custom signature packet 4
    I5 = os.getenv('I5', '')  # Custom signature packet 5
    
    # API Configuration
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', '8080'))
    API_KEY = os.getenv('API_KEY', '')
    
    # AmneziaWG Interface
    INTERFACE_NAME = os.getenv('INTERFACE_NAME', 'awg0')
    
    # Data directory
    DATA_DIR = os.getenv('DATA_DIR', '/etc/amneziawg')
    CONFIG_FILE = os.path.join(DATA_DIR, f'{INTERFACE_NAME}.conf')
    USERS_FILE = os.path.join(DATA_DIR, 'users.json')
