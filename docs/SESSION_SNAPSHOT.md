# BrunoBot — Session Snapshot
**Fecha:** 28 Abril 2026 | **Para retomar sin pérdida de contexto**

---

## 🟢 Estado del Sistema (Producción)

### Servicios EasyPanel (todos corriendo)
| Servicio | Función | Estado |
|---|---|---|
| `brunobot` | Hermes AI en Telegram | 🟢 Running |
| `bruno-inventario` | Monitor de Sheets → PostgreSQL | 🟢 Running |
| `bruno-monitor` | Monitor Gmail → Auditoría cierres | 🟢 Running |
| `metabase` | Dashboard visual | 🟢 Running (acceso via dominio) |

### Variables de entorno pendientes de verificar en `brunobot`
- Confirmar que `DATABASE_URL` está seteada (necesaria para `reporte_tool.py`)

---

## 📊 Google Sheets — IDs Definitivos

| Sheet | ID | Tabs |
|---|---|---|
| Bebidas_Inventario | `1PG5id1G_tpgMmLgCpkkRF8YXby0tidY0Wlb3smminxw` | INVENTARIO_BEBIDAS, ENTRADAS |
| Administracion | `1QQnEekHPRPaMgSYFjzbJWTftL_rj1RGQyfOccKfYNP8` | PROVEEDORES, POSTRES |
| Configuracion | `19TVVHdzOqVd1PiQdVvVokcGAT4uSaMJREFDvHSIJzuk` | CATALOGO_LICORES, RECETAS_BEBIDAS |
| Personal | `1UocFRyq7KTg_hrolz4awfraUMEoZrvFTd9kaFYNzH40` | EMPLEADOS |
| Agenda | `1GDrFopnvj8kYB8wSepaDBju43SSuWhWm7nOkf-dN-bM` | EVENTOS_CALENDARIO |

**Drive folder:** `1-gz0qdGvbt2EMoc0VtrxjFTBi6qeJ1_C` (Casa Antigua)

---

## 🗄️ PostgreSQL

**Conexión:** `postgres://postgres:06c5f13aaaaa58a7f6f1@76.13.250.83:5435/brunobot?sslmode=disable`

**Tablas principales:**
- `cierres_caja` — Cierres de caja (11 registros reales)
- `ventas_detalle` — Detalle por producto
- `inventario_catalogo` — Catálogo de bebidas
- `inventario_diario` — Stock diario (aún vacío — equipo debe llenar)
- `entradas_inventario` — Entradas de proveedor
- `alertas_inventario` — Alertas (campo: `enviado`, no `resuelta`)
- `notificaciones_log` — Control de notificaciones duplicadas
- `proveedores` — Proveedores

**Vistas:** `stock_vs_minimo`, `ventas_por_categoria`, `top_productos`, `resumen_financiero`

**Columnas clave de `cierres_caja`:**
- `v_total` (no total_ventas)
- `efectivo_cds` (no efectivo_declarado)
- `tarjetas_total`
- `diferencia_pos`
- `cajero`

---

## 📁 Archivos Clave — Scripts

| Archivo | Estado | Descripción |
|---|---|---|
| `scripts/inventario_monitor.py` | ✅ 1181 líneas | Monitor principal |
| `scripts/reporte_tool.py` | ✅ 407 líneas | Reportes para Bruno |
| `scripts/gmail_monitor.py` | ✅ | Monitor de Gmail |
| `scripts/audit_cierre.py` | ✅ | Auditoría de cierres |
| `scripts/sheets_tool.py` | ✅ | Herramienta Sheets para Hermes |
| `.hermes/skills/ventas.md` | ✅ | Skill de reportes |
| `.hermes/skills/inventario.md` | ✅ | Skill de inventario |
| `.hermes/SOUL.md` | ✅ | Personalidad de Bruno |
| `docs/METABASE_SETUP.md` | ✅ | Guía dashboards |

---

## 🔧 File Mounts en EasyPanel — `brunobot`

Verificar que estos mounts existen y están actualizados:
- `/app/scripts/reporte_tool.py` ← **Actualizado hoy** (407 líneas)
- `/app/scripts/sheets_tool.py`
- `/app/.hermes/skills/ventas.md` ← **Nuevo hoy**
- `/app/.hermes/skills/inventario.md`
- `/app/.hermes/SOUL.md` ← **Actualizado hoy**
- `/app/token.json`

---

## 🔧 File Mounts en EasyPanel — `bruno-inventario`

Variables de entorno que DEBEN estar presentes:
```
SHEETS_ID_BEBIDAS=1PG5id1G_tpgMmLgCpkkRF8YXby0tidY0Wlb3smminxw
SHEETS_ID_ADMIN=1QQnEekHPRPaMgSYFjzbJWTftL_rj1RGQyfOccKfYNP8
SHEETS_ID_CONFIG=19TVVHdzOqVd1PiQdVvVokcGAT4uSaMJREFDvHSIJzuk
```

---

## 🐛 Problemas Conocidos / Pendientes

### Pendiente ahora mismo
1. **Bruno no devuelve datos en Telegram** — reporte_tool.py recién actualizado (407 líneas). Requiere redeploy de `brunobot`. Causa probable: script aún no ejecutaba correctamente en contenedor.

2. **Inventario vacío** — El equipo (Flor/Jean/Jorge) aún no ha llenado:
   - `CATALOGO_LICORES` → pesos de botellas
   - `INVENTARIO_BEBIDAS` columnas 27/04 y 28/04

3. **Metabase dashboards incompletos** — Solo se creó "Resumen Ejecutivo" con 5 cards. Faltan 4 dashboards más (ver METABASE_SETUP.md)

### Para verificar en próxima sesión
- Abrir Telegram → enviar "ventas de esta semana" a Bruno → debe devolver datos reales
- Si falla: revisar logs de `brunobot` en EasyPanel → buscar `[DEBUG]` y `[INFO]` del reporte_tool.py

---

## 📅 Tareas Pendientes

### Alta prioridad
- [ ] Confirmar que Bruno devuelve datos reales en Telegram
- [ ] El equipo debe pesar botellas y llenar CATALOGO_LICORES
- [ ] El equipo debe llenar INVENTARIO_BEBIDAS (27/04 y 28/04)

### Media prioridad  
- [ ] Crear 4 dashboards restantes en Metabase
- [ ] Verificar `DATABASE_URL` en env vars de `brunobot`

### Baja prioridad
- [ ] GitHub + auto-deploy via webhooks
- [ ] Compartir Metabase con equipo (permisos por rol)
- [ ] Inventario de cocina (separado de bebidas)

---

## 💬 Comandos de Bruno que el equipo puede usar

```
ventas de esta semana
ventas de hoy
cómo estuvo el cierre de ayer
qué productos están bajo mínimo
/resumen
```
