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
        self.root.title("Llama.cpp Runner - MXLinux Optimized")
        self.root.geometry("700x650")
        
        # Deteksi Sistem Operasi
        self.is_windows = platform.system() == "Windows"
        
        # Default paths berdasarkan OS & Preferensi User
        if self.is_windows:
            self.default_bin_path = "C:\\llama.cpp\\build\\bin\\Release"
            self.server_exe = "llama-server.exe"
            self.cli_exe = "llama-cli.exe"
        else:
            # Sesuai setup user di MXLinux
            self.default_bin_path = "/media/2019DATA/www/llama.cpp/build/bin"
            self.server_exe = "llama-server"
            self.cli_exe = "llama-cli"
            
        self.process = None
        
        # PENTING: Buat widgets DULU sebelum cek proses
        self.create_widgets()
        self.check_running_processes()

    def create_widgets(self):
        # --- Notebook / Tab System ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Tab 1: Konfigurasi Utama
        tab_main = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_main, text="⚙️ Konfigurasi")
        self.create_main_tab(tab_main)
        
        # Tab 2: Argumen Lanjutan
        tab_adv = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_adv, text="🔧 Lanjutan (-ngl, dll)")
        self.create_advanced_tab(tab_adv)
        
        # Tab 3: Bantuan & Penjelasan
        tab_help = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab_help, text="❓ Help / Penjelasan")
        self.create_help_tab(tab_help)

        # --- Status & Control ---
        frame_status = ttk.Frame(self.root, padding=5)
        frame_status.pack(fill="x", padx=10, pady=5)
        self.status_label = ttk.Label(frame_status, text="Status: Idle", foreground="gray", font=("Arial", 10, "bold"))
        self.status_label.pack(side="left")
        
        btn_frame = ttk.Frame(self.root, padding=5)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="🚀 Run Llama.cpp", command=self.run_llama).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🛑 Stop & Clean", command=self.stop_and_clean).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🔄 Cek Proses", command=self.check_running_processes).pack(side="left", padx=5)

    def create_main_tab(self, parent):
        # --- Path Configuration ---
        frame_paths = ttk.LabelFrame(parent, text="Lokasi File", padding=10)
        frame_paths.pack(fill="x", pady=5)
        
        ttk.Label(frame_paths, text="Folder Bin Llama.cpp:").grid(row=0, column=0, sticky="w")
        self.bin_path_var = tk.StringVar(value=self.default_bin_path)
        ttk.Entry(frame_paths, textvariable=self.bin_path_var).grid(row=0, column=1, padx=5, sticky="ew")
        ttk.Button(frame_paths, text="Browse", command=self.browse_bin).grid(row=0, column=2)
        
        ttk.Label(frame_paths, text="File Model (.gguf):").grid(row=1, column=0, sticky="w")
        self.model_path_var = tk.StringVar()
        ttk.Entry(frame_paths, textvariable=self.model_path_var).grid(row=1, column=1, padx=5, sticky="ew")
        ttk.Button(frame_paths, text="Browse", command=self.browse_model).grid(row=1, column=2)
        
        # --- Mode Selection ---
        frame_mode = ttk.LabelFrame(parent, text="Mode Eksekusi", padding=10)
        frame_mode.pack(fill="x", pady=5)
        self.mode_var = tk.StringVar(value="server")
        ttk.Radiobutton(frame_mode, text="Server (Browser/WebUI)", variable=self.mode_var, value="server").pack(anchor="w")
        ttk.Radiobutton(frame_mode, text="CLI (Terminal Interaktif)", variable=self.mode_var, value="cli").pack(anchor="w")

    def create_advanced_tab(self, parent):
        # --- Parameter Performa Dasar ---
        frame_perf = ttk.LabelFrame(parent, text="Performa Dasar", padding=10)
        frame_perf.pack(fill="x", pady=5)
        
        grid_p = ttk.Frame(frame_perf)
        grid_p.pack(fill="x")
        
        ttk.Label(grid_p, text="Threads (-t):").grid(row=0, column=0, sticky="w")
        self.thread_var = tk.StringVar(value="4")
        ttk.Entry(grid_p, textvariable=self.thread_var, width=10).grid(row=0, column=1, padx=5)
        
        ttk.Label(grid_p, text="Context (-c):").grid(row=0, column=2, sticky="w")
        self.context_var = tk.StringVar(value="8192") # Aman dengan ZRAM 2GB
        ttk.Entry(grid_p, textvariable=self.context_var, width=10).grid(row=0, column=3, padx=5)
        
        ttk.Label(grid_p, text="Predict (-n):").grid(row=1, column=0, sticky="w")
        self.predict_var = tk.StringVar(value="-1") 
        ttk.Entry(grid_p, textvariable=self.predict_var, width=10).grid(row=1, column=1, padx=5)
        
        ttk.Label(grid_p, text="Port (--port):").grid(row=1, column=2, sticky="w")
        self.port_var = tk.StringVar(value="8080")
        ttk.Entry(grid_p, textvariable=self.port_var, width=10).grid(row=1, column=3, padx=5)

        # --- Argumen Lanjutan (GPU/CPU Specific) ---
        frame_gpu = ttk.LabelFrame(parent, text="Argumen Hardware & Lainnya", padding=10)
        frame_gpu.pack(fill="x", pady=5)
        
        grid_g = ttk.Frame(frame_gpu)
        grid_g.pack(fill="x")
        
        ttk.Label(grid_g, text="GPU Layers (-ngl):").grid(row=0, column=0, sticky="w")
        self.ngl_var = tk.StringVar(value="0") 
        ttk.Entry(grid_g, textvariable=self.ngl_var, width=10).grid(row=0, column=1, padx=5)
        
        ttk.Label(grid_g, text="Batch Size (-b):").grid(row=0, column=2, sticky="w")
        self.batch_var = tk.StringVar(value="512")
        ttk.Entry(grid_g, textvariable=self.batch_var, width=10).grid(row=0, column=3, padx=5)
        
        ttk.Label(grid_g, text="Flash Attention (--flash-attn):").grid(row=1, column=0, sticky="w")
        self.flash_attn_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(grid_g, variable=self.flash_attn_var).grid(row=1, column=1, sticky="w")
        
        ttk.Label(grid_g, text="Mirostat (--mirostat):").grid(row=1, column=2, sticky="w")
        self.mirostat_var = tk.StringVar(value="0")
        ttk.Combobox(grid_g, textvariable=self.mirostat_var, values=["0", "1", "2"], width=8).grid(row=1, column=3, padx=5)

    def create_help_tab(self, parent):
        help_text = """PENJELASAN ARGUMEN LLAMA.CPP:

[PERFORMA DASAR]
• -t (Threads): Jumlah thread CPU. Untuk i5 gen4/5, gunakan 4. 
  Jangan set melebihi jumlah physical core.
• -c (Context): Panjang konteks token. Default 8192 (aman dengan ZRAM 2GB).
  Naikkan ke 16384+ jika butuh dokumen sangat panjang.
• -n (Predict): Jumlah token prediksi. -1 = unlimited.
• --port: Port untuk mode Server. Default 8080.

[HARDWARE & LANJUTAN]
• -ngl (GPU Layers): Jumlah layer model yang di-offload ke GPU.
  ⚠️ SET KE 0 JIKA TIDAK ADA VGA! (Default di runner ini: 0)
  Jika punya NVIDIA/AMD, isi angka >0 (misal 99 untuk full offload).
• -b (Batch Size): Ukuran batch pemrosesan. 512 adalah sweet spot 
  untuk CPU-only. Terlalu besar justru memperlambat inference CPU.
• --flash-attn: Flash Attention. Menghemat VRAM/RAM pada context 
  panjang. Hanya aktif jika llama.cpp dikompilasi dengan support FA.
• --mirostat: Sampling algorithm untuk menjaga kualitas teks. 
  0 = disabled, 1 = mirostat, 2 = mirostat v2 (lebih stabil).

[TIPS UNTUK SETUP ANDA]
• Model Qwen3.8-4B-Q4_K_M (~2.6GB) sangat ringan.
• ZRAM 2GB + Swap 8GB membuat sistem sangat stabil.
• Selalu simpan model di /media/2019DATA agar root tetap lega.
• Gunakan 'Stop & Clean Memory' jika laptop terasa berat setelah 
  menjalankan inferensi lama."""
        
        txt = tk.Text(parent, wrap="word", font=("Consolas", 10), bg="#2d2d2d", fg="#e0e0e0")
        txt.insert("1.0", help_text)
        txt.config(state="disabled")
        txt.pack(fill="both", expand=True)

    def browse_bin(self):
        path = filedialog.askdirectory(initialdir=self.bin_path_var.get())
        if path: self.bin_path_var.set(path)

    def browse_model(self):
        path = filedialog.askopenfilename(
            initialdir="/media/2019DATA/models", 
            filetypes=[("GGUF Files", "*.gguf"), ("All Files", "*.*")]
        )
        if path: self.model_path_var.set(path)

    def check_running_processes(self):
        found = False
        target_names = [self.server_exe, self.cli_exe, "llama-server", "llama-cli"]
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
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
                    proc.kill()
                    killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        msg = f"Berhasil menghentikan {killed_count} proses." if killed_count > 0 else "Tidak ada proses yang berjalan."
        color = "red" if killed_count > 0 else "gray"
        messagebox.showinfo("Cleaned", msg)
        self.status_label.config(text=f"Status: {'Cleaned' if killed_count else 'Idle'}", foreground=color)

    def run_llama(self):
        bin_path = self.bin_path_var.get()
        model_path = self.model_path_var.get()
        
        if not os.path.exists(model_path):
            messagebox.showerror("Error", "File model tidak ditemukan!")
            return
            
        mode = self.mode_var.get()
        exe_name = self.server_exe if mode == 'server' else self.cli_exe
        executable = os.path.join(bin_path, exe_name)
        
        if not os.path.exists(executable):
            messagebox.showerror("Error", f"Executable tidak ditemukan:\n{executable}")
            return

        # Build command dasar
        cmd = [executable, "-m", model_path, "-t", self.thread_var.get(), "-c", self.context_var.get()]
        
        # Tambahkan argumen lanjutan
        ngl_val = self.ngl_var.get().strip()
        if ngl_val and ngl_val != "0":
            cmd.extend(["-ngl", ngl_val])
            
        batch_val = self.batch_var.get().strip()
        if batch_val:
            cmd.extend(["-b", batch_val])
            
        if self.flash_attn_var.get():
            cmd.append("--flash-attn")
            
        mirostat_val = self.mirostat_var.get().strip()
        if mirostat_val and mirostat_val != "0":
            # PERBAIKAN: Gunakan --mirostat, BUKAN -m (karena -m sudah dipakai untuk model)
            cmd.extend(["--mirostat", mirostat_val])

        # Tambahkan argumen spesifik mode
        if mode == 'server':
            cmd.extend(["--port", self.port_var.get(), "--host", "0.0.0.0"])
        else:
            cmd.extend(["-n", self.predict_var.get(), "--color"])

        # Run in background thread
        threading.Thread(target=self.execute_process, args=(cmd,), daemon=True).start()
        self.status_label.config(text="Status: Starting...", foreground="blue")

    def execute_process(self, cmd):
        try:
            if self.is_windows:
                subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            else:
                # start_new_session penting di Linux agar process detach dari GUI
                subprocess.Popen(cmd, start_new_session=True)
            self.root.after(1000, self.check_running_processes)
        except Exception as e:
            messagebox.showerror("Run Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = LlamaCppRunner(root)
    root.mainloop()