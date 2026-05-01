# 🤖 Arquitectura y Flujo de Trabajo de BrunoBot

Este documento detalla el ciclo de vida de los datos dentro del ecosistema de BrunoBot, desde que se genera un evento en el restaurante (como un cierre de caja) hasta que se notifica a la administración y se almacena en la base de datos.

---

## 🌊 Flujo Principal de Datos (Mermaid Diagram)

A continuación, el diagrama de arquitectura que muestra cómo interactúan los diferentes módulos del sistema.

```mermaid
graph TD
    %% Entradas Externas
    POS[Terminal CIELO POS] -->|Envía correo automático| Gmail[Gmail API]
    BAC[Banco BAC / BANPRO] -->|Envía correo automático| Gmail
    Staff[Staff del Restaurante] -->|Actualiza conteo físico| Sheets[Google Sheets\nINVENTARIO_BEBIDAS]

    %% Monitores (Background Services)
    subgraph Servicios en EasyPanel
        GM[gmail_monitor.py\n(Escucha cada 5 min)]
        IM[inventario_monitor.py\n(Sincronización)]
        Bot[brunobot.py\n(Interacción Telegram)]
    end

    Gmail -->|Descarga PDFs| GM
    Sheets <-->|Lectura/Escritura| IM

    %% Procesamiento
    subgraph Procesamiento y Auditoría
        Parse[parse_cierre.py\n(Extrae texto de PDFs)]
        Audit[audit_cierre.py\n(Calcula faltantes y cruza datos)]
    end

    GM -->|CierrePos.pdf\nVenta_Menu.pdf| Parse
    Parse -->|Datos Estructurados| Audit

    %% Almacenamiento
    DB[(PostgreSQL Database)]
    Audit -->|Inserta ventas y cierres| DB
    GM -->|Inserta liquidaciones bancarias| DB
    IM -->|Sincroniza Catálogo de Inventario| DB

    %% Salidas
    TG[Grupo Admin Telegram]
    Audit -->|Alerta de Cierre/Faltantes| TG
    IM -->|Alerta de Stock Mínimo\nPedido Miércoles| TG
    GM -->|Notificación de Liquidación Bancaria| TG
    Bot <-->|Comandos / Consultas| TG
```

---

## ⚙️ Descripción Detallada de los Módulos

### 1. El Ojo Clínico: `gmail_monitor.py`
Este es un servicio que se ejecuta de fondo 24/7. Su trabajo es estar "leyendo" la bandeja de entrada del correo del restaurante mediante la API oficial de Google.
*   **Filtro Inteligente:** Ignora el spam y solo busca correos que contengan en el asunto frases como *"Cierre de Caja"* o correos provenientes de correos oficiales del BAC y BANPRO.
*   **Manejo de Adjuntos:** Cuando detecta un correo válido, extrae silenciosamente los archivos PDF adjuntos (ej. `CierrePos.pdf` y `Venta_Menu.pdf`).
*   **Persistencia:** Mantiene un registro interno (`processed_emails.json`) para asegurarse de no procesar ni alertar dos veces sobre el mismo correo.

### 2. El Cerebro Analítico: `parse_cierre.py` & `audit_cierre.py`
Una vez que `gmail_monitor.py` descarga los PDFs, se los pasa a estos dos scripts para que los analicen.
*   **Parseo de Texto:** Lee línea por línea el PDF de ventas y el de cierre. Convierte los textos como *"TOTAL DE VENTAS 2,628.40"* en valores numéricos reales.
*   **Auditoría Automática:** El sistema cruza las ventas declaradas en el POS contra lo ingresado. Comprueba si hay **diferencia POS**, si sobra dinero, o si hay un **Faltante** de efectivo.
*   **Inyección a Base de Datos:** Toda la información (hasta el detalle de cuántos Cantaritos se vendieron) se guarda en la base de datos `PostgreSQL` para análisis futuro en plataformas como Metabase.

### 3. El Guardián del Almacén: `inventario_monitor.py`
Este servicio conecta el mundo físico (las botellas) con el sistema.
*   **Lectura de Google Sheets:** Constantemente lee la pestaña `INVENTARIO_BEBIDAS` donde el staff anota los conteos físicos.
*   **Evaluación de Stock:** Compara el inventario actual con el "Stock Mínimo" definido para cada producto.
*   **Alertas y Compras:** Si algo está bajo, lanza una alerta roja en Telegram. Además, todos los miércoles genera un reporte agrupado por Proveedor con la lista exacta de lo que hay que comprar.

### 4. El Vocero: Notificaciones de Telegram
Telegram es la "pantalla" del sistema. BrunoBot no espera a que le preguntes; él te avisa en tiempo real de lo que importa.
*   **Mensaje de Cierre:** Alerta con el total de ventas, desglose de métodos de pago, el top 5 de productos vendidos y, lo más importante, si el cajero tuvo algún faltante de dinero.
*   **Mensaje de Banco:** Alerta en cuanto cae la liquidación real del banco.

---

## 🏗️ La Base de Datos (PostgreSQL)

Todo el ecosistema converge en la base de datos, estructurada en tablas especializadas:

| Tabla | Función Principal |
| :--- | :--- |
| `cierres_caja` | Guarda el resumen de cada día: Quién cerró la caja, cuánto dinero entró por tarjetas, efectivo, faltantes y sobrantes. |
| `ventas_detalle` | Guarda el detalle microscópico: Cada platillo y trago vendido, cantidad y precio. Ideal para armar menús rentables. |
| `liquidaciones_banco` | El registro crudo de lo que el banco depositó, para futura conciliación automática contra las tarjetas del POS. |
| `inventario_catalogo` | La copia interna de Bruno de tu Excel, para saber qué proveedores y stock mínimo tiene cada bebida. |

## 🚀 Resumen del Valor Operativo

Con este flujo, **BrunoBot elimina el trabajo manual de auditoría**. Un gerente ya no tiene que revisar el PDF del POS y el portal del banco manualmente; Bruno cruza los datos, extrae lo importante, guarda el historial financiero y te avisa al celular solo de las métricas clave y las anomalías.
