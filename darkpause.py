import customtkinter as ctk
import tkinter as tk # Fallback para componentes sistema
from tkinter import messagebox
import threading
import time
from datetime import datetime, timedelta
import sys
import os

# Configuración Global de UI
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class DarkPauseApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configuración de Ventana
        self.title("darkpause")
        
        # Posición Fija Segura (para evitar problemas con 3 monitores)
        self.geometry("500x750+100+100")
        
        self.resizable(False, False)
        
        # Icono (Si existiera, por ahora default)
        # self.iconbitmap("icon.ico")
        
        self.blackout_active = False
        self.scheduled_tasks = []
        
        self.create_modern_widgets()
        
        # Iniciar hilo de monitoreo
        self.running = True
        self.monitor_thread = threading.Thread(target=self.time_monitor, daemon=True)
        self.monitor_thread.start()

        # Verificar persistencia (Watchdog recovery)
        self.check_persistence()

    def create_modern_widgets(self):
        # --- Header ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(pady=(30, 20))
        
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="darkpause", 
            font=("Segoe UI", 32, "bold"),
            text_color="#6C5CE7" # Un color púrpura/azulado moderno
        )
        self.title_label.pack()
        
        self.subtitle_label = ctk.CTkLabel(
            self.header_frame, 
            text="Distraction Freedom Protocol", 
            font=("Segoe UI", 12),
            text_color="gray"
        )
        self.subtitle_label.pack()

        # --- Sección: Programar Hora ---
        self.schedule_frame = ctk.CTkFrame(self)
        self.schedule_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(self.schedule_frame, text="📅 Programar una hora", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=15, pady=(10, 5))
        
        self.input_row_1 = ctk.CTkFrame(self.schedule_frame, fg_color="transparent")
        self.input_row_1.pack(fill="x", padx=10, pady=(0, 10))
        
        self.hour_entry = ctk.CTkEntry(self.input_row_1, placeholder_text="16:00", width=100, justify="center")
        self.hour_entry.pack(side="left", padx=5)
        self.hour_entry.insert(0, "16:00")
        
        self.hour_duration = ctk.CTkEntry(self.input_row_1, placeholder_text="Min", width=60, justify="center")
        self.hour_duration.pack(side="left", padx=5)
        self.hour_duration.insert(0, "60")
        
        ctk.CTkButton(
            self.input_row_1, 
            text="Programar", 
            width=100, 
            command=self.add_scheduled_task,
            fg_color="#2d3436"
        ).pack(side="right", padx=5)

        # --- Sección: Cuenta Atrás (Quick Focus) ---
        self.timer_frame = ctk.CTkFrame(self)
        self.timer_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(self.timer_frame, text="⏳ Quick Focus (Timer)", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=15, pady=(10, 5))
        
        self.input_row_2 = ctk.CTkFrame(self.timer_frame, fg_color="transparent")
        self.input_row_2.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(self.input_row_2, text="En").pack(side="left", padx=(5,2))
        self.wait_min = ctk.CTkEntry(self.input_row_2, width=50, justify="center")
        self.wait_min.pack(side="left", padx=2)
        self.wait_min.insert(0, "0")
        ctk.CTkLabel(self.input_row_2, text="min").pack(side="left", padx=(2,10))
        
        ctk.CTkLabel(self.input_row_2, text="Por").pack(side="left", padx=(5,2))
        self.wait_duration = ctk.CTkEntry(self.input_row_2, width=50, justify="center")
        self.wait_duration.pack(side="left", padx=2)
        self.wait_duration.insert(0, "25")
        ctk.CTkLabel(self.input_row_2, text="min").pack(side="left", padx=(2,5))
        
        ctk.CTkButton(
            self.input_row_2, 
            text="GO", 
            width=60, 
            command=self.add_countdown_task,
            fg_color="#00b894", 
            hover_color="#00cec9",
            text_color="black"
        ).pack(side="right", padx=5)

        # --- Sección: Shortcuts (Pomodoro) ---
        self.preset_frame = ctk.CTkFrame(self)
        self.preset_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(self.preset_frame, text="⚡ Shortcuts", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=15, pady=(10, 5))
        
        self.preset_row = ctk.CTkFrame(self.preset_frame, fg_color="transparent")
        self.preset_row.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkButton(
            self.preset_row, 
            text="🍅 Pomo 25\n(Work 25m ➜ Block 5m)", 
            command=lambda: self.add_countdown_task_preset(25, 5),
            fg_color="#e17055", 
            hover_color="#d63031",
            height=50
        ).pack(side="left", padx=5, fill="x", expand=True)

        ctk.CTkButton(
            self.preset_row, 
            text="🧘 Pomo 50\n(Work 50m ➜ Block 10m)", 
            command=lambda: self.add_countdown_task_preset(50, 10),
            fg_color="#0984e3", 
            hover_color="#74b9ff",
            height=50
        ).pack(side="left", padx=5, fill="x", expand=True)

        # --- Lista de Tareas ---
        ctk.CTkLabel(self, text="Cola de Ejecución:", font=("Segoe UI", 11, "bold"), text_color="gray").pack(anchor="w", padx=25, pady=(20, 0))
        
        self.task_listbox = tk.Listbox(
            self, 
            bg="#2d3436", 
            fg="white", 
            borderwidth=0, 
            highlightthickness=0, 
            font=("Consolas", 10),
            activestyle="none"
        )
        self.task_listbox.pack(fill="x", padx=20, pady=5, ipady=5)
        
        # Footer
        ctk.CTkLabel(self, text="⚠️ NO ESCAPE. NO MERCY.", font=("Segoe UI", 10, "bold"), text_color="#d63031").pack(side="bottom", pady=15)

    def add_scheduled_task(self):
        try:
            t_str = self.hour_entry.get()
            duration = int(self.hour_duration.get())
            datetime.strptime(t_str, "%H:%M") # Validate
            self.scheduled_tasks.append({"type": "fixed", "time": t_str, "duration": duration, "active": True})
            self.update_task_list()
        except ValueError:
            messagebox.showerror("Error", "Formato inválido. Usa HH:MM y números.")

    def add_countdown_task(self):
        try:
            wait = int(self.wait_min.get())
            duration = int(self.wait_duration.get())
            target_time = (datetime.now() + timedelta(minutes=wait)).strftime("%H:%M:%S")
            self.scheduled_tasks.append({"type": "countdown", "time": target_time, "duration": duration, "active": True})
            self.update_task_list()
        except ValueError:
            messagebox.showerror("Error", "Introduce números válidos.")

    def add_countdown_task_preset(self, wait, duration):
        target_time = (datetime.now() + timedelta(minutes=wait)).strftime("%H:%M:%S")
        self.scheduled_tasks.append({"type": "countdown", "time": target_time, "duration": duration, "active": True})
        self.update_task_list()

    def update_task_list(self):
        self.task_listbox.delete(0, tk.END)
        for task in self.scheduled_tasks:
            icon = "⏰" if task['type'] == 'fixed' else "⏳"
            info = f" {icon}  {task['time']}  ➜  {task['duration']} min"
            self.task_listbox.insert(tk.END, info)

    def check_persistence(self):
        # Misma lógica de persistencia que antes
        try:
            with open("session.lock", "r") as f:
                end_str = f.read().strip()
                if end_str:
                    try:
                        end_time = datetime.strptime(end_str, "%Y%m%d%H%M%S")
                        now = datetime.now()
                        if end_time > now:
                            remaining = (end_time - now).total_seconds() / 60
                            self.after(1000, lambda: self.start_blackout(remaining, restart=True))
                        else:
                            if os.path.exists("session.lock"): os.remove("session.lock")
                    except: pass
        except FileNotFoundError: pass

    def time_monitor(self):
        while self.running:
            now = datetime.now()
            current_time_short = now.strftime("%H:%M")
            current_time_full = now.strftime("%H:%M:%S")
            
            for task in self.scheduled_tasks:
                if task['active']:
                    is_time = False
                    if task['type'] == 'fixed' and current_time_short == task['time']: is_time = True
                    elif task['type'] == 'countdown' and current_time_full == task['time']: is_time = True
                        
                    if is_time:
                        task['active'] = False
                        self.after(0, lambda t=task: self.start_blackout(t['duration']))
                        self.after(0, self.update_task_list)
            time.sleep(1)

    def start_blackout(self, minutes, restart=False):
        if self.blackout_active: return
        self.blackout_active = True
        
        # --- Lógica Watchdog & Lock ---
        if not restart:
            end_dt = datetime.now() + timedelta(minutes=minutes)
            ahk_timestamp = end_dt.strftime("%Y%m%d%H%M%S")
            try:
                with open("session.lock", "w") as f: f.write(ahk_timestamp)
                if os.path.exists("watchdog.ahk"): os.startfile("watchdog.ahk")
            except Exception as e: print(f"Watchdog error: {e}")

        # --- Overlay Negro (Multi-Monitor) ---
        # Detectar configuración de monitores
        try:
            from screeninfo import get_monitors
            monitors = get_monitors()
        except ImportError:
            # Fallback a monitor principal si falla la librería
            monitors = [type('obj', (object,), {'x': 0, 'y': 0, 'width': self.winfo_screenwidth(), 'height': self.winfo_screenheight(), 'is_primary': True})]

        self.overlays = []

        for m in monitors:
            overlay = tk.Toplevel(self)
            
            # Geometría exacta para cada monitor
            # Nota: Usamos geometry() con offset para posicionar en monitores secundarios
            overlay.geometry(f"{m.width}x{m.height}+{m.x}+{m.y}")
            
            overlay.overrideredirect(True) # Sin bordes
            overlay.attributes("-topmost", True)
            overlay.configure(bg="black")
            overlay.config(cursor="none")
            
            # Título específico para el monitor principal (detectado por posición 0,0 o flag)
            if m.x == 0 and m.y == 0:
                overlay.title("darkpause_overlay") # Título para el Watchdog
            
            overlay.protocol("WM_DELETE_WINDOW", lambda: None)
            
            # Etiqueta solo en el monitor principal (opcional, o en todos)
            if m.x == 0 and m.y == 0:
                tk.Label(overlay, text="FOCUS MODE", bg="black", fg="#222222", font=("Segoe UI", 20, "bold")).pack(expand=True)
            
            self.overlays.append(overlay)

        def end_blackout():
            self.blackout_active = False
            # Liberar foco y destruir todas las ventanas
            try:
                for ov in self.overlays:
                    try:
                        ov.grab_release()
                        ov.destroy()
                    except: pass
            except: pass
            
            self.overlays = []
            
            if os.path.exists("session.lock"):
                try: os.remove("session.lock")
                except: pass

        # Timer sincronizado para cerrar todas
        self.after(int(minutes * 60000), end_blackout)
        
        def maintain_focus():
            if self.blackout_active:
                # Enfocar la ventana del monitor principal (asumimos que es la primera en (0,0))
                # o iterar para traerlas todas al frente
                for ov in self.overlays:
                    try:
                        ov.lift()
                        # Solo hacemos focus_force y grab en una para no volver loco al sistema
                        # Preferiblemente la que tiene título "darkpause_overlay"
                        if "darkpause_overlay" in ov.title():
                            ov.focus_force()
                            try: ov.grab_set_global() 
                            except: pass
                    except: pass
                
                self.after(300, maintain_focus)
        
        maintain_focus()

if __name__ == "__main__":
    app = DarkPauseApp()
    app.mainloop()
