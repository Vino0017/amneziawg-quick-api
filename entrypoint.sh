#!/bin/bash
set -e

echo "Starting AmneziaWG API Service..."

# Generate server keypair if not provided or is placeholder
if [ -z "$SERVER_PRIVATE_KEY" ] || [ "$SERVER_PRIVATE_KEY" = "your_server_private_key_here" ]; then
    echo "Generating server keypair..."
    SERVER_PRIVATE_KEY=$(awg genkey)
    SERVER_PUBLIC_KEY=$(echo "$SERVER_PRIVATE_KEY" | awg pubkey)
    export SERVER_PRIVATE_KEY
    export SERVER_PUBLIC_KEY
    echo "Generated Server Public Key: $SERVER_PUBLIC_KEY"
else
    echo "Using provided server keys"
    echo "Server Public Key: $SERVER_PUBLIC_KEY"
fi

# Calculate server IP (first IP in the network, e.g., 10.137.65.1)
SERVER_VPN_IP="${VPN_NETWORK_START%.*}.1"

echo "Starting AmneziaWG interface ${INTERFACE_NAME}..."
amneziawg-go ${INTERFACE_NAME} &

# Wait for interface to be created
sleep 2

# Create configuration file for awg setconf
# Note: setconf only accepts [Interface] with PrivateKey and ListenPort
# plus obfuscation params in the [Interface] section
CONFIG_FILE="/tmp/${INTERFACE_NAME}.conf"

cat > "$CONFIG_FILE" << EOF
[Interface]
PrivateKey = ${SERVER_PRIVATE_KEY}
ListenPort = ${SERVER_PORT}
EOF

# Add obfuscation parameters only if they are set and > 0
[ "${JC:-0}" != "0" ] && echo "Jc = ${JC}" >> "$CONFIG_FILE"
[ "${JMIN:-0}" != "0" ] && echo "Jmin = ${JMIN}" >> "$CONFIG_FILE"
[ "${JMAX:-0}" != "0" ] && echo "Jmax = ${JMAX}" >> "$CONFIG_FILE"
[ "${S1:-0}" != "0" ] && echo "S1 = ${S1}" >> "$CONFIG_FILE"
[ "${S2:-0}" != "0" ] && echo "S2 = ${S2}" >> "$CONFIG_FILE"
[ "${S3:-0}" != "0" ] && echo "S3 = ${S3}" >> "$CONFIG_FILE"
[ "${S4:-0}" != "0" ] && echo "S4 = ${S4}" >> "$CONFIG_FILE"
[ -n "$H1" ] && echo "H1 = ${H1}" >> "$CONFIG_FILE"
[ -n "$H2" ] && echo "H2 = ${H2}" >> "$CONFIG_FILE"
[ -n "$H3" ] && echo "H3 = ${H3}" >> "$CONFIG_FILE"
[ -n "$H4" ] && echo "H4 = ${H4}" >> "$CONFIG_FILE"

echo "=== Server Configuration ==="
cat "$CONFIG_FILE"
echo "=== End Configuration ==="

# Apply configuration
echo "Applying configuration..."
awg setconf ${INTERFACE_NAME} "$CONFIG_FILE"

# Set up IP address
ip addr add ${SERVER_VPN_IP}/24 dev ${INTERFACE_NAME}
ip link set ${INTERFACE_NAME} up

# Enable IP forwarding
sysctl -w net.ipv4.ip_forward=1

# Set up NAT (use the default interface)
DEFAULT_IFACE=$(ip route | grep default | awk '{print $5}' | head -1)
if [ -n "$DEFAULT_IFACE" ]; then
    iptables -t nat -A POSTROUTING -s ${VPN_NETWORK} -o ${DEFAULT_IFACE} -j MASQUERADE
fi
iptables -A FORWARD -i ${INTERFACE_NAME} -j ACCEPT
iptables -A FORWARD -o ${INTERFACE_NAME} -j ACCEPT

echo "AmneziaWG interface is up and running"
echo "Server Public Key: $SERVER_PUBLIC_KEY"
echo "VPN Network: $VPN_NETWORK"
echo "Server VPN IP: $SERVER_VPN_IP"

# Start Flask API
echo "Starting API service on port ${API_PORT}..."
exec python awg_api.py
