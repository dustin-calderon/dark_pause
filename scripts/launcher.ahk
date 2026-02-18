#Requires AutoHotkey v2.0
#SingleInstance Force

; 🌌 DarkPause Launcher
; Hotkey: Ctrl + Alt + D → Toggle Control Panel

^!d::
{
    ScriptDir := "D:\Code Projects\dark_pause"
    TargetTitle := "darkpause"

    ; If panel window exists, toggle visibility
    if WinExist(TargetTitle) {
        if WinActive(TargetTitle) {
            WinMinimize TargetTitle
        } else {
            WinActivate TargetTitle
        }
    } else {
        ; If the tray process isn't running, launch the app
        try {
            Run 'pythonw "' ScriptDir '\darkpause.py"', ScriptDir
        } catch as e {
            MsgBox "Error launching DarkPause: " e.Message
        }
    }
}
