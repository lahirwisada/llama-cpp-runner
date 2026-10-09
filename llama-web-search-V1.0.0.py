import requests
import json
from ddgs import DDGS
import sys

# Konfigurasi API Llama.cpp Server
LLAMA_API_URL = "http://localhost:8080/completion"

def search_web(query, max_results=5):
    """Mencari informasi di DuckDuckGo"""
    print(f"\n🔍 Sedang mencari di internet untuk: '{query}'...\n")
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=max_results)]
        if not results:
            return "Tidak ada hasil pencarian ditemukan."
        
        # Format hasil pencarian agar mudah dibaca AI
        context = ""
        for i, r in enumerate(results, 1):
            context += f"[{i}] Judul: {r['title']}\n    Snippet: {r['body']}\n    URL: {r['href']}\n\n"
        return context
    except Exception as e:
        return f"Error saat mencari: {e}"

def format_prompt(query, search_context):
    """Membuat prompt khusus untuk Qwen (ChatML format)"""
    system_instruction = (
        "Anda adalah asisten AI yang sangat membantu. "
        "Jawab pertanyaan pengguna berdasarkan HASIL PENCARIAN WEB di bawah ini. "
        "Jika jawaban tidak ada di hasil pencarian, gunakan pengetahuan umum Anda, "
        "tapi utamakan informasi dari pencarian. Sertakan URL sumber jika relevan."
    )
    
    prompt = f"""<|im_start|>system
{system_instruction}

KONTEKS PENCARIAN WEB:
{search_context}<|im_end|>
<|im_start|>user
{query}<|im_end|>
<|im_start|>assistant
"""
    return prompt

def stream_response(prompt):
    """Mengirim prompt ke llama-server dan menampilkan output secara real-time"""
    payload = {
        "prompt": prompt,
        "n_predict": 512,       # Batas token output
        "temperature": 0.3,     # Lebih rendah = lebih fokus pada fakta
        "top_k": 40,
        "top_p": 0.9,
        "stream": True          # Aktifkan streaming agar seperti chat biasa
    }

    print("🤖 AI sedang berpikir dan merangkum...\n")
    
    try:
        response = requests.post(LLAMA_API_URL, json=payload, stream=True)
        response.raise_for_status()
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                # Parse SSE (Server-Sent Events) dari llama.cpp
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

    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Tidak bisa terhubung ke llama-server!")
        print("💡 Pastikan Anda sudah menjalankan 'llama-server' via llama-cpp-runner.py di port 8080.")
        sys.exit(1)
    except Exception as e:
        print(f"\n Error: {e}")

def main():
    print("="*50)
    print("  LLAMA.CPP WEB SEARCH AGENT (Qwen 3.8B)")
    print("="*50)
    print("Ketik 'exit' atau 'quit' untuk keluar.\n")
    
    while True:
        query = input("👤 Anda: ").strip()
        if query.lower() in ['exit', 'quit', 'keluar']:
            print("Sampai jumpa! 👋")
            break
        if not query:
            continue
            
        # 1. Cari di Web
        context = search_web(query)
        
        # 2. Format Prompt
        final_prompt = format_prompt(query, context)
        
        # 3. Tanya ke AI
        stream_response(final_prompt)
        print("-" * 50)

if __name__ == "__main__":
    main()
