import logging
from database.postgres import execute_query

logger = logging.getLogger("admin_auditor")

def auditar_finanzas(cierre_data):
    """
    Cruza datos del POS vs Liquidaciones Bancarias guardadas.
    """
    fecha = cierre_data['fecha']
    tarjetas_pos = float(cierre_data['tarjetas_total'])
    
    # Buscar liquidaciones del banco para esa fecha
    query = "SELECT SUM(monto) as total FROM liquidaciones_banco WHERE fecha = %s"
    res = execute_query(query, (fecha,), fetch=True)
    banco_total = float(res[0]['total'] or 0.0)
    
    # Calculo real
    diferencia = tarjetas_pos - banco_total
    umbral = 50.0 # Córdobas
    
    alerta = abs(diferencia) > umbral
    
    # Guardar resultado en V2_sales_summary
    save_query = """
    INSERT INTO v2_sales_summary (documento_id, fecha, tarjetas_pos, banco_total, diferencia_dinero, status)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (documento_id) DO UPDATE SET
        banco_total = EXCLUDED.banco_total,
        diferencia_dinero = EXCLUDED.diferencia_dinero,
        status = EXCLUDED.status
    """
    status = "ALERTA" if alerta else "OK"
    execute_query(save_query, (cierre_data['documento_id'], fecha, tarjetas_pos, banco_total, diferencia, status))
    
    return {
        "banco_total": banco_total,
        "diferencia": diferencia,
        "alerta": alerta,
        "status": status
    }
