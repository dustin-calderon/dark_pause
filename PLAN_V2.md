# 🌌 DarkPause v3.0 — The Evolution Roadmap

Este documento define el plan maestro para transformar DarkPause de un MVP funcional a una suite de disciplina digital de nivel comercial, integrando lo mejor de **Cold Turkey**, **SelfControl** y **ActivityWatch**.

---

## 🗺️ Roadmap General

| Versión  | Enfoque         | Features Clave                                          | Est. Tiempo | Estado |
| :------- | :-------------- | :------------------------------------------------------ | :---------- | :----- |
| **v1.2** | **Quick Wins**  | Notificaciones, Lock Mode Irreversible, Stats Dashboard | ~4h         | ⏳     |
| **v1.3** | **Power User**  | Schedules, App Block, Allowlist, **Allowances**         | ~7h         | 📅     |
| **v2.0** | **Premium**     | Frozen Mode, Password Diferido, Temas, **Mobile Push**  | ~10h        | 📅     |
| **v3.0** | **Kernel Deep** | WFP Driver (C/Rust) para bloqueo imposible de saltar    | 8h+         | 🔮     |

---

## 🚀 v1.2: Quick Wins (Inmediato)

**Meta:** Mejorar la UX y añadir la opción "Nuclear" sin grandes cambios de arquitectura.

### S4: 🔔 Notificaciones de Tiempo Restante

_Inspiración: Cold Turkey / Desktop Time Limiter_

**Descripción:**
Notificar proactivamente al usuario cuando le queden 5 min y 1 min de tiempo en una plataforma.

**Implementación Técnica:**

- **Ubicación:** `ui/tray.py` -> `PlatformSession._timer_loop`.
- **Lógica:** Configurable `WARNING_STEPS = [5, 1]`. Usar `_safe_notify`.

### S2: 🔒 Lock Mode (Opción Nuclear)

_Inspiración: SelfControl_

**Descripción:**
Opción para hacer el blackout **irreversible**.

**Implementación Técnica:**

- Añadir campo `"locked": true` al `blackout_state.json`.
- En arranque (`darkpause.py`): Si locked activo, reanudar blackout inmediatamente y deshabilitar salida.

### S1: 📊 Dashboard de Estadísticas (+ A5 Export)

_Inspiración: ActivityWatch_

**Descripción:**
Visualizar uso diario/semanal y **exportar datos**.

**Implementación Técnica:**

- **Vis:** `CTkProgressBar` para uso hoy. API gráfica simple (`Canvas`) para historial.
- **A5 (Export):** Botón "Exportar a CSV" en el panel. Itera sobre los JSONs de `usage_tracker` y genera un reporte unificado.

---

## ⚡ v1.3: Power Features (Semana 2)

**Meta:** Automatización y flexibilidad inteligente.

### S3: ⏰ Schedules Recurrentes

_Inspiración: Cold Turkey_

**Descripción:**
"Bloquear Lunes a Viernes de 9:00 a 17:00".

**Implementación Técnica:**

- Módulo `core/scheduler.py` con `schedule.json`.
- Integración en loop principal.

### A3: 📱 Bloqueador de Apps por Proceso

_Inspiración: WebsiteAndAppBlocker_

**Descripción:**
Bloquear EXE específicos (`Steam.exe`, `Discord.exe`).

**Implementación Técnica:**

- Lista `BLOCKED_APPS` en config.
- `process_manager.kill_process_list(names)`.

### S5: 🌐 Allowlist Mode

_Inspiración: SelfControl_

**Descripción:**
"Bloquear TODO excepto X".

**Implementación Técnica:**

- `netsh advfirewall` con política "Block All Outbound" y reglas de excepción específicas.

### A1: ⏱️ Allowances (Micro-dosis)

_Inspiración: Cold Turkey Pro_

**Descripción:**
"Permitir 5 minutos de YouTube cada hora durante un bloqueo largo".

**Implementación Técnica:**

- Lógica compleja: Un "timer dentro del bloqueo".
- Requiere estado persistente: `last_allowance_time`.
- Unlock temporal del hosts file por X minutos, luego re-block automático.

---

## 💎 v2.0: Premium Experience (Semana 3)

**Meta:** Polish visual y ecosistema.

| Feature                   | Descripción                                     | Tech                             |
| :------------------------ | :---------------------------------------------- | :------------------------------- |
| **A2: Frozen Mode**       | Bloqueo de sesión de Windows (`Win+L`) cíclico. | `User32.LockWorkStation`         |
| **A4: Password Diferido** | Token de desinstalación con delay de 24h.       | Crypto hash + Timer              |
| **B2: Categorías**        | Listas comunitarias (StevenBlack).              | Git/HTTP Download                |
| **B4: Temas Blackout**    | Mensajes motivacionales, fondos.                | Custom UI Rendering              |
| **B3: Mobile Companion**  | Notificación al móvil al terminar bloqueo.      | API `ntfy.sh` (HTTP POST simple) |

---

## ☣️ v3.0: Kernel Deep (Largo Plazo)

### B1: 🛡️ WFP Kernel Filter

- Driver .sys firmado para filtrado de paquetes a prueba de balas.

---

## 📚 Referencias Completas

| Proyecto          | Features Inspiradas                    | Link                                                     |
| :---------------- | :------------------------------------- | :------------------------------------------------------- |
| **SelfControl**   | Lock Mode, Allowlist                   | [GitHub](https://github.com/SelfControlApp/selfcontrol)  |
| **Cold Turkey**   | Schedules, Frozen Mode, Allowances     | [Sitio](https://getcoldturkey.com)                       |
| **ActivityWatch** | Stats, Export (A5), Mobile Notify (B3) | [GitHub](https://github.com/ActivityWatch/activitywatch) |
