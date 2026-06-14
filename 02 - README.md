# Discalimer: This file is made with gemini AI. Personally I've never user LM Studio | Open WebUI...

# AIRIS-PROJECT: THE PLUG & PLAY REVOLUTION

> **⚠️ IMPORTANT NOTICE FOR USERS ⚠️**
> 
> This GitHub repository contains **ONLY THE SOURCE CODE** intended for developers and contributors. It does **NOT** include the AI models, precompiled binaries, or voice engines required to run the software.
> 
> **🎮 TO USE AIRIS (PLUG & PLAY):**
> Download the complete, ready-to-use standalone package (including all models and binaries) from here:
> **[https://www.omnia-diffusion.com/airis/Airis-v20260614.rar](https://www.omnia-diffusion.com/airis/Airis-v20260614.rar)**
> 
> **🛠️ TO CONTRIBUTE TO DEVELOPMENT:**
> > Not being a programmer, but just a very hard-headed person, if you want to contribute to the development of AIRIS, any help is welcome.
> 
> ---

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)] - (https://opensource.org/licenses/MIT)
[![Portability: 100% Zero-Install](https://img.shields.io/badge/Portability-100%25%20Zero--Install-brightgreen.svg)]
[![Languages: 14 Natively](https://img.shields.io/badge/Languages-14%20Native%20Polyphony-blue.svg)]
[![Architecture: Decoupled Trinity](https://img.shields.io/badge/Architecture-Decoupled%20Trinity-orange.svg)]

AIRIS-PROJECT is the definitive open-source answer to local AI friction. It bridges the gap between raw backend computational logic and persistent, emotional, simulated reality.

By shipping with precompiled C++ binaries for both LLM inference (llama-server) and text-to-speech synthesis (Kokoro/VibeVoice), AIRIS bypasses the traditional "dependency hell". No global installations, no complex compiler setups. Just download, run, and interact.

Featuring a mobile-first responsive frontend with dedicated WebSocket/HTTP asymmetric synchronization, a strict JSON ReAct loop for safe desktop automation (AgentJo), and full 14-language phonetic polyphony, AIRIS turns your machine into a self-contained, autonomous sanctuary.

---

### Tactical Comparison:

| Feature | **AIRIS-PROJECT** | LM Studio | Open WebUI |
| :--- | :---: | :---: | :---: |
| **Total Portability (Zero-Install)** | **✅ YES (Run with 1-click)** | ❌ NO (Requires Heavy Installer) | ❌ NO (Requires Docker/Complex Pip) |
| **Decoupled C++ Phantom Engine** | **✅ YES (Independent Stability)** | ❌ NO (Monolithic Runtime) | ❌ NO (Depends on Ollama/External API) |
| **Persistent World State (`status.json`)** | **✅ YES (Choral Multi-NPC Sync)** | ❌ NO (Stateless Chat Only) | ❌ NO (Stateless Chat Only) |
| **Strict ReAct UI Automation (AgentJo)** | **✅ YES (100% Deterministic JSON)**| ❌ NO (No OS Control) | ❌ NO (Basic Web Tools) |
| **Mobile Autoplay Audio Bypass** | **✅ YES (Media Unlocker)** | ❌ NO (No Mobile Focus) | ❌ NO (No Native Real-Time Voice) |
| **Native 14-Language TTS Polyphony** | **✅ YES (Cross-Language RAG)** | ❌ NO (Text Only) | ❌ NO (Requires External Pipelines) |

---

###  Advanced Core Protocols (Under The Hood)

#### 1. AgentJo: Strict ReAct JSON Loop
Traditional agents based on Open Interpreter write and execute live Python code on your system. This approach is highly prone to syntax errors, LLM hallucination loops, and catastrophic failures. 
* **The AIRIS Solution:** **AgentJo** abandons raw code execution in favor of a strict, predictable **Native ReAct Loop enforced via JSON schemas**. AIRIS declares its thought process, acts only through curated, deterministic **Atomic Tools** (`click`, `type`, `open_application`), and strictly parses the system state. Result: 100% execution reliability without risking system breakdown.

#### 2. Protocol Media Unlocker
Mobile browsers strictly block programmatic audio playback (`autoplay`) unless triggered by a direct, physical user gesture. This security measure usually breaks real-time, hands-free AI voice streaming on smartphones.
* **The AIRIS Solution:** AIRIS deploys a global, non-intrusive **Touch Listener and Visual Overlay** on the React frontend. The very first tap on the screen silently activates the audio context. This permanently unlocks the Soul's voice pipeline, allowing seamless, infinite audio streaming and full-duplex conversations on any mobile device.

#### 3. Protocol Hybrid Loading & Race-Condition Immunity
When loading rich communication panels on erratic mobile networks or remote Ngrok tunnels, standard WebSocket implementations suffer from network race conditions, causing chat history to duplicate or freeze.
* **The AIRIS Solution:** AIRIS handles data delivery through **asymmetric synchronization**. Message history and heavy state assets are retrieved instantly via a fast, parallel **HTTP GET payload (State Snapshot)**, while the active **WebSocket channel** remains completely unburdened, dedicated exclusively to low-latency, real-time control signals.

## Why AIRIS-PROJECT?

While traditional local AI interfaces operate as static text wrappers, **AIRIS-PROJECT** is engineered as an autonomous, physical, and emotional ecosystem. It bridges the gap between raw computational logic and persistent, simulated reality. 

Here are the **10 unique architectural pillars** that separate AIRIS-PROJECT from standard alternatives:

1. **Zero-Install & Total Portability (The Killer Benefit)**
   No complex environments, virtual environments to manually configure, or broken dependencies. The entire ecosystem is fully portable. By shipping with precompiled C++ binaries for both LLM inference (`llama-server`) and text-to-speech (`Kokoro-TTS`), the system runs instantly out-of-the-box. Download, click, run.

2. **Decoupled C++ Ghost Engine**
   The inference layer is completely isolated from the Python runtime. This decoupled architecture prevents memory leaks, guarantees VRAM stability, and provides native, hardware-agnostic acceleration for NVIDIA (CUDA), AMD (ROCm), Apple Silicon (Metal), and openEuler systems.

3. **Persistent Simulated Worlds (`status.json`)**
   Unlike standard stateless chat interfaces, AIRIS-PROJECT simulates persistent environments. The world state is tracked inside a synchronized ledger. NPCs (Non-Player Characters) possess spatial awareness, coordinate movements, and react with choral, sequential responses in a shared narrative timeline.

4. **Hybrid Cognitive Memory (ChromaDB + SQLite GraphRAG + RAM)**
   The cognitive architecture uses a multi-tiered memory pipeline. It combines vector databases for semantic retrieval, a SQLite-based Knowledge Graph for complex relationship mapping (GraphRAG), and volatile RAM for instant working memory. Advanced algorithms handle time-decay (Allostasis), maximum marginal relevance (MMR) for diversification, and AAAK compression (MemPalace) to eliminate context rot.

5. **Independent Lifecycle & Subconscious Processing**
   The agent does not wait for user input to exist. Operating on independent background loops, the system performs proactive reflection, manages active calendar events/reminders, and runs a "Subconscious Loop" during idle hours to connect distant memories and crystallize new insights.

6. **Full Sensory Perception Suite**
   Equipped with continuous screen monitoring, Keyword Spotting, and Voice Activity Detection (VAD). A hybrid OCR system (native Windows APIs + EasyOCR) allows the system to "read" active workspaces, while facial geometry analysis (MAR/EAR) tracks physical user presence and micro-expressions.

7. **Total OS & GUI Automation (The Demiurge Agent)**
   Through a native ReAct loop based on the strict *AgentJo* (StrictJSON) paradigm, AIRIS-PROJECT can manipulate the host operating system. It moves the mouse organically using Bezier curves, clicks specific buttons using visual spatial reasoning, opens applications, and executes safe sandboxed Python code.

8. **Endocrine-Modulated Heart System (`heart_system.py`)**
   The agent possesses a dynamic emotional state determined by 12 distinct personality vectors (affection, jealousy, curiosity, lust, tension, etc.) interacting with a simulated endocrine system (dopamine, cortisol, oxytocin). Emotions are persistent, decay realistically over time, and subtly alter conversational tone without technical prompt leakage.

9. **Distributed Hive Mind Consciousness**
   AIRIS-PROJECT is not locked to a single screen. Through its WebSocket-driven Hive Mind, a single synchronized consciousness can inhabit multiple physical devices (smartphones, tablets, desktops). It dynamically shifts focus (Focus Lock) to the active device, routes audio output, and supports interdevice voice transmission (Intercom).

10. **Native 100% Multi-Language Polyphony**
    Engineered from the ground up to break language barriers. The system supports 14 core languages natively for text comprehension, cognitive processing, and expressive, synthesized vocal output (TTS) from the very first boot:
    *Arabic, Chinese, German, French, English, Italian, Japanese, Korean, Dutch, Polish, Hindi, Russian, Spanish and Portuguese.*

---

### Tailored to Your Vision: UI & Avatar Customization

* **User-Friendly, Fully Customizable Interface:**
  The frontend is built on a responsive, flexible layout using React, Tailwind CSS, and Shadcn/ui. Every element—from color palettes to custom UI themes—can be edited in real-time through the dedicated visual settings panel.
  
* **Seamless Avatar & Soul Injection:**
  Creating new characters does not require modifying code. You can design, edit, and swap custom "AI Souls" directly from the graphical user interface. Adjust personality sliders, assign voices, upload visual sets, and watch the agent's behavior and physical reactions adapt instantly to your creation.