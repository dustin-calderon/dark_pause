import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import time
from datetime import datetime, timedelta
import sys
import os
import socket

# Configuración Global de UI
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# --- Instancia Única (Socket Robusto) ---
SINGLE_INSTANCE_PORT = 45678
instance_socket = None

def check_single_instance():
    global instance_socket
    instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Intentamos enlazar al puerto. Si falla, es que ya hay otra app.
        instance_socket.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
    except socket.error:
        messagebox.showinfo("DarkFocus", "La aplicación ya está abierta.\nRevisa tu barra de tareas.")
        sys.exit()

class DarkPauseApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configuración de Ventana
        self.title("darkpause")
        self.geometry("500x750+100+100")
        self.minsize(500, 750)
        self.resizable(False, False)

        # Icono (opcional)
        try: self.iconbitmap("assets/icon.ico")
        except: pass
        
        self.blackout_active = False
        self.scheduled_tasks = []
        
        # Interceptar cierre para minimizar
        self.protocol("WM_DELETE_WINDOW", self.minimize_app)

        self.create_ui()
        
        # Monitor Loop
        self.running = True
        self.monitor_thread = threading.Thread(target=self.time_monitor, daemon=True)
        self.monitor_thread.start()

    def create_ui(self):
        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(pady=(30, 20), fill="x", padx=20)
        
        # Botón QUIT
        self.exit_btn = ctk.CTkButton(
            self.header_frame, text="QUIT", width=50, height=25,
            fg_color="#ff7675", hover_color="#d63031", font=("Segoe UI", 10, "bold"),
            command=self.quit_app
        )
        self.exit_btn.pack(side="right", anchor="ne")
        
        # Título
        title_container = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_container.pack(side="left", expand=True, fill="x")
        
        ctk.CTkLabel(title_container, text="darkpause", font=("Segoe UI", 32, "bold"), text_color="#6C5CE7").pack()
        ctk.CTkLabel(title_container, text="Distraction Freedom Protocol", font=("Segoe UI", 12), text_color="gray").pack()

        # Inputs
        self.create_section_schedule()
        self.create_section_timer()
        self.create_section_shortcuts()
        self.create_task_list()
        
        # Footer
        ctk.CTkLabel(self, text="⚠️ NO ESCAPE. NO MERCY.", font=("Segoe UI", 10, "bold"), text_color="#d63031").pack(side="bottom", pady=15)

    def maximize_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def minimize_app(self):
        # Implementación simple y nativa: Minimizar a la barra
        self.iconify()

    def quit_app(self):
        if messagebox.askokcancel("Salir", "¿Cancelar bloqueos y cerrar?"):
            self.running = False
            self.destroy()
            try: instance_socket.close()
            except: pass
            sys.exit()

    # --- Secciones UI ---
    def create_section_schedule(self):
        f = ctk.CTkFrame(self)
        f.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(f, text="📅 Programar Hora", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=15, pady=(10,5))
        
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(0,10))
        
        self.hour_entry = ctk.CTkEntry(row, placeholder_text="16:00", width=100, justify="center")
        self.hour_entry.pack(side="left", padx=5)
        self.hour_entry.insert(0, "16:00")
        
        self.hour_duration = ctk.CTkEntry(row, placeholder_text="60", width=60, justify="center")
        self.hour_duration.pack(side="left", padx=5)
        self.hour_duration.insert(0, "60")
        
        ctk.CTkButton(row, text="Programar", width=100, command=self.add_fixed_task, fg_color="#2d3436").pack(side="right", padx=5)

    def create_section_timer(self):
        f = ctk.CTkFrame(self)
        f.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(f, text="⏳ Quick Focus", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=15, pady=(10,5))
        
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(0,10))
        
        ctk.CTkLabel(row, text="En").pack(side="left", padx=2)
        self.wait_min = ctk.CTkEntry(row, width=50, justify="center")
        self.wait_min.pack(side="left", padx=2); self.wait_min.insert(0, "0")
        
        ctk.CTkLabel(row, text="min, Por").pack(side="left", padx=5)
        self.wait_dur = ctk.CTkEntry(row, width=50, justify="center")
        self.wait_dur.pack(side="left", padx=2); self.wait_dur.insert(0, "25")
        ctk.CTkLabel(row, text="min").pack(side="left", padx=2)
        
        ctk.CTkButton(row, text="GO", width=60, command=self.add_timer_task, fg_color="#00b894", text_color="black").pack(side="right", padx=5)

    def create_section_shortcuts(self):
        f = ctk.CTkFrame(self)
        f.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(f, text="⚡ Shortcuts", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=15, pady=(10,5))
        
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(0,10))
        
        ctk.CTkButton(row, text="🍅 Pomo 25", command=lambda: self.add_preset(25, 5), fg_color="#e17055", width=140).pack(side="left", padx=5, expand=True)
        ctk.CTkButton(row, text="🧘 Pomo 50", command=lambda: self.add_preset(50, 10), fg_color="#0984e3", width=140).pack(side="left", padx=5, expand=True)

    def create_task_list(self):
        ctk.CTkLabel(self, text="Cola de Ejecución:", font=("Segoe UI", 11, "bold"), text_color="gray").pack(anchor="w", padx=25, pady=(20,0))
        self.task_listbox = tk.Listbox(self, bg="#2d3436", fg="white", borderwidth=0, highlightthickness=0, font=("Consolas", 10), height=6)
        self.task_listbox.pack(fill="x", padx=20, pady=5)

    # --- Lógica ---
    def add_fixed_task(self):
        try:
            t = self.hour_entry.get(); d = int(self.hour_duration.get())
            datetime.strptime(t, "%H:%M")
            self.scheduled_tasks.append({"type": "fixed", "time": t, "duration": d, "active": True})
            self.update_list()
        except: messagebox.showerror("Error", "Formato inválido (HH:MM)")

    def add_timer_task(self):
        try:
            w = int(self.wait_min.get()); d = int(self.wait_dur.get())
            t = (datetime.now() + timedelta(minutes=w)).strftime("%H:%M:%S")
            self.scheduled_tasks.append({"time": t, "duration": d, "active": True, "type": "timer"})
            self.update_list()
        except: messagebox.showerror("Error", "Números inválidos")

    def add_preset(self, w, d):
        t = (datetime.now() + timedelta(minutes=w)).strftime("%H:%M:%S")
        self.scheduled_tasks.append({"time": t, "duration": d, "active": True, "type": "timer"})
        self.update_list()

    def update_list(self):
        self.task_listbox.delete(0, tk.END)
        for t in self.scheduled_tasks:
            self.task_listbox.insert(tk.END, f"{'⏰' if t.get('type')=='fixed' else '⏳'} {t['time']} -> {t['duration']}m")

    def time_monitor(self):
        while self.running:
            now = datetime.now()
            t_short = now.strftime("%H:%M"); t_long = now.strftime("%H:%M:%S")
            
            for task in self.scheduled_tasks:
                if task['active']:
                    if (task.get('type') == 'fixed' and t_short == task['time']) or \
                       (task.get('type') == 'timer' and t_long == task['time']):
                        task['active'] = False
                        self.after(0, lambda t=task: self.start_blackout(t['duration']))
                        self.after(0, self.update_list)
            time.sleep(1)

    def start_blackout(self, minutes):
        if self.blackout_active: return
        self.blackout_active = True
        
        # Overlay Nativo Robusto
        self.overlays = []
        try:
            from screeninfo import get_monitors
            monitors = get_monitors()
        except:
            monitors = [type('obj', (), {'x':0, 'y':0, 'width':self.winfo_screenwidth(), 'height':self.winfo_screenheight()})]

        for m in monitors:
            win = tk.Toplevel(self)
            win.geometry(f"{m.width}x{m.height}+{m.x}+{m.y}")
            win.attributes("-topmost", True)
            win.overrideredirect(True)
            win.configure(bg="black")
            win.config(cursor="none")
            win.protocol("WM_DELETE_WINDOW", lambda: None)
            
            if m.x == 0: # Monitor principal
                tk.Label(win, text="FOCUS MODE", bg="black", fg="#222222", font=("Segoe UI", 20, "bold")).pack(expand=True)
            
            self.overlays.append(win)

        def end():
            self.blackout_active = False
            for o in self.overlays: o.destroy()
            self.overlays = []

        self.after(int(minutes * 60000), end)
        
        # Focus Loop Robusto
        def keep_focus():
            if self.blackout_active:
                for o in self.overlays:
                    o.lift()
                    if o.winfo_x() == 0: o.focus_force()
                self.after(500, keep_focus)
        keep_focus()

if __name__ == "__main__":
    check_single_instance()
    app = DarkPauseApp()
    app.mainloop()
