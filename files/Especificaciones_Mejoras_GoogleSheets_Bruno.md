# 🔄 ANÁLISIS REVISADO - SISTEMA DE INVENTARIO CON AGENTE
## Casa Antigua - Contexto Real (Conteo Manual + Agente de IA)

**Fecha:** 02/05/2026  
**Contexto:** Sistema manual diario + Agente de IA leyendo cierres + Reportes a Telegram  
**Plataforma:** Google Sheets  

---

## 📋 CONTEXTO OPERATIVO ACTUAL

✅ **Lo que ya funciona:**
1. Team llena **conteo manual diario** en "Inventario" (inevitable, necesario)
2. **Agente de IA** lee cierres diarios y compara con catálogo de productos
3. Agente reporta a **grupos de Telegram** (ya implementado)
4. Admin recibe **cierres auditados** diarios
5. Sistema base sirve para **múltiples insumos** (bebidas, pizza, sushi, etc.)

⚠️ **Problema actual:**
- Tabla "Bruno" es una **lista de recetas** (valiosa pero incompleta)
- No hay columna que permita al **agente comparar** venta real vs composición esperada
- No hay **consolidación de datos** desde múltiples insumos
- Difícil escalar a pizza, sushi sin cargar la tabla

---

## 🎯 QUÉ MANTENER, QUÉ MEJORAR, QUÉ IMPLEMENTAR

### ✅ MANTENER (No tocar - funcionan bien)

1. **Estructura de Catálogo Inventario**
   - ID_PRODUCTO + NOMBRE + CATEGORIA + PROVEEDOR
   - OZ_POR_UNIDAD (conversiones)
   - STOCK_MIN (niveles de alerta)
   - **Razón:** Base sólida, no hay razón para cambiar

2. **Conteo manual diario en "Inventario"**
   - Team llena unidades físicas por día
   - Una columna por día (fecha en header)
   - **Razón:** Es el punto de verdad; inevitable en restaurante

3. **Rol del Agente de IA leyendo cierres**
   - Agente extrae datos de cierres diarios
   - Compara con catálogo
   - Reporta a Telegram
   - **Razón:** Automatización valiosa; mantener tal cual

4. **Formato de Composición en Bruno** (REC_044 Margarita)
   ```
   HIE_033:4:oz|JUG_039:1.5:oz|LIC_057:2:oz
   ```
   - Estructura clara: ID_PRODUCTO:CANTIDAD:UNIDAD|ID_PRODUCTO:...
   - **Razón:** Agente puede parsear fácilmente

---

### 🔧 MEJORAR INMEDIATAMENTE (Alto impacto, bajo esfuerzo)

#### 1. **Agregar columna "COSTO_UNITARIO" al Catálogo**
```
Catalogo Inventario (nueva columna después de OZ_POR_UNIDAD):

ID_PRODUCTO | NOMBRE | CATEGORIA | UNIDAD_COMPRA | OZ_POR_UNIDAD | COSTO_UNITARIO | TIPO_MEDICION | STOCK_MIN

CER_001 | Boreal | Cervezas | caja_12 | 1 | 15 | unidad | 6
LIC_045 | Aliwen | Licores | botella_750ml | 25.36 | 450 | oz | 680
JUG_034 | Conc. Guayaba | Jugos | galón | 128 | 25 | oz | 64
```

**Beneficio:**
- Agente calcula COGS por venta: Margarita Clásica = (4 oz hielo × $0.05) + (1.5 oz limón × $2) + (2 oz ron × $18) = ~$39
- Admin ve margen real por bebida
- Permite decisiones de compra inteligentes

**Requiere:** Team actualice costo cada vez que compre (1x semana, 5 min)

---

#### 2. **Crear hoja "SALIDAS" (vinculada a cierres diarios)**
```
Estructura:
FECHA | ID_PRODUCTO | NOMBRE | CANTIDAD_VENDIDA | UNIDAD | ID_RECETA | NOMBRE_RECETA

2026-05-02 | GAS_021 | Canada Dry Verde | 3 | unidad | REC_001 | Canada Dry Azul
2026-05-02 | JUG_039 | Jugo limón | 1.5 | oz | REC_044 | Margarita Clásica
2026-05-02 | LIC_057 | Reposado | 2 | oz | REC_044 | Margarita Clásica
```

**Razón:**
- Agente **extrae esto del cierre diario** (ya está haciendo)
- Permite calcular inventario teórico: Inv_Teórico = Inv_Anterior + Entradas - Salidas
- Comparar Inv_Teórico vs Inv_Físico = Discrepancia (merma, hurto, error)

**Beneficio:**
- Detecta problemas **mismo día** (no al cierre mensual)
- Si Margarita Clásica gastó 50 oz limón pero tenías 30 → ALERTA
- Si Canada Dry vendió 50 botellas pero sistema solo restó 30 → FRAUDE

**Requiere:** Agente llene SALIDAS con datos que ya extrae (mismo esfuerzo, mejor estructura)

---

#### 3. **Mejorar tabla "Bruno" (Recetas) - Agregadas las faltantes**
```
Actualmente:
- 62 recetas definidas
- 15+ están incompletas (sin COMPOSICION)
- Mixtura de "Directo" y "Receta" sin criterio claro

Propuesta:
REC_ID | NOMBRE_ITEM | TIPO | COMPOSICION | PRECIO_VENTA | MARGEN_TARGET | NOTAS

REC_001 | CANADA DRY AZUL | Directo | GAS_021:1:unidad|HIE_033:4:oz | 55 | 60% | Se vende con hielo
REC_009 | GASIFICADA MANDARINA | Receta | GAS_028:0.75:unidad|JUG_036:0.25:oz|HIE_033:4:oz | 48 | 65% | Custom mix
REC_015 | CAFE | Receta | POL_001:5:g|LIQ_CAFE:200:ml|POL_AZUCAR:1:cucharada | 35 | 70% | Café espresso
```

**Beneficio:**
- Team sabe qué vender y a qué precio
- Agente extrae COMPOSICION exacta por venta
- Permite auditar margen real vs margen target

**Requiere:** Completar 15+ recetas faltantes (2-4 hrs)

---

#### 4. **Agregar categoría de INSUMOS para Pizza y Sushi (sin cargar tabla)**
```
Estructura modular:

Catálogo Inventario:
- BEBIDAS: CER_001...LIC_062 (ya existe)
- PIZZA_INSUMOS: PAN_001, SAL_001, QUESO_001, etc. (nueva sección)
- SUSHI_INSUMOS: ARR_001, ALG_001, SAL_001, etc. (nueva sección)
- POSTRES: POS_064...POS_069 (ya existe)

Bruno:
- BEBIDAS: REC_001...REC_062 (ya existe)
- PIZZA: REC_100...REC_120 (nueva sección, misma tabla)
- SUSHI: REC_200...REC_230 (nueva sección, misma tabla)

SALIDAS (mismo formato para todos):
ID_PRODUCTO | CANTIDAD | UNIDAD | ID_RECETA | TIPO_INSUMO
```

**Beneficio:**
- Una sola estructura para todo
- Escalable sin rediseño
- Admin ve todo en un dashboard unificado

**Requiere:** Definir insumos de pizza/sushi (1 hora por tipo)

---

### 🚀 IMPLEMENTAR (Nuevo, máximo impacto)

#### 5. **Crear hoja "DASHBOARD" (resumen en vivo para admin)**
```
Estructura:

ENCABEZADO:
Hoy: XX/XX/2026 | Responsable conteo: [nombre] | Última actualización: 14:32

SECCIÓN 1 - BEBIDAS:
Producto | Inv. Actual | Stock Min | % Stock | Status | COGS hoy | Margen %
Canada Dry Verde | 48 | 12 | 400% | ✅ | $120 | 65%
Boreal | 5 | 6 | 83% | ⚠️ BAJO | $50 | 62%
Victoria | 1 | 24 | 4% | 🔴 CRÍTICO | $10 | 55%

SECCIÓN 2 - DISCREPANCIAS:
Fecha | Producto | Inv. Física | Inv. Teórica | Diferencia | % | Estado
2026-05-02 | Hielo | 2 gal | 3.5 gal | -1.5 | -43% | INVESTIGAR
2026-05-02 | Limón | 12 oz | 20 oz | -8 | -40% | NORMAL (evaporación)

SECCIÓN 3 - RENTABILIDAD HOY:
Bebida | Unidades | COGS Total | Precio Total | Margen Neto | Margen %
Margarita Clásica | 12 | $390 | $660 | $270 | 41%
Canada Dry Azul | 24 | $300 | $1,320 | $1,020 | 77%

SECCIÓN 4 - PIZZAS/SUSHI (mismo formato)
```

**Cómo se llena automáticamente:**
- Hoja INVENTARIO (conteo manual) → DASHBOARD tira datos
- Hoja SALIDAS (agente extrae) → DASHBOARD calcula discrepancia
- Catálogo (COSTO_UNITARIO) → DASHBOARD calcula COGS

**Beneficio:**
- Admin abre **1 hoja** cada mañana
- Ve todo en **30 segundos**
- Detecta problemas **mismo día**
- Toma decisiones de compra inteligentes

**Requiere:** 
- Fórmulas en Google Sheets (VLOOKUP, SUMIF, etc.) → 6-8 hrs
- Agente debe llenar SALIDAS diario (ya lo hace)

---

#### 6. **Automatizar llenado de Entrada (si proveedores pasan OC por email/WhatsApp)**
```
Actualmente: Entrada está vacía (no sé qué entra cada día)

Propuesta: Si proveedor envía "Entramos 3 cajas Toña + 2 Boreal + 5 gal jugo"
→ Team llena en ENTRADA:
  CER_008 (Toña) | 3 | caja_24
  CER_001 (Boreal) | 2 | caja_12
  JUG_037 (Jamaica) | 5 | galón

Fórmula en INVENTARIO:
  Inventario_Hoy = Inventario_Ayer + Entrada_Hoy - Salidas_Hoy (parsed desde recetas vendidas)
```

**Beneficio:**
- Cierre = Inventario Actual + Costo - (COGS vendido)
- Reconciliación con costo contable
- Detecta faltantes o excedentes

**Requiere:**
- Team llene Entrada si hay compra (5 min/día)
- O: Automatizar via Telegram bot (opción premium)

---

#### 7. **Integración con Telegram Bot para captura en vivo (Opcional pero potente)**
```
Admin envía al bot cada venta:
/venta Margarita Clásica 2
/venta Canada Dry 5
/cierre 18:00

Bot → Google Sheets SALIDAS + CIERRE automáticamente
→ Agente lee y reporta
→ Dashboard se actualiza en vivo
```

**Beneficio:**
- Zero fricción
- Datos en tiempo real
- Agente tiene información limpia y estructurada

**Requiere:**
- Python bot + Google Sheets API (1-2 días de desarrollo)
- O: Usar Zapier/Make (automación sin código, $50-100/mes)

---

## 📊 PRIORIDADES PARA EL EQUIPO (Bruno, desarrollador)

### URGENTE (Esta semana)

1. **Agregar COSTO_UNITARIO a Catálogo** (1 hora)
   - Espacio: Nueva columna después de OZ_POR_UNIDAD
   - Datos: Team proporciona precios de últimas facturas
   - Validación: Editar protegido (solo admin puede cambiar)

2. **Completar Bruno - Recetas faltantes** (2-4 hrs)
   - 15 recetas están vacías (COMPOSICION = blanco)
   - Validar con camarero/chef: ¿Cuánta medida exacta cada ingrediente?
   - Llenar COMPOSICION para las 15 faltantes
   - Ejemplo: REC_015 CAFE → JUG_CAFE:200:ml|POL_AZUCAR:1:cucharada

3. **Crear hoja SALIDAS** (2 hours)
   - Headers: FECHA | ID_PRODUCTO | NOMBRE | CANTIDAD | UNIDAD | ID_RECETA | NOMBRE_RECETA
   - Formatear: Dropdown para ID_PRODUCTO (valida contra Catálogo)
   - Protección: Solo lunes-domingo, rango de hoy + 6 meses

4. **Crear hoja DASHBOARD básico** (4 hrs)
   - Sección 1: Estado de inventario (Actual, Min, % Stock, Status)
   - Sección 2: Discrepancias hoy (Física vs Teórica)
   - Fórmulas: VLOOKUP + SUMIF + IF para status
   - Formato: Código de colores (verde OK, amarillo BAJO, rojo CRÍTICO)

---

### ALTO (2-4 semanas)

5. **Estructura multi-insumo sin cargar tabla**
   - Agregar secciones en Catálogo: PIZZA_INSUMOS (10-20 ítems) + SUSHI_INSUMOS (15-25 ítems)
   - Agregar secciones en Bruno: PIZZA (10-15 recetas) + SUSHI (10-15 recetas)
   - **No** crear hojas separadas → todo en tablas existentes con CATEGORIA para filtrar

6. **Completar SALIDAS con datos históricos** (si agente ya capturó)
   - Agente retroalimenta abril-mayo con cierres diarios
   - Llenar SALIDAS con ventas reales
   - Validar: Inv_Teórico vs Inv_Físico → detectar donde hay discrepancias

7. **Expandir DASHBOARD a múltiples insumos**
   - Pestañas o filtros para BEBIDAS | PIZZA | SUSHI | POSTRES
   - Mantener mismo formato (Stock, COGS, Margen)

---

### MEDIO (4-8 semanas)

8. **Entrada automatizada**
   - Si hay flujo de entregas consistente, llenar ENTRADA desde órdenes de compra
   - Fórmula en INVENTARIO: = Anterior + SUMIF(ENTRADA, ID_PRODUCTO) - SUMIF(SALIDAS, ID_PRODUCTO)

9. **Telegram Bot para captura en vivo** (Optional pero valuable)
   - Agente reporta cierres
   - Agente también captura /venta [producto] [cantidad]
   - Google Sheets se alimenta en vivo

---

## 🔍 PREGUNTAS PARA EL EQUIPO (Bruno)

Antes de implementar, necesito claridad:

### Para definir SALIDAS:

1. **¿Cómo extrae agente datos del cierre diario?**
   - ¿Lee POS/caja registradora?
   - ¿Lee formulario manual que llena staff?
   - ¿Lee chat/Telegram?
   - **Razón:** Quiero saber qué datos están disponibles y en qué formato

2. **¿Qué precisión de datos tiene?**
   - ¿Sabe EXACTAMENTE cuántas Margaritas se vendieron hoy?
   - ¿O solo sabe "bebidas mixtas = ~50 oz licor"?
   - **Razón:** Impacta qué podemos auditar

3. **¿Qué información da admin al cierre?**
   - ¿Solo $ total vendido?
   - ¿Desglose por categoría (bebidas=$500, pizzas=$800)?
   - ¿Desglose por producto (Margarita 12×, Cerveza 30×)?
   - **Razón:** Define granularidad de SALIDAS

### Para definir COMPOSICION:

4. **¿Hay estándar de medidas?**
   - ¿Margarita siempre = 4 oz hielo, 1.5 oz limón, 2 oz ron?
   - ¿O varía por camarero?
   - **Razón:** Saber si COMPOSICION es fija o hay variación

5. **¿Pizza y Sushi tienen recetas definidas?**
   - ¿Qué gramos de queso = 1 pizza?
   - ¿Qué gramos de arroz = 1 rollo de sushi?
   - **Razón:** Saber qué llenar en COMPOSICION para no-bebidas

### Para priorizar:

6. **¿Cuál es la bebida/pizza/sushi que más $ genera?**
   - Top 3 por ingresos
   - **Razón:** Enfocar auditoría en los que importan más

7. **¿Hay productos con hurto sospechoso o merma alta?**
   - ¿Hielo desaparece rápido?
   - ¿Licores "se pierden"?
   - **Razón:** Priorizar donde poner controles

8. **¿Qué información visualiza admin diariamente actualmente?**
   - ¿Abre el Excel/Sheets?
   - ¿Solo lee Telegram del agente?
   - **Razón:** Conocer qué tan usado será el DASHBOARD

---

## 📝 CHECKLIST DE ESPECIFICACIONES PARA BRUNO

Si Bruno va a mejorar las tablas, dale esto:

### 1. CATÁLOGO INVENTARIO (Mejorado)
```
Agregar columna G (después de OZ_POR_UNIDAD):

Nombre: COSTO_UNITARIO
Tipo: Currency (C$)
Protección: Editable solo para Admin
Validación: > 0
Descripción: "Precio de compra unitario (caja o galón, según UNIDAD_COMPRA)"

Ejemplo:
CER_001 | Boreal | Caja_12 | 1 | 15 | unidad | 6 | TRUE
          (cuesta C$15 la caja)

JUG_034 | Conc. Guayaba | Galón | 128 | 25 | oz | 64 | TRUE
          (cuesta C$25 el galón)
```

### 2. HOJA NUEVA: "SALIDAS"
```
Headers (Row 1):
A: FECHA (date, formato DD/MM/YYYY)
B: ID_PRODUCTO (dropdown → valida contra Catálogo.ID_PRODUCTO)
C: NOMBRE_PRODUCTO (VLOOKUP desde Catálogo)
D: CANTIDAD (number)
E: UNIDAD (dropdown: "unidad" o "oz", valida contra Catálogo.TIPO_MEDICION)
F: ID_RECETA (dropdown → valida contra Bruno.ID_ITEM)
G: NOMBRE_RECETA (VLOOKUP desde Bruno)
H: NOTAS (optional, texto)

Rango de datos: 2-1000 (365 días × ~2-3 ventas/producto/día)
Protección: Solo puede editar Team (no puede borrar filas)
Formato: Colores alternados (gris claro cada 10 filas para legibilidad)

Validación:
- FECHA no puede ser futura
- CANTIDAD > 0
- UNIDAD = Catálogo.TIPO_MEDICION (si GAS_021 es "unidad", solo aceptar "unidad")
```

### 3. HOJA NUEVA: "DASHBOARD"
```
Estructura:

CABECERA (Row 1-5):
A1: "DASHBOARD DIARIO"
A2: =TODAY() (formateado "XX de [mes] de 2026")
A3: "Último conteo:" [hora]
A4: "Responsable: [dropdown team]"

SECCIÓN 1: INVENTARIO ACTUAL (Row 7-35)
Headers (Row 7):
A7: Producto
B7: Inventario Actual (oz o unidad)
C7: Stock Mínimo
D7: % Stock
E7: Estado (fórmula IF)
F7: COSTO Invertido (Inv * Precio)

Datos (Rows 8-35): VLOOKUP + SUMIF desde hojas INVENTARIO + CATÁLOGO
Colores: 
  - Verde: % Stock > 100%
  - Amarillo: 50% < % < 100%
  - Rojo: % Stock < 50%

SECCIÓN 2: DISCREPANCIAS HOY (Row 37-50)
Headers (Row 37):
A37: Producto
B37: Inv. Física (última entrada en INVENTARIO)
C37: Inv. Teórica (anterior + entradas - salidas)
D37: Diferencia (B-C)
E37: % Diferencia
F37: Estado (si >5% = INVESTIGAR)

Datos: SUMIF desde ENTRADA + SALIDAS

SECCIÓN 3: RENTABILIDAD HOY (Row 52-70)
Headers:
A52: Receta
B52: Unidades Vendidas
C52: COGS Total (B * Costo)
D52: Precio Total Teorico (B * Precio_Venta)
E52: Margen Bruto
F52: Margen %

Datos: SUMIF desde SALIDAS + BRUNO + CATÁLOGO

SECCIÓN 4: ALERTAS CRÍTICAS (Row 72-80)
Listar solo:
- Productos bajo stock min (rojo)
- Discrepancias >10%
- Rotación muy lenta (inv > 30 días consumo)

Formato: Bullet points, fondo rojo/amarillo
```

### 4. BRUNO (Tabla de Recetas - Mejorada)
```
Agregar columnas:
I: PRECIO_VENTA (Currency, precio venta al público)
J: MARGEN_TARGET (%, margen esperado = 60%, 65%, etc.)
K: COGS_ESPERADO (fórmula: parsea COMPOSICION y multiplica por costo unitario)
L: MARGEN_REAL (PRECIO_VENTA - COGS_ESPERADO)
M: NOTAS (detalles, alérgenos, variaciones)

Validación:
- Si TIPO = "Directo" → COMPOSICION debe tener solo 1 producto
- Si TIPO = "Receta" → COMPOSICION debe tener 2+ productos
- Todas las COMPOSICION deben referenciar IDs válidos del Catálogo

Completar 15 recetas faltantes:
REC_009 GASIFICADA MANDARINA | Receta | GAS_028:0.75:unidad|JUG_036:0.25:oz|HIE_033:4:oz
REC_014 AGUA LUNA | Receta | GAS_020:1:unidad|HIE_033:4:oz
REC_015 CAFE | Receta | POL_CAFE:5:g|JUG_HOT:200:ml|POL_AZUCAR:1:cucharada
... (resto)
```

---

## 🎁 BENEFICIO FINAL PARA ADMIN/AGENTE

Con estas mejoras:

**Admin:**
- Abre DASHBOARD mañana
- Ve: 3 cervezas bajo stock (amarillo), 1 bebida mixta con margen bajísimo (investigar receta), discrepancia de 15% en hielo (merma normal)
- Toma decisión en 2 minutos: "Comprar 2 cajas Heineken hoy"

**Agente:**
- Sigue reportando a Telegram (sin cambio)
- Ahora sus datos alimentan SALIDAS automáticamente
- DASHBOARD genera reportes semanales: "Margarita rentabilidad bajó 8% (posible error en medidas)"
- Permite auditar: "Vendimos 50 Margaritas → deberían gastar 200 oz limón, pero gastamos 150"

**Team (conteo):**
- Sigue llenando conteo manual (no cambia)
- Ahora ven DASHBOARD: "Boreal bajo stock, próximo turno pedir reposición"

**Restaurante:**
- Margen real por bebida (sabe si Margarita a $60 es rentable o no)
- Detección de problemas same-day (no al cierre mensual)
- Base escalable para pizza, sushi, postres sin rediseño
- ROI: recupera inversión en 2 meses por reducción de merma + hurto

---

## ✅ RESUMEN: QUÉ PEDIRLE A BRUNO

**ESTA SEMANA:**
1. Agregar COSTO_UNITARIO a Catálogo
2. Completar 15 recetas vacías en Bruno
3. Crear hoja SALIDAS
4. Crear hoja DASHBOARD (básico)

**PRÓXIMAS 2 SEMANAS:**
5. Validaciones y protecciones en hojas

**PRÓXIMO MES:**
6. Agregar PIZZA_INSUMOS y SUSHI_INSUMOS al Catálogo
7. Expandir DASHBOARD a múltiples insumos

**Costo:** 0 (es mejora de lo que ya existe)  
**Tiempo implementación:** 8-12 horas (Bruno puede hacer 2-3 hrs/día)  
**Beneficio:** Visibilidad 100% + auditoría automática + escalabilidad

---

*Documento para compartir con Bruno (desarrollador de tablas)*
