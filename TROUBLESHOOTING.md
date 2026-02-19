# 🔧 Solución de Problemas (Troubleshooting)

Si **DarkPause** no se comporta como debe, aquí tienes las soluciones a los problemas más comunes.

## 1. El programa no se abre al presionar `Ctrl + Alt + D`

- **Causa A:** El _launcher_ no está corriendo.
  - **Solución:** Busca el icono de la **H verde** en la bandeja de sistema (cerca del reloj). Si no está, ejecuta `scripts/launcher.ahk` de nuevo.
- **Causa B:** Falta alguna librería.
  - **Solución:** Abre una terminal en la carpeta del proyecto y escribe:
    ```ps1
    pip install -r requirements.txt
    ```
    Si tienes varias versiones de Python, intenta con `python -m pip install -r requirements.txt`.
- **Causa C:** DarkPause no está corriendo.
  - **Solución:** Ejecuta `run.bat` o `python darkpause.py` como Administrador. El launcher AHK solo abre/cierra el panel, pero necesita que DarkPause ya esté en ejecución.

## 2. Solo se bloquea una pantalla (tengo 2 o 3)

- **Causa:** La librería `screeninfo` no está instalada o falló al detectar monitores.
- **Solución:**
  1.  Asegúrate de instalarla: `pip install screeninfo`.
  2.  Reinicia la aplicación.
  3.  El programa detecta los monitores AL INICIO del blackout. Si conectaste una pantalla después de iniciar un blackout, no la verá. El siguiente blackout sí la detectará.

## 3. "No puedo salir del bloqueo y tengo una emergencia"

- **La dura verdad:** El programa está diseñado para esto.
- **La salida de emergencia (Solo técnicos):**
  1.  Presiona `Ctrl + Alt + Supr`.
  2.  Abre el **Administrador de Tareas**.
  3.  Debes ser rápido: Finaliza primero `AutoHotkey` (el perro guardián) y LUEGO `pythonw` (la pantalla negra). Si matas Python primero, AHK lo revivirá en menos de 1 segundo.

## 4. La ventana aparece fuera de pantalla o cortada

- **Solución:** La aplicación está configurada para aparecer en la posición `(100, 100)` de la pantalla principal. Si aún falla, verifica que tu monitor principal esté configurado correctamente en Windows ("Hacer de esta mi pantalla principal").

## 5. Mi internet dejó de funcionar después de instalar DarkPause

- **Causa:** DarkPause aplica reglas de **Windows Firewall** que bloquean DNS públicos (Google 8.8.8.8, Cloudflare 1.1.1.1, etc.). Si tu ISP/router depende de uno de estos como DNS primario, tu conexión puede verse afectada.
- **Solución temporal:**
  1.  Abre una terminal como Administrador.
  2.  Ejecuta:
      ```ps1
      netsh advfirewall firewall delete rule name="DarkPause-DNS-Lock"
      netsh advfirewall firewall delete rule name="DarkPause-DoT-Lock"
      ```
  3.  Esto restaura el acceso a DNS públicos. DarkPause volverá a aplicar las reglas en su próximo inicio.
- **Solución permanente:** Configura tu router/PC para usar el DNS de tu ISP (que no está en la lista de bloqueo) en vez de Google/Cloudflare.

## 6. "Edité el hosts file manualmente pero se revirtió solo"

- **Causa:** Esto es intencional. DarkPause ejecuta un **monitor de integridad** cada 30 segundos que verifica que los bloqueos permanentes estén presentes. Si detecta que fueron eliminados, los re-aplica automáticamente.
- **Si necesitas editar el hosts file:**
  1.  Detén DarkPause primero (desde la bandeja de sistema → "❌ Salir").
  2.  Haz tus cambios.
  3.  Nota: al reiniciar DarkPause, volverá a aplicar sus bloqueos.

## 7. Desinstalar DarkPause completamente

Para eliminar **todos** los cambios de DarkPause de tu sistema:

```ps1
# Ejecutar como Administrador:
install.bat uninstall
```

Esto elimina:

- La tarea programada de auto-arranque (Task Scheduler).
- Las reglas de firewall (`DarkPause-DNS-Lock` y `DarkPause-DoT-Lock`).

**Nota:** Los bloqueos del hosts file NO se eliminan automáticamente por seguridad. Para limpiarlos manualmente, edita `C:\Windows\System32\drivers\etc\hosts` y elimina todas las líneas entre los marcadores `# >>> DARKPAUSE-...-START <<<` y `# >>> DARKPAUSE-...-END <<<`.

## 8. DarkPause no arranca automáticamente al encender el PC

- **Causa A:** La tarea de Task Scheduler no tiene `WorkingDirectory`.
  - Task Scheduler lanza el proceso desde `C:\Windows\System32`, lo que rompe los `from core.* import ...` relativos.
  - **Solución:** Re-ejecutar `install.bat` como Administrador. La versión actual crea la tarea con un XML que incluye `<WorkingDirectory>` apuntando a la carpeta del proyecto.
- **Causa B:** Los paquetes están instalados en otra versión de Python.
  - `install.bat` registra `pythonw.exe` de una versión específica (ej: Python 3.11). Si instalaste las dependencias con `pip install` de otra versión (ej: Python 3.14), Task Scheduler no las encontrará.
  - **Diagnóstico:** Revisa qué Python usa la tarea:
    ```ps1
    schtasks /query /tn "DarkPause" /xml | Select-String "Command"
    ```
    E instala las dependencias con esa versión específica:
    ```ps1
    & "C:\...\Python311\python.exe" -m pip install -r requirements.txt
    ```
- **Causa C:** Crash silencioso con `pythonw.exe`.
  - `pythonw.exe` no tiene consola — los errores de stderr son **completamente invisibles**.
  - **Diagnóstico:** Ejecuta manualmente con `python.exe` (con consola) para ver el error:
    ```ps1
    & "C:\...\Python311\python.exe" "D:\Code Projects\dark_pause\darkpause.py"
    ```
  - **Diagnóstico alternativo:** Revisa el log en `%APPDATA%\DarkPause\darkpause.log`. Si el log se corta abruptamente sin "✅ All systems initialized", el crash ocurrió antes de esa línea.

## 9. El panel no se abre automáticamente (pero el tray sí funciona)

- **Causa:** El tray icon está activo pero `open_panel()` falló silenciosamente.
- **Diagnóstico:** Busca en el log:
  ```ps1
  Select-String "panel|Creating|Failed" "$env:APPDATA\DarkPause\darkpause.log"
  ```

  - Si ves `📋 Creating control panel...` pero NO `📋 Control panel created successfully.`, la creación del panel crasheó.
  - Si no ves ningún mensaje de panel, el proceso murió antes de llegar a esa fase.
- **Solución:** Asegúrate de que `customtkinter` esté instalado en la misma versión de Python que usa Task Scheduler (ver sección 8).

## 10. Ctrl+Alt+D pide aprobación de Administrador (UAC)

- **Causa:** El AHK launcher no encuentra la ventana "darkpause" (porque el tray process crasheó), así que lanza una nueva instancia que requiere UAC.
- **Solución:** Asegúrate de que DarkPause esté corriendo correctamente vía Task Scheduler (ver sección 8). Si el trayicon está activo y el panel se abrió correctamente, Ctrl+Alt+D solo lo minimiza/restaura — sin UAC.

---

_Si el problema persiste, abre un Issue en el repositorio._
