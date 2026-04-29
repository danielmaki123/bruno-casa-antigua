# BrunoBot - Casa Antigua
# Extends the official Hermes Agent image with our custom skills and tools

FROM nousresearch/hermes-agent:latest

# Set working directory for project assets/scripts
WORKDIR /app

# Install Python runtime + pip in Hermes base image (Debian-based)
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies (psycopg2-binary, python-dotenv, etc.)
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt --break-system-packages

# Copy Bruno personality, skills, and config into Hermes home directory
COPY .hermes/SOUL.md /root/.hermes/SOUL.md
COPY .hermes/skills/ /root/.hermes/skills/
COPY .hermes/config.yaml /root/.hermes/config.yaml

# Copy Python bridge scripts invoked by Hermes tools/skills
COPY scripts/sheets_tool.py /app/scripts/sheets_tool.py
COPY scripts/reporte_tool.py /app/scripts/reporte_tool.py

# Credentials (token.json, .env) are injected at runtime via env vars/volumes
# Hermes image entrypoint/CMD remains unchanged
