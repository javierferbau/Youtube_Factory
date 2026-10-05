# 🎬 AI Affiliate Video Factory

> **Autonomous multi-channel media production engine orchestrating n8n, Local LLMs (Ollama), ComfyUI, Kokoro TTS, and GPU-accelerated FFmpeg for automated YouTube affiliate publishing.**

---

## 🚀 Overview

**AI Affiliate Video Factory** is a 24/7 automated pipeline that autonomously researches, scripts, voices, renders, and publishes high-CTR affiliate video content (Horizontal Long-Form + Vertical Shorts) across multiple niche channels on YouTube with Amazon Associates integration.

### Core Highlights
- 🧠 **Local LLM Intelligence**: Driven by Ollama (`qwen3.8:27b`) for copywriting, video scripts, objections analysis, and contextual comment replies.
- 🎙️ **Local TTS & Voice Cloning**: Zero-cost, high-speed neural speech synthesis using Kokoro ONNX and customized voice models.
- 🎨 **Dynamic Thumbnails & Backdrops**: ComfyUI local image generation (AMD ROCm / CUDA) combined with Pillow for dynamic text glowing badges, product cutouts, and high-CTR layouts.
- ⚡ **GPU-Accelerated FFmpeg Pipeline**: Hardware-accelerated video rendering (AMD VAAPI / NVENC) with automated Ken Burns camera zooms, animated reviewer frames, dynamic progress bars, and Whisper SRT subtitles.
- 🤖 **Automated YouTube Growth & Auto-Responder**: Automatic tag optimization, rich descriptions, thumbnail uploading, synthetic media compliance tagging, and AI comment response engine.
- 🛡️ **Self-Healing Watchdog**: Concurrency gating (strict single execution rule), SQLite health monitors, corrupted output auto-purge, and daily automated audits.

---

## 🗺️ Multi-Channel Network Architecture

The factory operates across specialized topical niches in Amazon Spain (`amazon.es`):

| Channel / Niche | Type | Target Content | Style & Focus |
| :--- | :---: | :--- | :--- |
| **Cocina Tecnológica** | TOP & VS | Air fryers, robot vacuum cleaners, kitchen tech | High-intent transactional reviews & comparisons |
| **Zapatería del Pueblo** | TOP & VS | Running sneakers, safety footwear, rain boots | Durability, comfort and price-performance ratio |
| **La Barbería del Pueblo**| TOP & VS | Shavers, clippers, beard grooming kits | Precision grooming and professional barber tools |
| **El Taller del Pueblo** | TOP & VS | Socket sets, impact wrenches, DIY power tools | Power tests, torque, and workshop efficiency |
| **Limpieza del Pueblo** | TOP & VS | Cordless vacuums, steam cleaners, pressure washers | Deep cleaning comparisons and home maintenance |
| **Librería del Pueblo** | TOP & VS | Non-fiction, personal development, bestsellers | Summary reviews, takeaways and book buying guides |

---

## 🏗️ System Architecture

```text
               ┌────────────────────────────────────────────────────────┐
               │              n8n Workflow Orchestrator                 │
               └───────────┬────────────────────────────────┬───────────┘
                           │                                │
            ┌──────────────▼─────────────┐    ┌─────────────▼──────────────┐
            │   Amazon Ranking Scraper   │    │     Local LLM (Ollama)     │
            │   (Price, ASIN, Reviews)   │    │  (Copywriting & Scripts)   │
            └──────────────┬─────────────┘    └─────────────┬──────────────┘
                           │                                │
                           └───────────────┬────────────────┘
                                           │
                           ┌───────────────▼────────────────┐
                           │    Voice Engine (Kokoro ONNX)  │
                           │    (Neural Speech + Subtitles) │
                           └───────────────┬────────────────┘
                                           │
                           ┌───────────────▼────────────────┐
                           │  ComfyUI + FFmpeg GPU Render   │
                           │  - Horizontal Full HD (16:9)   │
                           │  - Vertical Short (9:16)       │
                           │  - Dynamic Glowing Badges      │
                           └───────────────┬────────────────┘
                                           │
                           ┌───────────────▼────────────────┐
                           │    YouTube Data API v3 Upload  │
                           │    + AI Auto-Responder Engine  │
                           └────────────────────────────────┘
```

---

## 📂 Repository Structure

```text
Youtube_Factory/
├── workflows/                     # Sanitized production n8n workflows
│   ├── 01_workflow_amazon_top_ranking.json
│   ├── 02_workflow_amazon_vs_comparison.json
│   ├── 03_workflow_youtube_metrics_monitor.json
│   └── 04_workflow_youtube_auto_responder.json
├── tools/                         # Modular Python production engine
│   ├── reviewer_frame_engine.py   # FFmpeg motion filter & layout builder
│   ├── render_vs_video.py         # Horizontal VS comparison renderer
│   ├── render_vertical_short.py   # Vertical 9:16 Short video renderer
│   ├── render_taller_video.py     # Channel-specific video render pipelines
│   ├── thumbnail_engine.py        # High-CTR thumbnail generator (Pillow + Neon)
│   ├── comfyui_backdrop_generator.py # Local ComfyUI API bridge
│   ├── kokoro_tts.py              # Neural speech synthesis
│   ├── youtube_auto_responder.py  # AI automated comment replies with Ollama
│   ├── daily_affiliate_audit.py   # 24h performance & health audit
│   ├── fetch_youtube_metrics.py   # Search vs Suggested traffic analytics
│   ├── system_watchdog.py         # RAM/CPU watchdog & process monitor
│   ├── n8n_helper.py              # n8n REST API manager
│   ├── webhook_tester.py          # Watch-mode execution runner
│   └── test_metadata_scripts.py   # Multi-niche cross-regression test suite
├── assets/                        # Fonts, audio SFX, background music
│   ├── fonts/                     # High-impact typography
│   ├── music/                     # Royalty-free audio tracks
│   └── sfx/                       # Sound effects & transitions
├── systemd/                       # Linux automation timers
│   ├── affiliate-daily-audit.service
│   └── affiliate-daily-audit.timer
├── AGENTS.md                      # AI Orchestration and Agent Directives
├── .env.example                   # Environment configuration template
└── requirements.txt               # Python package dependencies
```

---

## 🛠️ Quickstart & Deployment

### 1. Prerequisites
- **Linux (Arch / Ubuntu / Debian)** with Bash
- **Docker & Docker Compose** (for n8n)
- **Python 3.10+**
- **FFmpeg 6+** compiled with hardware acceleration (`vaapi` or `nvenc`)
- **Ollama** running locally (`ollama run qwen3.8:27b`)
- **ComfyUI** running locally on port `8188` (Optional, for AI backdrop generation)

### 2. Installation
```bash
# Clone the repository
git clone git@github.com:javierferbau/Youtube_Factory.git
cd Youtube_Factory

# Install Python requirements
python3 -m pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
nano .env
```

### 3. Deploy Linux Systemd Timers (Automated Daily Audits)
```bash
mkdir -p ~/.config/systemd/user/
cp systemd/* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now affiliate-daily-audit.timer
```

### 4. Running Regression Tests
Before launching production workflows, verify all 6 channel niches locally:
```bash
python3 tools/test_metadata_scripts.py
```

---

## 🛡️ License

Private / Proprietary. Developed for automated multi-channel affiliate media operations.
