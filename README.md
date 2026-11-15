<div align="center">

# ⚡ JARVIS
#> ## JARVIS v4 (current)
> The assistant has been rebuilt as a native Windows desktop app: holographic humanoid interface, headset-first
> voice with real-time recognition of your voice, an autonomous plan→act→verify agent with 88 tools, persistent
> memory, screen understanding, a coding agent, research and a scheduler.
> **Install:** `powershell -ExecutionPolicy Bypass -File scripts\install.ps1` · **Run:** `python -m jarvis`
> (or the JARVIS shortcut) · **Full guide:** [docs/JARVIS_V4.md](docs/JARVIS_V4.md)
>
> The sections below describe the legacy v0.1 app (`python main.py --legacy`). It exposes an unauthenticated
> remote-control server through a public tunnel — see the security notes in the v4 guide.

## Autonomous Local-First AI Computer Companion & Remote Control Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![CI: Passing](https://img.shields.io/badge/CI-Passing-10b981?style=flat&logo=githubactions&logoColor=white)](https://github.com/aayushbhatta230-ux/jarvis-ai-agent/actions)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%2011%20%7C%2010-0078D6.svg)](https://microsoft.com/windows)
[![LLM: Ollama](https://img.shields.io/badge/LLM-Llama%203.2%20(Local)-orange.svg)](https://ollama.com)
[![Tunnel: Cloudflare](https://img.shields.io/badge/Tunnel-Cloudflare%20Zero--Trust-F38020.svg)](https://cloudflare.com)

*JARVIS is an autonomous, privacy-first computer companion built for Windows. It fuses local LLM reasoning with real-world OS automation, voice perception, an interactive 3D WebGL interface, and a seamless iPhone/mobile remote companion.*

---

</div>

## 🌟 Key Highlights

- 🧠 **100% Local Intelligence**: Powered by Ollama (`llama3.2`) and Neural Vector Memory — your conversations, code, and system commands never leave your personal machine.
- ⏰ **Smart Alarms & Countdown Timers**: Background thread engine managing precision timers, reminders, and voice notifications.
- 🐙 **Git Intelligence & Remote Sync**: Conversational git status auditor, commit log explorer, and automated one-shot commit/push pipeline.
- 🔍 **Resilient Web Researcher**: DuckDuckGo instant knowledge retrieval with automatic offline LLM fallback.
- 📋 **Windows Clipboard & Code Intelligence**: Native OS clipboard reading/writing and deep workspace source code inspection.
- 📱 **Mobile Remote & PWA Companion**:
  - Full-screen real-time **laptop screen mirroring** streamed straight to your phone.
  - **Remote Touchpad & Navigation**: Scroll, tap, drag, select text, and send keystrokes from your phone.
  - Dedicated **iPhone 15 & Safari PWA** optimization with Add-to-Home-Screen app mode.
- 🎙️ **Natural Voice Interaction**:
  - High-fidelity British Neural voice synthesis (`en-GB-RyanNeural`) powered by Edge TTS.
  - Dual-mic anti-echo architecture: your PC hardware speakers stay muted during remote mobile sessions.
  - Sub-second streaming speech response and natural conversational barge-in.
- 🌐 **Instant Cloudflare Quick Tunnel**:
  - Unlimited bandwidth tunneling with zero monthly quotas and no login required.
  - Remote access anywhere in the world with automatic HTTPS provisioning.
- 🎵 **Autonomous Media & YouTube Music Agency**:
  - Deep song resolution via `yt_dlp` without relying on search listings.
  - Autonomous cursor gliding and physical click execution on player controls.
- 🛡️ **Gated Safety Execution Model**:
  - 40+ capabilities categorized by risk levels (`low`, `medium`, `high`).
  - Gated confirmation before any destructive file or system modifications.
- ✨ **Celestial Hologram Visualizer**:
  - Interactive 3D WebGL particle hologram that reacts dynamically to agent thinking and speech states.

---

## 🏛️ System Architecture

```text
               +---------------------------------------------------+
               |             Remote Companion (iPhone/Web)         |
               |   [Screen Mirror] [Touchpad Control] [Neural TTS]  |
               +-------------------------+-------------------------+
                                         |
                       Cloudflare HTTPS / Local LAN HTTP
                                         |
                                         v
+-----------------------------------------------------------------------------+
|                           JARVIS Core Orchestrator                          |
|                                                                             |
|  [Voice Stream]  -->  [Intent Engine]  -->  [Task Planner]  -->  [Ollama]   |
|        ^                     |                      |                 |     |
|        |                     v                      v                 v     |
|  [Audio I/O]          [Local Memory]         [Capabilities]     [Llama 3.2] |
|                              |                      |                       |
+------------------------------|----------------------|-----------------------+
                               |                      |
                               v                      v
               +-----------------------------------------------+
               |                 Host OS (Windows)             |
               |  [Mouse/Keyboard]  [Chrome/Media]  [Terminal] |
               |  [Screen Capture]  [File System]   [Registry] |
               +-----------------------------------------------+
```

---

## 🌐 Triển khai trang giới thiệu lên GitHub Pages

Workflow [`.github/workflows/pages.yml`](.github/workflows/pages.yml) xuất bản **chỉ** nội dung tĩnh trong thư mục [`pages/`](pages/) — không đăng portfolio cũ, mã Python, dữ liệu máy cục bộ hay địa chỉ tunnel. Địa chỉ dự kiến sau khi triển khai thành công là:

**[https://xuankhanh1612.github.io/jarvis-ai-agent/](https://xuankhanh1612.github.io/jarvis-ai-agent/)**

1. Trong repository GitHub, mở **Settings → Pages → Build and deployment**, chọn **Source: GitHub Actions**.
2. Gộp thay đổi này vào `main`. Workflow **Deploy JARVIS to GitHub Pages** sẽ chạy tự động mỗi khi có thay đổi được đẩy lên `main`.
3. Để chạy lại thủ công, mở **Actions → Deploy JARVIS to GitHub Pages → Run workflow**, chọn `main`. Nếu lần chạy đầu thất bại vì Pages chưa được bật, hãy chọn nguồn như bước 1 rồi chạy lại.
4. Theo dõi kết quả trong tab **Actions**; không cần tạo secret hoặc token riêng.

Có thể xem trang cục bộ bằng `python -m http.server 8000 --directory pages` và mở `http://localhost:8000/`.

> GitHub Pages chỉ phục vụ trang giới thiệu tĩnh; nó không chạy ứng dụng Python/Windows, AI, giọng nói hay điều khiển máy tính. Hãy cài JARVIS v4 trên Windows theo [hướng dẫn đầy đủ](docs/JARVIS_V4.md), hoặc dùng bản chat web riêng sau khi cấu hình bên dưới. Đặc biệt, không đưa server điều khiển từ xa không có xác thực của phiên bản cũ lên Internet công khai.

---

## ▲ Triển khai JARVIS trên web (Vercel)

Bản web tại [jarvis-ai-agent-nine.vercel.app](https://jarvis-ai-agent-nine.vercel.app/) dùng giao diện [`web/`](web/) và API [`api/chat.py`](api/chat.py), kết nối **Google Gemini** qua `OpenAICompatProvider` của JARVIS v4 sau khi triển khai và cấu hình khóa. Có hội thoại nhiều lượt, lưu ngữ cảnh trong tab và tùy chọn giọng nói do trình duyệt hỗ trợ. Đây là **phiên bản chat trên cloud**, không phải toàn bộ ứng dụng Windows: không truy cập màn hình/tệp, chạy lệnh, duyệt web hay điều khiển PC. GitHub Pages vẫn là trang giới thiệu trong `pages/`.

### Cấu hình Vercel

1. Import `xuankhanh1612/jarvis-ai-agent` vào [Vercel](https://vercel.com/xuankhanh1612s-projects), giữ Root Directory ở gốc repository. [`vercel.json`](vercel.json) chọn cấu hình không framework, chỉ phục vụ tĩnh `web/` và triển khai Python Function `/api/chat`. Phụ thuộc nhẹ của API nằm riêng trong [`api/requirements.txt`](api/requirements.txt); không cài bộ phụ thuộc Windows trên Vercel.
2. Trong [Google AI Studio](https://aistudio.google.com/api-keys), tạo một Gemini API key cho dự án của bạn. Trong **Vercel Project → Settings → Environment Variables**, tạo `GEMINI_API_KEY` với giá trị đó cho **Production** và **Preview**; chọn loại **Secret** (hoặc **Sensitive**) nếu có. Khóa này chỉ nằm trên máy chủ, không nhập vào giao diện chat.
3. Tại cùng trang Vercel, tạo thêm `JARVIS_ACCESS_KEY` loại **Secret** cho **Production** và **Preview**. Đây là khóa *riêng*, khác Gemini API key, dùng để mở trang chat. Giá trị phải ngẫu nhiên, khó đoán, tối thiểu 32 ký tự ASCII không có khoảng trắng. Có thể tự tạo trên máy bằng `python -c "import secrets; print(secrets.token_urlsafe(32))"` rồi lưu bằng trình quản lý mật khẩu trước khi thêm vào Vercel. Chỉ nhập khóa này vào trang chat. Nếu thiếu khóa an toàn, API từ chối mọi yêu cầu. **Không gửi cả hai khóa qua chat hoặc commit vào Git.**
4. Redeploy sau khi thay đổi biến môi trường. Ứng dụng mặc định gọi `gemini-3.5-flash-lite`; Google có [gói miễn phí](https://ai.google.dev/gemini-api/docs/pricing) cho mô hình này đối với dự án đủ điều kiện, nhưng hạn mức và tính sẵn có có thể thay đổi. Dự án Google đã bật thanh toán có thể bị tính phí; tài nguyên Vercel cũng có hạn mức/chi phí riêng. Kiểm tra dự án, chính sách thanh toán và [hạn mức Gemini](https://ai.google.dev/gemini-api/docs/rate-limits). Ứng dụng chưa có giới hạn tần suất riêng: chỉ chia sẻ khóa truy cập với người tin cậy và dùng Firewall/giới hạn chi tiêu phù hợp trước khi sử dụng rộng rãi.
5. Mở trang web đã triển khai, nhập `JARVIS_ACCESS_KEY` và gửi một câu hỏi để kiểm tra phản hồi từ mô hình. Nếu Git deployments được bật, các thay đổi sau trên nhánh production sẽ tự triển khai.

Hội thoại được lưu trong `sessionStorage` của tab và đi qua máy chủ Vercel tới Google Gemini mỗi khi bạn gửi tin nhắn. Theo [chính sách giá của Google](https://ai.google.dev/gemini-api/docs/pricing), nội dung ở gói miễn phí có thể được dùng để cải thiện sản phẩm; không gửi thông tin nhạy cảm. Ứng dụng chỉ giữ khóa truy cập trong bộ nhớ trang cho đến khi khóa lại/tải lại; trình duyệt hoặc trình quản lý mật khẩu có thể lưu khóa nếu bạn chọn. Nhận dạng giọng nói (nếu được bật) do trình duyệt cung cấp và có thể gửi âm thanh tới dịch vụ của trình duyệt. Không có lưu trữ server-side hoặc Supabase trong phiên bản này.

Chạy giao diện/API cục bộ: cài `python -m pip install -r api/requirements.txt`, đặt `JARVIS_ACCESS_KEY` và `GEMINI_API_KEY` trong môi trường của bạn, rồi chạy `python scripts/web_dev.py`. Không công khai server phát triển. Kiểm thử: `python -m unittest discover -s tests -p 'test_web.py'`.

Không đưa server điều khiển từ xa không có xác thực của phiên bản cũ lên Internet công khai.

---

## 🚀 Quickstart

### 1. Prerequisites
- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **Python**: Version 3.10, 3.11, or 3.12
- **Ollama**: Download and install from [ollama.com](https://ollama.com)

### 2. Installation
```powershell
# Clone the repository
git clone https://github.com/aayushbhatta230-ux/jarvis-companion.git
cd jarvis-companion

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Pull the lightweight local language model
ollama pull llama3.2
```

### 3. Launching JARVIS
```powershell
python main.py
```

Once running:
- **Local PC Interface**: Open `http://127.0.0.1:8765/` in your browser.
- **iPhone / Mobile Companion**: JARVIS prints your local network IP and a live Cloudflare Tunnel URL in the terminal (e.g. `https://xxxx.trycloudflare.com`). Scan the QR code or open the link on your mobile browser!

---

## 💬 Natural Language Examples

JARVIS understands messy, human conversational language without rigid syntax:

| You Say | JARVIS Does |
|---------|-------------|
| *"Play Starboy on YouTube Music"* | Resolves official track ID, opens Chrome, glides cursor to play button, and begins playback |
| *"What's on my screen right now?"* | Captures display buffer, analyzes open windows, and describes current activity |
| *"Find all PDF notes from last week in Downloads"* | Performs filesystem scan, indexes relevant documents, and provides an organized summary |
| *"Switch to VS Code and show me recent commits"* | Focuses editor, executes git log query via terminal capability, and displays results |
| *"Turn down the volume and record my screen for 30s"* | Controls hardware volume and triggers high-fps background screen recording |

---

## 🛠️ Capability Registry

All agent actions are governed by declarative capabilities in `core/capabilities.py`:

| Category | Available Tools | Safety Level |
|----------|-----------------|:------------:|
| **Media & Audio** | `play_music`, `stop_music`, `pause_music`, `volume_control` | Low |
| **Browser & Web** | `open_url`, `search_web`, `resolve_site` | Low |
| **System & Desktop** | `launch`, `close_app`, `focus_window`, `get_system_info` | Low |
| **Screen Perception** | `capture_screen`, `start_recording`, `stop_recording`, `screen_stream` | Low |
| **File Automation** | `search_files`, `read_file`, `create_folder`, `organize_files` | Low / Med |
| **Destructive Files** | `delete_file`, `overwrite_file`, `rename_file` | **High (Confirmed)** |
| **Terminal & Shell** | `execute_command`, `run_python` | **High (Confirmed)** |

---

## 🔒 Privacy & Security

1. **Zero Data Telemetry**: Your queries, audio input, system files, and screen frames are never uploaded to any remote server or third-party AI provider.
2. **Local Memory Isolation**: Preferences and conversation history are persisted in local JSON stores that are never committed to version control.
3. **Hardware Isolation**: PC microphones and speakers automatically coordinate to prevent audio feedback or conflicting playback during remote turns.

---

## 🤝 Contributing

Contributions are welcomed! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for local development workflows and pull request guidelines.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).