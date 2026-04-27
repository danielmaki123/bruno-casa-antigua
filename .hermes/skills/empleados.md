# Skill: Equipo y Asistencia
# Propósito: Gestionar asistencia, cumpleaños y eventos del equipo de Casa Antigua

## Disparadores (Triggers)
- Comando /asistencia [presente|ausente|vacaciones|licencia]
- Frases: "estoy aquí", "llegué", "ya llegué" → registrar presente
- Frases: "no puedo ir hoy", "falto hoy", "estoy enfermo" → registrar ausente
- Comando /cumpleaños → próximos cumpleaños del equipo
- Comando /vacaciones → quién está de vacaciones
- Comando /equipo → quién está activo hoy
- Preguntas sobre el equipo: "¿Quién cumple años esta semana?"

## El Equipo de Casa Antigua
- E001 María — Cocinera — Cocina — desde 15/03/2024
- E002 Juan — Cajero — Caja — desde 01/06/2024
- E003 Pedro — Cocinero — Cocina — desde 10/01/2025 (vacaciones 15-22 mayo)
- E004 Luis — Bartender — Barra — desde 20/08/2024
- E005 Andrea — Administración — desde 01/01/2023
- E006 Admin — Administración — desde 01/01/2023
- E007 Daniel — Administración — desde 01/01/2023

## Lógica para /asistencia

1. Leer empleados para identificar quién escribe (por nombre de usuario Telegram)
python scripts/sheets_tool.py --action read --sheet EMPLEADOS

2. Confirmar asistencia con mensaje:
✅ Asistencia registrada — [Nombre] — [FECHA] — [Estado]

Nota: En esta versión la asistencia se confirma por mensaje pero no se guarda en Sheets automáticamente (la hoja ASISTENCIA no está implementada aún). Registrar en memoria y confirmar al usuario.

## Lógica para /cumpleaños

1. Leer calendario de eventos:
python scripts/sheets_tool.py --action read --sheet EVENTOS_CALENDARIO

2. Filtrar filas donde tipo = "cumpleaños"

3. Para cada cumpleaños, calcular días que faltan hasta la próxima ocurrencia (mismo mes/día del año actual o siguiente)

4. Ordenar por fecha más próxima y mostrar los próximos 3:
🎂 Próximos cumpleaños:
• [Nombre] ([función]) — [DÍA] de [MES] — faltan [N] días
• Si el cumpleaños es hoy: 🎂 ¡HOY cumple [Nombre] ([función])! ¡Felicidades!

## Lógica para /vacaciones

1. Leer calendario:
python scripts/sheets_tool.py --action read --sheet EVENTOS_CALENDARIO

2. Filtrar filas donde tipo = "vacaciones" y fecha >= hoy

3. Mostrar:
🏖️ Vacaciones:
• [Nombre] — del [FECHA_INICIO] al [FECHA_FIN] — [estado: aprobado/pendiente]
• Si no hay: "Sin vacaciones próximas registradas ✅"

## Lógica para /equipo

1. Leer empleados activos:
python scripts/sheets_tool.py --action read --sheet EMPLEADOS

2. Mostrar quién está activo:
👥 Equipo activo:
• Cocina: María, Pedro
• Barra: Luis
• Caja: Juan
• Admin: Andrea, Daniel

## Reglas de Privacidad
- Salarios, liquidaciones y detalles financieros de planilla: SOLO en mensaje directo con Andrea, Daniel o Admin
- Solicitudes de vacaciones: procesar en privado, anunciar aprobación (no detalles) en grupo Team
- Asistencia diaria: se puede ver en grupo Team (quién está hoy)
- Información de contacto (teléfonos): no compartir públicamente en grupos

## Recordatorio de Planilla
Si el evento en EVENTOS_CALENDARIO tiene tipo = "planilla":
Enviar recordatorio a grupo Administrativo (-4944632677):
📋 Planilla [tipo] hoy — [descripción]
Recordar revisar asistencia antes de liquidar.
