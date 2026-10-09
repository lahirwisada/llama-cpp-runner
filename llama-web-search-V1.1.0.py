import requests
import json
from ddgs import DDGS
import sys
import re

# Konfigurasi API Llama.cpp Server
LLAMA_API_URL = "http://localhost:8080/completion"

def call_llama(prompt, max_tokens=256, temperature=0.2):
    """Fungsi helper untuk memanggil llama-server"""
    payload = {
        "prompt": prompt,
        "n_predict": max_tokens,
        "temperature": temperature,
        "top_k": 40,
        "top_p": 0.9,
        "stream": False # Non-streaming untuk proses internal agar lebih mudah diparsing
    }
    try:
        response = requests.post(LLAMA_API_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("content", "").strip()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Tidak bisa terhubung ke llama-server!")
        print("💡 Pastikan Anda sudah menjalankan 'llama-server' via llama-cpp-runner.py di port 8080.")
        sys.exit(1)
    except Exception as e:
        return f"Error API: {e}"

def generate_search_query(user_query):
    """Langkah 1: AI memahami permintaan dan membuat keyword pencarian yang powerful"""
    system_prompt = (
        "Anda adalah ahli mesin pencari. Tugas Anda adalah menganalisis permintaan user "
        "dan menghasilkan SATU frasa kata kunci pencarian (search query) yang sangat spesifik, "
        "powerful, dan optimal untuk mesin pencari (lebih baik dalam bahasa Inggris untuk hasil global, "
        "atau bahasa Indonesia jika sangat spesifik lokal).\n\n"
        "ATURAN PENTING: Jawab HANYA dengan kata kuncinya. Jangan berikan tanda kutip, "
        "penjelasan, atau kalimat tambahan apa pun."
    )
    
    prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\nPermintaan: {user_query}<|im_end|>\n<|im_start|>assistant\n"
    
    raw_query = call_llama(prompt, max_tokens=50, temperature=0.1)
    # Bersihkan output dari tanda kutip atau karakter aneh yang mungkin dihasilkan model
    clean_query = re.sub(r'^["\']|["\']$', '', raw_query).strip()
    return clean_query

def search_web(query, max_results=3):
    """Langkah 2: Melakukan pencarian DAN mengekstrak konten penuh dari URL teratas"""
    print(f"🔍 AI mencari di internet dengan keyword: '{query}'...\n")
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=max_results)]
        
        if not results:
            return "Tidak ada hasil pencarian ditemukan."
        
        context = "=== HASIL PENCARIAN (SNIPPET) ===\n"
        top_url = None
        
        for i, r in enumerate(results, 1):
            context += f"[{i}] Judul: {r.get('title', 'No Title')}\n    Snippet: {r.get('body', 'No Snippet')}\n    URL: {r.get('href', 'No URL')}\n\n"
            # Simpan URL teratas untuk diekstraksi konten penuhnya
            if i == 1 and r.get('href'):
                top_url = r.get('href')
        
        # Ekstraksi konten penuh dari URL teratas agar AI bisa membaca dan menarik kesimpulan
        if top_url:
            print(f"📖 AI sedang membaca konten penuh dari URL teratas: {top_url}...\n")
            try:
                with DDGS() as ddgs:
                    # Ekstrak teks dari halaman web (fmt="text" mengembalikan teks bersih tanpa HTML)
                    extracted_text = ddgs.extract(top_url, fmt="text")
                    
                    if extracted_text:
                        context += "\n=== KONTEN PENUH HALAMAN WEB (SUMBER UTAMA) ===\n"
                        # Batasi panjang ekstraksi agar tidak melebihi context window (max ~4000 karakter)
                        max_len = 4000
                        if len(extracted_text) > max_len:
                            context += extracted_text[:max_len] + "\n\n... [Konten dipotong karena terlalu panjang, fokus pada bagian awal] ..."
                        else:
                            context += extracted_text
                    else:
                        context += "\n=== KONTEN PENUH HALAMAN WEB ===\n(Gagal mengekstrak atau konten kosong)\n"
            except Exception as e:
                context += f"\n=== KONTEN PENUH HALAMAN WEB ===\n(Error saat ekstraksi: {e})\n"
        
        return context
    except Exception as e:
        return f"Error saat mencari: {e}"

def generate_final_answer(user_query, search_context):
    """Langkah 3: AI mengevaluasi hasil pencarian (termasuk konten penuh) dan merangkum jawaban"""
    system_prompt = (
        "Anda adalah asisten AI yang sangat membantu, ringkas, dan padat. "
        "Anda telah diberikan SNIPPET pencarian dan KONTEN PENUH dari halaman web sumber utama. "
        "Jawab pertanyaan user HANYA berdasarkan informasi di bawah ini. "
        "Gunakan KONTEN PENUH HALAMAN WEB untuk mencari jawaban detail dan menarik kesimpulan yang akurat. "
        "BERIKAN PENJELASAN YANG SINGKAT DAN LANGSUNG PADA INTINYA, kecuali user secara eksplisit meminta penjelasan detail/panjang. "
        "Jika informasi tidak ada, katakan 'Informasi tidak ditemukan di hasil pencarian terkini'. "
        "Sertakan referensi URL sumber dalam format singkat di akhir jika relevan."
    )
    
    prompt = f"""<|im_start|>system
{system_prompt}

{search_context}<|im_end|>
<|im_start|>user
{user_query}<|im_end|>
<|im_start|>assistant
"""
    
    print("🤖 AI sedang menganalisis konten web dan merangkum jawaban...\n")
    
    # Gunakan streaming untuk jawaban akhir agar terasa interaktif
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
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    json_str = decoded_line[6:]
                    if json_str == "[DONE]":
                        break
                    data = json.loads(json_str)
                    content = data.get("content", "")
                    print(content, end="", flush=True)
                    full_response += content
                    
        print("\n\n✅ Selesai!")
        return full_response

    except Exception as e:
        print(f"\n❌ Error saat mendapatkan jawaban: {e}")

def main():
    print("="*70)
    print("  🧠 LLAMA.CPP AGENTIC WEB SEARCH (Qwen 3.8B + DDGS Extract)")
    print("="*70)
    print("AI akan: 1. Buat keyword → 2. Cari → 3. Baca konten penuh URL teratas → 4. Rangkum.")
    print("Ketik 'exit' atau 'quit' untuk keluar.\n")
    
    while True:
        try:
            query = input("👤 Anda: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSampai jumpa! 👋")
            break
            
        if query.lower() in ['exit', 'quit', 'keluar']:
            print("Sampai jumpa! 👋")
            break
        if not query:
            continue
            
        print("\n" + "-"*70)
        
        # Langkah 1: AI membuat keyword
        search_keyword = generate_search_query(query)
        print(f"💡 Keyword yang dibuat AI: '{search_keyword}'")
        
        # Langkah 2 & 2.5: Cari di Web + Ekstrak Konten Penuh URL Teratas
        context = search_web(search_keyword, max_results=3)
        
        # Langkah 3: AI merangkum jawaban berdasarkan konten penuh
        generate_final_answer(query, context)
        
        print("-" * 70 + "\n")

if __name__ == "__main__":
    main()