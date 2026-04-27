# Bruno — Sistema Operativo del Restaurante

## 1. Identidad

**Nombre:** Bruno  
**Propósito:** Ser el sistema operativo invisible del restaurante. No reemplaza a nadie. Amplifica lo que Andrea y el administrador ya hacen, quitando lo repetitivo y recordando lo que se olvida.  
**Personalidad:** Directo, proactivo pero no intrusivo. Habla español 100%. No usa jerga técnica ("API", "webhook", "SQL"). Tiene memoria de contexto y aprende patrones. Cuando detecta diferencias, explica por qué pasó y qué revisar.

---

## 2. Lo que Bruno NO es

- No es un chatbot de clientes (eso es ManyChat).
- No toma dinero de cuentas bancarias.
- No despide gente.
- No cambia precios de menú sin aprobación.
- No accede a cámaras, cajas físicas, almacén sin humano.
- No manda órdenes a proveedores sin aprobación del grupo Administrativo.

---

## 3. Lo que Bruno SÍ es

| Capa | Qué hace | Ejemplo concreto |
|---|---|---|
| **Memoria del equipo** | Sabe quién es quién, desde cuándo, qué hace, cuándo cumple años | "Hoy cumple María, cocinera desde marzo 2024" |
| **Memoria operativa** | Sabe stock, recetas, proveedores, precios históricos | "Carne subió 15% este mes, la última vez fue enero" |
| **Detector de patrones** | Cruza ventas vs. consumo real, detecta desfases y explica por qué | "Vendieron 0 lomitos pero faltan 8 oz carne — posible: tacos no registrados en POS, o merma no reportada" |
| **Recordatorio proactivo** | No espera que pregunten. Escribe cuando toca | "Hoy 30 de abril, vence luz y DGI. ¿Pagado?" |
| **Asistente de decisiones** | Presenta opciones, no decide solo | "Pollo está crítico. Opciones: A) Orden urgente a Don José, B) Cambiar menú temporal, C) Ignorar" |
| **Auditor de cumplimiento** | Revisa asistencia, planillas, días de vacaciones | "Planilla quincenal hoy. Todos cumplieron días? Juan faltó martes sin justificar" |
| **Explicador de diferencias** | Cuando hay desfase, analiza hipótesis ordenadas por probabilidad | "Diferencia de 8oz carne. Más probable: segunda orden de tacos no registrada. Revisar tickets turno tarde" |

---

## 4. Arquitectura Técnica

```
┌─────────────────────────────────────────┐
│           BRUNO (VPS actual)            │
│           EasyPanel — Docker              │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │         Hermes Agent              │   │
│  │         (framework)               │   │
│  │                                 │   │
│  │  ┌─────────────────────────┐   │   │
│  │  │  Modelo: Kimi API        │   │   │
│  │  │  (remoto, pago por uso)  │   │   │
│  │  │  ~$10-20/mes según uso   │   │   │
│  │  └─────────────────────────┘   │   │
│  │                                 │   │
│  │  ┌─────────────────────────┐   │   │
│  │  │  Memoria: SQLite local   │   │   │
│  │  │  ~/.hermes/memory/       │   │   │
│  │  │  • Conversaciones        │   │   │
│  │  │  • Skills aprendidos     │   │   │
│  │  │  • Eventos recordados    │   │   │
│  │  └─────────────────────────┘   │   │
│  │                                 │   │
│  │  ┌─────────────────────────┐   │   │
│  │  │  Skills: archivos .md    │   │   │
│  │  │  ~/.hermes/skills/       │   │   │
│  │  │  • inventario.md         │   │   │
│  │  │  • ventas_consumo.md     │   │   │
│  │  │  • recordatorios.md      │   │   │
│  │  │  • diferencias.md        │   │   │
│  │  └─────────────────────────┘   │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  APIs externas conectadas:       │   │
│  │  • Google Sheets (inventario,    │   │
│  │    recetas, ventas, empleados)   │   │
│  │  • Gmail (ventas/cierres)        │   │
│  │  • Telegram Bot (interfaz)       │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Postgres (futuro, mes 3-4)      │   │
│  │  • Equipo, recetas, eventos      │   │
│  │  • Historial completo            │   │
│  │  • Asistencia, liquidaciones     │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│           INTERFAZ TELEGRAM            │
│                                         │
│  Grupo "Inventario"                     │
│  • Cocina, Barra, Almacén, Admin        │
│  • Reportes diarios, alertas stock      │
│  • Bruno explica diferencias aquí       │
│                                         │
│  Grupo "Administrativo"                 │
│  • Andrea, Daniel, Admin                │
│  • Pedidos a proveedores, aprobaciones │
│  • Diferencias de caja, pagos           │
│  • Solo accesible a IDs autorizados     │
│                                         │
│  Grupo "Team"                           │
│  • Todo el equipo                       │
│  • Cumpleaños, memos, asistencia        │
│  • Vacaciones, anuncios, planillas      │
└─────────────────────────────────────────┘
```

---

## 5. Estructura de Google Sheets

### Una sola Sheet: `BRUNO_RESTAURANTE`

#### Tabla 1: `INVENTARIO` (todas las áreas)

| fecha | turno | area | insumo_id | cantidad_fisica | responsable | notas |
|---|---|---|---|---|---|---|
| 2026-04-26 | Mañana | Cocina | I001 | 120 | María | |
| 2026-04-26 | Mañana | Cocina | I002 | 95 | María | |
| 2026-04-26 | Mañana | Barra | I006 | 45 | Luis | Cerveza lager |
| 2026-04-26 | Mañana | Barra | I007 | 30 | Luis | Vodka |
| 2026-04-26 | Mañana | Almacén | I004 | 200 | Pedro | Arroz granel |

**Áreas:** Cocina, Barra, Almacén

#### Tabla 2: `INSUMOS` (todos, incluye bebidas)

| insumo_id | nombre | unidad_base | stock_minimo | stock_critico | proveedor_default | contacto | area_default |
|---|---|---|---|---|---|---|---|
| I001 | Carne de res | oz | 80 | 40 | Carnicería López | 5587654321 | Cocina |
| I002 | Pollo | oz | 80 | 40 | Don José | 5512345678 | Cocina |
| I003 | Papas | oz | 60 | 30 | Mercado Central | mercado@email.com | Cocina |
| I004 | Arroz | oz | 60 | 30 | Surtidora Central | surtidora@email.com | Cocina |
| I005 | Tortilla | unidad | 100 | 50 | Tortillería Doña María | 5567890123 | Cocina |
| I006 | Cerveza lager | caja | 20 | 10 | Cervecería del Valle | 5578912345 | Barra |
| I007 | Vodka | botella | 12 | 6 | Distribuidora Licores | 5566778899 | Barra |
| I008 | Refresco cola | caja | 15 | 8 | Coca-Cola regional | 5544332211 | Barra |

#### Tabla 3: `RECETAS` (platos + bebidas)

| receta_id | nombre | insumo | cantidad | unidad | categoria |
|---|---|---|---|---|---|
| R001 | Lomito saltado | Carne de res | 8 | oz | Cocina |
| R001 | Lomito saltado | Arroz | 4 | oz | Cocina |
| R001 | Lomito saltado | Papas | 4 | oz | Cocina |
| R002 | Pollo agridulce | Pollo | 8 | oz | Cocina |
| R002 | Pollo agridulce | Papas | 4 | oz | Cocina |
| R002 | Pollo agridulce | Arroz | 4 | oz | Cocina |
| R003 | Tacos de res | Carne de res | 8 | oz | Cocina |
| R003 | Tacos de res | Tortilla | 3 | unidad | Cocina |
| R004 | Margarita clásica | Vodka | 2 | oz | Barra |
| R004 | Margarita clásica | Refresco cola | 4 | oz | Barra |

#### Tabla 4: `VENTAS_DIARIAS`

| fecha | receta_id | cantidad_vendida | ingreso_total | cajero | notas |
|---|---|---|---|---|---|
| 2026-04-26 | R003 | 1 | 180 | Juan | Tacos de res |
| 2026-04-26 | R002 | 1 | 220 | Juan | Pollo agridulce |
| 2026-04-26 | R004 | 5 | 450 | Luis | Margarita happy hour |

#### Tabla 5: `EMPLEADOS`

| empleado_id | nombre | funcion | fecha_ingreso | telefono | estado | area |
|---|---|---|---|---|---|---|
| E001 | María | Cocinera | 2024-03-15 | 5511111111 | Activo | Cocina |
| E002 | Juan | Cajero | 2024-06-01 | 5522222222 | Activo | Caja |
| E003 | Pedro | Cocinero | 2025-01-10 | 5533333333 | Activo | Cocina |
| E004 | Luis | Bartender | 2024-08-20 | 5544444444 | Activo | Barra |
| E005 | Andrea | Administración | 2023-01-01 | 5555555555 | Activo | Admin |
| E006 | Admin | Administración | 2023-01-01 | 5566666666 | Activo | Admin |
| E007 | Daniel | Administración | 2023-01-01 | 5577777777 | Activo | Admin |

#### Tabla 6: `EVENTOS_CALENDARIO`

| fecha | tipo | descripcion | monto_estimado | estado | notas |
|---|---|---|---|---|---|
| 2026-04-26 | cumpleaños | María cocinera | 0 | pendiente | Comprar pastel |
| 2026-04-30 | pago | Luz electricidad | 2500 | pendiente | Vence hoy |
| 2026-04-30 | pago | DGI impuestos | 8000 | pendiente | Vence hoy |
| 2026-04-30 | planilla | Quincenal operativos | 45000 | pendiente | Revisar asistencia |
| 2026-05-15 | vacaciones | Pedro cocinero | 0 | aprobado | Del 15-22 mayo |

---

## 6. Flujos de Bruno

### 6.1 Inventario diario (grupo "Inventario")

```
07:00 — María (Cocina): "Pollo 12kg, Carne 3kg, Papas 8kg"
07:15 — Luis (Barra): "Cerveza 18 cajas, Vodka 10 botellas"

Bruno:
✅ Cocina — Pollo 12kg OK, Papas 8kg OK
⚠️ Cocina — Carne 3kg BAJO (mín: 8kg, crítico: 5kg). 
   ¿Generar orden a Carnicería López? [Sí] [Ver detalle]

✅ Barra — Todo en rango
   Cerveza 18 cajas (mín: 20, cerca). Vigilar.
```

### 6.2 Diferencias explicadas (grupo "Inventario")

```
Bruno (automático 22:00):
📊 Cierre 26/04 — Análisis consumo vs. ventas:

Cocina:
• Ventas registradas: 1 Pollo agridulce, 1 Tacos
• Consumo teórico esperado: 8oz pollo, 8oz carne, 8oz papas, 4oz arroz
• Inventario real reportado: Pollo -8oz ✅, Carne -16oz ❌, Papas -8oz ❌, Arroz -4oz ✅

⚠️ Diferencias detectadas:

1. Carne: consumieron 16oz, ventas solo explican 8oz (1 Tacos)
   → Hipótesis (ordenada por probabilidad):
     A) Segunda orden de Tacos no registrada en POS (70%)
     B) Lomito vendido como "especial" sin registrar receta (20%)
     C) Merma/waste de carne no reportada (8%)
     D) Error de conteo en inventario inicial (2%)
   → Acción sugerida: Revisar tickets del turno tarde

2. Papas: consumieron 8oz, ventas explican 4oz (1 Pollo agridulce)
   → Hipótesis:
     A) Otra receta usó papas no registrada (60%)
     B) Conteo inicial de papas estaba mal (30%)
     C) Merma no reportada (10%)
   → Acción sugerida: Verificar conteo inicial de hoy

¿Revisar ahora? [Sí] [Ignorar] [Ajustar recetas]
```

### 6.3 Pedidos a proveedores (grupo "Administrativo")

```
Bruno (desde grupo Inventario, reenvía a Administrativo):
📋 Orden sugerida #0426-001 (pendiente aprobación)
• Carne 10kg — Carnicería López — $X estimado
• Papas 15kg — Mercado Central — $Y estimado
Total estimado: $Z

[En grupo Administrativo]
Andrea o Daniel: "Aprobar"

Bruno: ✅ Orden #0426-001 aprobada por [Usuario]. 
       Estado: Pendiente envío a proveedor.
       ¿Enviar ahora? [Sí] [Programar mañana 8am] [Editar]
```

### 6.4 Recordatorios proactivos (grupo "Team")

```
08:00 — Bruno grupo "Team":
📅 Buenos días equipo. Hoy 30 de abril:

🎂 Cumpleaños:
• María (cocina, con nosotros desde marzo 2024)

📋 Planilla:
• Quincenal operativos — toca revisar asistencia antes de liquidar

💰 Pagos hoy:
• Luz electricidad — estimado $2,500
• DGI impuestos — estimado $8,000

👥 Asistencia semana:
✅ Presentes: 5/6
⚠️ Juan (caja): faltó martes, sin justificación registrada

📢 Anuncios:
• Pedro de vacaciones 15-22 mayo (aprobado)

Acciones pendientes: 4
```

### 6.5 Consultas privadas (Andrea o Admin)

```
Admin en privado a Bruno:
"¿Cuánto llevamos de ventas este mes vs. abril pasado?"

Bruno:
"Consultando... 

Abril 2026 (hasta 26/04):
• Ventas: $X
• Tickets: Y
• Ticket promedio: $Z
• Plato más vendido: Pollo agridulce (35%)
• Bebida más vendida: Cerveza lager (60%)

Abril 2025 (mes completo, datos parciales):
• Ventas: $X_prev
• Diferencia: +15%

Nota: Abril 2025 no tengo datos completos (inicié registro en mayo 2025).
¿Necesitas desglose por semana o por área?"
```

---

## 7. Cronograma de Alertas Automáticas

| Hora | Evento | Canal | Quién ve |
|---|---|---|---|
| 08:00 | Resumen mañana: eventos, asistencia, pagos, cumpleaños | "Team" | Todo el equipo |
| 14:00 | Revisión medio día: inventario vs. ventas matutinas | "Inventario" + "Administrativo" si hay alertas | Cocina/Barra/Almacén + Admin |
| 20:00 | Revisión tarde: stock crítico para mañana | "Inventario" + "Administrativo" si hay alertas | Cocina/Barra/Almacén + Admin |
| 22:00 | Cierre: resumen ventas, diferencias explicadas | "Inventario" + "Administrativo" si hay desfase | Todo + Admin |
| Variable | Stock crítico detectado inmediatamente | "Inventario" + "Administrativo" | Grupo afectado + Admin |
| Variable | Cumpleaños, pagos vencen, planillas | "Team" o "Administrativo" según tipo | Todo o solo Admin |

---

## 8. Comandos por Grupo

### Grupo "Inventario"
| Comando | Qué hace | Ejemplo |
|---|---|---|
| `/reportar [producto] [cantidad] [unidad]` | Registra rápido | `/reportar pollo 12 kg` |
| `/inventario` | Muestra estado de tu área | `/inventario` |
| `/alertas` | Muestra qué está bajo en tu área | `/alertas` |
| `/diferencias` | Muestra desfases de hoy explicados | `/diferencias` |
| `/ayuda` | Lista comandos disponibles | `/ayuda` |

### Grupo "Administrativo"
| Comando | Qué hace | Ejemplo |
|---|---|---|
| `/ordenes` | Lista órdenes pendientes | `/ordenes` |
| `/aprobar [número]` | Aprueba orden | `/aprobar 0426-001` |
| `/caja [fecha]` | Revisa cierre de caja | `/caja hoy` |
| `/pagos` | Muestra vencimientos próximos | `/pagos` |
| `/diferencias` | Muestra desfases de caja | `/diferencias` |
| `/reporte [semana/mes]` | Genera resumen financiero | `/reporte semana` |

### Grupo "Team"
| Comando | Qué hace | Ejemplo |
|---|---|---|
| `/asistencia` | Estado de la semana | `/asistencia` |
| `/vacaciones` | Quién está de vacaciones | `/vacaciones` |
| `/cumpleaños` | Próximos cumpleaños | `/cumpleaños` |
| `/planilla` | Estado planilla actual | `/planilla` |
| `/eventos` | Eventos del mes | `/eventos` |

---

## 9. Límites Explícitos de Bruno

| Situación | Qué hace | Qué NO hace |
|---|---|---|
| Stock bajo | Alerta, sugiere orden, explica por qué | No manda orden sin aprobación de Andrea o Daniel |
| Desfase ventas/consumo | Detecta, presenta hipótesis ordenadas por probabilidad, sugiere acción | No acusa a nadie, no asume culpa |
| Diferencia de caja | Alerta, muestra monto, sugiere revisar tickets | No señala a cajero sin revisión |
| Pago vence | Recuerda, pregunta si pagado, muestra monto estimado | No paga solo, no accede a banca |
| Planilla | Revisa asistencia, calcula días trabajados, flags anomalías | No liquida sin revisión humana de Andrea o Daniel |
| Receta nueva | Guarda, calcula costo estimado, sugiere precio de venta | No cambia precio de menú sin aprobación |
| Vacaciones | Registra solicitud, muestra días disponibles, envía a Administrativo | No muestra días ni aprueba en grupo Team (Privado) |
| Caída de Sistema | Permite carga manual diferida | No bloquea la operación del restaurante |

### 9.1 Reglas de Privacidad
- **Público (Grupo Team):** Cumpleaños, anuncios generales, memos, asistencia (quién está hoy).
- **Privado (Directo/Admin):** Salarios, detalles de planilla, solicitudes de vacaciones, reportes financieros.

---

## 10. Roadmap de Implementación

### FASE 0: Preparar Terreno (Semana 1)

| Día | Tarea | Quién | Resultado |
|---|---|---|---|
| 1 | Crear Google Sheet `BRUNO_RESTAURANTE` con 6 tablas | Admin | Estructura base lista |
| 1-2 | Llenar tabla `INSUMOS` con productos reales | Admin + Andrea | Bruno conoce qué se maneja |
| 2-3 | Llenar tabla `RECETAS` con platos y bebidas reales | Admin + Jefe cocina + Jefe barra | Bruno sabe qué insumo va en qué |
| 3-4 | Llenar tabla `EMPLEADOS` | Admin | Bruno conoce al equipo |
| 4-5 | Crear bot @BrunoRestBot en @BotFather | Admin | Token listo |
| 5 | Crear 3 grupos Telegram, agregar bot, obtener IDs | Admin | Grupos listos |
| 5-7 | Probar leer/escribir Sheets desde script Python | Admin | Conexión API validada |

**Costo:** $0  
**Bruno corre:** No, solo preparación manual

---

### FASE 1: Inventario + Alertas Básicas (Semana 2-3)

| Paso | Qué se instala/configura | Qué hace Bruno | Validación |
|---|---|---|---|
| 1.1 | Docker Compose en EasyPanel: Hermes + config Kimi API | Bruno está vivo en VPS | `hermes --version` funciona |
| 1.2 | Configurar Bruno con token Telegram, IDs de grupos | Bruno puede leer/escribir en grupos | Manda mensaje de prueba en cada grupo |
| 1.3 | Skill `inventario_basico.md`: leer Sheet, comparar vs. mínimos | Cuando alguien reporta en grupo, Bruno guarda y alerta si bajo | María reporta "Pollo 12kg", Bruno responde OK o BAJO |
| 1.4 | Cron cada 30 min: revisar Sheet, alertar stock crítico | Bruno avisa solo sin que nadie pregunte | Stock de algo baja a crítico, Bruno alerta en 30 min |
| 1.5 | Comandos `/reportar`, `/inventario`, `/alertas` | Colaboradores usan Telegram, no tocan Sheet | Luis usa `/reportar cerveza 18 cajas`, Bruno guarda |

**Costo:** ~$10-15 (Kimi API uso inicial)  
**Bruno hace:** Lee inventario, alerta stock bajo, responde comandos básicos  
**Bruno NO hace:** Aún no explica diferencias, no cruza ventas, no recordatorios proactivos

---

### FASE 2: Ventas + Cruce Recetas/Consumo (Semana 4-5)

| Paso | Qué se configura | Qué hace Bruno | Validación |
|---|---|---|---|
| 2.1 | Conectar Gmail API a Bruno | Lee cierres de caja | Bruno extrae monto, tickets, recetas vendidas |
| 2.2 | Tabla `VENTAS_DIARIAS` se alimenta automático desde Gmail | Guarda ventas sin que nadie escriba | Cierre de caja llega a Gmail, Bruno aparece en Sheet |
| 2.3 | Skill `diferencias.md`: calcular consumo teórico vs. real | Bruno detecta desfase y explica por qué | Desfase de 8oz carne, Bruno presenta 4 hipótesis |
| 2.4 | Alerta automática 22:00 en grupo "Inventario" | Resumen diario con diferencias explicadas | Grupo ve resumen claro, no raw data |
| 2.5 | Reenvío de órdenes sugeridas a grupo "Administrativo" | Bruno propone, Admin aprueba | Orden carne 10kg aparece en Admin, Andrea dice "aprobar" |

**Costo:** ~$15-20 (más uso Kimi, análisis de diferencias consume más tokens)  
**Bruno hace:** Cruza ventas vs. inventario, explica desfases, sugiere órdenes  
**Bruno NO hace:** Aún no recordatorios proactivos de calendario, no asistencia

---

### FASE 3: Recordatorios Proactivos + Asistencia (Semana 6-7)

| Paso | Qué se configura | Qué hace Bruno | Validación |
|---|---|---|---|
| 3.1 | Tabla `EVENTOS_CALENDARIO` + skill `recordatorios.md` | Bruno sabe qué pasa cuándo | Eventos llenados, Bruno alerta el día que toca |
| 3.2 | Cron 08:00: resumen mañana en grupo "Team" | Cumpleaños, pagos, planilla, asistencia | Equipo recibe resumen sin preguntar |
| 3.3 | Tabla `ASISTENCIA` (nueva) | Registro diario presente/ausente | Encargado marca asistencia, Bruno calcula |
| 3.4 | Skill `planilla.md`: revisar días trabajados, flags faltas | "Juan faltó martes sin justificar" | Bruno detecta anomalía antes de liquidar |
| 3.5 | Comandos `/asistencia`, `/vacaciones`, `/cumpleaños`, `/planilla` | Equipe consulta sin molestar a Admin | María pregunta `/vacaciones`, Bruno responde |

**Costo:** ~$20-25 (más tokens por análisis de asistencia, eventos)  
**Bruno hace:** Recordatorios proactivos, revisa asistencia, prepara planilla  
**Bruno NO hace:** Aún no Postgres, todo en Sheets. No liquidaciones automáticas.

---

### FASE 4: Postgres + Escalabilidad (Mes 2-3)

| Paso | Qué se instala | Por qué | Validación |
|---|---|---|---|
| 4.1 | Postgres en VPS (EasyPanel tiene botón) | Sheets es lento con muchos datos, Postgres es robusto | Consultas instantáneas, no 5 segundos |
| 4.2 | Migrar tablas maestras a Postgres: empleados, recetas, eventos | Datos estructurados, relaciones, búsqueda rápida | Bruno responde más rápido |
| 4.3 | Sheets queda como interfaz de entrada (escritura) + vistas (lectura) | Tu gente sigue usando lo mismo, Bruno usa Postgres por detrás | Sin cambio para colaboradores |
| 4.4 | Skill `liquidacion.md`: calcular liquidación basada en días, horas, faltas | Bruno presenta borrador, Admin revisa y aprueba | Planilla quincenal lista en 2 min, no 2 horas |
| 4.5 | Histórico completo: ventas, inventario, asistencia desde inicio | Tendencias, predicciones, "abril vs. abril" | Admin pregunta "¿cómo íbamos hace un año?", Bruno sabe |

**Costo:** ~$20-25 (Kimi) + $0 (Postgres en mismo VPS)  
**Bruno hace:** Todo lo anterior, más rápido, con histórico, liquidaciones borrador  
**Bruno NO hace:** Aún no Ollama local, sigue en Kimi API

---

### FASE 5: Ollama en VPS Dedicado (Mes 3-4, opcional)

| Paso | Qué se hace | Por qué | Costo nuevo |
|---|---|---|---|
| 5.1 | VPS Hetzner CX32 ($7.40/mes) | RAM 8GB para Ollama local | $7.40/mes |
| 5.2 | Instalar Ollama + Llama 3.2 8B | Cerebro local, gratis, más rápido, sin depender de internet a Moonshot | $0 |
| 5.3 | Migrar Bruno: copiar skills, memory, config | Mismo Bruno, modelo cambia de Kimi a Ollama | $0 |
| 5.4 | Kimi queda como fallback (opcional) | Si Ollama cae o no entiende algo complejo | ~$5/mes ocasional |

**Costo total:** ~$7.40 (VPS) + ~$5 (Kimi fallback) = ~$12.40/mes  
**Ventaja:** Bruno responde en 200ms, no 2 segundos. Funciona aunque caiga internet a Kimi.

---

## 11. Resumen: Qué hace Bruno en cada Fase

| Capacidad | Fase 0 | Fase 1 | Fase 2 | Fase 3 | Fase 4 | Fase 5 |
|---|---|---|---|---|---|---|
| Leer inventario Sheet | Manual | ✅ Auto | ✅ Auto | ✅ Auto | ✅ Auto | ✅ Auto |
| Alertar stock bajo | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Guardar desde Telegram | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Leer ventas Gmail | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Cruzar ventas vs. consumo | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Explicar diferencias | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Generar órdenes sugeridas | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Recordatorios proactivos | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Revisar asistencia | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Preparar planilla borrador | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Postgres maestro | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Histórico completo | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Ollama local (rápido, offline) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 12. Costos Acumulados

| Fase | Kimi API | VPS | Postgres | Total mensual |
|---|---|---|---|---|
| 0 | $0 | $0 (ya tienes) | $0 | $0 |
| 1 | ~$10-15 | $0 | $0 | ~$10-15 |
| 2 | ~$15-20 | $0 | $0 | ~$15-20 |
| 3 | ~$20-25 | $0 | $0 | ~$20-25 |
| 4 | ~$20-25 | $0 | $0 | ~$20-25 |
| 5 | ~$5 (fallback) | ~$7.40 (Hetzner) | $0 | ~$12.40 |

---

## 13. Migración a VPS Propio (cuando toque)

Bruno guarda todo en archivos locales. Migrar es copiar y pegar:

```bash
# En VPS actual (Kimi)
mkdir -p /tmp/bruno-backup
cp -r ~/.hermes/skills /tmp/bruno-backup/
cp -r ~/.hermes/memory /tmp/bruno-backup/
cp ~/.hermes/config.json /tmp/bruno-backup/
cp ~/.hermes/bruno/*.json /tmp/bruno-backup/ 2>/dev/null
cd /tmp && tar -czvf bruno-migracion.tar.gz bruno-backup/

# Descargar a PC
scp root@VPS_ACTUAL:/tmp/bruno-migracion.tar.gz ~/Desktop/

# En VPS nuevo (Ollama)
# Instalar Ollama + Hermes
# Restaurar backup
# Cambiar config: provider de "kimi" a "ollama"
# Listo. Mismo Bruno, mismos skills, misma memoria.
```

---

*Documento creado: 2026-04-26*  
*Versión: 2.0 (Bruno)*  
*Estado: Pendiente aprobación para proceder a Fase 0*
