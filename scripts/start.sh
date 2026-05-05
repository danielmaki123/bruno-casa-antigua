#!/bin/sh
set -e

python scripts/gmail_monitor.py &

exec python -m bot.main
