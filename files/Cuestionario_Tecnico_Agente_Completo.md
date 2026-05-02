# 🔍 CUESTIONARIO TÉCNICO COMPLETO - AGENTE DE INVENTARIO
## Casa Antigua - Análisis de Arquitectura e Integración

**Objetivo:** Entender flujo completo, APIs, integraciones y limitaciones técnicas para hacer recomendaciones precisas.

---

## SECCIÓN 1: VISIÓN GENERAL DEL AGENTE

### 1.1 ¿Cuál es el objetivo principal del agente?
- [ ] **Leer cierres diarios y generar reportes**
  - ¿Qué datos extrae exactamente del cierre? (montos, productos, cantidades?)
  - ¿Qué formato tiene el cierre? (PDF, imagen, texto, archivo)?
  - ¿Dónde se guarda el cierre? (Email, WhatsApp, Google Drive, servidor?)
  - ¿Cada cuánto se genera? (1×/día, 2×/día, fin de semana?)

- [ ] **Comparar ventas vs composición de bebidas**
  - ¿Busca validar que las medidas sean correctas?
  - ¿Detecta cuando una bebida usa más ingredientes de lo normal?
  - ¿Genera alertas si hay desviación?

- [ ] **Auditar diferencias entre inventario teórico y físico**
  - ¿Calcula: Inv_Teórica = Anterior + Entrada - (Salidas por recetas)?
  - ¿Compara con Inv_Física (lo que team contó)?
  - ¿Reporta diferencias? (merma, fraude, error)

- [ ] **Otro:** ________________________

---

## SECCIÓN 2: FUENTES DE DATOS (¿De dónde obtiene información?)

### 2.1 ¿Cómo obtiene los datos del cierre diario?

**Opción A: Email**
- [ ] Lee emails de una dirección específica
  - ¿De quién? (gerente, camarero, sistema POS?)
  - ¿Cada cuánto llegan? (10am, 6pm, 11pm?)
  - ¿Qué formato? (PDF adjunto, tabla en body, imagen?)
  - ¿Qué información contiene?
    - [ ] Montos totales por categoría (bebidas, pizzas, etc)
    - [ ] Desglose por producto individual (Margarita×12, Cerveza×30)
    - [ ] Horarios de venta (10am-12pm: $xxx)
    - [ ] Nombre camarero/operador
    - [ ] Fecha/hora del cierre
  - ¿Cuál es la dirección Gmail? (agent@..., casa-antigua@..., etc)
  - ¿Quién envía? (¿puede ser cualquiera o solo direcciones autorizadas?)

**Opción B: Google Sheet**
- [ ] Lee datos de hoja específica
  - ¿Cuál es la URL del Sheet?
  - ¿Qué permisos tiene? (solo lectura, lectura+escritura?)
  - ¿Qué columnas lee?
    - [ ] Fecha
    - [ ] Producto
    - [ ] Cantidad
    - [ ] Precio
    - [ ] Responsable
    - [ ] Timestamp
  - ¿Con qué frecuencia verifica? (tiempo real, cada hora, cada 30min?)
  - ¿Tiene triggers? (ONCHANGE, ONTIME, ONAPPSCRIPT?)

**Opción C: API de POS (Square, Toast, etc)**
- [ ] Conecta a sistema de caja
  - ¿Cuál es el POS? (Square, Toast, Lightspeed, otro?)
  - ¿Qué endpoints usa?
  - ¿Qué información extrae?
    - [ ] Transacciones completas
    - [ ] Items vendidos (with SKU)
    - [ ] Montos y cambio
    - [ ] Camarero/operador
    - [ ] Mesa/ticket
  - ¿Qué permisos tiene? (read-only?)
  - ¿Frecuencia de consulta?

**Opción D: WhatsApp/Telegram del operador**
- [ ] El camarero/gerente envía mensaje directo
  - ¿A qué número/chat?
  - ¿Qué formato? ("Cerveza: 30, Margarita: 12")
  - ¿El agente parsea texto libre o espera formato estructurado?

**Opción E: Google Drive (carpeta compartida)**
- [ ] Agente monitorea carpeta de cierres diarios
  - ¿Qué carpeta?
  - ¿Qué formatos? (XLSX, CSV, PDF, imagen?)
  - ¿Cómo detecta archivo nuevo? (busca por fecha, por patrón de nombre?)

**Opción F: Otro:** ________________________

---

### 2.2 ¿Cómo obtiene el inventario físico (conteo manual)?

- [ ] **Lee directamente de Google Sheet "Inventario"**
  - ¿Con qué frecuencia? (en tiempo real, 1×/hora, al cierre?)
  - ¿Qué columna usa? (última fecha con datos, última actualización?)
  - ¿Lee solo bebidas o todos los insumos?

- [ ] **Team envía por email/mensaje**
  - ¿Formato? ("Boreal: 14, Victoria: 73, ...")
  - ¿Cuándo se envía? (después de conteo a las 6pm?)

- [ ] **Otro método:** ________________________

---

### 2.3 ¿Cómo obtiene el catálogo de productos y recetas?

- [ ] **Lee de Google Sheet "Catálogo Inventario" y "Bruno"**
  - ¿Con qué frecuencia? (una sola vez al iniciar, recarga cada hora?)
  - ¿Qué carga?
    - [ ] ID_PRODUCTO + NOMBRE
    - [ ] OZ_POR_UNIDAD (conversiones)
    - [ ] COSTO_UNITARIO (si existe)
    - [ ] STOCK_MIN
  - ¿Qué carga de Bruno?
    - [ ] ID_RECETA + NOMBRE
    - [ ] TIPO (Directo vs Receta)
    - [ ] COMPOSICION (HIE_033:4:oz|JUG_039:1.5:oz|LIC_057:2:oz)

- [ ] **Lo tiene hardcodeado en código**
  - ¿Cómo se actualiza cuando hay productos nuevos?
  - ¿Cada cuánto se redeploy el agente?

- [ ] **Otro método:** ________________________

---

## SECCIÓN 3: PROCESAMIENTO DE DATOS (¿Qué hace el agente con los datos?)

### 3.1 Parseo del cierre

**Formato del cierre (ejemplo real):**
```
Por favor enviar formato actual de un cierre:
[Pegar aquí un ejemplo del cierre que agente recibe]
```

- [ ] ¿El agente parsea texto libre?
  - ¿Qué NLP usa? (regex simple, Anthropic API, Google NLP?)
  - ¿Qué tan robusto es? (falla si hay cambios de formato?)
  - ¿Entiende variaciones? ("Cerveza Boreal", "Boreal", "CER_001"?)

- [ ] ¿Espera formato estructurado?
  - ¿Tabla HTML, JSON, CSV?
  - ¿Qué pasa si formato es incorrecto?

- [ ] **¿Qué extrae exactamente?**
  - [ ] Productos vendidos (lista)
  - [ ] Cantidades por producto
  - [ ] Precios unitarios
  - [ ] Total diario
  - [ ] Camarero/responsable
  - [ ] Fecha y hora
  - [ ] Mesas/tickets
  - [ ] Notas (promociones, descuentos?)

### 3.2 Validaciones que realiza

- [ ] **Validación de productos:**
  - ¿Verifica que existan en Catálogo?
  - ¿Qué pasa si detecta producto desconocido?
    - [ ] Lo ignora
    - [ ] Genera alerta
    - [ ] Intenta fuzzy match ("Cervesa" → "Cerveza"?)

- [ ] **Validación de cantidades:**
  - ¿Valida que sean números > 0?
  - ¿Detecta si cantidad es anormalmente alta? (¿Límite?)
  - ¿Detecta si cantidad es irracional? (0.5 cervezas?)

- [ ] **Validación de composición:**
  - ¿Para bebidas mixtas, verifica que haya composición definida en Bruno?
  - ¿Si no la hay, qué hace? (asume una, reporta error?)

- [ ] **Validación de margen:**
  - ¿Calcula margen esperado vs margen real?
  - ¿Genera alerta si margen es anormalmente bajo?

### 3.3 Cálculos que realiza

- [ ] **COGS (Cost of Goods Sold)**
  - Ejemplo: Si se vendió Margarita Clásica = 4oz hielo + 1.5oz limón + 2oz ron
  - ¿El agente calcula costo total?
  - ¿Usa COSTO_UNITARIO del Catálogo?
  - ¿Qué pasa si no existe COSTO_UNITARIO?

- [ ] **Margen**
  - Margen = (Precio Venta - COGS) / Precio Venta × 100
  - ¿Lo calcula? ¿Lo reporta?

- [ ] **Inventario Teórico**
  - Inv_Teórica_Hoy = Inv_Física_Ayer + Entrada_Hoy - Consumo_Hoy
  - ¿El agente lo calcula?
  - ¿Consumo_Hoy = suma de oz/unidades de cada receta vendida?

- [ ] **Discrepancia**
  - Discrepancia = Inv_Física_Hoy - Inv_Teórica_Hoy
  - ¿Lo calcula? ¿Genera alerta si > X%?

- [ ] **Otro cálculo:** ________________________

---

## SECCIÓN 4: SALIDAS (¿Qué hace el agente con los resultados?)

### 4.1 Reportes a Telegram

- [ ] **¿A qué grupo/canal?**
  - ¿ID del grupo?
  - ¿Quiénes reciben? (solo admin, todo el team?)

- [ ] **¿Qué formato tiene el reporte?**
  ```
  Por favor, pegar un ejemplo real de mensaje Telegram:
  [Pegar aquí]
  ```

- [ ] **¿Qué información incluye?**
  - [ ] Resumen de ventas (totales por categoría)
  - [ ] Detalle por producto (Margarita×12, Cerveza×30)
  - [ ] COGS calculado
  - [ ] Margen %
  - [ ] Discrepancias (si Inv_Física ≠ Inv_Teórica)
  - [ ] Alertas (bajo stock, margen bajísimo, etc)
  - [ ] Errores o inconsistencias encontradas

- [ ] **¿Con qué frecuencia?**
  - [ ] Una sola vez al día (cuándo?)
  - [ ] Múltiples veces (cada venta? cada hora?)
  - [ ] Bajo demanda (admin pide "/reporte"?)

- [ ] **¿Formato de mensaje?**
  - [ ] Texto plano
  - [ ] Con emojis
  - [ ] Tabla (HTML, código)
  - [ ] PDF/imagen
  - [ ] Bot con botones interactivos

### 4.2 Otros destinos

- [ ] **¿Escribe en Google Sheet?**
  - ¿Qué hoja? (¿Ya existe o necesita crear?)
  - ¿Qué datos?
    - [ ] FECHA | PRODUCTO | CANTIDAD | PRECIO | COGS | MARGEN
    - [ ] O solo resumen diario?
  - ¿Qué permisos tiene? (append, overwrite, read-only?)

- [ ] **¿Envía emails?**
  - ¿A quién? (admin, gerente, propietario?)
  - ¿Cuándo?
  - ¿Qué información?

- [ ] **¿Genera reportes PDF/Excel?**
  - ¿Dónde se guardan? (Google Drive, email, servidor?)

- [ ] **¿Guarda en base de datos?**
  - ¿Cuál? (Firebase, MySQL, PostgreSQL, MongoDB?)
  - ¿Qué información?

- [ ] **Otro destino:** ________________________

---

## SECCIÓN 5: INFRAESTRUCTURA TÉCNICA (¿Dónde corre y cómo?)

### 5.1 Plataforma del agente

- [ ] **Claude API (Anthropic)**
  - ¿Cuál modelo? (Claude 3 Opus, Sonnet, Haiku?)
  - ¿Qué tipo de llamadas?
    - [ ] Prompts simples (leer + parsear)
    - [ ] Function calling (para estructurar datos)
    - [ ] Análisis de documentos (si lee PDFs/imágenes)
  - ¿Tokens usados por ejecución? (estimado)
  - ¿Costo mensual estimado?

- [ ] **Google Gemini**
  - ¿Cuál modelo? (1.0 Pro, 1.5 Pro, Flash?)
  - ¿Mismas preguntas que arriba?

- [ ] **OpenAI (ChatGPT)**
  - ¿Cuál modelo? (GPT-4, GPT-4o, etc?)

- [ ] **Local (no cloud)**
  - ¿Qué modelo? (Llama, Mistral, otro?)
  - ¿Dónde corre? (servidor propio, contenedor Docker?)

- [ ] **Otro:** ________________________

### 5.2 Dónde está el código

- [ ] **Google Apps Script**
  - ¿El agente corre dentro de Google Sheets?
  - ¿O es un script separado que lee/escribe el Sheet?
  - ¿Triggers? (ONCHANGE, ONTIME, ONAPPSCRIPT?)

- [ ] **Python (servidor propio o cloud)**
  - ¿Dónde? (local, AWS, Google Cloud, Heroku?)
  - ¿Libraries?
    - [ ] google-auth (para acceder Sheets, Drive)
    - [ ] python-telegram-bot (para Telegram)
    - [ ] pdf2image (si parsea PDFs)
    - [ ] Anthropic, OpenAI (para LLM)
  - ¿Es un script que corre una sola vez o servidor 24/7?

- [ ] **Node.js**
  - ¿Dónde?
  - ¿Libraries? (googleapis, telegram-bot-api, etc)

- [ ] **Make/Zapier/Integromat (no-code)**
  - ¿Qué workflows?
  - ¿Costo?

- [ ] **Otro framework:** ________________________

### 5.3 Triggers y scheduling

- [ ] **Cómo inicia el agente:**
  - [ ] Time-based (cada hora, cada día a las 6pm)
  - [ ] Event-based (cuando llega email, cuando se modifica Sheet)
  - [ ] Manual (alguien presiona botón)
  - [ ] Webhook (sistema externo notifica)

- [ ] **¿Cuánto tiempo toma ejecutar?**
  - Desde que obtiene datos → hasta que reporta en Telegram
  - (segundos? minutos?)

- [ ] **¿Qué pasa si falla?**
  - ¿Genera log?
  - ¿Reintenta?
  - ¿Notifica a admin?

---

## SECCIÓN 6: AUTENTICACIÓN Y SEGURIDAD

### 6.1 Google (Sheets, Drive, Gmail)

- [ ] **¿Cómo autentica?**
  - [ ] Service Account (account.json)
  - [ ] OAuth 2.0 (usuario inicia sesión)
  - [ ] API key simple

- [ ] **¿Qué permisos tiene?**
  - [ ] Lectura solo
  - [ ] Lectura + escritura
  - [ ] Solo hoja específica o todo el Drive?

- [ ] **¿Qué información accede?**
  - [ ] Solo "Catálogo", "Bruno", "Inventario", "Entrada"?
  - [ ] O tiene acceso a todo el Google Drive de la empresa?

### 6.2 Telegram

- [ ] **¿Usa Bot Token?**
  - ¿Quién lo generó? (¿está seguro?)
  - ¿Se regeneró alguna vez?

- [ ] **¿Tiene restricciones?**
  - ¿Solo puede escribir o puede leer mensajes también?
  - ¿Solo en un grupo específico?

### 6.3 Email (Gmail)

- [ ] **¿Quién es el remitente?**
  - ¿Google Workspace (company@casaantigua.com)?
  - ¿Gmail personal?

- [ ] **¿Cómo accede?**
  - [ ] Gmail API + credentials
  - [ ] SMTP credentials (inseguro)
  - [ ] Otro

### 6.4 Almacenamiento de secretos

- [ ] **¿Dónde guarda claves/tokens?**
  - [ ] Variables de entorno (.env, no versionado)
  - [ ] Hardcodeadas en código (¡peligro!)
  - [ ] Google Secret Manager
  - [ ] Otro

- [ ] **¿Quién tiene acceso?**
  - ¿Solo desarrollador?
  - ¿Team completo?

---

## SECCIÓN 7: LIMITACIONES CONOCIDAS

### 7.1 Problemas actuales

- [ ] ¿Cuáles son los 3 principales problemas que enfrenta el agente?
  1. ________________________
  2. ________________________
  3. ________________________

### 7.2 Datos incompletos

- [ ] ¿Qué información le gustaría tener pero no tiene?
  - [ ] COSTO_UNITARIO de productos
  - [ ] Composición completa de recetas
  - [ ] Timestamps precisos
  - [ ] Información de entradas (qué compró cada día)
  - [ ] Precios de venta de bebidas
  - [ ] Otro: ________________________

### 7.3 Escalabilidad

- [ ] ¿Si agregamos Pizza y Sushi, qué tendrías que cambiar en el agente?
- [ ] ¿Si volumen de datos se duplica, sigue funcionando?
- [ ] ¿Token limit es un problema? (si usa Claude)

### 7.4 Errores comunes

- [ ] ¿Cuáles son los errores más frecuentes que reporta el agente?
  - [ ] Producto desconocido
  - [ ] Formato incorrecto del cierre
  - [ ] Discrepancia en conteo
  - [ ] Números fuera de rango
  - [ ] Otro: ________________________

---

## SECCIÓN 8: INTEGRACIONES FUTURAS

### 8.1 ¿Qué le falta integrar?

- [ ] **POS/Caja registradora**
  - ¿Cuál sistema usan? (Square, Toast, PAX, otro?)
  - ¿Tienen API?
  - ¿Se puede conectar el agente?

- [ ] **Proveedores**
  - ¿Sistema para órdenes de compra?
  - ¿API de proveedor?

- [ ] **Contabilidad**
  - ¿Usan Xero, QuickBooks, Wave, otro?
  - ¿El agente necesita reportar ahí?

- [ ] **Otro sistema:** ________________________

### 8.2 ¿Reportes que necesitarían del agente?

- [ ] Reporte de margen diario por bebida
- [ ] Reporte de discrepancias semanales
- [ ] Predicción de qué comprar próxima semana
- [ ] Auditoría de camareros (quién tiene mayor merma)
- [ ] Otro: ________________________

---

## SECCIÓN 9: VISIÓN DEL DESARROLLADOR

### 9.1 ¿Cuál es tu objetivo final con este agente?

- [ ] Automatizar cierre diario (ahorrar tiempo manual)
- [ ] Detectar fraude/hurto
- [ ] Auditar margen por bebida
- [ ] Optimizar inventario (compra inteligente)
- [ ] Base para sistema más grande
- [ ] Otro: ________________________

### 9.2 ¿Cuál es el siguiente paso en roadmap?

- [ ] Mejorar precisión del parseo
- [ ] Agregar nuevos insumos (pizza, sushi)
- [ ] Automatizar entradas (órdenes de compra)
- [ ] Dashboard para admin
- [ ] Predicción/ML
- [ ] Otro: ________________________

### 9.3 ¿Recursos disponibles?

- [ ] ¿Presupuesto para herramientas pagas?
- [ ] ¿Tiempo para desarrollo? (hrs/semana)
- [ ] ¿Acceso a APIs de sistemas internos?
- [ ] ¿Equipo técnico de soporte?

---

## SECCIÓN 10: DATOS DE EJEMPLO

### 10.1 Cierre típico

```
Por favor, compartir formato actual de un cierre diario:

[Pegar aquí]
```

### 10.2 Conteo físico típico

```
Cómo actualmente se reporta el conteo físico:

[Pegar aquí]
```

### 10.3 Mensaje Telegram típico

```
Ejemplo de lo que reporta agente actualmente a Telegram:

[Pegar aquí]
```

### 10.4 Información de volúmenes

- ¿Cuántas bebidas se venden/día en promedio?
  - [ ] < 50
  - [ ] 50-100
  - [ ] 100-200
  - [ ] 200-500
  - [ ] 500+

- ¿Cuántos tipos de bebida diferentes se venden/día?
  - [ ] < 10
  - [ ] 10-20
  - [ ] 20-40
  - [ ] 40+

- ¿Cuántos camareros?
  - [ ] 1-2
  - [ ] 3-5
  - [ ] 5-10
  - [ ] 10+

---

## SECCIÓN 11: PREGUNTAS ABIERTAS PARA EL IDE

### 11.1 Flujo exacto

```
Describe paso por paso qué ocurre desde que admin cierra caja hasta que admin recibe reporte en Telegram:

1. [Usuario/sistema dispara el proceso]
2. [El agente obtiene datos de ___]
3. [El agente procesa: ___]
4. [El agente valida: ___]
5. [El agente calcula: ___]
6. [El agente genera reporte: ___]
7. [El agente envía a Telegram con formato: ___]
```

### 11.2 Limitaciones principales

```
¿Cuáles son las 3 cosas que te gustaría que el agente hiciera mejor?

1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

¿Por qué no las implementaste?

1. _______________________________________________
2. _______________________________________________
3. _______________________________________________
```

### 11.3 Métricas

```
¿Qué métrica te importa más?

- Velocidad (cuán rápido procesa)
- Precisión (cuán correcto es el parseo)
- Escalabilidad (qué tan fácil agregar nuevos insumos)
- Costo (cuán barato operar)
- Otro: _______________

¿Actualmente cuál es el valor de esa métrica?

Ejemplo: "Precision: 95% (5% de cierres tienen al menos 1 error)"
```

---

## SECCIÓN 12: SÍNTESIS - INFORMACIÓN CRÍTICA

**Si SOLO pudieras responder una cosa, responde esto:**

```
¿Cuál es el flujo exacto desde que se genera un cierre diario hasta que admin lo ve en Telegram?

Incluir:
- Quién inicia
- Formato de datos
- Dónde se almacenan
- Cómo agente obtiene datos
- Qué procesa exactamente
- Qué reporta
```

---

*Cuestionario para compartir con el IDE que creó el agente*
*Tiempo estimado de respuesta: 1-2 horas (puede responder por secciones)*
