# 🎨 DarkPause — UI Redesign Plan

> **Problema:** Las funciones del panel no se entienden. La UI es confusa.
> **Fecha:** 2026-02-19
> **Estado: ✅ COMPLETADO** — Panel refactorizado en módulos (`ui/sections/`), secciones colapsables, y Freedom-style web blocking añadido.

---

## 🔍 Diagnóstico

### El problema central

El panel actual organiza las funciones por **implementación técnica**, no por **modelo mental del usuario**. Hay **4 formas diferentes de hacer lo mismo** (iniciar un blackout) repartidas en secciones que parecen features independientes.

### Mapa de confusión actual

| Sección actual       | Qué hace realmente        | Por qué confunde                                |
| :------------------- | :------------------------ | :---------------------------------------------- |
| "Programar Hora"     | Blackout a hora fija      | ¿Programar qué? No dice "blackout"              |
| "Quick Focus"        | Blackout inmediato/delay  | "En 0 min, Por 25 min" es críptico              |
| "Shortcuts" Pomo 25  | Blackout 25min + break 5m | Solo se entiende si conoces Pomodoro            |
| "Schedules"          | Blackout semanal auto     | Ok, pero visualmente igual que "Programar Hora" |
| Lock Mode (checkbox) | Hace irreversible         | Está bajo Quick Focus pero afecta a TODO        |
| Deep Work            | Firewall allowlist        | Mezclado entre secciones de blackout            |
| Cola de Ejecución    | Tareas pendientes         | Escondida al final, no sabes qué esperar        |

### Insight clave

El usuario tiene **3 preguntas mentales** cuando abre el panel:

1. 📊 **"¿Cuánto llevo hoy?"** → Estado actual
2. 🌌 **"Quiero bloquearme"** → Acción principal
3. ⚙️ **"Quiero que esto pase solo"** → Automatización

---

## ✨ Propuesta: Rediseño por Modelo Mental

### Nueva estructura (5 bloques claros)

```
┌─────────────────────────────────────────────┐
│              🌌 darkpause                    │
│         Distraction Freedom Protocol         │
│                                              │
│ ═══════════════════════════════════════════  │
│                                              │
│  📊 USO DE HOY                               │
│  ─────────────────────────────────────────   │
│  📸 Instagram   ████░░░░░░░  02:30 / 10m    │
│  ▶ YouTube     ██████████░  55:00 / 60m    │
│                                              │
│ ═══════════════════════════════════════════  │
│                                              │
│  🌌 BLOQUEAR PANTALLA                        │
│  ─────────────────────────────────────────   │
│                                              │
│  Duración:                                   │
│  ┌──────┐ ┌──────┐ ┌────────────────────┐   │
│  │ 25 m │ │ 50 m │ │    ___  min        │   │
│  └──────┘ └──────┘ └────────────────────┘   │
│                                              │
│  ☐ Retrasar inicio ___ min                   │
│  ☐ 🔒 Lock Mode (sin cancelación)           │
│                                              │
│         ┌────────────────────────┐           │
│         │    🌌 BLOQUEAR         │           │
│         └────────────────────────┘           │
│                                              │
│ ═══════════════════════════════════════════  │
│                                              │
│  ⏰ PROGRAMAR                                │
│  ─────────────────────────────────────────   │
│                                              │
│  ┌─ Una vez ────────────────────────────┐    │
│  │ Hoy a las [16:00] durante [60] min   │    │
│  │                        [Programar]   │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ┌─ Cada semana ────────────────────────┐    │
│  │ ☑L ☑M ☑X ☑J ☑V ☐S ☐D               │    │
│  │ De [09:00] a [17:00]                 │    │
│  │ Nombre: [Work Mode]                  │    │
│  │                      [+ Añadir]      │    │
│  │                                      │    │
│  │ ✓ Work Mode · LMXJV · 09:00-17:00   │    │
│  └──────────────────────────────────────┘    │
│                                              │
│ ═══════════════════════════════════════════  │
│                                              │
│  🌐 DEEP WORK                                │
│  ─────────────────────────────────────────   │
│  Bloquea todo internet excepto webs de       │
│  trabajo (Google Docs, GitHub, etc.)         │
│                                              │
│  ┌────────────────────────────────────┐      │
│  │       🌐 Activar Deep Work         │      │
│  └────────────────────────────────────┘      │
│                                              │
│ ═══════════════════════════════════════════  │
│                                              │
│  📋 PENDIENTE                                │
│  ─────────────────────────────────────────   │
│  ⏰ Hoy 16:00 → 60 min                      │
│  🍅 En cola → 25 min 🔒                     │
│                                              │
│          ⚠️ NO ESCAPE. NO MERCY.             │
└─────────────────────────────────────────────┘
```

### Qué cambia y por qué

| #   | Cambio                                                | Rationale                                                               |
| :-- | :---------------------------------------------------- | :---------------------------------------------------------------------- |
| R1  | "Quick Focus" + "Shortcuts" → **"Bloquear Pantalla"** | Una sola sección para la acción principal. Presets + custom unificados. |
| R2  | "Programar Hora" + "Schedules" → **"Programar"**      | Todo lo que es "futuro" va junto: una vez + semanal                     |
| R3  | Lock Mode sube al bloque de acción principal          | Porque aplica a TODO blackout, no solo a Quick Focus                    |
| R4  | "Plataformas" → **"Uso de Hoy"**                      | Nombre más claro: le dice al usuario QUÉ está mirando                   |
| R5  | "Cola de Ejecución" → **"Pendiente"**                 | Lenguaje más humano, menos técnico                                      |
| R6  | Duración con presets visuales (25/50/custom)          | Un clic para lo común, input para lo custom. Elimina "Pomo" críptico.   |
| R7  | "Retrasar inicio" como checkbox opcional              | En vez de "En X min" obligatorio con "0" por defecto (confuso)          |
| R8  | Bot ón principal "🌌 BLOQUEAR" grande y claro         | Acción obvia y prominente                                               |
| R9  | Separadores visuales entre bloques                    | Hierarchy visual clara                                                  |

### Lo que NO cambia (funcionalidad intacta)

- Toda la lógica de `_add_timer_task`, `_add_fixed_task`, `_add_preset` se mantiene
- El callback `on_start_blackout(minutes, locked)` no cambia
- `_start_task_monitor` y los loops siguen igual
- Deep Work (allowlist) funciona exactamente igual
- Schedules recurrentes: misma funcionalidad

---

## 📐 Especificaciones Técnicas

### Archivos afectados

- `ui/control_panel.py` — Reescritura de `_create_ui()` y las secciones
- Ningún otro archivo cambia (solo UI, no lógica)

### Desglose de cambios

1. `_create_platform_section()` → Renombrar título a "📊 Uso de Hoy"
2. `_create_schedule_section()` → Mover dentro de nuevo frame "⏰ Programar"
3. `_create_quick_focus_section()` + `_create_shortcuts_section()` → FUSIONAR en `_create_blackout_section()`
4. `_create_allowlist_section()` → Sin cambios funcionales, solo visual
5. `_create_recurring_schedule_section()` → Mover dentro del frame "⏰ Programar"
6. `_create_task_list()` → Renombrar a "📋 Pendiente"
7. Lock Mode checkbox → Mover al bloque "Bloquear Pantalla"
8. Presets (25/50) → Botones de selección de duración, no "shortcuts" separados

### Comportamiento de los presets de duración

- Al pulsar "25 m" → se rellena el campo de duración con 25
- Al pulsar "50 m" → se rellena el campo de duración con 50
- El usuario puede escribir cualquier número en el campo custom
- El botón "BLOQUEAR" ejecuta la misma lógica que `_add_timer_task()`

---

## ✅ Checklist

- [x] Rediseñar `_create_ui()` con nuevo orden
- [x] Fusionar Quick Focus + Shortcuts en "Bloquear Pantalla"
- [x] Agrupar Programar Hora + Schedules en "Programar"
- [x] Mover Lock Mode al bloque principal
- [x] Renombrar secciones
- [x] Añadir separadores visuales
- [x] Implementar preset buttons para duración
- [x] Verificar que toda la funcionalidad sigue igual
- [x] Test visual del panel
