FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/gmail_monitor.py /app/scripts/gmail_monitor.py
COPY scripts/parse_cierre.py /app/scripts/parse_cierre.py
COPY scripts/audit_cierre.py /app/scripts/audit_cierre.py

CMD ["python", "scripts/gmail_monitor.py"]
