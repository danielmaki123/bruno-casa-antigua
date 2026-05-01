# BrunoBot - Casa Antigua
# Extends the official Hermes Agent image with our custom skills and tools

FROM nousresearch/hermes-agent:latest

# Set working directory for project assets/scripts
WORKDIR /app

# Install Python runtime + Node.js (for PM2) in Hermes base image
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g pm2 && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt --break-system-packages

# Copy Bruno configuration and scripts
COPY .hermes/SOUL.md /opt/data/SOUL.md
COPY .hermes/skills/ /opt/data/skills/
COPY .hermes/config.yaml /opt/data/config.yaml
COPY ecosystem.config.js /app/ecosystem.config.js
COPY . /app/

# Ensure logs directory exists
RUN mkdir -p /app/logs

# Set PM2 as the entrypoint for high-availability background services
CMD ["pm2-runtime", "start", "ecosystem.config.js"]
