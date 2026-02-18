#Requires AutoHotkey v2.0
#SingleInstance Force

; DarkPause Watchdog
; Monitors the blackout overlay and restarts if killed.

LockFile := "session.lock"
ScriptDir := "D:\Code Projects\dark_pause"

Loop {
    ; Check if lock file exists
    if !FileExist(LockFile) {
        ExitApp
    }

    ; Read end time from lock file
    try {
        EndTimestamp := FileRead(LockFile)
    } catch {
        ExitApp
    }

    if (EndTimestamp = "") {
        ExitApp
    }

    ; Check if time expired
    try {
        SecondsLeft := DateDiff(EndTimestamp, A_Now, "Seconds")
    } catch {
        ExitApp
    }

    if (SecondsLeft <= 0) {
        ExitApp
    }

    ; Check if main process is alive (look for pythonw running darkpause)
    if !ProcessExist("pythonw.exe") {
        try {
            Run 'pythonw "' ScriptDir '\darkpause.py"', ScriptDir, "Hide"
        }
    }

    Sleep 1000
}
