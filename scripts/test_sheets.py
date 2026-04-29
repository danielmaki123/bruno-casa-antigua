"""
test_sheets.py — Prueba directa del puente Google Sheets
Ejecutar: python scripts/test_sheets.py
"""
import os, sys, json
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

os.environ.setdefault("GOOGLE_SHEETS_ID", "1PG5id1G_tpgMmLgCpkkRF8YXby0tidY0Wlb3smminxw")

# Importar funciones directamente (sin argparse)
from sheets_tool import _spreadsheet_id, _append_row, _read_sheet

TEST_ROW = {
    "fecha": "2026-04-28",
    "turno": "manana",
    "area": "cocina",
    "insumo_id": "arroz",
    "cantidad_fisica": "10",
    "responsable": "test",
    "notas": "prueba local",
}

print("[TEST] Intentando guardar fila de prueba en hoja INVENTARIO...")
sid = _spreadsheet_id()
result = _append_row(sid, "INVENTARIO", TEST_ROW)
print("[OK] Resultado:", json.dumps(result, indent=2, ensure_ascii=False))

print("[TEST] Leyendo las ultimas filas de INVENTARIO...")
rows = _read_sheet(sid, "INVENTARIO")
print(f"   Total filas: {len(rows)}")
if rows:
    print("   Ultima fila:", json.dumps(rows[-1], ensure_ascii=False))
