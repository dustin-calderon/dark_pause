# 🔧 Solución de Problemas (Troubleshooting)

Si **darkpause** no se comporta como debe, aquí tienes las soluciones a los problemas más comunes.

## 1. El programa no se abre al presionar `Ctrl + Alt + D`

- **Causa A:** El _launcher_ no está corriendo.
  - **Solución:** Busca el icono de la **H verde** en la bandeja de sistema (cerca del reloj). Si no está, ejecuta `launcher.ahk` de nuevo.
- **Causa B:** Falta alguna librería.
  - **Solución:** Abre una terminal en la carpeta del proyecto y escribe:
    ```ps1
    pip install customtkinter screeninfo
    ```
    Si tienes varias versiones de Python, intenta con `python -m pip install ...`.

## 2. Solo se bloquea una pantalla (tengo 2 o 3)

- **Causa:** La librería `screeninfo` no está instalada o falló al detectar monitores.
- **Solución:**
  1.  Asegúrate de instalarla: `pip install screeninfo`.
  2.  Reinicia la aplicación (cierra la ventana de darkpause y vuelve a abrirla).
  3.  El programa detecta los monitores AL INICIO. Si conectaste una pantalla después de abrir la app, no la verá. **Reinicia la app.**

## 3. "No puedo salir del bloqueo y tengo una emergencia"

- **La dura verdad:** El programa está diseñado para esto.
- **La salida de emergencia (Solo técnicos):**
  1.  Presiona `Ctrl + Alt + Supr`.
  2.  Abre el **Administrador de Tareas**.
  3.  Debes ser rápido: Finaliza primero `AutoHotkey` (el perro guardián) y LUEGO `python` (la pantalla negra). Si matas Python primero, AHK lo revivirá en menos de 1 segundo.

## 4. La ventana aparece fuera de pantalla o cortada

- **Solución:** Hemos configurado la aplicación para aparecer en una posición segura `(100, 100)` de la pantalla principal. Si aún falla, verifica que tu monitor principal esté configurado correctamente en Windows ("Hacer de esta mi pantalla principal").

---

_Si el problema persiste, abre un Issue en el repositorio._
