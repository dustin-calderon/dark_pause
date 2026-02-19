# 🌌 DarkPause — Plan de Evolución (v2.1 → v3.0)

---

## 📍 Estado Actual del Proyecto (v2.0 — Estable)

DarkPause v2.0 es la fusión completada de **InnerCrab** (limitador de plataformas) y **DarkPause** (bloqueador de pantalla). Todas las fases del `PLAN.md` original (Fase 0-7) están **✅ completadas**.

### Arquitectura Actual

```
D:\Code Projects\dark_pause\
│
├── core/                          # Lógica de negocio (sin UI)
│   ├── __init__.py
│   ├── config.py                  # Platformas (IG 10min, YT 60min), dominios porno,
│   │                                constantes (RESET_HOUR=4AM, WARNING_THRESHOLD=2min),
│   │                                colores, paths (HOSTS_FILE, APP_DATA_DIR)
│   ├── hosts_manager.py           # Lectura/escritura atómica del hosts file
│   │                                block_platform() / unblock_platform()
│   │                                block_permanent_domains() (porno)
│   │                                DNS flush, markers, backup
│   ├── firewall_manager.py        # DNS Lock via netsh advfirewall
│   │                                Bloquea 8.8.8.8, 1.1.1.1, etc + puerto 853 (DoT)
│   ├── process_manager.py         # is_app_running() / kill_app()
│   │                                Fallback PowerShell para UWP apps
│   ├── usage_tracker.py           # Tracking diario por plataforma (JSON por platform)
│   │                                add_usage() / get_remaining_seconds()
│   │                                Atomic writes + per-platform thread locks
│   │                                Datos en: %APPDATA%/DarkPause/usage_*.json
│   └── icon_generator.py          # Genera iconos dinámicos para el tray
│                                    Estados: BLOCKED, ACTIVE, WARNING, PAUSED
│
├── ui/                            # Interfaz
│   ├── __init__.py
│   ├── tray.py                    # System Tray (pystray) — PROCESO PRINCIPAL
│   │                                PlatformSession (timer loop por plataforma)
│   │                                _safe_notify() para toast notifications
│   │                                WARNING_THRESHOLD_MINUTES ya conectado
│   ├── blackout.py                # Overlay fullscreen (todos los monitores)
│   │                                Timer countdown, keep_focus() anti-bypass
│   │                                blackout_state.json para persistencia/crash recovery
│   └── control_panel.py           # Panel de control (CustomTkinter)
│                                    Quick Focus, Programar hora, Pomodoro (25/5, 50/10)
│                                    Cola de tareas
│
├── scripts/
│   ├── launcher.ahk               # Ctrl+Alt+D → abre/cierra panel
│   └── watchdog.ahk               # Resucita el proceso si muere
│
├── .references/                   # Repos clonados para inspiración/código
│   ├── blockers/                  # 8 repos de bloqueo
│   │   ├── selfcontrol/           # (Obj-C) Nuclear option, allowlist
│   │   ├── selfrestraint/         # (Python) Port de SelfControl a Windows
│   │   ├── website-app-blocker/   # (Python) Bloqueo de webs + apps por períodos
│   │   ├── webblockerscript/      # (Shell) CLI hosts con backup/restore
│   │   ├── focus-cli/             # (Rust) CLI minimalista, bloquea hosts
│   │   ├── site-blocker/          # (Python/Tkinter) GUI block/unblock
│   │   ├── website-blocker/       # (Flutter/Dart) GUI manage hosts
│   │   └── hosts-file-editor/     # (C#/.NET) Editor avanzado del hosts
│   ├── trackers/                  # 5 repos de tracking
│   │   ├── activitywatch/         # (Python) REST API, categorías, privacy-first
│   │   ├── desktop-time-limiter/  # (Python) Limita uso total, lock tras X horas
│   │   ├── screentime/            # (Python) Tracking por app y hora
│   │   ├── screeny/               # (C#/WinUI) Tracker nativo Win11
│   │   └── super-productivity/    # (TypeScript) Task manager + time tracking
│   └── lists/
│       └── steven-black-hosts/    # +170k dominios: ads, malware, porno, gambling
│
├── darkpause.py                   # Entry point: admin check, UAC, logging, crash handler
├── run.bat                        # Launcher silencioso con UAC
├── install.bat                    # Auto-start (Task Scheduler) + uninstall
├── requirements.txt               # pystray, Pillow, customtkinter, screeninfo
├── PLAN.md                        # Plan original v2.0 (COMPLETADO)
├── PLAN_V2.md                     # Este archivo — roadmap v2.1+
├── README.md                      # Documentación pública
├── TROUBLESHOOTING.md             # Guía de resolución de problemas
└── LICENSE                        # MIT
```

### Capas de Protección Existentes (v2.0)

| #   | Capa                  | Técnica                                                        | Archivo                    |
| :-- | :-------------------- | :------------------------------------------------------------- | :------------------------- |
| 1   | **Hosts File**        | `127.0.0.1 dominio.com`                                        | `core/hosts_manager.py`    |
| 2   | **DNS Anti-Bypass**   | Firewall rules (`netsh`) bloquean Google DNS, Cloudflare, etc. | `core/firewall_manager.py` |
| 3   | **DoT Lock**          | Bloqueo de puerto 853 (DNS-over-TLS)                           | `core/firewall_manager.py` |
| 4   | **Integrity Monitor** | Loop cada 30s verifica y repara hosts file                     | `darkpause.py`             |
| 5   | **Persistent State**  | `blackout_state.json` sobrevive crashes/reinicios              | `ui/blackout.py`           |
| 6   | **Watchdog**          | Script AHK externo resucita el proceso                         | `scripts/watchdog.ahk`     |

### Infraestructura Reutilizable para Features Nuevas

| Componente                   | Qué es                                | Dónde se usará                         |
| :--------------------------- | :------------------------------------ | :------------------------------------- |
| `_safe_notify()`             | Toast notification segura via pystray | S4 (Notificaciones)                    |
| `WARNING_THRESHOLD_MINUTES`  | Config de umbral ya existente (2 min) | S4 (Ampliar a [15, 5, 1])              |
| `blackout_state.json`        | Estado persistente del blackout       | S2 (Lock Mode: añadir campo `locked`)  |
| `usage_*.json` files         | Datos diarios por plataforma          | S1 (Stats), A5 (Export)                |
| `watchdog.ahk`               | Resurrección automática del proceso   | S2 (Lock Mode: resistencia)            |
| `process_manager.kill_app()` | Mata procesos por nombre              | A3 (App Blocker: extender)             |
| `firewall_manager.py`        | Reglas netsh de firewall              | S5 (Allowlist: block all + exceptions) |

---

## 📖 Investigación de Mercado

Hemos estudiado **SelfControl** (macOS), **Cold Turkey** (Windows, referente comercial), **ActivityWatch** (tracking open source), **SelfRestraint** (Python), **desktop-time-limiter**, y las técnicas avanzadas de bypass prevention con **WFP** (Windows Filtering Platform).

Los repos están clonados en `.references/` para consulta directa de código.

### Mapa de Referencias por Feature

| #   | Feature                | Inspirado en                | Repo Local                                  | Archivo Clave                        |
| :-- | :--------------------- | :-------------------------- | :------------------------------------------ | :----------------------------------- |
| S1  | Estadísticas de uso    | ActivityWatch               | `.references/trackers/activitywatch`        | `aw-server/` (data schema, buckets)  |
| S2  | Lock Mode (Nuclear)    | SelfControl, Cold Turkey    | `.references/blockers/selfrestraint`        | `blocker.py` (persistencia en disco) |
| S3  | Schedules Recurrentes  | Cold Turkey                 | `.references/blockers/webblockerscript`     | `config.json` (estructura horarios)  |
| S4  | Notificaciones         | desktop-time-limiter        | `.references/trackers/desktop-time-limiter` | `main.py` (notification logic)       |
| S5  | Allowlist Mode         | SelfControl                 | `.references/blockers/selfcontrol`          | `SCCoreManager.m` (pf.conf rules)    |
| A1  | Allowances             | Cold Turkey Pro             | — (concepto)                                | —                                    |
| A2  | Frozen Mode            | Cold Turkey "Frozen Turkey" | `.references/blockers/focus-cli`            | `src/platform/windows.rs` (WinAPI)   |
| A3  | App Blocker            | WebsiteAndAppBlocker        | `.references/blockers/website-app-blocker`  | `WebsiteAndAppBlocker.py` (psutil)   |
| A4  | Password Diferido      | SelfControl philosophy      | — (concepto)                                | —                                    |
| A5  | Exportar datos         | ActivityWatch               | `.references/trackers/activitywatch`        | `aw-server/` (export endpoints)      |
| B1  | WFP Kernel Filter      | EDR/Antivirus               | — (investigación)                           | Microsoft Docs — WFP                 |
| B2  | Categorías StevenBlack | StevenBlack/hosts           | `.references/lists/steven-black-hosts`      | `hosts` (raw file, 170k+ domains)    |
| B3  | Companion Mobile       | ActivityWatch               | — (concepto)                                | ntfy.sh (HTTP POST)                  |
| B4  | Temas Blackout         | Original                    | —                                           | —                                    |

---

## 🗓️ Roadmap

### Tiers de Prioridad

**🏆 Tier S — Alto impacto, Factible ahora**

| #   | Feature                  | Esfuerzo | Estado | Descripción resumida                                                            |
| :-- | :----------------------- | :------- | :----- | :------------------------------------------------------------------------------ |
| S1  | 📊 Estadísticas de uso   | ~2h      | ⏳     | Dashboard en Control Panel con gráfico semanal. Datos ya en `usage_tracker.py`. |
| S2  | 🔒 Lock Mode (nuclear)   | ~1h      | ✅     | Checkbox "Lock" al activar blackout. Persiste en disco. Ignora cancelación.     |
| S3  | ⏰ Schedules recurrentes | ~2h      | ✅     | Programar bloqueos automáticos semanales. JSON + integrity check loop.          |
| S4  | 🔔 Notificaciones        | ~30min   | ✅     | Toast notifications a los 5 min y 1 min restantes.                              |
| S5  | 🌐 Allowlist Mode        | ~1h      | ✅     | Bloquear TODO internet excepto dominios permitidos.                             |

**🥇 Tier A — Buen valor, Esfuerzo medio**

| #   | Feature              | Esfuerzo | Descripción resumida                                                  |
| :-- | :------------------- | :------- | :-------------------------------------------------------------------- |
| A1  | ⏱️ Allowances        | ~2h      | "5 min de YouTube cada hora durante bloqueo". Timer interno temporal. |
| A2  | 🧊 Frozen Mode       | ~1.5h    | Bloquear sesión de Windows (`LockWorkStation`) por X minutos.         |
| A3  | 📱 App Blocker       | ~1h      | Matar procesos en lista negra cada 5s (`Discord.exe`, `Steam.exe`).   |
| A4  | 🔐 Password diferido | ~1h      | Password de desbloqueo con cooling off period de 24h.                 |
| A5  | 📄 Exportar datos    | ~30min   | Export `usage_tracker` a CSV/JSON.                                    |

**🥉 Tier B — Avanzado, Más esfuerzo**

| #   | Feature                   | Esfuerzo | Descripción resumida                                                        |
| :-- | :------------------------ | :------- | :-------------------------------------------------------------------------- |
| B1  | 🛡️ WFP Kernel Filter      | ~8h+     | Driver Python+ctypes o C/Rust. Imposible de bypassear. Alto riesgo técnico. |
| B2  | 🌍 Categorías StevenBlack | ~1h      | Integrar listas curadas (>170k dominios). Usuario elige categorías.         |
| B3  | 📱 Companion mobile       | ~4h      | Push al móvil via ntfy.sh cuando termina un bloqueo.                        |
| B4  | 🎨 Temas blackout         | ~1h      | Mensajes motivacionales, timer visual, fondos ambientales.                  |

### Versiones Planificadas

```
v2.1 (Quick Wins)                          (~4h total)
├── S4: Notificaciones de tiempo restante   (~30 min)
├── S1: Dashboard de estadísticas           (~2h)
├── A5: Exportar datos                      (~30 min)
└── S2: Lock Mode irreversible              (~1h)

v2.2 (Power Features)                      (~6h total)
├── S3: Schedules recurrentes               (~2h)
├── A3: Bloqueador de apps por proceso      (~1h)
├── A1: Allowances (micro-dosis)            (~2h)
└── S5: Allowlist Mode                      (~1h)

v2.3 (Premium Tier)                        (~5.5h total)
├── A2: Frozen Mode (lock desktop)          (~1.5h)
├── A4: Password diferido                   (~1h)
├── B2: Categorías StevenBlack              (~1h)
├── B4: Temas para blackout                 (~1h)
└── B3: Companion mobile (ntfy.sh)          (~1h)

v3.0 (Kernel Deep)                         (~8h+)
└── B1: WFP Kernel Filter                   (~8h+)
```

---

## 🚀 v2.1: Especificaciones Detalladas

### 🔔 S4: Notificaciones de Tiempo Restante (~30 min) ✅

> **Estado:** Implementado 2026-02-18. Ver `IMPLEMENTATION_TIER_S.md`.

**Qué existe hoy:**

- `core/config.py` → `WARNING_THRESHOLD_MINUTES = 2` (un solo umbral).
- `ui/tray.py` → `PlatformSession._warning_sent` (bool, una sola alerta).
- `ui/tray.py` → `DarkPauseTray._safe_notify(title, message)` (wrapper seguro de `icon.notify()`).

**Qué hay que hacer:**

1. En `core/config.py`: Reemplazar `WARNING_THRESHOLD_MINUTES = 2` por `WARNING_STEPS: list[int] = [5, 1]`.
2. En `ui/tray.py` → `PlatformSession.__init__`: Reemplazar `self._warning_sent: bool = False` por `self._warnings_sent: set[int] = set()`.
3. En `ui/tray.py` → `PlatformSession._timer_loop` (línea ~155): Reemplazar el bloque `if remaining <= WARNING_THRESHOLD_MINUTES * 60` por:
   ```python
   for step in WARNING_STEPS:
       if remaining <= step * 60 and step not in self._warnings_sent:
           self._notify_callback(
               f"⚠️ {self.platform.display_name}: Quedan {step} min",
               "Cierra lo que estés haciendo.",
           )
           self._warnings_sent.add(step)
   ```
4. En `PlatformSession.start()`: Reset `self._warnings_sent = set()` al iniciar sesión.

**Referencia:** `.references/trackers/desktop-time-limiter/main.py` (lógica de notificación).

---

### 📊 S1: Dashboard de Estadísticas (~2h)

**Qué existe hoy:**

- `core/usage_tracker.py` → JSONs diarios: `usage_instagram.json`, `usage_youtube.json`.
- Formato: `{"date": "2026-02-18", "used_seconds": 345.2, "sessions": 5}`.
- `ui/control_panel.py` → Panel con CustomTkinter (sin tabs actualmente).

**Qué hay que hacer:**

1. **Backend** — En `core/usage_tracker.py`, añadir:
   ```python
   def get_weekly_history(platform: Platform) -> list[dict]:
       """Retorna los últimos 7 días de uso para una plataforma."""
       # Iterar fechas hacia atrás, intentar leer cada JSON.
       # Retorna: [{"date": "2026-02-12", "used_seconds": 300}, ...]
   ```
2. **Frontend** — En `ui/control_panel.py`:
   - Migrar a `CTkTabview` con dos tabs: "⚡ Control" y "📊 Estadísticas".
   - Tab Control: Mover la UI actual aquí (Quick Focus, Schedule, Pomodoro).
   - Tab Stats:
     - **Barras de hoy:** `CTkProgressBar` para cada plataforma (used/limit).
     - **Gráfico semanal:** `tkinter.Canvas` con 7 barras verticales.
       - Color: Verde (<50%), Amarillo (<80%), Rojo (>80%).
     - **Texto resumen:** "Instagram: 8m / 10m hoy | YouTube: 45m / 60m hoy".

**Referencia:** `.references/trackers/activitywatch` (schema de buckets y datos).

---

### 📄 A5: Exportar Datos (~30 min)

**Qué existe hoy:**

- Los datos ya están en JSONs individuales en `%APPDATA%/DarkPause/`.

**Qué hay que hacer:**

1. Botón "📄 Exportar CSV" en Tab Estadísticas.
2. Al pulsar, iterar `APP_DATA_DIR / usage_*.json`, leer todos, generar CSV:
   ```csv
   Date,Platform,UsedMinutes,LimitMinutes,Sessions
   2026-02-18,Instagram,8.5,10,3
   2026-02-18,YouTube,45.0,60,2
   ```
3. Diálogo de guardado (`filedialog.asksaveasfilename`).

**Referencia:** `.references/trackers/activitywatch` (export endpoints en aw-server).

---

### 🔒 S2: Lock Mode — Opción Nuclear (~1h) ✅

> **Estado:** Implementado 2026-02-18. Ver `IMPLEMENTATION_TIER_S.md` para detalles.

**Qué existe hoy:**

- `ui/blackout.py` → `blackout_state.json`: `{"end_time": "...", "duration_minutes": 25}`.
- `ui/blackout.py` → `_save_blackout_state()` / `_clear_blackout_state()`.
- `darkpause.py` → En arranque, chequea si hay blackout pendiente (crash recovery).
- `scripts/watchdog.ahk` → Resucita `pythonw.exe` si muere.

**Qué hay que hacer:**

1. **UI** — En `ui/control_panel.py`, al activar Blackout: Checkbox `☑ 🔒 Lock (irreversible)`.
2. **Persistencia** — `_save_blackout_state()` ahora guarda: `{"end_time": "...", "duration_minutes": 25, "locked": true}`.
3. **Boot** — En `darkpause.py`, al arrancar:
   - Leer `blackout_state.json`.
   - Si `locked == True` y `now < end_time`:
     - Iniciar `ScreenBlackout` ANTES de inicializar Tray.
     - Deshabilitar hotkeys de cierre.
     - Ignorar cualquier intento de cancelación.
4. **Kill Defense** — Si el usuario mata el proceso:
   - `watchdog.ahk` lo reinicia.
   - Al reiniciar, lee `locked` → vuelve a pantalla negra en <2s.

**Referencia:** `.references/blockers/selfrestraint` (lógica de persistencia de bloqueo).

---

## 🔥 v2.2: Especificaciones Detalladas

### ⏰ S3: Schedules Recurrentes (~2h) ✅

> **Estado:** Implementado 2026-02-18. Nuevo módulo `core/scheduler.py`. Ver `IMPLEMENTATION_TIER_S.md`.

**Qué existe hoy:**

- Nada de scheduling automático. Todo es manual.

**Qué hay que hacer:**

1. **Nuevo módulo:** `core/scheduler.py`.
2. **Config:** `schedule.json` en `APP_DATA_DIR`:
   ```json
   {
     "schedules": [
       {
         "name": "Work Mode",
         "days": [0, 1, 2, 3, 4],
         "start": "09:00",
         "end": "17:00",
         "action": "blackout",
         "strict": true
       }
     ]
   }
   ```
3. **Engine:** Thread dedicado (`scheduler_thread`) que cada 60s:
   - Lee `schedule.json`.
   - Chequea si `current_day` y `current_time` está en algún rango activo.
   - Si sí y no hay blackout activo → `blackout.start(minutes=remaining_in_range)`.
4. **UI:** Nueva sección en Control Panel (o nuevo tab) para crear/editar schedules.

**Referencia:** `.references/blockers/webblockerscript` (formato JSON de config).

---

### 📱 A3: Bloqueador de Apps por Proceso (~1h)

**Qué existe hoy:**

- `core/process_manager.py` → `kill_app(platform)` mata procesos de una plataforma.
- `core/config.py` → `Platform.process_names` (ej: `["Instagram.exe"]`).

**Qué hay que hacer:**

1. **Config:** Nueva lista en `core/config.py`:
   ```python
   BLOCKED_APPS: list[str] = [
       "Discord.exe",
       "Steam.exe",
       "steamwebhelper.exe",
       "EpicGamesLauncher.exe",
   ]
   ```
2. **Engine:** Nuevo método en `core/process_manager.py`:
   ```python
   def kill_blocked_apps() -> list[str]:
       """Mata todos los procesos en BLOCKED_APPS. Retorna lista de killed."""
   ```
3. **Loop:** En el integrity check loop (cada 30s), si hay blackout activo o schedule activo → llamar `kill_blocked_apps()`.

**Referencia:** `.references/blockers/website-app-blocker/WebsiteAndAppBlocker.py`.

---

### ⏱️ A1: Allowances — Micro-dosis (~2h)

**Qué existe hoy:**

- Nada. El bloqueo es total.

**Qué hay que hacer:**

1. **Config:** `ALLOWANCE_MINUTES = 5`, `ALLOWANCE_COOLDOWN_MINUTES = 60`.
2. **Estado:** En `blackout_state.json`, añadir `"last_allowance": "2026-02-18T10:30:00"`.
3. **UI (Blackout Screen):**
   - Si `allowance_enabled` y han pasado >60 min desde el último uso:
     - Mostrar botón "☕ Descanso (5 min)" en la pantalla negra.
   - Al pulsar:
     - `hosts_manager.unblock_all()`.
     - Timer de 5:00 visible en pantalla.
     - Al terminar → `hosts_manager.block_all()`, ocultar botón, guardar timestamp.

---

### 🌐 S5: Allowlist Mode (~1h) ✅

> **Estado:** Implementado 2026-02-18. Incluye crash recovery con flag file. Ver `IMPLEMENTATION_TIER_S.md`.

**Qué existe hoy:**

- `core/firewall_manager.py` → Ya sabe crear reglas `netsh advfirewall`.

**Qué hay que hacer:**

1. **Config:** `ALLOWLIST_DOMAINS = ["docs.google.com", "stackoverflow.com", ...]`.
2. **Engine:**
   - Resolver IPs de los dominios permitidos: `socket.getaddrinfo()`.
   - Crear regla `Block All Outbound` + reglas `Allow` para cada IP resuelta.
   - Re-resolver cada 5 min (IPs dinámicas de CDNs).
3. **Toggle:** Botón en Control Panel: "🌐 Modo Deep Work (Solo Allowlist)".
4. **Cleanup:** Al desactivar, eliminar las reglas de firewall.

**Referencia:** `.references/blockers/selfcontrol` (lógica pf.conf en macOS, adaptada a `netsh`).

---

## 💎 v2.3: Especificaciones Detalladas

### 🧊 A2: Frozen Mode — Desktop Lock (~1.5h)

**Qué existe hoy:**

- `ui/blackout.py` → Overlay fullscreen con `keep_focus()`.

**Qué hay que hacer:**

1. **Modo alternativo** al Blackout: En vez de pantalla negra, bloquear la sesión de Windows.
2. **Engine:**
   ```python
   import ctypes
   user32 = ctypes.windll.user32
   while frozen_mode_active:
       user32.LockWorkStation()
       time.sleep(1)  # Si el usuario logra entrar, lo vuelve a expulsar
   ```
3. **Toggle:** Opción en Control Panel: "Frozen Mode (bloquear escritorio)" vs "Blackout Mode (pantalla negra)".
4. **Advertencia:** Mostrar diálogo de confirmación antes de activar. Es la opción más extrema.

**Referencia:** `.references/blockers/focus-cli` (Rust implementation con WinAPI).

---

### 🔐 A4: Password Diferido (~1h)

**Qué existe hoy:**

- Nada. El usuario puede cambiar config o cerrar la app libremente.

**Qué hay que hacer:**

1. **Config Protegida:** En `core/config.py`, flag `CONFIG_LOCKED = True`.
2. **Unlock Flow:**
   - El usuario pide desbloquear → Se genera un token.
   - El token se guarda en `unlock_request.json`: `{"requested_at": "...", "token_hash": "..."}`.
   - El token solo se muestra/es válido 24h después de la solicitud.
3. **UI:** Diálogo: "Has solicitado desbloquear. Podrás hacerlo el [fecha+24h]. Si es una decisión real, esperarás."
4. **Protege:** Cambios de config, desinstalación, cierre de la app.

**Referencia:** SelfControl philosophy (cooling off period).

---

### 🌍 B2: Categorías StevenBlack (~1h)

**Qué existe hoy:**

- `core/hosts_manager.py` → Sabe inyectar dominios en el hosts file.
- `.references/lists/steven-black-hosts/hosts` → Archivo raw con 170k+ dominios categorizados.

**Qué hay que hacer:**

1. **Parser:** Leer el archivo `hosts` de StevenBlack y extraer dominios por categoría.
   - Categorías disponibles: `ads`, `malware`, `fakenews`, `gambling`, `social`, `porn`.
2. **UI:** Checkboxes en Control Panel: "☑ Ads ☑ Gambling ☐ Social Media".
3. **Engine:** Al activar una categoría, inyectar sus dominios en el hosts file usando los markers existentes.
4. **Update:** Botón "🔄 Actualizar listas" que descarga la última versión del repo.

**Referencia:** `.references/lists/steven-black-hosts` (archivo hosts unificado).

---

### 🎨 B4: Temas para Blackout (~1h)

**Qué existe hoy:**

- `ui/blackout.py` → Pantalla negra plana con timer countdown blanco.

**Qué hay que hacer:**

1. **Mensajes motivacionales rotativos:**
   - Array de frases: `["Keep pushing", "Focus is power", "Tu futuro yo te lo agradecerá", ...]`.
   - Cambiar texto cada 30-60 segundos con fade transition.
2. **Timer visual mejorado:** Reloj grande y minimalista (fuente grande, centrado).
3. **Fondos alternativos:** Degradado suave (negro → gris oscuro) o colores personalizable.
4. **Config:** `blackout_theme` en config: `"minimal"`, `"motivational"`, `"zen"`.

---

### 📱 B3: Companion Mobile — Notificaciones Push (~1h)

**Qué existe hoy:**

- Nada. El usuario no sabe cuándo termina el bloqueo si se aleja del PC.

**Qué hay que hacer:**

1. **Servicio:** Usar `ntfy.sh` (gratuito, open source, sin app propia necesaria).
2. **Config:** `NTFY_TOPIC = "darkpause-user-secret-topic"` en config.
3. **Engine:** Al finalizar blackout:
   ```python
   import requests
   requests.post(
       f"https://ntfy.sh/{NTFY_TOPIC}",
       data="🌌 Bloqueo terminado. ¡Eres libre!",
       headers={"Title": "DarkPause"}
   )
   ```
4. **Setup del usuario:** Instalar app `ntfy` en el móvil y suscribirse al topic.

---

## ☣️ v3.0: Especificaciones Detalladas

### 🛡️ B1: WFP Kernel Filter (~8h+)

**Qué existe hoy:**

- `core/firewall_manager.py` → Reglas `netsh` (user-space, bypasseable con admin).

**Por qué es necesario:**

- El `hosts` file se puede saltar con DoH (DNS-over-HTTPS) si el usuario configura un browser compatible.
- Ya bloqueamos puerto 853 (DoT), pero DoH usa puerto 443 (HTTPS) que no podemos bloquear sin romper internet.
- Un driver WFP filtra **todo** el tráfico a nivel kernel, antes de que llegue a cualquier aplicación.

**Qué hay que hacer:**

1. **Driver:** Escribir un driver `.sys` en C/C++ o Rust usando la Windows Filtering Platform API.
2. **Controller:** Script Python que carga/descarga el driver y le pasa las reglas de filtrado.
3. **Firma:** Requiere certificado EV (Extended Validation) para firmar el driver. Sin firma, solo funciona en modo test de Windows.
4. **Riesgo:** Alto. Un bug en un driver kernel = BSOD. Requiere testing exhaustivo.

**Referencia:** Microsoft Docs — WFP, técnicas EDR/Antivirus.

---

## 📝 Checklist Inmediata (v2.1 — Próxima Sesión)

- [ ] Refactor `ui/control_panel.py` a `CTkTabview` (Tab Control + Tab Stats).
- [ ] Implementar `core/usage_tracker.get_weekly_history()`.
- [ ] Implementar lógica `WARNING_STEPS = [5, 1]` en `ui/tray.py`.
- [ ] Añadir botón "Exportar CSV" en Tab Stats.
- [ ] Añadir checkbox "🔒 Lock" en panel de activación de Blackout.
- [ ] Añadir campo `locked` en `_save_blackout_state()`.
- [ ] Actualizar boot check en `darkpause.py` para respetar `locked`.

---

_Este documento es la fuente de verdad (Source of Truth) para el desarrollo de DarkPause v2.1 → v3.0._
_Última actualización: 2026-02-18._
