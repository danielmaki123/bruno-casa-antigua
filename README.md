# BrunoBot — Sistema Operativo de Casa Antigua

Bot de Telegram para gestión operativa del restaurante Casa Antigua.
Basado en Hermes Agent (NousResearch) con skills y herramientas propias.

## Arquitectura
- **Base:** Hermes Agent (ghcr.io/nousresearch/hermes-agent:latest)
- **Skills:** .hermes/skills/ (inventario, empleados, alertas, google_sheets)
- **Personalidad:** .hermes/SOUL.md
- **Bridge Sheets:** scripts/sheets_tool.py
- **Config:** docker-compose.yml

## Setup
1. Copiar .env.example a .env y completar variables
2. Ejecutar: python scripts/authenticate_google.py (solo primera vez)
3. Ejecutar: python scripts/initialize_google_sheets.py (solo primera vez)
4. Deploy: docker-compose up -d

## Variables de entorno requeridas
- TELEGRAM_TOKEN
- KIMI_API_KEY
- GOOGLE_SHEETS_ID
- DATABASE_URL

## Skills disponibles
- /inventario — ver estado del stock
- /reportar — registrar inventario
- /asistencia — marcar asistencia
- /cumpleaños — próximos cumpleaños
- /vacaciones — vacaciones del equipo
- Mensajes libres de inventario: "pollo 12kg, carne 3kg"
- Alertas automáticas: 08:00 y 22:00
