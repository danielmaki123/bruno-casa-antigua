import argparse
import json
import os
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from requests.exceptions import RequestException

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GROUP_ID_INVENTARIO = os.getenv('GROUP_ID_INVENTARIO')
GROUP_ID_ADMIN = os.getenv('GROUP_ID_ADMIN')
GOOGLE_SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID')
SHEETS_ID_BEBIDAS = os.getenv('SHEETS_ID_BEBIDAS') or os.getenv('GOOGLE_SHEETS_ID')
SHEETS_ID_ADMIN = os.getenv('SHEETS_ID_ADMIN')
SHEETS_ID_CONFIG = os.getenv('SHEETS_ID_CONFIG')
INVENTARIO_CHECK_INTERVAL = 3600

BASE_URL = 'https://sheets.googleapis.com/v4/spreadsheets'

_session = requests.Session()
_session.trust_env = False


def _find_token_path() -> Path:
    env_path = os.getenv('SHEETS_TOKEN_PATH')
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    root_token = Path(__file__).resolve().parent.parent / 'token.json'
    if root_token.exists():
        return root_token

    docker_token = Path('/app/token.json')
    if docker_token.exists():
        return docker_token

    cwd_token = Path.cwd() / 'token.json'
    if cwd_token.exists():
        return cwd_token

    raise RuntimeError('No se encontro token.json (ROOT/token.json ni /app/token.json).')


def _get_access_token() -> str:
    token_path = _find_token_path()
    data = json.loads(token_path.read_text(encoding='utf-8'))

    expiry_raw = data.get('expiry')
    if data.get('token') and expiry_raw:
        try:
            expiry = datetime.fromisoformat(expiry_raw.replace('Z', '+00:00'))
            if expiry - datetime.now(timezone.utc) > timedelta(seconds=60):
                return data['token']
        except Exception:
            pass

    required = ['token_uri', 'client_id', 'client_secret', 'refresh_token']
    missing = [k for k in required if not data.get(k)]
    if missing:
        raise RuntimeError(f'token.json incompleto. Faltan campos: {", ".join(missing)}')

    resp = _session.post(
        data['token_uri'],
        data={
            'client_id': data['client_id'],
            'client_secret': data['client_secret'],
            'refresh_token': data['refresh_token'],
            'grant_type': 'refresh_token',
        },
        timeout=20,
    )
    resp.raise_for_status()
    refreshed = resp.json()

    access_token = refreshed.get('access_token')
    if not access_token:
        raise RuntimeError('No se recibio access_token al refrescar token de Google.')

    data['token'] = access_token
    expires_in = int(refreshed.get('expires_in', 3600))
    new_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    data['expiry'] = new_expiry.strftime('%Y-%m-%dT%H:%M:%SZ')
    token_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    return access_token


def _auth_headers() -> dict[str, str]:
    return {
        'Authorization': f'Bearer {_get_access_token()}',
        'Content-Type': 'application/json',
    }


def _parse_cantidad(val: Any) -> float | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None

    s = s.replace(',', '.').replace(' ', '')

    try:
        return float(s)
    except ValueError:
        pass

    if '/' in s:
        if '.' in s:
            entero, frac = s.split('.', 1)
            if '/' in frac:
                try:
                    base = float(entero)
                    num, den = frac.split('/', 1)
                    return base + (float(num) / float(den))
                except (ValueError, ZeroDivisionError):
                    return None
        else:
            try:
                num, den = s.split('/', 1)
                return float(num) / float(den)
            except (ValueError, ZeroDivisionError):
                return None

    return None


def _parse_header_date(header: str) -> date | None:
    if not header:
        return None
    text = str(header).strip()
    for fmt in ('%d/%m/%Y', '%d-%m-%Y'):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _sheet_values(sheet_name: str, value_range: str = 'A:ZZ', sheet_id: str = None) -> list[list[str]]:
    sid = sheet_id or SHEETS_ID_BEBIDAS or GOOGLE_SHEETS_ID
    if not sid:
        raise RuntimeError('No sheet ID configured')
    url = f'{BASE_URL}/{sid}/values/{sheet_name}!{value_range}'
    resp = _session.get(url, headers=_auth_headers(), timeout=25)
    resp.raise_for_status()
    return resp.json().get('values', [])


def _sheet_update_values(
    sheet_name: str,
    value_range: str,
    values: list[list[Any]],
    sheet_id: str = None,
) -> None:
    sid = sheet_id or SHEETS_ID_BEBIDAS or GOOGLE_SHEETS_ID
    if not sid:
        raise RuntimeError('No sheet ID configured')
    url = f'{BASE_URL}/{sid}/values/{sheet_name}!{value_range}?valueInputOption=USER_ENTERED'
    resp = _session.put(url, headers=_auth_headers(), json={'values': values}, timeout=25)
    resp.raise_for_status()


def _sheet_batch_update(requests_payload: list[dict[str, Any]], sheet_id: str = None) -> dict[str, Any]:
    sid = sheet_id or SHEETS_ID_BEBIDAS or GOOGLE_SHEETS_ID
    if not sid:
        raise RuntimeError('No sheet ID configured')
    url = f'{BASE_URL}/{sid}:batchUpdate'
    resp = _session.post(url, headers=_auth_headers(), json={'requests': requests_payload}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _sheet_metadata(sheet_id: str) -> dict[str, Any]:
    url = f'{BASE_URL}/{sheet_id}'
    resp = _session.get(url, headers=_auth_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def _get_sheet_info(metadata: dict[str, Any], title: str) -> dict[str, Any] | None:
    for sheet in metadata.get('sheets', []):
        props = sheet.get('properties', {})
        if props.get('title') == title:
            return sheet
    return None


def _rgb(hex_color: str) -> dict[str, float]:
    h = hex_color.lstrip('#')
    return {
        'red': int(h[0:2], 16) / 255.0,
        'green': int(h[2:4], 16) / 255.0,
        'blue': int(h[4:6], 16) / 255.0,
    }


def _col_to_a1(index_1_based: int) -> str:
    if index_1_based < 1:
        raise ValueError('column index must be >= 1')
    n = index_1_based
    out = ''
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def rebuild_entradas_tab() -> None:
    """Recrea ENTRADAS para reflejar el formato/tablas de INVENTARIO_BEBIDAS."""
    metadata = _sheet_metadata(SHEETS_ID_BEBIDAS)
    inv_info = _get_sheet_info(metadata, 'INVENTARIO_BEBIDAS')
    if not inv_info:
        raise RuntimeError('No existe pestaña INVENTARIO_BEBIDAS en SHEETS_ID_BEBIDAS.')

    inv_values = _sheet_values('INVENTARIO_BEBIDAS', 'A:ZZ', sheet_id=SHEETS_ID_BEBIDAS)
    if not inv_values or len(inv_values) < 3:
        raise RuntimeError('INVENTARIO_BEBIDAS no tiene estructura esperada (min 3 filas).')

    inv_headers = [str(h).strip() for h in inv_values[0]]
    date_headers = [h for h in inv_headers[5:] if _parse_header_date(h)]

    product_rows: list[list[Any]] = []
    for row in inv_values[2:]:
        producto = row[0].strip() if len(row) > 0 else ''
        if not producto:
            continue
        categoria = row[1].strip() if len(row) > 1 else ''
        unidad = row[2].strip() if len(row) > 2 else ''
        proveedor_id = row[4] if len(row) > 4 else ''
        product_rows.append([producto, categoria, unidad, proveedor_id])

    entradas_info = _get_sheet_info(metadata, 'ENTRADAS')
    requests_payload: list[dict[str, Any]] = []
    if entradas_info:
        requests_payload.append({'deleteSheet': {'sheetId': entradas_info['properties']['sheetId']}})
    requests_payload.append({
        'duplicateSheet': {
            'sourceSheetId': inv_info['properties']['sheetId'],
            'newSheetName': 'ENTRADAS',
        }
    })
    create_resp = _sheet_batch_update(requests_payload, sheet_id=SHEETS_ID_BEBIDAS)
    entries_sheet_id = create_resp['replies'][-1]['duplicateSheet']['properties']['sheetId']

    header_row = ['Producto', 'Categoria', 'Unidad', 'Proveedor ID'] + date_headers
    responsable_row = ['Responsable', '', '', ''] + ([''] * len(date_headers))
    value_rows = [header_row, responsable_row]
    for p in product_rows:
        value_rows.append(p + ([''] * len(date_headers)))

    end_row = len(value_rows)
    end_col = len(header_row)
    end_col_a1 = _col_to_a1(end_col)
    _sheet_update_values('ENTRADAS', f'A1:{end_col_a1}{end_row}', value_rows, sheet_id=SHEETS_ID_BEBIDAS)

    _sheet_batch_update([{
        'updateSheetProperties': {
            'properties': {
                'sheetId': entries_sheet_id,
                'gridProperties': {
                    'frozenRowCount': 1,
                    'frozenColumnCount': 4,
                    'rowCount': max(200, len(value_rows) + 5),
                    'columnCount': max(end_col, 30),
                },
            },
            'fields': 'gridProperties.frozenRowCount,gridProperties.frozenColumnCount,gridProperties.rowCount,gridProperties.columnCount',
        }
    }], sheet_id=SHEETS_ID_BEBIDAS)

    format_requests: list[dict[str, Any]] = [
        {
            'repeatCell': {
                'range': {
                    'sheetId': entries_sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': 1,
                    'startColumnIndex': 0,
                    'endColumnIndex': end_col,
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': _rgb('#E65100'),
                        'textFormat': {'bold': True, 'foregroundColor': _rgb('#FFFFFF')},
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat)',
            }
        },
        {
            'repeatCell': {
                'range': {
                    'sheetId': entries_sheet_id,
                    'startRowIndex': 1,
                    'endRowIndex': 2,
                    'startColumnIndex': 0,
                    'endColumnIndex': end_col,
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': _rgb('#FFF3E0'),
                        'textFormat': {'bold': True, 'italic': True},
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat)',
            }
        },
    ]

    if end_row > 2:
        format_requests.append({
            'addBanding': {
                'bandedRange': {
                    'range': {
                        'sheetId': entries_sheet_id,
                        'startRowIndex': 2,
                        'endRowIndex': end_row,
                        'startColumnIndex': 0,
                        'endColumnIndex': end_col,
                    },
                    'rowProperties': {
                        'firstBandColor': _rgb('#FFFFFF'),
                        'secondBandColor': _rgb('#FFF8E1'),
                    },
                }
            }
        })

    _sheet_batch_update(format_requests, sheet_id=SHEETS_ID_BEBIDAS)


def leer_inventario_sheet() -> list[dict[str, Any]]:
    values = _sheet_values('INVENTARIO_BEBIDAS', 'A:ZZ')
    if not values or len(values) < 3:
        return []

    headers = [str(h).strip() for h in values[0]]
    responsable_row = values[1] if len(values) > 1 else []
    out: list[dict[str, Any]] = []

    fixed_cols = 5
    for row in values[2:]:
        producto = row[0].strip() if len(row) > 0 else ''
        if not producto:
            continue

        categoria = row[1].strip() if len(row) > 1 else ''
        unidad = row[2].strip() if len(row) > 2 else ''
        stock_min_raw = row[3] if len(row) > 3 else None
        proveedor_raw = row[4] if len(row) > 4 else None

        stock_min = _parse_cantidad(stock_min_raw)
        try:
            proveedor_id = int(str(proveedor_raw).strip()) if str(proveedor_raw).strip() else None
        except ValueError:
            proveedor_id = None

        for idx in range(fixed_cols, len(headers)):
            fecha = _parse_header_date(headers[idx])
            if not fecha:
                continue

            cantidad_raw = row[idx] if idx < len(row) else None
            if not cantidad_raw or str(cantidad_raw).strip() == '':
                continue
            responsable = ''
            if idx < len(responsable_row):
                responsable = str(responsable_row[idx]).strip()
            out.append({
                'producto': producto,
                'categoria': categoria,
                'unidad': unidad,
                'stock_min': stock_min,
                'proveedor_id': proveedor_id,
                'fecha': fecha,
                'cantidad_raw': cantidad_raw,
                'cantidad_normalizada': _parse_cantidad(cantidad_raw),
                'responsable': responsable,
            })

    return out


def leer_proveedores_sheet() -> dict[int, dict[str, str]]:
    values = _sheet_values('PROVEEDORES', 'A:E', sheet_id=SHEETS_ID_ADMIN)
    if not values:
        return {}

    data: dict[int, dict[str, str]] = {}
    for row in values[1:]:
        raw_id = row[0].strip() if len(row) > 0 else ''
        if not raw_id:
            continue
        try:
            pid = int(raw_id)
        except ValueError:
            continue

        data[pid] = {
            'nombre': row[1].strip() if len(row) > 1 else '',
            'telefono': row[2].strip() if len(row) > 2 else '',
            'dia_pedido': row[3].strip() if len(row) > 3 else '',
        }
    return data


def leer_postres_sheet() -> list[dict[str, Any]]:
    values = _sheet_values('POSTRES', 'A:D', sheet_id=SHEETS_ID_ADMIN)
    if not values:
        return []

    out: list[dict[str, Any]] = []
    for row in values[1:]:
        producto = row[0].strip() if len(row) > 0 else ''
        if not producto:
            continue

        out.append({
            'producto': producto,
            'stock_min': _parse_cantidad(row[1] if len(row) > 1 else None),
            'stock_actual': _parse_cantidad(row[2] if len(row) > 2 else None),
            'proveedor_id': int(row[3]) if len(row) > 3 and str(row[3]).strip().isdigit() else None,
        })
    return out


def leer_catalogo_licores() -> dict:
    """Lee CATALOGO_LICORES y retorna dict {producto: {capacidad_oz, peso_lleno_g, peso_vacio_g, gramos_por_oz}}."""
    values = _sheet_values('CATALOGO_LICORES', 'A:I', sheet_id=SHEETS_ID_CONFIG)
    if not values or len(values) < 2:
        return {}

    catalogo = {}
    for row in values[1:]:
        if len(row) < 6:
            continue
        producto = str(row[0]).strip()
        if not producto or producto.startswith('*'):
            continue
        try:
            capacidad_oz = float(str(row[2]).replace(',', '.')) if row[2] else 25.4
            peso_lleno = float(str(row[3]).replace(',', '.')) if row[3] and '(' not in str(row[3]) else None
            peso_vacio = float(str(row[4]).replace(',', '.')) if row[4] else 680.0
            gramos_por_oz = float(str(row[6]).replace(',', '.')) if len(row) > 6 and row[6] else 27.5
        except (ValueError, TypeError):
            continue

        catalogo[producto] = {
            'capacidad_oz': capacidad_oz,
            'peso_lleno_g': peso_lleno,
            'peso_vacio_g': peso_vacio,
            'gramos_por_oz': gramos_por_oz,
        }
    return catalogo


def gramos_a_oz(producto: str, gramos: float, catalogo: dict) -> float:
    """Convierte gramos medidos a oz de licor restante usando el catálogo."""
    info = catalogo.get(producto)
    if not info:
        # fallback: assume standard 750ml bottle
        return max(0.0, (gramos - 680.0) / 27.5)

    peso_vacio = info['peso_vacio_g']
    gramos_por_oz = info['gramos_por_oz']
    oz = (gramos - peso_vacio) / gramos_por_oz
    return max(0.0, round(oz, 2))


def leer_entradas_sheet() -> list[dict]:
    """Lee ENTRADAS con formato paralelo a INVENTARIO_BEBIDAS.
    Row1 encabezados con fechas; Row2 responsable; Row3+ productos.
    """
    values = _sheet_values('ENTRADAS', 'A:ZZ')
    if not values or len(values) < 3:
        return []

    headers = [str(h).strip() for h in values[0]]
    responsable_row = values[1] if len(values) > 1 else []
    out: list[dict[str, Any]] = []
    fixed_cols = 4

    for row in values[2:]:
        producto = row[0].strip() if len(row) > 0 else ''
        if not producto:
            continue

        categoria = row[1].strip() if len(row) > 1 else ''
        unidad = row[2].strip() if len(row) > 2 else ''
        proveedor_raw = row[3] if len(row) > 3 else None
        try:
            proveedor_id = int(str(proveedor_raw).strip()) if str(proveedor_raw).strip() else None
        except ValueError:
            proveedor_id = None

        for idx in range(fixed_cols, len(headers)):
            fecha = _parse_header_date(headers[idx])
            if not fecha:
                continue
            cantidad_raw = row[idx] if idx < len(row) else None
            cantidad = _parse_cantidad(cantidad_raw)
            if cantidad in (None, 0.0):
                continue
            responsable = str(responsable_row[idx]).strip() if idx < len(responsable_row) else ''
            out.append({
                'producto': producto,
                'categoria': categoria,
                'unidad': unidad,
                'proveedor_id': proveedor_id,
                'fecha': fecha,
                'cantidad': cantidad,
                'responsable': responsable,
            })
    return out


def leer_recetas_bebidas() -> dict[str, list[dict[str, Any]]]:
    values = _sheet_values('RECETAS_BEBIDAS', 'A:E', sheet_id=SHEETS_ID_CONFIG)
    if not values or len(values) <= 1:
        return {}

    out: dict[str, list[dict[str, Any]]] = {}
    for row in values[1:]:
        bebida = row[0].strip() if len(row) > 0 else ''
        ingrediente = row[1].strip() if len(row) > 1 else ''
        cantidad_raw = row[2] if len(row) > 2 else None
        unidad = row[3].strip() if len(row) > 3 else ''

        # Salta fila de notas al pie u otras filas incompletas.
        if not bebida or not ingrediente:
            continue

        cantidad_oz = _parse_cantidad(cantidad_raw)
        if cantidad_oz is None:
            continue

        out.setdefault(bebida, []).append({
            'ingrediente': ingrediente,
            'cantidad_oz': float(cantidad_oz),
            'unidad': unidad,
        })
    return out


def guardar_inventario_postgres(registros: list[dict[str, Any]]) -> int:
    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL no esta configurado en .env')
    if not registros:
        return 0

    inserted = 0
    skipped = []
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for r in registros:
                try:
                    cur.execute(
                        """
                        INSERT INTO inventario_catalogo (producto, categoria, unidad_tipo, stock_minimo, proveedor_id, activo)
                        VALUES (%s, %s, %s, %s, %s, TRUE)
                        ON CONFLICT (producto) DO UPDATE
                        SET
                            categoria = EXCLUDED.categoria,
                            unidad_tipo = EXCLUDED.unidad_tipo,
                            stock_minimo = COALESCE(EXCLUDED.stock_minimo, inventario_catalogo.stock_minimo),
                            proveedor_id = COALESCE(EXCLUDED.proveedor_id, inventario_catalogo.proveedor_id),
                            activo = TRUE
                        """,
                        (r['producto'], r['categoria'], r['unidad'], r['stock_min'], r['proveedor_id']),
                    )

                    cur.execute('SELECT id FROM inventario_catalogo WHERE producto = %s', (r['producto'],))
                    row = cur.fetchone()
                    if not row:
                        continue
                    producto_id = row[0]

                    # cantidad_raw es NUMERIC en la DB — pasar el valor ya parseado (float),
                    # NO el string crudo ('2,5', '1/2', etc.) que PostgreSQL rechazaría.
                    cantidad_para_db = r['cantidad_normalizada']  # ya es float o None

                    cur.execute(
                        """
                        INSERT INTO inventario_diario (
                            fecha, producto_id, cantidad_raw, unidad_raw, cantidad_normalizada, responsable, fuente
                        ) VALUES (%s, %s, %s, %s, %s, %s, 'sheets')
                        ON CONFLICT (fecha, producto_id) DO UPDATE
                        SET
                            cantidad_raw = EXCLUDED.cantidad_raw,
                            unidad_raw = EXCLUDED.unidad_raw,
                            cantidad_normalizada = EXCLUDED.cantidad_normalizada,
                            responsable = EXCLUDED.responsable,
                            fuente = EXCLUDED.fuente
                        """,
                        (
                            r['fecha'],
                            producto_id,
                            cantidad_para_db,
                            r['unidad'],
                            r['cantidad_normalizada'],
                            r.get('responsable', ''),
                        ),
                    )
                    inserted += 1
                except psycopg2.Error as row_err:
                    # Fila con datos inválidos — saltar y loggear sin romper el batch.
                    conn.rollback()
                    raw_val = r.get('cantidad_raw', '?')
                    producto = r.get('producto', '?')
                    print(
                        f'[WARN] Fila omitida por error DB '
                        f'(producto={producto!r}, cantidad_raw={raw_val!r}): {row_err}',
                        flush=True,
                    )
                    skipped.append(f'{producto}: {raw_val!r}')

    if skipped:
        print(f'[WARN] {len(skipped)} filas omitidas por datos inválidos: {skipped}', flush=True)
    return inserted


def guardar_entradas_postgres(entradas: list[dict]) -> int:
    """Guarda entradas de inventario en PostgreSQL."""
    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL no esta configurado en .env')
    if not entradas:
        return 0

    saved = 0
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'uq_entrada_dia'
                    ) THEN
                        ALTER TABLE entradas_inventario
                        ADD CONSTRAINT uq_entrada_dia UNIQUE (fecha, producto_id);
                    END IF;
                END
                $$;
                """
            )
            for e in entradas:
                if not e.get('cantidad'):
                    continue
                # lookup producto_id
                cur.execute('SELECT id FROM inventario_catalogo WHERE producto = %s', (e['producto'],))
                row = cur.fetchone()
                if not row:
                    continue
                producto_id = row[0]

                cur.execute("""
                    INSERT INTO entradas_inventario
                        (fecha, producto_id, cantidad, unidad, proveedor_id, responsable, fuente)
                    VALUES (%s, %s, %s, %s, %s, %s, 'sheets')
                    ON CONFLICT (fecha, producto_id) DO UPDATE
                    SET
                        cantidad = EXCLUDED.cantidad,
                        unidad = EXCLUDED.unidad,
                        proveedor_id = COALESCE(EXCLUDED.proveedor_id, entradas_inventario.proveedor_id),
                        responsable = COALESCE(NULLIF(EXCLUDED.responsable, ''), entradas_inventario.responsable),
                        fuente = EXCLUDED.fuente
                """, (e['fecha'], producto_id, e['cantidad'], e['unidad'],
                      e['proveedor_id'], e['responsable']))
                saved += 1
        conn.commit()
    return saved


def asegurar_ajustes_stock_min_licores() -> None:
    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL no esta configurado en .env')
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE inventario_catalogo
                SET stock_minimo = CASE
                    WHEN producto ILIKE '%%litro%%' OR producto ILIKE '%%1L%%' THEN 11.0
                    WHEN producto ILIKE '%%1/2%%' OR producto ILIKE '%%375%%' THEN 4.0
                    ELSE 8.5
                END
                WHERE categoria = 'Licores y Vinos'
                """
            )
        conn.commit()


def actualizar_catalogo_licores_stock_min_oz() -> None:
    values = _sheet_values('CATALOGO_LICORES', 'A:ZZ', sheet_id=SHEETS_ID_CONFIG)
    if not values:
        return
    headers = [str(h).strip() for h in values[0]]
    if not headers:
        return

    if 'Stock_min_oz' not in headers:
        insert_idx = headers.index('Gramos_por_oz') + 1 if 'Gramos_por_oz' in headers else len(headers)
        headers.insert(insert_idx, 'Stock_min_oz')
    else:
        insert_idx = headers.index('Stock_min_oz')

    out = [headers]
    for row in values[1:]:
        expanded = list(row) + ([''] * max(0, len(headers) - len(row)))
        if len(expanded) < len(headers):
            expanded.extend([''] * (len(headers) - len(expanded)))

        capacidad_raw = expanded[2] if len(expanded) > 2 else ''
        producto = str(expanded[0]).lower() if expanded and expanded[0] else ''
        stock_min = 8.5
        cap_text = str(capacidad_raw).replace(',', '.').strip()
        try:
            capacidad_oz = float(cap_text) if cap_text else 25.4
        except ValueError:
            capacidad_oz = 25.4

        if ('litro' in producto) or ('1l' in producto) or capacidad_oz >= 33.0:
            stock_min = 11.0
        elif ('1/2' in producto) or ('375' in producto) or capacidad_oz <= 13.2:
            stock_min = 4.0

        expanded[insert_idx] = stock_min
        out.append(expanded[:len(headers)])

    end_col = _col_to_a1(len(headers))
    _sheet_update_values('CATALOGO_LICORES', f'A1:{end_col}{len(out)}', out, sheet_id=SHEETS_ID_CONFIG)


def asegurar_notificaciones_log() -> None:
    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL no esta configurado en .env')
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS notificaciones_log (
                    id SERIAL PRIMARY KEY,
                    fecha DATE NOT NULL,
                    tipo VARCHAR(50) NOT NULL,
                    enviado_at TIMESTAMP DEFAULT NOW(),
                    resumen TEXT,
                    UNIQUE(fecha, tipo)
                );
                """
            )
        conn.commit()


def ya_notificado_hoy(tipo: str) -> bool:
    """Retorna True si ya se envio una notificacion de este tipo hoy."""
    hoy = date.today()
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT 1 FROM notificaciones_log WHERE fecha = %s AND tipo = %s',
                (hoy, tipo),
            )
            return cur.fetchone() is not None


def registrar_notificacion(tipo: str, resumen: str = '') -> None:
    """Registra que se envio una notificacion de este tipo hoy."""
    hoy = date.today()
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO notificaciones_log (fecha, tipo, resumen)
                VALUES (%s, %s, %s)
                ON CONFLICT (fecha, tipo) DO UPDATE SET
                    enviado_at = NOW(),
                    resumen = EXCLUDED.resumen
                """,
                (hoy, tipo, resumen),
            )
        conn.commit()


def analizar_diferencias(fecha_hoy: date, fecha_ayer: date) -> list[dict[str, Any]]:
    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL no esta configurado en .env')

    query = """
    SELECT
        c.producto,
        c.categoria,
        c.unidad_tipo,
        c.stock_minimo,
        c.proveedor_id,
        h.cantidad_normalizada AS cantidad_hoy,
        y.cantidad_normalizada AS cantidad_ayer,
        (COALESCE(y.cantidad_normalizada, 0) + COALESCE(ei.total_entradas, 0) - COALESCE(h.cantidad_normalizada, 0)) AS consumo_real
    FROM inventario_catalogo c
    LEFT JOIN inventario_diario h
        ON h.producto_id = c.id AND h.fecha = %s
    LEFT JOIN inventario_diario y
        ON y.producto_id = c.id AND y.fecha = %s
    LEFT JOIN (
        SELECT producto_id, SUM(cantidad) AS total_entradas
        FROM entradas_inventario
        WHERE fecha = %s
        GROUP BY producto_id
    ) ei ON ei.producto_id = c.id
    WHERE c.activo = TRUE
      AND (h.id IS NOT NULL OR y.id IS NOT NULL)
    ORDER BY c.categoria, c.producto
    """

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (fecha_hoy, fecha_ayer, fecha_hoy))
            rows = cur.fetchall()

    out = []
    for row in rows:
        cantidad_hoy = float(row['cantidad_hoy']) if row['cantidad_hoy'] is not None else None
        cantidad_ayer = float(row['cantidad_ayer']) if row['cantidad_ayer'] is not None else None
        consumo_real = float(row['consumo_real']) if row['consumo_real'] is not None else None
        stock_min = float(row['stock_minimo']) if row['stock_minimo'] is not None else None

        out.append({
            'producto': row['producto'],
            'categoria': row['categoria'],
            'unidad': row['unidad_tipo'],
            'stock_min': stock_min,
            'proveedor_id': row['proveedor_id'],
            'cantidad_hoy': cantidad_hoy,
            'cantidad_ayer': cantidad_ayer,
            'delta': consumo_real,
            'bajo_minimo': (cantidad_hoy is not None and stock_min is not None and (cantidad_hoy < stock_min or (cantidad_hoy <= 0 and stock_min >= 0))),
        })

    return out


def analizar_consumo_cierre(fecha: date) -> list[dict[str, Any]]:
    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL no esta configurado en .env')

    recetas = leer_recetas_bebidas()
    if not recetas:
        return []

    consumo_por_ingrediente: dict[str, dict[str, Any]] = {}
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT descripcion, SUM(cantidad) AS unidades_vendidas
                FROM ventas_detalle
                WHERE fecha = %s
                GROUP BY descripcion
                """,
                (fecha,),
            )
            ventas = cur.fetchall()

            for venta in ventas:
                bebida = (venta.get('descripcion') or '').strip()
                if not bebida or bebida not in recetas:
                    continue

                try:
                    unidades_vendidas = float(venta.get('unidades_vendidas') or 0)
                except (TypeError, ValueError):
                    continue

                if unidades_vendidas <= 0:
                    continue

                for receta_item in recetas[bebida]:
                    ingrediente = receta_item['ingrediente']
                    cantidad_oz = float(receta_item['cantidad_oz'])
                    unidad = (receta_item.get('unidad') or '').strip().lower()
                    consumo_oz = unidades_vendidas * cantidad_oz

                    slot = consumo_por_ingrediente.setdefault(
                        ingrediente,
                        {'unidad': unidad, 'consumo_teorico_oz': 0.0},
                    )
                    slot['consumo_teorico_oz'] += consumo_oz
                    if not slot.get('unidad'):
                        slot['unidad'] = unidad

            resultados: list[dict[str, Any]] = []
            fecha_ayer = fecha - timedelta(days=1)
            for ingrediente, data in consumo_por_ingrediente.items():
                cur.execute(
                    'SELECT id FROM inventario_catalogo WHERE producto = %s AND activo = TRUE LIMIT 1',
                    (ingrediente,),
                )
                prod = cur.fetchone()
                if not prod:
                    continue
                producto_id = prod['id']

                cur.execute(
                    """
                    SELECT cantidad_normalizada
                    FROM inventario_diario
                    WHERE producto_id = %s AND fecha = %s
                    LIMIT 1
                    """,
                    (producto_id, fecha),
                )
                hoy_row = cur.fetchone()

                cur.execute(
                    """
                    SELECT cantidad_normalizada
                    FROM inventario_diario
                    WHERE producto_id = %s AND fecha = %s
                    LIMIT 1
                    """,
                    (producto_id, fecha_ayer),
                )
                ayer_row = cur.fetchone()

                cantidad_hoy = float(hoy_row['cantidad_normalizada']) if hoy_row and hoy_row['cantidad_normalizada'] is not None else None
                cantidad_ayer = float(ayer_row['cantidad_normalizada']) if ayer_row and ayer_row['cantidad_normalizada'] is not None else None
                consumo_real = (cantidad_ayer - cantidad_hoy) if (cantidad_hoy is not None and cantidad_ayer is not None) else None

                consumo_teorico_oz = float(data['consumo_teorico_oz'])
                unidad = data.get('unidad', '')
                if 'licor' in unidad or 'botella' in unidad:
                    consumo_teorico = consumo_teorico_oz / 25.4
                elif 'jugo' in unidad or 'galon' in unidad:
                    consumo_teorico = consumo_teorico_oz / 128
                else:
                    consumo_teorico = consumo_teorico_oz

                diferencia = (consumo_real - consumo_teorico) if consumo_real is not None else None
                if consumo_teorico > 0 and diferencia is not None:
                    porcentaje_error = (diferencia / consumo_teorico) * 100
                else:
                    porcentaje_error = None

                alerta = bool(porcentaje_error is not None and abs(porcentaje_error) > 15)
                resultados.append({
                    'ingrediente': ingrediente,
                    'consumo_teorico': consumo_teorico,
                    'consumo_real': consumo_real,
                    'diferencia': diferencia,
                    'porcentaje_error': porcentaje_error,
                    'alerta': alerta,
                    'consumo_teorico_oz': consumo_teorico_oz,
                })

    return resultados


def generar_reporte_inventario(fecha: date) -> str:
    diferencias = analizar_diferencias(fecha, fecha - timedelta(days=1))

    bajos = [d for d in diferencias if d['bajo_minimo']]
    cambios = [d for d in diferencias if d['delta'] not in (None, 0.0)]

    lines = [
        f'📦 <b>Reporte Inventario</b> ({fecha.strftime("%d/%m/%Y")})',
        '',
        f'🧾 Productos analizados: <b>{len(diferencias)}</b>',
        f'⚠️ Bajo mínimo: <b>{len(bajos)}</b>',
        f'🔄 Con cambios vs ayer: <b>{len(cambios)}</b>',
        '',
    ]

    if bajos:
        lines.append('🚨 <b>Stock Bajo Mínimo</b>')
        for d in bajos:
            unidad = d['unidad'] or ''
            lines.append(
                f"• <b>{d['producto']}</b>: {d['cantidad_hoy']} {unidad} (mín {d['stock_min']})"
            )
        lines.append('')

    if cambios:
        lines.append('📉 <b>Diferencias vs Ayer</b>')
        for d in cambios[:40]:
            unidad = d['unidad'] or ''
            delta = d['delta'] if d['delta'] is not None else 0
            emoji = '⬆️' if delta > 0 else '⬇️'
            lines.append(
                f"• {emoji} <b>{d['producto']}</b>: {d['cantidad_ayer']} → {d['cantidad_hoy']} {unidad} (Δ {delta:+.2f})"
            )

    if len(lines) == 6:
        lines.append('✅ Sin alertas ni cambios relevantes hoy.')

    return '\n'.join(lines)


def enviar_telegram(chat_id: str | int, texto: str) -> dict[str, Any]:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError('TELEGRAM_BOT_TOKEN no esta configurado en .env')

    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': str(chat_id),
        'text': texto,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
    }
    resp = _session.post(url, json=payload, timeout=20)
    resp.raise_for_status()
    return resp.json()


def notificacion_miercoles() -> None:
    hoy = datetime.now().date()
    diferencias = analizar_diferencias(hoy, hoy - timedelta(days=1))
    proveedores = leer_proveedores_sheet()

    bajos = [d for d in diferencias if d['bajo_minimo']]
    agrupado: dict[int | None, list[dict[str, Any]]] = {}
    for item in bajos:
        agrupado.setdefault(item['proveedor_id'], []).append(item)

    lines = [f'🧾 <b>Pedido Miércoles</b> ({hoy.strftime("%d/%m/%Y")})', '']

    if not agrupado:
        lines.append('✅ No hay productos bajo mínimo para pedir hoy.')
    else:
        for proveedor_id, items in agrupado.items():
            prov = proveedores.get(proveedor_id or -1, {})
            nombre = prov.get('nombre') or f'Proveedor {proveedor_id or "N/D"}'
            telefono = prov.get('telefono') or 'sin teléfono'
            lines.append(f'🏪 <b>{nombre}</b> ({telefono})')
            for it in items:
                lines.append(
                    f"• {it['producto']}: {it['cantidad_hoy']} {it['unidad'] or ''} (mín {it['stock_min']})"
                )
            lines.append('')

    enviar_telegram(GROUP_ID_INVENTARIO, '\n'.join(lines))


def notificacion_lunes_postres() -> None:
    postres = leer_postres_sheet()
    proveedores = leer_proveedores_sheet()

    bajo_min = []
    for p in postres:
        if p['stock_min'] is None or p['stock_actual'] is None:
            continue
        if p['stock_actual'] < p['stock_min']:
            bajo_min.append(p)

    lines = [f'🍰 <b>Control de Postres (Lunes)</b> {datetime.now().strftime("%d/%m/%Y")}', '']

    if not bajo_min:
        lines.append('✅ Todos los postres están sobre el mínimo.')
    else:
        lines.append('⚠️ <b>Postres bajo mínimo</b>')
        for p in bajo_min:
            prov = proveedores.get(p['proveedor_id'] or -1, {})
            proveedor = prov.get('nombre', f"Proveedor {p['proveedor_id'] or 'N/D'}")
            lines.append(
                f"• <b>{p['producto']}</b>: {p['stock_actual']} (mín {p['stock_min']}) | {proveedor}"
            )

    enviar_telegram(GROUP_ID_INVENTARIO, '\n'.join(lines))


def run_once() -> None:
    hoy = datetime.now().date()
    ayer = hoy - timedelta(days=1)

    try:
        asegurar_notificaciones_log()

        registros = leer_inventario_sheet()
        catalogo_licores = leer_catalogo_licores()

        # Convert gramos to oz for licores
        for r in registros:
            if r['unidad'] == 'gramos' and r['cantidad_normalizada'] is not None:
                oz = gramos_a_oz(r['producto'], r['cantidad_normalizada'], catalogo_licores)
                r['oz_calculado'] = oz
                # Store oz as normalized quantity for comparison purposes
                r['cantidad_normalizada'] = oz
                r['unidad'] = 'oz'

        guardados = guardar_inventario_postgres(registros)
        entradas = leer_entradas_sheet()
        entradas_guardadas = guardar_entradas_postgres(entradas)
        registros_hoy = sum(1 for r in registros if r.get('fecha') == hoy)

        diferencias = analizar_diferencias(hoy, ayer)
        bajos = sum(1 for d in diferencias if d['bajo_minimo'])
        cruce_cierre = analizar_consumo_cierre(hoy)
        alertas_cierre = [c for c in cruce_cierre if c['alerta']]
        hay_alertas = bool(bajos > 0 or alertas_cierre)

        resumen = [
            f'✅ Inventario sincronizado ({hoy.strftime("%d/%m/%Y")})',
            f'• Registros procesados: {len(registros)}',
            f'• Upserts en DB: {guardados}',
            f'• Entradas registradas: {entradas_guardadas}',
            f'• Bajo mínimo: {bajos}',
            '',
            generar_reporte_inventario(hoy),
        ]
        # Show who did the inventory today
        responsables_hoy = set(r['responsable'] for r in registros if r['fecha'] == hoy and r['responsable'])
        if responsables_hoy:
            resumen.append(f'👤 Responsable(s): {", ".join(sorted(responsables_hoy))}')
        if cruce_cierre:
            resumen.extend(['', '🍹 <b>Cruce Cierre vs Inventario</b>'])
            for item in cruce_cierre[:20]:
                consumo_teorico_oz = float(item.get('consumo_teorico_oz') or 0.0)
                consumo_real = item.get('consumo_real')
                pct = item.get('porcentaje_error')
                if item['alerta']:
                    signo = '+' if (pct is not None and pct >= 0) else ''
                    resumen.append(
                        f"⚠️ {item['ingrediente']}: consumo teórico {consumo_teorico_oz:.1f}oz, "
                        f"real {consumo_real:.1f}oz ({signo}{pct:.0f}%) — revisar"
                    )
                elif pct is not None and consumo_real is not None and abs(pct) <= 5:
                    resumen.append(f"✅ {item['ingrediente']}: cuadra (±5%)")
            if alertas_cierre and not any(line.startswith('⚠️') for line in resumen):
                for item in alertas_cierre[:20]:
                    consumo_teorico_oz = float(item.get('consumo_teorico_oz') or 0.0)
                    consumo_real = float(item.get('consumo_real') or 0.0)
                    pct = float(item.get('porcentaje_error') or 0.0)
                    signo = '+' if pct >= 0 else ''
                    resumen.append(
                        f"⚠️ {item['ingrediente']}: consumo teórico {consumo_teorico_oz:.1f}oz, "
                        f"real {consumo_real:.1f}oz ({signo}{pct:.0f}%) — revisar"
                    )
        resumen_text = '\n'.join(resumen)
        if registros_hoy > 0 and ((not ya_notificado_hoy('resumen_diario')) or hay_alertas):
            enviar_telegram(GROUP_ID_INVENTARIO, resumen_text)
            registrar_notificacion('resumen_diario', resumen_text)
    except (RequestException, psycopg2.Error, RuntimeError, ValueError) as exc:
        # Solo enviar alerta si no se envió en las últimas 2 horas
        # (evita loops de mensajes si el error es persistente).
        if not ya_notificado_hoy('error_monitor'):
            enviar_telegram(
                GROUP_ID_ADMIN,
                f'❌ <b>Error inventario_monitor</b>\n<code>{type(exc).__name__}: {exc}</code>',
            )
            registrar_notificacion('error_monitor', str(exc))
        print(f'[ERROR] run_once falló: {exc}', flush=True)
        # NO re-lanzar: el loop principal debe continuar, no morir.


def main() -> None:
    parser = argparse.ArgumentParser(description='Inventario Monitor')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--miercoles', action='store_true', help='Force Wednesday report')
    parser.add_argument('--lunes', action='store_true', help='Force Monday report')
    args = parser.parse_args()

    if args.once:
        run_once()
        return

    if args.miercoles:
        asegurar_notificaciones_log()
        if not ya_notificado_hoy('compras_miercoles'):
            notificacion_miercoles()
            registrar_notificacion('compras_miercoles', 'Notificacion de compras del miercoles enviada.')
        return

    if args.lunes:
        asegurar_notificaciones_log()
        if not ya_notificado_hoy('postres_lunes'):
            notificacion_lunes_postres()
            registrar_notificacion('postres_lunes', 'Notificacion de postres del lunes enviada.')
        return

    while True:
        try:
            run_once()
            now = datetime.now()
            if now.weekday() == 2 and 11 <= now.hour <= 12 and not ya_notificado_hoy('compras_miercoles'):
                notificacion_miercoles()
                registrar_notificacion('compras_miercoles', 'Notificacion de compras del miercoles enviada.')
            if now.weekday() == 0 and 7 <= now.hour <= 8 and not ya_notificado_hoy('postres_lunes'):
                notificacion_lunes_postres()
                registrar_notificacion('postres_lunes', 'Notificacion de postres del lunes enviada.')
        except Exception as loop_exc:
            # Captura de último recurso: el proceso NO debe morir aunque run_once falle.
            print(f'[CRITICAL] Error inesperado en loop principal: {loop_exc}', flush=True)
        time.sleep(INVENTARIO_CHECK_INTERVAL)


if __name__ == '__main__':
    main()
