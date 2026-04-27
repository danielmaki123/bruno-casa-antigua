# 📊 Estructura de Google Sheets: BRUNO_RESTAURANTE

Crea una sola hoja de Google Sheets llamada `BRUNO_RESTAURANTE` y añade las siguientes pestañas (tabs) con sus respectivas columnas:

### 1. INVENTARIO
| fecha | turno | area | insumo_id | cantidad_fisica | responsable | notas |
|---|---|---|---|---|---|---|

### 2. INSUMOS
| insumo_id | nombre | unidad_base | stock_minimo | stock_critico | proveedor_default | contacto | area_default |
|---|---|---|---|---|---|---|---|

### 3. RECETAS
| receta_id | nombre | insumo | cantidad | unidad | categoria |
|---|---|---|---|---|---|

### 4. VENTAS_DIARIAS
| fecha | receta_id | cantidad_vendida | ingreso_total | cajero | notas |
|---|---|---|---|---|---|

### 5. EMPLEADOS
| empleado_id | nombre | funcion | fecha_ingreso | telefono | estado | area | telegram_id |
|---|---|---|---|---|---|---|---|

### 6. EVENTOS_CALENDARIO
| fecha | tipo | descripcion | monto_estimado | estado | notas |
|---|---|---|---|---|---|

---
**💡 Tip:** Una vez creada, comparte la hoja con el correo de la cuenta de servicio de Google que usaremos para la API.
