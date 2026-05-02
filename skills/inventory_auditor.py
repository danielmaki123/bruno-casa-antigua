from database.postgres import execute_query

def auditar_inventario(cierre_id, fecha, ventas_detalle):
    """
    Toma ventas del cierre, busca recetas y genera consumo teórico.
    """
    resumen_consumo = {}
    
    for venta in ventas_detalle:
        plato = venta['descripcion']
        cantidad_vendida = float(venta['cantidad'])
        
        # Buscar receta en SQL (V2_recipes)
        # Nota: Kimi o tú deben llenar esta tabla con el Excel nuevo
        query = "SELECT ingrediente, cantidad, unidad FROM v2_recipes WHERE plato_pos = %s"
        receta = execute_query(query, (plato,), fetch=True)
        
        for item in receta:
            ingrediente = item['ingrediente']
            consumo_unitario = float(item['cantidad'])
            total_consumo = cantidad_vendida * consumo_unitario
            
            if ingrediente not in resumen_consumo:
                resumen_consumo[ingrediente] = 0.0
            resumen_consumo[ingrediente] += total_consumo

    # Guardar auditoria en SQL
    for ingrediente, consumo in resumen_consumo.items():
        save_query = """
        INSERT INTO v2_inventory_audit (fecha, producto, consumo_teorico)
        VALUES (%s, %s, %s)
        ON CONFLICT (fecha, producto) DO UPDATE SET
            consumo_teorico = EXCLUDED.consumo_teorico
        """
        # Nota: La tabla necesita un UNIQUE(fecha, producto) para el ON CONFLICT. 
        # Lo añado en el siguiente paso si es necesario.
        execute_query(save_query, (fecha, ingrediente, consumo))
        
    return resumen_consumo
