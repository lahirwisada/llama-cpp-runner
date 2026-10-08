import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import sys
import psutil
import threading
import platform

class LlamaCppRunner:
    def __init__(self, root):
        self.root = root
        self.root.title("Llama.cpp Runner - Cross Platform")
        self.root.geometry("600x550")
        
        # Deteksi Sistem Operasi
        self.is_windows = platform.system() == "Windows"
        
        # Default paths berdasarkan OS
        if self.is_windows:
            # Contoh path default di Windows
            self.default_bin_path = "C:\\llama.cpp\\build\\bin\\Release"
            self.server_exe = "llama-server.exe"
            self.cli_exe = "llama-cli.exe"
        else:
            self.default_bin_path = "/media/2019DATA/www/llama.cpp/build/bin"
            self.server_exe = "llama-server"
            self.cli_exe = "llama-cli"

        self.process = None
        
        self.create_widgets()
        self.check_running_processes()

    def create_widgets(self):
        # --- Path Configuration ---
        frame_paths = ttk.LabelFrame(self.root, text="Lokasi File", padding=10)
        frame_paths.pack(fill="x", padx=10, pady=5)

        # Bin Path
        ttk.Label(frame_paths, text="Folder Bin Llama.cpp:").grid(row=0, column=0, sticky="w")
        self.bin_path_var = tk.StringVar(value=self.default_bin_path)
        ttk.Entry(frame_paths, textvariable=self.bin_path_var).grid(row=0, column=1, padx=5, sticky="ew")
        ttk.Button(frame_paths, text="Browse", command=self.browse_bin).grid(row=0, column=2)

        # Model Path
        ttk.Label(frame_paths, text="File Model (.gguf):").grid(row=1, column=0, sticky="w")
        self.model_path_var = tk.StringVar()
        ttk.Entry(frame_paths, textvariable=self.model_path_var).grid(row=1, column=1, padx=5, sticky="ew")
        ttk.Button(frame_paths, text="Browse", command=self.browse_model).grid(row=1, column=2)

        # --- Parameters ---
        frame_params = ttk.LabelFrame(self.root, text="Konfigurasi Performa", padding=10)
        frame_params.pack(fill="x", padx=10, pady=5)

        params_grid = ttk.Frame(frame_params)
        params_grid.pack(fill="x")

        ttk.Label(params_grid, text="Threads (-t):").grid(row=0, column=0, sticky="w")
        self.thread_var = tk.StringVar(value="4")
        ttk.Entry(params_grid, textvariable=self.thread_var, width=10).grid(row=0, column=1, padx=5)

        ttk.Label(params_grid, text="Context (-c):").grid(row=0, column=2, sticky="w")
        self.context_var = tk.StringVar(value="2048")
        ttk.Entry(params_grid, textvariable=self.context_var, width=10).grid(row=0, column=3, padx=5)

        ttk.Label(params_grid, text="Predict (-n):").grid(row=1, column=0, sticky="w")
        self.predict_var = tk.StringVar(value="-1") 
        ttk.Entry(params_grid, textvariable=self.predict_var, width=10).grid(row=1, column=1, padx=5)

        ttk.Label(params_grid, text="Port (--port):").grid(row=1, column=2, sticky="w")
        self.port_var = tk.StringVar(value="8080")
        ttk.Entry(params_grid, textvariable=self.port_var, width=10).grid(row=1, column=3, padx=5)

        # --- Mode Selection ---
        frame_mode = ttk.LabelFrame(self.root, text="Mode Eksekusi", padding=10)
        frame_mode.pack(fill="x", padx=10, pady=5)

        self.mode_var = tk.StringVar(value="server")
        ttk.Radiobutton(frame_mode, text="Server (Browser/WebUI)", variable=self.mode_var, value="server").pack(anchor="w")
        ttk.Radiobutton(frame_mode, text="CLI (Terminal Interaktif)", variable=self.mode_var, value="cli").pack(anchor="w")

        # --- Status & Control ---
        frame_status = ttk.Frame(self.root, padding=10)
        frame_status.pack(fill="x", padx=10, pady=5)

        self.status_label = ttk.Label(frame_status, text="Status: Idle", foreground="gray")
        self.status_label.pack(side="left")

        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(btn_frame, text="🚀 Run Llama.cpp", command=self.run_llama).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🛑 Stop & Clean Memory", command=self.stop_and_clean).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🔄 Cek Proses", command=self.check_running_processes).pack(side="left", padx=5)

    def browse_bin(self):
        if self.is_windows:
            path = filedialog.askdirectory(initialdir=self.bin_path_var.get())
        else:
            path = filedialog.askdirectory(initialdir=self.bin_path_var.get())
        if path:
            self.bin_path_var.set(path)

    def browse_model(self):
        path = filedialog.askopenfilename(filetypes=[("GGUF Files", "*.gguf"), ("All Files", "*.*")])
        if path:
            self.model_path_var.set(path)

    def check_running_processes(self):
        found = False
        target_names = [self.server_exe, self.cli_exe, "llama-server", "llama-cli"]
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Cek nama proses atau command line
                proc_name = proc.info['name'] or ""
                cmdline = " ".join(proc.info['cmdline'] or [])
                
                if any(name in proc_name or name in cmdline for name in target_names):
                    self.status_label.config(text=f"Status: DETECTED (PID: {proc.info['pid']})", foreground="orange")
                    found = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        if not found:
            self.status_label.config(text="Status: Idle (No process found)", foreground="green")

    def stop_and_clean(self):
        killed_count = 0
        target_names = [self.server_exe, self.cli_exe, "llama-server", "llama-cli"]

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_name = proc.info['name'] or ""
                cmdline = " ".join(proc.info['cmdline'] or [])
                
                if any(name in proc_name or name in cmdline for name in target_names):
                    proc.kill() # kill() works on both Windows and Linux
                    killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if killed_count > 0:
            messagebox.showinfo("Cleaned", f"Berhasil menghentikan {killed_count} proses llama.cpp.")
            self.status_label.config(text="Status: Cleaned", foreground="red")
        else:
            self.status_label.config(text="Status: Nothing to clean", foreground="gray")

    def run_llama(self):
        bin_path = self.bin_path_var.get()
        model_path = self.model_path_var.get()
        
        if not os.path.exists(model_path):
            messagebox.showerror("Error", "File model tidak ditemukan!")
            return

        mode = self.mode_var.get()
        
        # Tentukan nama executable berdasarkan OS dan Mode
        if mode == 'server':
            exe_name = self.server_exe
        else:
            exe_name = self.cli_exe
            
        executable = os.path.join(bin_path, exe_name)
        
        if not os.path.exists(executable):
            messagebox.showerror("Error", f"Executable tidak ditemukan di: {executable}")
            return

        # Build command
        cmd = [
            executable,
            "-m", model_path,
            "-t", self.thread_var.get(),
            "-c", self.context_var.get(),
        ]

        if mode == 'server':
            cmd.extend(["--port", self.port_var.get(), "--host", "0.0.0.0"])
        else:
            cmd.extend(["-n", self.predict_var.get(), "--color"])

        # Run in background thread
        threading.Thread(target=self.execute_process, args=(cmd, mode), daemon=True).start()
        self.status_label.config(text="Status: Starting...", foreground="blue")

    def execute_process(self, cmd, mode):
        try:
            # Detach process agar bisa menutup GUI runner tanpa mematikan AI
            if self.is_windows:
                # CREATE_NEW_PROCESS_GROUP diperlukan di Windows untuk detach yang bersih
                subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            else:
                subprocess.Popen(cmd, start_new_session=True)
            
            self.root.after(1000, self.check_running_processes)
        except Exception as e:
            messagebox.showerror("Run Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = LlamaCppRunner(root)
    root.mainloop()
