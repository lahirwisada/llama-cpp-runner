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

def search_web(query, max_results=5):
    """Langkah 2: Melakukan pencarian menggunakan library ddgs"""
    print(f"🔍 AI mencari di internet dengan keyword: '{query}'...\n")
    try:
        with DDGS() as ddgs:
            # Menggunakan endpoint .text() dari ddgs
            results = [r for r in ddgs.text(query, max_results=max_results, safesearch="off")]
        
        if not results:
            return "Tidak ada hasil pencarian ditemukan."
        
        context = ""
        for i, r in enumerate(results, 1):
            context += f"[{i}] Judul: {r.get('title', 'No Title')}\n    Snippet: {r.get('body', 'No Snippet')}\n    URL: {r.get('href', 'No URL')}\n\n"
        return context
    except Exception as e:
        return f"Error saat mencari: {e}"

def generate_final_answer(user_query, search_context):
    """Langkah 3: AI mengevaluasi hasil pencarian dan merangkum jawaban secara SINGKAT"""
    system_prompt = (
        "Anda adalah asisten AI yang sangat membantu, ringkas, dan padat. "
        "Jawab pertanyaan user HANYA berdasarkan HASIL PENCARIAN WEB di bawah ini. "
        "BERIKAN PENJELASAN YANG SINGKAT DAN LANGSUNG PADA INTINYA, kecuali user secara eksplisit meminta penjelasan detail/panjang. "
        "Jika informasi tidak ada di hasil pencarian, katakan 'Informasi tidak ditemukan di hasil pencarian terkini'. "
        "Sertakan referensi URL sumber dalam format singkat di akhir jika relevan."
    )
    
    prompt = f"""<|im_start|>system
{system_prompt}

KONTEKS PENCARIAN WEB:
{search_context}<|im_end|>
<|im_start|>user
{user_query}<|im_end|>
<|im_start|>assistant
"""
    
    print("🤖 AI sedang mengevaluasi hasil dan merangkum jawaban...\n")
    
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
    print("="*60)
    print("  🧠 LLAMA.CPP AGENTIC WEB SEARCH (Qwen 3.8B + DDGS)")
    print("="*60)
    print("AI akan: 1. Memahami intent → 2. Buat keyword → 3. Cari → 4. Rangkum singkat.")
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
            
        print("\n" + "-"*60)
        
        # Langkah 1: AI membuat keyword
        search_keyword = generate_search_query(query)
        print(f"💡 Keyword yang dibuat AI: '{search_keyword}'")
        
        # Langkah 2: Cari di Web
        context = search_web(search_keyword, max_results=5)
        
        # Langkah 3: AI merangkum jawaban (dengan instruksi singkat)
        generate_final_answer(query, context)
        
        print("-" * 60 + "\n")

if __name__ == "__main__":
    main()
