#Requires AutoHotkey v2.0
#SingleInstance Force

; 🌌 darkpause Launcher
; Atajo: Ctrl + Alt + D

^!d::
{
    ScriptPath := "d:\Code Projects\dark_pause\darkpause.py"
    WorkingDir := "d:\Code Projects\dark_pause"
    TargetTitle := "darkpause"

    if WinExist(TargetTitle) {
        WinActivate TargetTitle
    } else {
        try {
            ; En V2 los parámetros son expresiones.
            ; Pasamos el directorio de trabajo para asegurar que Python encuentre los assets.
            Run 'python "' ScriptPath '"', WorkingDir, "Hide"
        } catch as e {
            MsgBox "Error lanzando darkpause: " e.Message
        }
    }
}
