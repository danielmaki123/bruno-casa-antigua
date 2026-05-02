# CONTEXT.md — BrunoBot

## Domain Glossary

| Term | Definition | Not to be confused with |
|---|---|---|
| **Bruno** | The Telegram bot and restaurant OS for Casa Antigua. Single identity across all groups. | Not a customer chatbot. Not a web app. |
| **Cierre** | Daily POS closing report. Arrives as PDF via Gmail. Contains sales totals, payment methods, cash count, differences. | Not the same as Venta Menú. |
| **Venta Menú** | Itemized sales report per product. Arrives as PDF alongside Cierre. Used for analytics and consumption tracking. | Not the Cierre (which is financial summary). |
| **Área** | Operational zone of the restaurant: Cocina, Barra, Almacén, Sushi, Birria, Pizza. Each has its own products. | Not a Telegram group. |
| **Conteo** | Physical inventory count done by staff. Currently captured in Google Sheets daily. | Not theoretical consumption (which is calculated from sales × recipes). |
| **Stock mínimo** | Threshold below which Bruno triggers an alert. Defined per product per area. | Not stock crítico (future: urgent level below mínimo). |
| **Consumo teórico** | Calculated ingredient usage based on sales × recipe definitions. Used to detect discrepancies vs physical count. | Not actual consumption (which is measured by inventory difference). |
| **Diferencia** | Gap between expected and actual values. Applies to: POS cash vs counted cash, theoretical consumption vs physical count. | Context-dependent — always specify what's being compared. |
| **Compra sugerida** | Purchase recommendation: `max(stock_objetivo - conteo_real, 0)`. Requires admin approval before action. | Not an order. Bruno suggests, humans approve. |

## Telegram Groups

| Group | ID | Purpose | Bruno behavior |
|---|---|---|---|
| **Inventario** | `-5240974489` | Stock operations: entries, exits, counts, alerts | Responds to queries + sends proactive alerts |
| **Administrativo** | `-4944632677` | Financial: closings, differences, approvals, purchases | Responds to queries + sends cierre summaries |
| **Team** | `-5181251045` | Broadcast only: shifts, rotations, announcements | Bruno writes only. Ignores user messages. |
| **Private chat** | per-user | Full access for Admin/Andrea/Daniel | Responds to everything |

## Access Control

| Role | Groups | Private | Can approve purchases |
|---|---|---|---|
| Admin | All | Full access | Yes |
| Andrea | Admin, Inventario | Full access | Yes |
| Daniel | Admin, Inventario | Full access | Yes |
| Staff (Flor, Jean, Jorge, etc.) | Team (read), Inventario (interact) | Limited (stock queries only) | No |

## System Boundaries

| System | Role | Owns |
|---|---|---|
| **Bruno (Python bot)** | All logic, all Telegram, all LLM | Messages, queries, formatting, responses |
| **PostgreSQL** | Source of truth | All persistent data |
| **Google Sheets** | Input interface for inventory | Daily counts (bridge until web app) |
| **n8n** | External triggers only | Gmail watch, cron schedules, Sheets change detection |
| **Kimi (Moonshot)** | Conversational layer | Natural language understanding + response generation |
| **Metabase** | Visualization | Dashboards (reads Postgres directly) |
| **EasyPanel** | Infrastructure | Docker services, SSL, domains |

## Data Flow

```
Gmail (PDF) → n8n trigger → HTTP webhook → Bruno bot → parse + save → Postgres
                                                     → format + send → Telegram Admin

Sheets (inventory) → n8n trigger → HTTP webhook → Bruno bot → sync → Postgres
                                                             → alert if low → Telegram Inventario

User (Telegram) → Bruno bot → classify intent (Kimi) → query Postgres → format (Kimi) → reply
```
