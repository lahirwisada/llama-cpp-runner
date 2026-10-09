import requests
import json
import re
import sys
from datetime import datetime
from ddgs import DDGS

# Konfigurasi API Llama.cpp Server
LLAMA_API_URL = "http://localhost:8080/completion"
MAX_RETRIES = 4  # Maksimal 4 kali percobaan pencarian ulang untuk mencegah infinite loop

def get_current_time():
    """Mendapatkan waktu saat ini agar AI sadar konteks waktu (kemarin, hari ini, dll)"""
    return datetime.now().strftime("%A, %d %B %Y, pukul %H:%M WIB")

def call_llama(prompt, max_tokens=512, temperature=0.2):
    """Fungsi helper untuk memanggil llama-server"""
    payload = {
        "prompt": prompt,
        "n_predict": max_tokens,  # <-- PERBAIKAN: Tambahkan koma di sini
        "temperature": temperature,
        "top_k": 40,
        "top_p": 0.9,
        "stream": False
    }
    try:
        response = requests.post(LLAMA_API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("content", "").strip()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Tidak bisa terhubung ke llama-server!")
        print("💡 Pastikan 'llama-server' sudah berjalan via llama-cpp-runner.py di port 8080.")
        sys.exit(1)
    except Exception as e:
        return f"Error API: {e}"

def analyze_intent(user_query):
    """Langkah 1: AI menganalisis apakah perlu mencari di web atau bisa langsung jawab"""
    current_time = get_current_time()
    system_prompt = (
        f"Waktu saat ini adalah: {current_time}. "
        "Anda adalah AI yang cerdas dan efisien. Analisis permintaan user. "
        "Jika Anda YAKIN bisa menjawabnya dengan akurat menggunakan pengetahuan umum Anda, pilih NO_SEARCH. "
        "Jika pertanyaan membutuhkan fakta terkini, data spesifik, berita terbaru, atau perbandingan waktu (misal: 'kemarin', 'saat ini'), pilih NEED_SEARCH.\n\n"
        "ATURAN OUTPUT (WAJIB 2 BARIS):\n"
        "Baris 1: NEED_SEARCH atau NO_SEARCH\n"
        "Baris 2: Jika NEED_SEARCH, tuliskan SATU keyword pencarian terbaik (Inggris/Indonesia). Jika NO_SEARCH, tulis NONE."
    )
    
    prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\nPermintaan: {user_query}<|im_end|>\n<|im_start|>assistant\n"
    
    raw_response = call_llama(prompt, max_tokens=100, temperature=0.1)
    lines = raw_response.split('\n')
    
    intent = lines[0].strip().upper() if len(lines) > 0 else "NEED_SEARCH"
    keyword = lines[1].strip() if len(lines) > 1 else user_query
    
    # Bersihkan keyword dari tanda kutip
    keyword = re.sub(r'^["\']|["\']$', '', keyword).strip()
    
    return intent, keyword

def search_web(query, max_results=3):
    """Langkah 2: Melakukan pencarian web"""
    print(f"🔍 Mencari di internet dengan keyword: '{query}'...")
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=max_results)]
        
        if not results:
            return "NO_RESULTS", []
        
        context = "=== SNIPPET HASIL PENCARIAN ===\n"
        urls = []
        for i, r in enumerate(results, 1):
            url = r.get('href', 'No URL')
            context += f"[{i}] Judul: {r.get('title', 'No Title')}\n    Snippet: {r.get('body', 'No Snippet')}\n    URL: {url}\n\n"
            urls.append(url)
            
        return context, urls
    except Exception as e:
        return f"ERROR: {e}", []

def extract_content(url):
    """Langkah 3: Ekstraksi konten penuh dari URL"""
    print(f"📖 Membaca konten penuh dari: {url}...")
    try:
        with DDGS() as ddgs:
            extracted_text = ddgs.extract(url, fmt="text")
            if extracted_text:
                # Batasi 4000 karakter agar muat di context window ZRAM
                return extracted_text[:4000] + ("\n\n...[Konten dipotong, fokus pada bagian awal]..." if len(extracted_text) > 4000 else "")
            return "KONTEN KOSONG"
    except Exception as e:
        return f"ERROR EKSTRAKSI: {e}"

def evaluate_context(user_query, context):
    """Langkah 4: AI mengevaluasi apakah konteks yang ada sudah cukup untuk menjawab"""
    current_time = get_current_time()
    system_prompt = (
        f"Waktu saat ini: {current_time}. "
        "Tugas Anda: Evaluasi apakah informasi di bawah ini CUKUP untuk menjawab pertanyaan user secara akurat, faktual, dan relevan dengan waktu saat ini.\n\n"
        "ATURAN OUTPUT (WAJIB 2 BARIS):\n"
        "Baris 1: YES (jika cukup) atau NO (jika belum cukup).\n"
        "Baris 2: Jika NO, tuliskan 'EXTRACT: [pilih salah satu URL dari konteks]' ATAU 'NEW_KEYWORD: [keyword pencarian baru yang lebih spesifik]'. Jika YES, tulis NONE."
    )
    
    prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\nPertanyaan: {user_query}\n\nInformasi yang ditemukan:\n{context}<|im_end|>\n<|im_start|>assistant\n"
    
    raw_response = call_llama(prompt, max_tokens=150, temperature=0.1)
    lines = raw_response.split('\n')
    
    decision = lines[0].strip().upper() if len(lines) > 0 else "NO"
    action = lines[1].strip() if len(lines) > 1 else "NONE"
    
    return decision, action

def generate_final_answer(user_query, context_used):
    """Langkah 5: Merangkum jawaban akhir yang singkat dan padat"""
    current_time = get_current_time()
    system_prompt = (
        f"Waktu saat ini: {current_time}. "
        "Anda adalah asisten AI yang sangat membantu, ringkas, dan padat. "
        "Jawab pertanyaan user HANYA berdasarkan informasi yang diberikan. "
        "PERHATIKAN KONTEKS WAKTU (misal: 'kemarin', 'tadi', 'saat ini') dan komparasi data agar relevan. "
        "BERIKAN PENJELASAN YANG SINGKAT DAN LANGSUNG PADA INTINYA. "
        "Jika informasi tidak ditemukan, katakan 'Informasi spesifik tidak ditemukan dalam pencarian terkini'. "
        "Sertakan sumber (URL) secara singkat di akhir jika ada."
    )
    
    prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\nPertanyaan: {user_query}\n\nKonteks Informasi:\n{context_used}<|im_end|>\n<|im_start|>assistant\n"
    
    print("\n🤖 Merangkum jawaban akhir...\n")
    
    payload = {
        "prompt": prompt,
        "n_predict": 1024,
        "temperature": 0.3,
        "top_k": 40,
        "top_p": 0.9,
        "stream": True
    }
    
    try:
        response = requests.post(LLAMA_API_URL, json=payload, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    json_str = decoded_line[6:]
                    if json_str == "[DONE]":
                        break
                    data = json.loads(json_str)
                    print(data.get("content", ""), end="", flush=True)
        print("\n")
    except Exception as e:
        print(f"\n❌ Error saat mendapatkan jawaban: {e}")

def main():
    print("="*70)
    print("  🧠 LLAMA.CPP AGENTIC WEB SEARCH (Qwen 3.8B + Time-Aware)")
    print("="*70)
    print(f"  🕒 Waktu Sistem Saat Ini: {get_current_time()}")
    print("  AI akan: Analisis → Cari → Evaluasi → (Ekstrak/Ulang) → Jawab Singkat.")
    print("  Ketik 'exit' atau 'quit' untuk keluar.\n")
    
    while True:
        try:
            query = input(" Anda: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSampai jumpa! 👋")
            break
            
        if query.lower() in ['exit', 'quit', 'keluar']:
            print("Sampai jumpa! 👋")
            break
        if not query:
            continue
            
        print("\n" + "="*70)
        
        # 1. Analisis Intent
        print("🤔 Menganalisis kebutuhan pencarian...")
        intent, keyword = analyze_intent(query)
        
        if intent == "NO_SEARCH":
            print("💡 AI memutuskan: Bisa dijawab langsung tanpa pencarian web.")
            generate_final_answer(query, "Menggunakan pengetahuan internal AI (tanpa pencarian web).")
            print("="*70 + "\n")
            continue
            
        print(f"💡 AI memutuskan: Perlu pencarian web. Keyword: '{keyword}'")
        
        # 2. Loop Pencarian & Evaluasi (Maksimal MAX_RETRIES)
        current_context = ""
        search_success = False
        
        for attempt in range(1, MAX_RETRIES + 1):
            print(f"\n--- Percobaan Pencarian ke-{attempt} ---")
            
            # Cari di Web
            search_result, urls = search_web(keyword, max_results=3)
            
            if search_result == "NO_RESULTS":
                print("⚠️ Tidak ada hasil ditemukan.")
                current_context = "Tidak ada hasil pencarian."
                break
            elif search_result.startswith("ERROR"):
                print(f"❌ {search_result}")
                break
                
            current_context = search_result
            
            # Evaluasi oleh AI
            print(" AI sedang mengevaluasi apakah snippet cukup...")
            decision, action = evaluate_context(query, current_context)
            
            if decision == "YES":
                print("✅ AI memutuskan: Informasi sudah cukup untuk dijawab.")
                search_success = True
                break
                
            # Jika NO, cek apakah perlu ekstrak atau keyword baru
            if action.startswith("EXTRACT:"):
                url_to_extract = action.replace("EXTRACT:", "").strip()
                # Fallback: jika AI tidak memberikan URL valid, ambil URL pertama dari hasil
                if not url_to_extract.startswith("http") and len(urls) > 0:
                    url_to_extract = urls[0]
                    
                extracted_text = extract_content(url_to_extract)
                current_context = f"=== KONTEN PENUH DARI {url_to_extract} ===\n{extracted_text}"
                
                # Evaluasi ulang setelah ekstrak
                print("🧠 AI sedang mengevaluasi konten penuh yang baru dibaca...")
                decision2, action2 = evaluate_context(query, current_context)
                
                if decision2 == "YES":
                    print("✅ AI memutuskan: Konten penuh sudah cukup untuk dijawab.")
                    search_success = True
                    break
                else:
                    print("️ AI memutuskan: Konten penuh masih belum cukup. Mencoba keyword baru...")
                    keyword = action2.replace("NEW_KEYWORD:", "").strip() if "NEW_KEYWORD:" in action2 else f"{query} latest update detail"
                    
            elif action.startswith("NEW_KEYWORD:"):
                keyword = action.replace("NEW_KEYWORD:", "").strip()
                print(f"🔄 AI memutuskan: Perlu mencari ulang dengan keyword baru: '{keyword}'")
            else:
                print("⚠️ Format respons AI tidak dikenali, menghentikan loop.")
                break
                
        # 3. Hasil Akhir
        print("\n" + "-"*70)
        if search_success:
            generate_final_answer(query, current_context)
        else:
            print("❌ Maaf, setelah beberapa kali percobaan pencarian dan pembacaan konten, AI tidak dapat menemukan informasi spesifik yang Anda minta.")
            
        print("="*70 + "\n")

if __name__ == "__main__":
    # Cek koneksi awal
    try:
        requests.get(LLAMA_API_URL.replace("/completion", ""), timeout=2)
    except:
        print("❌ PERINGATAN: llama-server tidak terdeteksi di port 8080.")
        print("💡 Jalankan 'llama-cpp-runner.py' dan pilih mode 'Server' terlebih dahulu!")
        sys.exit(1)
        
    main()