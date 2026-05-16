# Gokil 🚀

> AI agent yang **gokil** — otonom, gercep, dan punya banyak tools. Jalanin di terminal lo, langsung bisa diajak ngobrol & nyuruh-nyuruh.

Gokil itu agent berbasis **ReAct loop** (Reason → Act → Observe → Respond) yang bisa:
- 🔍 Cari di web (DuckDuckGo) + baca isi halamannya
- 🐚 Jalanin shell command & Python snippet
- 📁 Baca/tulis file di workspace lo
- 🧮 Hitung-hitungan & ngecek waktu
- 🧠 Inget catatan persisten antar-sesi
- 🎨 UI terminal cakep pake `rich` (panel, syntax highlight, streaming)
- 🔌 Pake **provider mana aja yang OpenAI-compatible**: OpenAI, OpenRouter, Groq, Together, Ollama, LM Studio, vLLM, dll.
- 🇮🇩 Personality santai-gokil, bilingual ID/EN.

---

## Install

```bash
git clone https://github.com/tasikidn-jpg/Gokil.git
cd Gokil
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

Butuh Python 3.9+.

## Setup

Copy contoh env, terus isi API key lo:

```bash
cp .env.example .env
```

Edit `.env`:

```env
GOKIL_BASE_URL=https://api.openai.com/v1
GOKIL_API_KEY=sk-xxxxx
GOKIL_MODEL=gpt-4o-mini
```

Mau pake provider lain? Tinggal ganti `GOKIL_BASE_URL`:

| Provider   | Base URL                              | Contoh model               |
|-----------:|---------------------------------------|----------------------------|
| OpenAI     | `https://api.openai.com/v1`           | `gpt-4o-mini`              |
| OpenRouter | `https://openrouter.ai/api/v1`        | `anthropic/claude-3.5-sonnet` |
| Groq       | `https://api.groq.com/openai/v1`      | `llama-3.3-70b-versatile`  |
| Ollama     | `http://localhost:11434/v1`           | `llama3.1`                 |
| LM Studio  | `http://localhost:1234/v1`            | (model yg di-load)         |

> ⚠️ Tool-calling cuma jalan optimal di model yang support function calling.

## Pemakaian

### Interactive REPL

```bash
gokil
```

Lo bakal masuk ke prompt `you ▸`. Ketik apa aja, atau pake command:

```
/help          — lihat command
/tools         — lihat tools tersedia
/clear         — reset percakapan
/model <name>  — ganti model
/lang id|en|mix — ganti bahasa persona
/exit          — keluar
```

### One-shot

```bash
gokil "carikan harga BTC sekarang dan hitung 0.05 BTC dalam IDR"
```

### Safe mode

Disable shell/write/python_exec biar agent gak bisa nyentuh sistem:

```bash
gokil --safe
```

---

## Tools Bawaan

| Tool            | Fungsi                                                  |
|-----------------|---------------------------------------------------------|
| `web_search`    | Cari di DuckDuckGo                                       |
| `fetch_url`     | Ambil & bersihin konten halaman web                      |
| `read_file`     | Baca file teks                                           |
| `write_file`    | Tulis/append ke file *(danger)*                          |
| `list_dir`      | List isi direktori                                       |
| `shell_exec`    | Jalanin shell command *(danger)*                         |
| `python_exec`   | Jalanin Python snippet di subprocess *(danger)*          |
| `calculator`    | Evaluasi ekspresi aritmatika dengan AST aman             |
| `datetime_now`  | Tanggal/jam sekarang (boleh kasih tz offset)             |
| `remember`      | Simpen catatan persisten ke `.gokil/memory.json`         |
| `recall`        | Ambil catatan dari memori                                |
| `forget`        | Hapus catatan dari memori                                |

## Bikin Tool Sendiri

```python
from gokil import GokilAgent
from gokil.tools import default_registry

reg = default_registry()
reg.add(
    name="reverse_text",
    description="Reverse the input string.",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
    func=lambda text: text[::-1],
)

agent = GokilAgent(registry=reg)
agent.chat("balikin kata 'gokil banget'")
```

## Pake sebagai Library

```python
from gokil import GokilAgent

agent = GokilAgent()
reply = agent.chat("apa headline IT terbaru hari ini?")
print(reply)
```

## Struktur Project

```
src/gokil/
├── __init__.py
├── agent.py        # ReAct loop
├── cli.py          # entry point `gokil`
├── config.py       # env config
├── llm.py          # OpenAI-compatible client
├── persona.py      # system prompt
├── ui.py           # rich terminal UI
└── tools/
    ├── __init__.py
    ├── base.py     # Tool, ToolRegistry, ToolResult
    └── builtins.py # tool bawaan
```

## Lisensi

MIT.
