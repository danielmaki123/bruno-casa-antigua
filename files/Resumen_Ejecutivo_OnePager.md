# 🎯 RESUMEN EJECUTIVO - MEJORAS GOOGLE SHEETS
## Casa Antigua - Sistema de Inventario Integrado

---

## ¿QUÉ ESTÁ BIEN? (MANTENER)

✅ Conteo manual diario (Team en Inventario)  
✅ Agente leyendo cierres y reportando  
✅ Catálogo Inventario bien estructurado  
✅ Google Sheets como plataforma  

---

## ¿QUÉ ESTÁ ROTO? (MEJORAR)

❌ **Sin conexión entre datos:**
   - Team llena conteo → Agente lee cierre → Admin lee Telegram
   - Pero **no hay tabla que unifique todo**

❌ **Sin auditoría real:**
   - No hay comparación: Inv. Física vs Inv. Teórica
   - No se detectan pérdidas/mermas/fraude

❌ **Sin rentabilidad:**
   - No sabemos COSTO real de cada bebida (COGS)
   - No sabemos MARGEN real (¿Margarita gana o pierde?)

❌ **Bruno incompleto:**
   - 15 recetas sin composición completa
   - No hay columna de COSTO_UNITARIO
   - No escalable a pizzas/sushi

❌ **Admin sin visibilidad:**
   - No hay DASHBOARD consolidado
   - Lee Telegram = información tardía, fragmentada

---

## ¿QUÉ IMPLEMENTAR? (PRIORIDAD)

### 🔴 ESTA SEMANA (Crítico - 8 horas)

1. **Agregar COSTO_UNITARIO al Catálogo**
   - Columna nueva: Precio que pagó por cada caja/galón
   - Actualizarla 1× semana
   - Permite calcular COGS

2. **Crear hoja SALIDAS**
   - Agente llena automáticamente con datos del cierre
   - Formato: FECHA | PRODUCTO | CANTIDAD | RECETA
   - Base para calcular auditoría

3. **Completar Bruno (15 recetas)**
   - Validar con camarero: Margarita = 4 oz hielo + 1.5 oz limón + 2 oz ron
   - Llenar fórmula COMPOSICION para todas

4. **Crear DASHBOARD básico**
   - 3 secciones:
     - Stock actual (Inv, Min, % Status)
     - Discrepancias hoy (Física vs Teórica)
     - Rentabilidad hoy (COGS, Margen)
   - Admin lo abre cada mañana

### 🟡 PRÓXIMAS 2 SEMANAS (Alto - 6 horas)

5. **Agregar validaciones:**
   - SALIDAS: dropdown para productos
   - ENTRADA: solo números > 0
   - COMPOSICION: validar que refs. existan

6. **Expandir Bruno:**
   - Agregar columnas: PRECIO_VENTA, MARGEN_TARGET, COGS_ESPERADO

### 🟢 PRÓXIMO MES (Medio - 8 horas)

7. **Preparar para Pizza y Sushi:**
   - No hojas nuevas → misma tabla
   - Agregar categoría PIZZA_INSUMOS al Catálogo
   - Agregar recetas de pizza a Bruno
   - DASHBOARD: filtros por tipo

8. **Automatización (Optional):**
   - Si hay flujo de entregas consistente, llenar ENTRADA automática

---

## 📊 IMPACTO EN 4 SEMANAS

| Antes | Después |
|-------|---------|
| Admin no sabe rentabilidad | Admin ve COGS + Margen por bebida |
| Pérdidas se detectan en cierre mensual | Pérdidas se detectan MISMO DÍA |
| Sistema solo sirve para bebidas | Sistema escalable a pizza, sushi, postres |
| Bruno es solo "lista de recetas" | Bruno es "cerebro del sistema" |
| Agente reporta números sueltos | Agente alimenta sistema auditable |

---

## 💰 INVERSIÓN & ROI

| Item | Costo | Tiempo |
|------|-------|--------|
| COSTO_UNITARIO | $0 | 1 hora |
| SALIDAS | $0 | 2 horas |
| Completar Bruno | $0 | 3 horas |
| DASHBOARD | $0 | 4 horas |
| Validaciones | $0 | 3 horas |
| **Total** | **$0** | **13 horas** |

**ROI:** 2-3 meses (recupera por reducción de merma + fraude)

---

## 📋 CHECKLIST - QUÉ PEDIRLE A BRUNO

- [ ] Agregar COSTO_UNITARIO a Catálogo (columnG, tipo Currency)
- [ ] Crear SALIDAS (FECHA|PRODUCTO|CANTIDAD|RECETA) con validaciones
- [ ] Completar 15 recetas vacías en Bruno con COMPOSICION exacta
- [ ] Crear DASHBOARD con 3 secciones (Stock, Discrepancias, Rentabilidad)
- [ ] Agregar protecciones: solo admin edita precios, team no puede borrar
- [ ] Expandir Bruno: +columnas PRECIO_VENTA, MARGEN_TARGET, COGS
- [ ] Preparar estructura para PIZZA_INSUMOS (sin crear aún)

---

## ❓ PREGUNTAS PARA CLARIFICAR CON AGENTE/TEAM

Antes que Bruno comience, responder:

1. ¿Agente extrae EXACTAMENTE qué bebidas se vendieron o solo $total?
2. ¿Cuántas Margaritas se venden/día en promedio?
3. ¿Hay estándar de medidas (Margarita siempre = 4 oz hielo)?
4. ¿Qué top 3 bebidas/pizzas generan más $?
5. ¿Hay producto con hurto sospechoso o merma alta?
6. ¿Admin necesita otros reportes además de DASHBOARD?

---

## 🔗 CONEXIÓN CON AGENTE ACTUAL

Lo que hace agente **SIGUE IGUAL:**
- Lee cierres diarios ✅
- Reporta a Telegram ✅
- Compara con catálogo ✅

Lo que MEJORA:
- Ahora sus datos se guardan en SALIDAS (estructura limpia)
- DASHBOARD usa esos datos automáticamente
- Puede generar reportes semanales más ricos

---

## 🎓 CONCLUSIÓN

**Hoy:** Sistema fragmentado (datos en silos)  
**En 4 semanas:** Sistema integrado (todo conectado + auditable)

**Costo:** Gratis (mejoras dentro de Google Sheets)  
**Tiempo:** ~13 horas (Bruno puede hacer 2-3 hrs/día)  
**Beneficio:** Visibilidad 100% + escalable a múltiples insumos

---

**Próximo paso:** Compartir con Bruno + responder 6 preguntas → comenzar implementación
