FROM golang:1.24-alpine AS awg-go-builder

# Install build dependencies
RUN apk add --no-cache git make

# Clone and build amneziawg-go
WORKDIR /build
RUN git clone https://github.com/amnezia-vpn/amneziawg-go.git
WORKDIR /build/amneziawg-go
RUN make

# Build amneziawg-tools
FROM alpine:latest AS awg-tools-builder

RUN apk add --no-cache git make gcc musl-dev linux-headers bash

WORKDIR /build
RUN git clone https://github.com/amnezia-vpn/amneziawg-tools.git
WORKDIR /build/amneziawg-tools/src
RUN make

# Final runtime image
FROM python:3.11-alpine

# Install runtime dependencies
RUN apk add --no-cache \
    iptables \
    ip6tables \
    iproute2 \
    bash \
    openresolv

# Copy built binaries
COPY --from=awg-go-builder /build/amneziawg-go/amneziawg-go /usr/local/bin/
COPY --from=awg-tools-builder /build/amneziawg-tools/src/wg /usr/local/bin/awg
COPY --from=awg-tools-builder /build/amneziawg-tools/src/wg-quick/linux.bash /usr/local/bin/awg-quick

# Make scripts executable
RUN chmod +x /usr/local/bin/awg /usr/local/bin/awg-quick /usr/local/bin/amneziawg-go

# Set up working directory
WORKDIR /app

# Copy application files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY awg_api.py .
COPY awg_manager.py .
COPY config.py .
COPY entrypoint.sh /entrypoint.sh

# Make entrypoint executable
RUN chmod +x /entrypoint.sh

# Create data directory
RUN mkdir -p /etc/amneziawg

# Expose API port
EXPOSE 8080

# Expose VPN port (will be overridden by environment variable)
EXPOSE 51820/udp

ENTRYPOINT ["/entrypoint.sh"]

