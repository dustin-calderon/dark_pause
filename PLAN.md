# 🌌 DarkPause v2.0 — Migration & Refactoring Plan

## Objetivo

Fusionar **InnerCrab** (limitador de plataformas por tiempo + bloqueo de porno) dentro de **DarkPause** (bloqueador de pantalla completa para focus). El resultado es una **única aplicación de disciplina digital** que:

1. Vive en el **System Tray** (invisible, siempre corriendo).
2. **Limita el tiempo** en Instagram, YouTube, etc. (hosts file + kill process).
3. **Bloquea permanentemente** sitios de contenido adulto.
4. **Bloquea toda la pantalla** con overlay negro para sesiones de enfoque (Pomodoro).
5. Se invoca con **Ctrl+Alt+D** para abrir el panel de control.
6. **Arranca automáticamente** al encender el PC (Task Scheduler, con admin, sin ventana).

---

## Origen de los archivos

| Módulo          | Origen                                                 | Destino                   |
| --------------- | ------------------------------------------------------ | ------------------------- |
| Hosts blocking  | `inner-crab/hosts_manager.py`                          | `core/hosts_manager.py`   |
| Process killing | `inner-crab/process_manager.py`                        | `core/process_manager.py` |
| Usage tracking  | `inner-crab/usage_tracker.py`                          | `core/usage_tracker.py`   |
| Icon generation | `inner-crab/icon_generator.py`                         | `core/icon_generator.py`  |
| Platform config | `inner-crab/config.py`                                 | `core/config.py`          |
| System tray     | `inner-crab/tray_app.py`                               | `ui/tray.py`              |
| Screen blackout | `dark_pause/darkpause.py` (clase DarkPauseApp)         | `ui/blackout.py`          |
| Control panel   | `dark_pause/darkpause.py` (UI inputs/shortcuts)        | `ui/control_panel.py`     |
| Entry point     | `inner-crab/inner_crab.py` + `dark_pause/darkpause.py` | `darkpause.py`            |
| AHK launcher    | `dark_pause/launcher.ahk`                              | `scripts/launcher.ahk`    |
| AHK watchdog    | `dark_pause/watchdog.ahk`                              | `scripts/watchdog.ahk`    |

---

## Arquitectura de Carpetas (Target)

```
D:\Code Projects\dark_pause\
│
├── assets/                        # Recursos visuales
│   ├── icon.ico                   # Icono de la app (existente)
│   ├── icon.png                   # Icono PNG (existente)
│   └── screenshot.png             # Captura del panel de control
│
├── core/                          # Lógica de negocio (sin UI)
│   ├── __init__.py
│   ├── config.py                  # Toda la configuración centralizada
│   │                                - Platforms (IG, YT) con dominios y límites
│   │                                - Permanent block domains (porno)
│   │                                - Colores, constantes globales
│   │                                - Paths (hosts file, app data dir)
│   ├── hosts_manager.py           # Lectura/escritura del hosts file
│   │                                - block_platform() / unblock_platform()
│   │                                - block_permanent_domains()
│   │                                - DNS flush, backup, atomic writes
│   ├── process_manager.py         # Detección y kill de procesos
│   │                                - is_app_running() / kill_app()
│   │                                - Fallback PowerShell para UWP apps
│   ├── usage_tracker.py           # Tracking de uso por plataforma/día
│   │                                - add_usage() / get_remaining_seconds()
│   │                                - Atomic JSON writes
│   │                                - Per-platform thread locks
│   └── icon_generator.py          # Generador de iconos para el tray
│                                    - create_icon(state, text)
│                                    - Estados: BLOCKED, ACTIVE, WARNING, PAUSED
│
├── ui/                            # Todo lo visual
│   ├── __init__.py
│   ├── tray.py                    # System Tray (pystray)
│   │                                - Menú con Start/Pause por plataforma
│   │                                - Botón "🌌 DarkPause" para activar blackout
│   │                                - Botón "Salir"
│   │                                - Timer dinámico con callables
│   ├── blackout.py                # Overlay de pantalla completa
│   │                                - Multi-monitor support (screeninfo)
│   │                                - Timer countdown en el overlay
│   │                                - keep_focus() anti-bypass loop
│   └── control_panel.py           # Panel de control (CustomTkinter)
│                                    - Quick Focus (bloquear en X min)
│                                    - Programar hora fija
│                                    - Pomodoro shortcuts (25/5, 50/10)
│                                    - Cola de tareas
│                                    - Se abre/cierra sin matar el proceso
│
├── scripts/                       # Scripts de Windows
│   ├── launcher.ahk               # Ctrl+Alt+D → abre/cierra control panel
│   └── watchdog.ahk               # Vigila que el overlay no muera
│
├── darkpause.py                   # Entry point principal
│                                    - Checks admin privileges
│                                    - Requests UAC elevation (pythonw)
│                                    - Inicia tray icon
│                                    - Bloquea plataformas + porno en hosts
│                                    - Logging setup
│                                    - Crash handler (fail-safe block all)
│
├── run.bat                        # Launcher silencioso con UAC
├── install.bat                    # Registra auto-start en Task Scheduler
├── requirements.txt               # pystray, Pillow, customtkinter, screeninfo
├── README.md                      # Documentación actualizada
├── PLAN.md                        # Este archivo
└── LICENSE                        # MIT (existente)
```

---

## Fases de Implementación

### Fase 0: Preparación

- [x] Commit del estado actual de `dark_pause` (backup)
- [x] Crear estructura de carpetas: `core/`, `ui/`, `scripts/`
- [x] Crear `__init__.py` vacíos en `core/` y `ui/`
- [x] Mover `launcher.ahk` y `watchdog.ahk` a `scripts/`

### Fase 1: Migrar Core de InnerCrab

- [x] Copiar `config.py` → `core/config.py`
- [x] Copiar `hosts_manager.py` → `core/hosts_manager.py`
- [x] Copiar `process_manager.py` → `core/process_manager.py`
- [x] Copiar `usage_tracker.py` → `core/usage_tracker.py`
- [x] Copiar `icon_generator.py` → `core/icon_generator.py`
- [x] Actualizar todos los imports internos (`from config import` → `from core.config import`)

### Fase 2: Migrar y Refactorizar UI

- [x] Crear `ui/tray.py` basado en `tray_app.py` de InnerCrab
  - Actualizar imports a `core.*`
  - Añadir ítem "🌌 DarkPause" al menú del tray
  - Añadir ítem "⚙️ Panel de Control" al menú del tray
- [x] Crear `ui/blackout.py` extrayendo la lógica de overlay de `darkpause.py`
  - Clase `ScreenBlackout` independiente
  - Métodos: `start(minutes)`, `stop()`, `is_active`
  - Multi-monitor support
  - keep_focus() loop
- [x] Crear `ui/control_panel.py` extrayendo la UI de CustomTkinter de `darkpause.py`
  - Clase `ControlPanel` que extiende `ctk.CTkToplevel` (no `ctk.CTk`)
  - Se abre/cierra sin matar el proceso principal
  - Secciones: Schedule, Quick Focus, Pomodoro Shortcuts, Task Queue
  - Callback al blackout: `on_start_blackout(minutes)`

### Fase 3: Entry Point Unificado

- [x] Reescribir `darkpause.py` como entry point:
  - Admin check + UAC elevation (de InnerCrab)
  - Logging setup (fichero + consola)
  - Bloqueo permanente de porno (hosts)
  - Bloqueo inicial de plataformas (hosts)
  - Inicio del System Tray (proceso principal)
  - Crash handler fail-safe
- [x] Single-instance check (del socket de DarkPause original)

### Fase 4: Integración Tray ↔ Control Panel ↔ Blackout

- [x] Desde el tray menu: "🌌 Focus Mode" → abre Control Panel
- [x] Desde el tray menu: "🍅 Pomo 25" → activa blackout directamente (25 min)
- [x] Desde el Control Panel: "GO" / "Programar" → activa blackout
- [x] El blackout callback notifica al tray cuando termina

### Fase 5: Scripts y Auto-arranque

- [x] Actualizar `scripts/launcher.ahk` para nueva ubicación
- [x] Actualizar `scripts/watchdog.ahk` para vigilar `pythonw`
- [x] Crear `run.bat` con UAC silencioso
- [x] Crear `install.bat` con Task Scheduler
- [x] Actualizar `requirements.txt`

### Fase 6: Testing & Polish

- [x] Verificar compilación de todos los módulos
- [x] Verificar imports de todos los módulos core
- [x] Test: arranque con admin → tray icon visible
- [x] Test: menú tray → Start/Pause IG funciona
- [x] Test: menú tray → Focus Mode abre panel
- [x] Test: Ctrl+Alt+D abre/cierra panel
- [x] Test: Pomo 25 → blackout se activa
- [x] Test: Blackout termina → tray se actualiza
- [x] Test: Porno bloqueado siempre
- [x] Test: install.bat → arranca al reiniciar
- [x] Actualizar README.md

### Fase 7: Anti-Bypass Hardening (NUEVO)

Implementación de medidas avanzadas para evitar que el usuario se salte los bloqueos:

- [x] **DNS Lock (Firewall):** Bloquear servidores DNS públicos (8.8.8.8, 1.1.1.1, etc) via `firewall_manager.py`.
- [x] **DoT Lock:** Bloquear puerto 853 (DNS-over-TLS).
- [x] **Integrity Monitor:** Loop en background (30s) que verifica y repara el hosts file si es modificado externamente.
- [x] **Persistent Blackout:** Estado del blackout guardado en disco (`blackout_state.json`) para sobrevivir reinicios/crashes.
- [x] **Uninstall Cleanup:** Limpiar reglas de firewall al desinstalar via `install.bat`.

---

## Decisiones Arquitectónicas

### 1. ¿Quién es el proceso principal?

**El System Tray (pystray).** Es el proceso que vive siempre. El Control Panel (CTk) se abre como ventana secundaria (Toplevel) cuando el usuario lo pide.

### 2. ¿Cómo coexisten pystray y CustomTkinter?

pystray corre su propio event loop en un thread. CustomTkinter necesita el mainloop de Tkinter. Solución:

- pystray se inicia con `icon.run(setup=...)` en un thread separado (`threading.Thread`).
- Tkinter corre en el **thread principal** (requisito de Tk).
- La ventana CTk comienza **oculta** (`withdraw()`), y se muestra (`deiconify()`) cuando el usuario hace clic en "Panel de Control" o pulsa Ctrl+Alt+D.

### 3. ¿Qué pasa con el socket de single-instance?

Se mantiene. Evita que se lancen múltiples instancias. El puerto 45678 sigue siendo el mecanismo.

### 4. ¿El admin es obligatorio?

**Sí.** Sin admin no se puede modificar el hosts file ni las reglas del firewall. El entry point pide UAC si no es admin.

### 5. ¿Qué pasa si me quedo sin tiempo en Instagram?

DarkPause bloquea los dominios en hosts + mata el proceso. El usuario no puede desbloquear hasta el día siguiente (reset a las 4:00 AM).

### 6. ¿Qué pasa si el blackout está activo y se acaba el tiempo de IG?

No hay conflicto. Son sistemas independientes. El blackout cubre la pantalla. Los hosts se bloquean en background. Cuando el blackout termina, IG sigue bloqueado si se acabó el tiempo.

### 7. ¿Cómo evito que cambien el DNS para saltarse el bloqueo?

`firewall_manager.py` aplica reglas de Windows Firewall (netsh) al inicio que bloquean la salida a DNS públicos conocidos y al puerto 853. Esto obliga al sistema a usar el DNS local (hosts file) o el del router (que no suele tener DoH configurado por defecto en Windows doméstico).

---

## Dependencias Finales

```txt
pystray>=0.19
Pillow>=10.0
customtkinter>=5.2
screeninfo>=0.8
```

---

## Estimación Final

| Fase                    | Estado        |
| ----------------------- | ------------- |
| Fase 0: Preparación     | ✅ Completado |
| Fase 1: Migrar Core     | ✅ Completado |
| Fase 2: Refactorizar UI | ✅ Completado |
| Fase 3: Entry Point     | ✅ Completado |
| Fase 4: Integración     | ✅ Completado |
| Fase 5: Scripts         | ✅ Completado |
| Fase 6: Testing         | ✅ Completado |
| Fase 7: Anti-Bypass     | ✅ Completado |
