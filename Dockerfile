# BrunoBot — Casa Antigua
# Extends the official Hermes Agent image with our custom skills and tools

FROM ghcr.io/nousresearch/hermes-agent:latest

# Set working directory (Hermes default)
WORKDIR /app

# Install Python dependencies for sheets_tool.py
# (Hermes image may already have Python, we ensure our deps are there)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt 2>/dev/null || \
    pip3 install --no-cache-dir -r /app/requirements.txt 2>/dev/null || \
    echo "pip not available, skipping Python deps"

# Copy Bruno's personality and skills into the Hermes home directory
COPY .hermes/SOUL.md /root/.hermes/SOUL.md
COPY .hermes/skills/ /root/.hermes/skills/

# Copy config (only the yaml, NOT credentials)
COPY .hermes/config.yaml /root/.hermes/config.yaml

# Copy our Python bridge script
COPY scripts/sheets_tool.py /app/scripts/sheets_tool.py

# Credentials (token.json, .env) are injected at runtime via EasyPanel env vars
# and volume mounts — never baked into the image

# Hermes handles its own entrypoint
