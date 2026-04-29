FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/inventario_monitor.py /app/scripts/inventario_monitor.py
COPY scripts/sheets_tool.py /app/scripts/sheets_tool.py

CMD ["python", "scripts/inventario_monitor.py"]
