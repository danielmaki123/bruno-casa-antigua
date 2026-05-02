# BrunoBot MVP — Issues

Issues ordenados por dependencia. Cada uno es un vertical slice independiente.

## Parallelizable

```
[#1 Bot Skeleton]     [#2 DB Migration]
       │                     │
       ├──────┬──────────────┤
       │      │              │
    [#3 LLM] [#4 Memory]    │
       │      │              │
       └──────┼──────────────┘
              │
       [#5 Message Router]
              │
       ┌──────┼──────────┐
       │      │          │
    [#6]   [#7]       [#8]
   Ventas  Cierres  Inventario
       │      │          │
       └──────┼──────────┘
              │
       [#9 Webhook HTTP]
              │
       [#10 Deploy] ← HITL
```
