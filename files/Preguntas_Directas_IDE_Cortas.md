# ⚡ PREGUNTAS DIRECTAS PARA EL IDE (Versión Rápida)
## Casa Antigua - Agente de Inventario

**Tiempo respuesta estimado: 30 minutos (máximo)**

---

## 🎯 FLUJO GENERAL (5 preguntas)

**1. ¿Cómo inicia el proceso?**
```
Ejemplo: 
- [ ] Staff cierra caja a las 6pm → presiona botón "Generar cierre" 
- [ ] El cierre se genera automáticamente (¿dónde se guarda?)
- [ ] Staff envía WhatsApp/email al agente
- [ ] Otro: _____________
```

**2. ¿De qué formato recibe el cierre?**
```
Pegar ejemplo real:

[Pegar aquí]

¿Es siempre igual o varía?
```

**3. ¿A dónde reporta?**
```
- [ ] Solo Telegram
- [ ] Telegram + Google Sheets
- [ ] Telegram + Email
- [ ] Otro: _____________
```

**4. ¿Qué información incluye el reporte a Telegram?**
```
Pegar ejemplo real de mensaje Telegram:

[Pegar aquí]
```

**5. ¿Con qué frecuencia reporta?**
```
- [ ] 1× al día (cuándo? _____:____)
- [ ] Cada vez que hay cierre
- [ ] A demanda (admin pide "/reporte")
- [ ] Otro: _____________
```

---

## 🔧 INFRAESTRUCTURA TÉCNICA (5 preguntas)

**6. ¿Dónde corre el agente?**
```
- [ ] Google Apps Script (dentro de Sheets)
- [ ] Python en servidor propio (¿IP/dominio?)
- [ ] Python en Heroku/AWS/GCP
- [ ] Node.js (¿dónde?)
- [ ] Make/Zapier
- [ ] Otro: _____________
```

**7. ¿Qué API usa para LLM?**
```
- [ ] Claude (Anthropic) - ¿Qué modelo? (Opus, Sonnet, Haiku?)
- [ ] Gemini (Google) - ¿Qué modelo?
- [ ] ChatGPT (OpenAI) - ¿Qué modelo?
- [ ] Otro: _____________

¿Costo/mes estimado?
```

**8. ¿Cómo se autentica con Google Sheets?**
```
- [ ] Service Account (account.json)
- [ ] OAuth 2.0
- [ ] API key
- [ ] Otro: _____________

¿Qué permisos tiene? (solo lectura, lectura+escritura?)
```

**9. ¿Cómo envía mensajes a Telegram?**
```
- [ ] Bot Token (¿cuál grupo/canal?)
- [ ] Webhooks
- [ ] Direct API
- [ ] Otro: _____________
```

**10. ¿Cuánto tiempo toma ejecutar?** (desde inicio hasta reporte en Telegram)
```
_______ segundos / minutos
```

---

## 📊 PROCESAMIENTO DE DATOS (5 preguntas)

**11. ¿Qué calcula el agente?**
```
Marcar lo que ACTUALMENTE hace:

- [ ] COGS (costo de ingredientes por bebida vendida)
- [ ] Margen (Precio - COSTO / Precio × 100)
- [ ] Inventario Teórico (Anterior + Entrada - Salida)
- [ ] Discrepancia (Física vs Teórica)
- [ ] Rotación (días que dura un producto)
- [ ] Otro: _____________
```

**12. ¿Cómo parsea el cierre?**
```
- [ ] Texto libre (Lee cualquier formato, NLP inteligente)
  - ¿Entiende variaciones? ("Cerveza Boreal" = "Boreal" = "CER_001"?)
  - ¿Falla frecuentemente? (¿Cuál es el % de error?)
  
- [ ] Formato estructurado esperado (tabla, JSON, CSV)
  - ¿Qué pasa si no cumple formato?
  
- [ ] Mix (espera formato pero tolera variaciones)
```

**13. ¿Qué validaciones realiza?**
```
- [ ] Producto existe en Catálogo
- [ ] Cantidad > 0 y < limit
- [ ] Composición está definida en Bruno
- [ ] Margen es razonable (>X%)
- [ ] Otro: _____________

¿Qué pasa si validación falla? (ignora, alerta, error?)
```

**14. ¿Cómo obtiene Catálogo + Bruno?**
```
- [ ] Carga 1 sola vez al iniciar
- [ ] Recarga cada X tiempo (¿cuánto?)
- [ ] Está hardcodeado en código
- [ ] Otro: _____________
```

**15. ¿Qué information le FALTA para hacer mejor?**
```
Top 3 cosas que desearías tener:

1. [ ] COSTO_UNITARIO de productos
2. [ ] Composiciones más completas en Bruno
3. [ ] Información de ENTRADAS (compras diarias)
4. [ ] Timestamps exactos
5. [ ] Otro: _____________
```

---

## 🚨 PROBLEMAS CONOCIDOS (3 preguntas)

**16. ¿Cuál es el problema principal que enfrenta?**
```
________________________
```

**17. ¿Cuántas veces por semana el agente reporta algo incorrecto?**
```
Nunca / Raramente / 1-2 veces / 3+ veces
```

**18. ¿Si agregamos Pizza y Sushi, qué tendrías que cambiar?**
```
- [ ] Agregar items a Catálogo (sin cambios en agente)
- [ ] Cambiar lógica de parseo
- [ ] Cambiar cálculos
- [ ] Expandir Telegram bot
- [ ] Otro: _____________
```

---

## 📈 VOLÚMENES Y ESCALA (3 preguntas)

**19. ¿Cuánto data procesa?**
```
Bebidas vendidas/día: _____ (rango: 50-500?)
Tipos diferentes de bebidas: _____ (rango: 10-50?)
Camareros/operadores: _____ (rango: 1-20?)
```

**20. ¿Si volumen se duplica, sigue funcionando?**
```
- [ ] Sí, sin problema
- [ ] Probablemente, pero no testado
- [ ] No, hay límites (¿cuáles?)
- [ ] No sé
```

**21. ¿Costo operativo actual?**
```
LLM API: $___/mes
Servidor: $___/mes
Otros: $___/mes
Total: $___/mes
```

---

## 💡 VISIÓN Y PRÓXIMOS PASOS (2 preguntas)

**22. ¿Cuál es el próximo mejora prioritaria?**
```
- [ ] Aumentar precisión del parseo
- [ ] Agregar nuevos insumos (pizza, sushi)
- [ ] Dashboard para admin
- [ ] Automatizar entradas
- [ ] Otra: _____________
```

**23. ¿Cuál es el objetivo final?**
```
En 3-6 meses, el agente debería:

_____________________________________
```

---

## 📎 ANEXO: PEDIR EVIDENCIA

### Si responde "sí" a algo, pedir:
- Ejemplo real (pegar en respuesta)
- Screenshot
- Link a código (GitHub, Google Apps Script, etc)

### Ejemplos específicos a pedir:

1. **Cierre típico:** "Pega un ejemplo de cierre de hoy"
2. **Reporte Telegram:** "Pega el último mensaje que envió el agente a Telegram"
3. **Error típico:** "Ejemplo de un cierre que procesó incorrectamente"
4. **Código:** "Link a repo o Google Apps Script (si es Open)"

---

## ✅ RESPUESTAS CRÍTICAS

Si SOLO contesta 3 cosas, que sean:

1. **Flujo completo:** Desde cierre → Agente → Telegram (paso a paso)
2. **Ejemplo real:** Cierre típico + Reporte típico (para ver formatos)
3. **Qué le falta:** Top 3 mejoras o datos que necesita

---

*Versión corta - máximo 30 minutos de respuesta*
*Si quieres más detalle, ver: Cuestionario_Tecnico_Agente_Completo.md*
