import requests
import json
import re
import sys
import os
from datetime import datetime
from ddgs import DDGS

# Konfigurasi
LLAMA_API_URL = "http://localhost:8080/completion"
MAX_RETRIES = 4
TEMP_STATE_FILE = ".search_state.json"

def get_current_time():
    return datetime.now().strftime("%A, %d %B %Y, pukul %H:%M WIB")

def call_llama(prompt, max_tokens=512, temperature=0.2):
    payload = {
        "prompt": prompt,
        "n_predict": max_tokens,
        "temperature": temperature,
        "top_k": 40,
        "top_p": 0.9,
        "stream": False
    }
    try:
        response = requests.post(LLAMA_API_URL, json=payload)
        response.raise_for_status()
        return response.json().get("content", "").strip()
    except requests.exceptions.ConnectionError:
        print("\n ERROR: Tidak bisa terhubung ke llama-server!")
        sys.exit(1)
    except Exception as e:
        return f"Error API: {e}"

# --- Manajemen State (File Temporary) ---
def load_state():
    if os.path.exists(TEMP_STATE_FILE):
        with open(TEMP_STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"visited_urls": [], "search_history": [], "final_context": ""}

def save_state(state):
    with open(TEMP_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def clear_state():
    if os.path.exists(TEMP_STATE_FILE):
        os.remove(TEMP_STATE_FILE)

# --- Fungsi Inti AI ---
def analyze_intent(user_query):
    current_time = get_current_time()
    prompt = f"""<|im_start|>system
Waktu saat ini: {current_time}. Analisis permintaan user.
Jika bisa dijawab dengan pengetahuan umum, pilih NO_SEARCH.
Jika butuh fakta terkini/berita, pilih NEED_SEARCH.
Output 2 baris:
Baris 1: NEED_SEARCH atau NO_SEARCH
Baris 2: Keyword pencarian (Inggris/Indonesia) atau NONE.<|im_end|>
<|im_start|>user
Permintaan: {user_query}<|im_end|>
<|im_start|>assistant"""
    
    resp = call_llama(prompt, max_tokens=100, temperature=0.1)
    lines = resp.split('\n')
    intent = lines[0].strip().upper() if lines else "NEED_SEARCH"
    keyword = lines[1].strip() if len(lines) > 1 else user_query
    return intent, re.sub(r'^["\']|["\']$', '', keyword).strip()

def search_web(query, max_results=5):
    print(f" Mencari di internet: '{query}'...")
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=max_results)]
        return results if results else []
    except Exception as e:
        print(f"❌ Error pencarian: {e}")
        return []

def evaluate_snippets(query, results, visited_urls):
    """AI membaca SEMUA snippet dan memutuskan: Jawab langsung, Kunjungi URL, atau Cari Ulang"""
    current_time = get_current_time()
    
    snippets_text = ""
    for i, r in enumerate(results):
        status = "[SUDAH DIKUNJUNGI]" if r['href'] in visited_urls else "[BARU]"
        snippets_text += f"{i+1}. {status} {r['title']}\n   {r['body']}\n   URL: {r['href']}\n\n"

    prompt = f"""<|im_start|>system
Waktu: {current_time}. Anda adalah analis pencarian.
Query User: {query}
URL yang sudah dikunjungi: {visited_urls if visited_urls else 'Belum ada'}

Daftar Hasil Pencarian (Snippet):
{snippets_text}

TUGAS: Evaluasi snippet di atas. Pilih SATU tindakan:
1. Jika snippet sudah cukup untuk menjawab query secara akurat:
   ACTION: ANSWER
   VALUE: [Ringkasan singkat fakta yang ditemukan dari snippet]
2. Jika perlu membaca artikel lengkap, pilih SATU URL paling relevan yang berstatus [BARU]:
   ACTION: VISIT
   VALUE: [Tulis URL lengkap persis seperti di atas]
3. Jika tidak ada snippet yang relevan:
   ACTION: NEW_KEYWORD
   VALUE: [Tulis keyword pencarian baru yang lebih spesifik]

OUTPUT WAJIB FORMAT 2 BARIS:
ACTION: [ANSWER/VISIT/NEW_KEYWORD]
VALUE: [Isi sesuai pilihan]<|im_end|>
<|im_start|>user
Evaluasi sekarang.<|im_end|>
<|im_start|>assistant"""

    resp = call_llama(prompt, max_tokens=200, temperature=0.1)
    lines = resp.split('\n')
    
    action = "NEW_KEYWORD"
    value = query
    
    for line in lines:
        if line.startswith("ACTION:"):
            action = line.replace("ACTION:", "").strip().upper()
        elif line.startswith("VALUE:"):
            value = line.replace("VALUE:", "").strip()
            
    return action, value

def extract_content(url):
    print(f"📖 Membaca konten penuh: {url}...")
    try:
        with DDGS() as ddgs:
            text = ddgs.extract(url, fmt="text")
            return text[:5000] if text else "" # Batasi 5000 char
    except Exception as e:
        return f"Error ekstraksi: {e}"

def evaluate_content(query, content):
    """AI mengevaluasi apakah isi artikel sudah menjawab pertanyaan"""
    current_time = get_current_time()
    prompt = f"""<|im_start|>system
Waktu: {current_time}. Anda adalah fact-checker.
Query User: {query}

Isi Artikel:
{content[:3000]}...

TUGAS: Apakah artikel ini berisi jawaban spesifik, faktual, dan relevan untuk query user?
Output HANYA: YES atau NO<|im_end|>
<|im_start|>user
Evaluasi.<|im_end|>
<|im_start|>assistant"""
    
    resp = call_llama(prompt, max_tokens=10, temperature=0.1)
    return "YES" in resp.upper()

def generate_final_answer(query, context_source, context_data):
    current_time = get_current_time()
    prompt = f"""<|im_start|>system
Waktu: {current_time}. Jawab pertanyaan user dengan SINGKAT, PADAT, dan FAKTUAL berdasarkan data di bawah ini.
Perhatikan konteks waktu (kemarin, hari ini, dll). Sertakan sumber.

Data {context_source}:
{context_data}
<|im_end|>
<|im_start|>user
{query}<|im_end|>
<|im_start|>assistant"""

    print("\n🤖 Merangkum jawaban akhir...\n")
    payload = {
        "prompt": prompt, "n_predict": 1024, "temperature": 0.3, 
        "top_k": 40, "top_p": 0.9, "stream": True
    }
    
    try:
        response = requests.post(LLAMA_API_URL, json=payload, stream=True)
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith("data: "):
                    json_str = decoded[6:]
                    if json_str == "[DONE]": break
                    print(json.loads(json_str).get("content", ""), end="", flush=True)
        print("\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")

def main():
    print("="*70)
    print("  🧠 LLAMA.CPP AGENTIC SEARCH (State-Aware + Snippet Eval)")
    print("="*70)
    print(f"   {get_current_time()}")
    print("  Ketik 'exit' untuk keluar.\n")
    
    # Cek server
    try: requests.get(LLAMA_API_URL.replace("/completion", ""), timeout=2)
    except: 
        print(" llama-server tidak aktif di port 8080!"); sys.exit(1)

    while True:
        try: query = input("👤 Anda: ").strip()
        except (KeyboardInterrupt, EOFError): break
        if query.lower() in ['exit', 'quit']: break
        if not query: continue

        print("\n" + "="*70)
        intent, keyword = analyze_intent(query)
        
        if intent == "NO_SEARCH":
            print("💡 AI memutuskan: Bisa dijawab langsung.")
            generate_final_answer(query, "Pengetahuan Internal", "Tanpa pencarian web.")
            print("="*70 + "\n")
            continue

        print(f"💡 AI memutuskan: Perlu pencarian. Keyword awal: '{keyword}'")
        
        # Inisialisasi State
        state = {"visited_urls": [], "search_history": []}
        save_state(state)
        search_success = False

        for attempt in range(1, MAX_RETRIES + 1):
            print(f"\n--- Iterasi Pencarian ke-{attempt} ---")
            results = search_web(keyword, max_results=5)
            
            if not results:
                print("⚠️ Tidak ada hasil. Mencoba keyword alternatif...")
                keyword = f"{query} news today"
                continue

            state['search_history'].append({"attempt": attempt, "keyword": keyword, "results_count": len(results)})
            save_state(state)

            # 1. Evaluasi Snippet oleh AI
            print("🧠 AI sedang menganalisis seluruh hasil pencarian (snippet)...")
            action, value = evaluate_snippets(query, results, state['visited_urls'])
            print(f"   ➡️ Keputusan AI: {action}")

            if action == "ANSWER":
                print("✅ AI menemukan jawaban dari snippet.")
                generate_final_answer(query, "Snippet Pencarian", value)
                search_success = True
                break

            elif action == "NEW_KEYWORD":
                print(f"🔄 AI meminta keyword baru: '{value}'")
                keyword = value
                continue

            elif action == "VISIT":
                url_to_visit = value
                # Fallback jika AI memilih URL yang sudah dikunjungi
                if url_to_visit in state['visited_urls']:
                    print("⚠️ AI memilih URL yang sudah dikunjungi. Mencari URL [BARU] dari hasil...")
                    url_to_visit = next((r['href'] for r in results if r['href'] not in state['visited_urls']), None)
                
                if not url_to_visit:
                    print("⚠️ Tidak ada URL baru yang tersedia. Mengulang pencarian...")
                    keyword = f"{keyword} detailed analysis"
                    continue

                # 2. Ekstraksi & Evaluasi Konten
                print(f"📖 Mengunjungi: {url_to_visit}")
                content = extract_content(url_to_visit)
                state['visited_urls'].append(url_to_visit)
                save_state(state)

                if not content or len(content) < 200:
                    print("⚠️ Konten terlalu pendek/invalid (mungkin halaman index). Mencoba URL lain...")
                    continue

                print("🧠 AI sedang mengevaluasi isi artikel...")
                if evaluate_content(query, content):
                    print("✅ AI puas dengan konten artikel ini.")
                    generate_final_answer(query, f"Artikel: {url_to_visit}", content)
                    search_success = True
                    break
                else:
                    print("❌ AI menilai artikel tidak relevan/cukup. Mencoba iterasi berikutnya...")
                    # Biarkan loop berlanjut, AI akan diminta keyword baru atau URL baru di iterasi berikutnya

        if not search_success:
            print("\n❌ Maaf, AI tidak dapat menemukan informasi yang memuaskan setelah beberapa percobaan.")

        # Bersihkan file temporary
        clear_state()
        print("="*70 + "\n")

if __name__ == "__main__":
    main()