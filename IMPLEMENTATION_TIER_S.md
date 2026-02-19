# 🏆 Tier S — Implementation Plan

> Features: S2 (Lock Mode), S3 (Schedules), S4 (Notifications), S5 (Allowlist)  
> Excluido: S1 (Estadísticas de uso)  
> **Estado: ✅ COMPLETADO** — 2026-02-18

---

## Orden de Implementación

1. ✅ **S4: Notificaciones** (~30 min) — Mínimo cambio, base para otras features
2. ✅ **S2: Lock Mode** (~1h) — Crítico, toca blackout + control panel + darkpause.py
3. ✅ **S5: Allowlist Mode** (~1h) — Nuevo modo, toca firewall_manager + control_panel
4. ✅ **S3: Schedules Recurrentes** (~2h) — Nuevo módulo core/scheduler.py + UI

---

## S4: Notificaciones de Tiempo Restante ✅

### Archivos afectados:

- `core/config.py` — `WARNING_STEPS: list[int] = [5, 1]` + `WARNING_THRESHOLD_MINUTES` derivado
- `ui/tray.py` — `_warnings_sent: set[int]` con multi-step loop bajo `_state_lock`

### Cambios implementados:

1. `config.py`: `WARNING_STEPS` reemplaza threshold único; `WARNING_THRESHOLD_MINUTES = max(WARNING_STEPS)` para compat
2. `tray.py` → `PlatformSession.__init__`: `_warnings_sent: set[int] = set()`
3. `tray.py` → `_timer_loop`: Loop sobre `WARNING_STEPS`, acceso protegido por `_state_lock`
4. `tray.py` → `start()`: Reset `_warnings_sent = set()` bajo lock
5. `tray.py` → import: Añadido `WARNING_STEPS` al import

---

## S2: Lock Mode (Nuclear) ✅

### Archivos afectados:

- `ui/control_panel.py` — Checkbox Lock + confirmación dialog
- `ui/blackout.py` — Campo `locked` en state, `stop()` bloqueado, visual indicator
- `ui/tray.py` — Callback signature actualizada
- `darkpause.py` — Boot check para locked state

### Cambios implementados:

1. `blackout.py` → `_save_blackout_state(locked=)`: Persiste campo `locked` en JSON
2. `blackout.py` → `load_persisted_blackout()`: Retorna `tuple[int, bool] | None`
3. `blackout.py` → `ScreenBlackout`: Propiedad `is_locked`, `start(locked=)`, `stop(force=)`
4. `blackout.py` → Overlay: Texto "🔒 LOCKED — NO ESCAPE" visible en lock mode
5. `control_panel.py`: Checkbox "🔒 Lock Mode (irreversible)" + `_confirm_lock_mode()` dialog
6. `control_panel.py`: Todos los task creation methods pasan `locked` y confirman con usuario
7. `tray.py` + `control_panel.py`: Callback `Callable[[int, bool], None]`
8. `darkpause.py` → crash recovery: Si `locked`, restaura blackout locked

---

## S5: Allowlist Mode ✅

### Archivos afectados:

- `core/config.py` — `ALLOWLIST_DOMAINS`, `ALLOWLIST_REFRESH_SECONDS`
- `core/firewall_manager.py` — Allowlist engine completa + crash recovery
- `ui/control_panel.py` — Botón toggle "🌐 Deep Work"
- `darkpause.py` — Cleanup on exit + orphan cleanup on boot

### Cambios implementados:

1. `config.py`: 15 dominios de trabajo esenciales + refresh cada 300s
2. `firewall_manager.py`: `_resolve_domain_ips()`, `_get_all_allowed_ips()`, `_apply_allowlist_rules()`
3. `firewall_manager.py`: `enable_allowlist_mode()`, `disable_allowlist_mode()`, `is_allowlist_active()`
4. `firewall_manager.py`: Refresh thread que re-resuelve IPs cada 5 min
5. `firewall_manager.py`: Estado persistido en `allowlist_active.flag` para crash recovery
6. `firewall_manager.py`: `cleanup_orphaned_allowlist()` limpia reglas huérfanas en boot
7. `control_panel.py`: Sección Deep Work con botón toggle (purple → red)
8. `darkpause.py`: Cleanup allowlist on exit + orphan cleanup on startup

---

## S3: Schedules Recurrentes ✅

### Archivos nuevos:

- `core/scheduler.py` — Módulo completo (~330 líneas)

### Archivos afectados:

- `ui/control_panel.py` — UI para crear/ver schedules
- `darkpause.py` — Iniciar scheduler thread

### Cambios implementados:

1. `scheduler.py`: Clase `Schedule` con serialización/deserialización
2. `scheduler.py`: Clase `ScheduleManager` con JSON persistence (`schedules.json`)
3. `scheduler.py`: Background thread que chequea cada 60s, `_triggered_today` evita re-trigger
4. `scheduler.py`: Thread safety via `threading.Lock`
5. `control_panel.py`: Sección "⏰ Schedules Recurrentes" con checkboxes L-D, hora inicio/fin
6. `control_panel.py`: Listbox mostrando schedules existentes con estado ✓/✗
7. `darkpause.py`: `ScheduleManager` inicializado antes del panel, pasado como dependencia

---

## 🔍 Code Review Post-Implementation

### Bugs encontrados y corregidos:

| #     | Severidad | Issue                                                            | Fix                                                  |
| :---- | :-------- | :--------------------------------------------------------------- | :--------------------------------------------------- |
| BUG-1 | Media     | `_warnings_sent` race condition entre timer thread y `start()`   | Acceso protegido bajo `_state_lock`                  |
| BUG-2 | Baja      | `remaining_minutes()` llamaba `is_active_now()` redundantemente  | Eliminada comprobación duplicada                     |
| BUG-3 | 🔴 Alta   | `_allowlist_stop_event` no se reseteaba antes de aplicar reglas  | `clear()` movido antes de `_apply_allowlist_rules()` |
| BUG-4 | Media     | Loop de 200 iteraciones `netsh show rule` innecesariamente lento | Reemplazado por cleanup de sufijos conocidos         |

### Mejoras de UX aplicadas:

| #      | Issue                                             | Fix                                                      |
| :----- | :------------------------------------------------ | :------------------------------------------------------- |
| WARN-1 | Sin feedback visual de Lock Mode en overlay       | "🔒 LOCKED — NO ESCAPE" en texto del blackout            |
| WARN-2 | Allowlist no persistía estado para crash recovery | `allowlist_active.flag` + `cleanup_orphaned_allowlist()` |
| WARN-3 | `import time` sin usar en scheduler.py            | Eliminado                                                |
| WARN-5 | Sin confirmación al activar Lock Mode             | `_confirm_lock_mode()` dialog antes de crear tasks       |

---

## 🎨 Polish Pass (Manual Refinements)

Refinamientos adicionales aplicados manualmente al `control_panel.py`:

| #   | Cambio                                                                        | Rationale                                                                          |
| :-- | :---------------------------------------------------------------------------- | :--------------------------------------------------------------------------------- |
| P1  | `_confirm_lock_mode()` se llama **después** de validar inputs                 | Evita mostrar el dialog de confirmación si el usuario ya tiene un error de formato |
| P2  | Break tasks usan `locked: False` explícito                                    | Los breaks nunca deben ser irreversibles, incluso si el work session tenía lock    |
| P3  | `_refresh_platforms()` envuelto en `try/except` con `finally` para reschedule | Si un tick falla, el loop no muere — siempre se reprograma                         |
| P4  | Task monitor usa `any_triggered` para batch update                            | Solo actualiza la UI una vez, no por cada task triggered                           |
| P5  | `_platform_widgets` inicializado en `__init__`                                | Asegura que el dict existe antes de que cualquier método lo use                    |
| P6  | `import os` movido a nivel de módulo                                          | Estaba dentro de `__init__` como import local innecesario                          |
| P7  | Task list migrada de `tk.Listbox` a `CTkScrollableFrame`                      | Consistencia visual con el resto del panel CustomTkinter                           |

---

## 🖥️ Taskbar Integration (Panel Persistence)

### Cambios en `control_panel.py`:

| #   | Cambio                                                      | Rationale                                                                   |
| :-- | :---------------------------------------------------------- | :-------------------------------------------------------------------------- |
| T1  | `WM_DELETE_WINDOW` → `iconify()` en vez de `withdraw()`     | Panel se minimiza a barra de tareas en vez de desaparecer                   |
| T2  | `wm_attributes('-toolwindow', False)` forzado               | CTkToplevel con root withdrawn puede no aparecer en taskbar                 |
| T3  | Binding `<Map>` + `<Unmap>` para detectar restore/minimize  | Win+D, Win+M, click en taskbar pausan/resumen loops automáticamente         |
| T4  | `_loops_active` flag para idempotencia                      | Evita doble inicio de loops cuando `show()` y `<Map>` coinciden             |
| T5  | `_pause_loops()` / `_resume_loops()` extraídos como métodos | DRY — compartidos entre `show`, `hide`, `_minimize_to_taskbar`, y OS events |

### Cambios en `darkpause.py`:

| #   | Cambio                                      | Rationale                                       |
| :-- | :------------------------------------------ | :---------------------------------------------- |
| T6  | `root.after(2000, open_panel)` en boot      | Panel se abre automáticamente al encender el PC |
| T7  | Skip auto-open si hay crash recovery activo | No abrir panel detrás de un blackout fullscreen |

### Senior review (taskbar):

| #      | Severidad | Issue                                         | Fix                                        |
| :----- | :-------- | :-------------------------------------------- | :----------------------------------------- |
| BUG-1  | 🔴 Alta   | CTkToplevel podría no aparecer en taskbar     | `wm_attributes('-toolwindow', False)` (T2) |
| BUG-2  | 🟡 Media  | Win+D/Win+M no pausaban loops                 | Binding `<Unmap>` (T3)                     |
| WARN-1 | 🟢 Baja   | Doble `_resume_loops` al restaurar desde tray | Flag `_loops_active` (T4)                  |
| WARN-2 | 🟢 Baja   | Auto-open conflicta con crash recovery        | Condición `if persisted is None` (T7)      |

---

## Checklist Final

- [x] S4: WARNING_STEPS en config.py
- [x] S4: Lógica multi-step en tray.py (con lock protection)
- [x] S2: locked field en blackout_state.json
- [x] S2: Checkbox Lock en control_panel.py
- [x] S2: Boot lock check en darkpause.py
- [x] S2: Visual indicator en blackout overlay
- [x] S2: Confirmación dialog antes de Lock Mode (post-validation)
- [x] S2: Break tasks nunca locked
- [x] S5: ALLOWLIST_DOMAINS en config.py
- [x] S5: Firewall allowlist en firewall_manager.py
- [x] S5: Crash recovery con flag file
- [x] S5: Orphan cleanup en boot (darkpause.py)
- [x] S5: Toggle UI en control_panel.py
- [x] S5: Cleanup on app exit
- [x] S3: core/scheduler.py módulo nuevo
- [x] S3: UI schedules en control_panel.py
- [x] S3: Init scheduler en darkpause.py
- [x] Code review: 4 bugs corregidos
- [x] Code review: 4 mejoras UX aplicadas
- [x] Polish pass: 7 refinamientos aplicados
- [x] Taskbar: Auto-open on boot
- [x] Taskbar: Minimize to taskbar (iconify)
- [x] Taskbar: Force toolwindow=False
- [x] Taskbar: Map/Unmap event bindings
- [x] Taskbar: \_loops_active idempotency guard
- [x] Taskbar: Skip auto-open on crash recovery
- [x] Documentación: README.md, PLAN_V2.md, IMPLEMENTATION_TIER_S.md actualizados
- [x] Auto-start: Fix `SetCurrentProcessExplicitAppUserModelID` (nombre Win32 correcto)
- [x] Auto-start: Paquetes instalados en Python 3.11 (la versión usada por Task Scheduler)
- [x] Auto-start: `_flush_log()` forzado en secciones críticas para pythonw debugging
- [x] Auto-start: `install.bat` → XML task con `<WorkingDirectory>` + sin restricción batería
- [x] Auto-start: `sys.path.insert` + `os.chdir` para CWD correcto desde Task Scheduler
- [x] Auto-start: `open_panel()` con try/except + logging para diagnóstico
- [x] Documentación: TROUBLESHOOTING.md actualizado con secciones 8-10 (auto-start)

---

## 🔧 Post-Implementation: UI Refactoring (2026-02-19)

Tras completar Tier S, el panel fue refactorizado para mejorar mantenibilidad y UX:

| Cambio               | Detalle                                                                                          |
| :------------------- | :----------------------------------------------------------------------------------------------- |
| **Modularización**   | `control_panel.py` → orquestador. Lógica movida a `ui/sections/` (5 módulos)                     |
| **Design Tokens**    | Nuevo `ui/theme.py` centraliza colores, fuentes y spacing                                        |
| **Widgets**          | `ui/widgets.py` con `CollapsibleFrame` reutilizable                                              |
| **Web Blocking**     | `ui/sections/web_block.py` — Freedom-style: seleccionar → duración → countdown → auto-desbloqueo |
| **Secciones Toggle** | Todas las secciones son colapsables (click en header para expandir/colapsar)                     |

### Archivos nuevos:

- `ui/theme.py` — Design tokens
- `ui/widgets.py` — `CollapsibleFrame`
- `ui/sections/__init__.py` — Package exports
- `ui/sections/blackout.py` — 🌌 Bloquear Pantalla
- `ui/sections/web_block.py` — 🚫 Bloquear Webs
- `ui/sections/schedule.py` — ⏰ Programar
- `ui/sections/allowlist.py` — 🌐 Deep Work
- `ui/sections/task_queue.py` — 📋 Pendiente
