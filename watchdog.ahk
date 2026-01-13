#Requires AutoHotkey v2.0
#SingleInstance Force

; Archivo de bloqueo compartido con Python
LockFile := "session.lock"

Loop {
    ; 1. Verificar si el archivo de bloqueo existe
    if !FileExist(LockFile) {
        ExitApp
    }

    ; 2. Leer la hora de fin del archivo
    try {
        EndTimestamp := FileRead(LockFile)
    } catch {
        ExitApp
    }
    
    ; Si el archivo está vacío o corrupto, salir
    if (EndTimestamp = "") {
        ExitApp
    }

    ; 3. Calcular tiempo restante
    ; AHK v2 usa DateDiff para comparar fechas
    try {
        ; EndTimestamp viene en formato YYYYMMDDHHMMSS, compatible con AHK
        SecondsLeft := DateDiff(EndTimestamp, A_Now, "Seconds")
    } catch {
        ; Si el timestamp es inválido
        ExitApp
    }
    
    ; Si el tiempo ha expirado (diferencia negativa), salir
    if (SecondsLeft <= 0) {
        ExitApp
    }

    ; 4. Verificar si la app principal está viva
    ; En v2 WinExist es una función
    if !WinExist("darkpause_overlay") {
        ; Si no existe la ventana de overlay, relanzar la app
        ; Asumimos que python está en el path. Usamos comillas para path con espacios.
        try {
            Run 'python "d:\Code Projects\dark_pause\darkpause.py"', , "Hide"
        }
    } else {
        ; 5. Forzar la ventana a estar siempre encima y maximizada
        try {
            WinSetAlwaysOnTop 1, "darkpause_overlay"
            WinActivate "darkpause_overlay"
            WinMaximize "darkpause_overlay"
        }
    }

    ; Dormir 1 segundo (como pidió el usuario)
    Sleep 1000
}
