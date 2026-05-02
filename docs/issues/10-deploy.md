# Issue #10: Deploy — actualizar servicio bruno-bot en EasyPanel

**Type:** HITL (requiere acceso manual a EasyPanel + validación)
**Blocked by:** #1-#9 (todos)

## What to build

Actualizar el servicio `bruno-bot` en EasyPanel con la nueva imagen Docker.

Pasos:
1. Push imagen a GitHub Container Registry (o build directo en EasyPanel)
2. Actualizar servicio bruno-bot con nueva imagen
3. Configurar variables de entorno en EasyPanel (copiar de .env)
4. Verificar que el bot responde en Telegram
5. Verificar que webhooks internos funcionan (bruno-monitor → bot)
6. Verificar health check
7. Monitorear logs por 24h

## Acceptance criteria

- [ ] Servicio bruno-bot corriendo con nueva imagen Python
- [ ] Bot responde en los 3 grupos de Telegram
- [ ] Bot respeta permisos por grupo
- [ ] Consultas de ventas retornan datos reales
- [ ] Alertas de cierre llegan al grupo Admin
- [ ] Health check responde OK
- [ ] Logs sin errores críticos en primeras 24h
- [ ] Servicio se auto-reinicia si crashea

## References
- Todos los issues anteriores
- `.env` — variables de producción
- EasyPanel dashboard del VPS
