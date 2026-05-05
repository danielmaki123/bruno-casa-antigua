#!/bin/sh
set -e

# Resetear IDs procesados para reintento de correos con cierres mal parseados
mkdir -p data
echo '[]' > data/processed_emails.json

python scripts/gmail_monitor.py &

exec python -m bot.main
