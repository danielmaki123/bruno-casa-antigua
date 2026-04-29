# 🤖 Manual Operativo: Bruno (Casa Antigua)

Este documento detalla las tareas automáticas, horarios y comandos interactivos de **Bruno**, el Sistema Operativo de Casa Antigua.

---

## 🛠️ 1. Tareas Automáticas (Sin intervención humana)

Bruno corre tres procesos independientes en la nube que vigilan el restaurante 24/7:

### A. Monitoreo de Ventas (Gmail)
- **Frecuencia:** Cada 10 minutos.
- **Qué hace:** Revisa el correo `casaantigua.rest@gmail.com` buscando los reportes de cierre del sistema de ventas (POS).
- **Acción:** Procesa el archivo adjunto, extrae las ventas (Efectivo, Tarjeta, Total) y las guarda en la Base de Datos.
- **Evita duplicados:** Registra cada ID de mensaje procesado para no duplicar datos.

### B. Sincronización de Inventario
- **Frecuencia:** Cada 1 hora.
- **Qué hace:** Lee las hojas de Google Sheets (`INVENTARIO_BEBIDAS`) y descarga el stock actual a la base de datos para que esté disponible en Telegram.

### C. Reportes Programados
Bruno envía notificaciones automáticas en horarios específicos:

| Reporte | Horario | Grupo Destino | Propósito |
| :--- | :--- | :--- | :--- |
| **Resumen Diario** | 08:00 AM | **Team** | Informar cómo cerraron las ventas del día anterior. |
| **Control de Postres** | Lunes 07:00 AM | **Inventario** | Avisar qué postres están bajos para pedir a proveedores. |
| **Pedido Semanal** | Miércoles 11:00 AM | **Inventario** | Generar la lista de compras basada en el stock bajo mínimo. |
| **Auditoría de Cierre** | 22:00 PM | **Administrativo** | Reportar si hubo diferencias de caja o descuadres de consumo. |

---

## 💬 2. Comandos Interactivos (Telegram)

Puedes hablar con Bruno en cualquier momento. Él responderá de forma breve para ahorrar tokens.

### Reportes de Ventas
- `Bruno, ventas de hoy`: Muestra el total vendido hasta el momento.
- `Bruno, ventas de la semana`: Muestra un resumen de los últimos 7 días con promedio diario.
- `Bruno, cierre del 2026-04-28`: Consulta un día específico (formato AAAA-MM-DD).

### Control de Inventario
- `Bruno, inventario actual`: Te da la lista de TODO el stock con emojis (✅ OK, ⚠️ Bajo).
- `Bruno, qué está bajo`: Solo muestra los productos que necesitan compra urgente o están en cero.
- `Bruno, stock de whisky`: Puedes preguntar por un producto específico.

### Auditoría y Diferencias
- `Bruno, reporte de discrepancias`: Muestra si el consumo de botellas cuadra con lo vendido.

---

## 📍 3. Grupos de Telegram

Bruno sabe a quién decirle qué. Es importante no cambiar los IDs de los grupos en la configuración:

1.  **Grupo Administrativo:** Reportes de dinero, auditorías y errores críticos del sistema.
2.  **Grupo Inventario:** Listas de compras, stock bajo y alertas de insumos.
3.  **Grupo Team:** Anuncios generales y resúmenes de éxito del día.

---

## 🚨 4. ¿Qué hacer si Bruno no responde?
1.  **Revisar EasyPanel:** Asegurarse de que el servicio `brunobot` esté en verde (Running).
2.  **Verificar el Token:** Si cambiaste la clave en @BotFather, debes actualizarla en EasyPanel.
3.  **Base de Datos:** Si Bruno dice "Error de conexión", avisar al administrador técnico.

---
*Manual generado el 29 de abril de 2026 para Casa Antigua.*
