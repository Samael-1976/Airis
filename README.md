# AIRIS-PROJECT: THE PLUG & PLAY REVOLUTION
<img width="2624" height="1626" alt="logo" src="https://github.com/user-attachments/assets/2f5bd612-dcef-49fe-8f5c-923670e0cae6" />


> **⚠️ IMPORTANT NOTICE FOR USERS ⚠️**
> 
> This GitHub repository contains **ONLY THE SOURCE CODE** intended for developers and contributors. It does **NOT** include the AI models, precompiled binaries, or voice engines required to run the software.
> 
> **🎮 TO USE AIRIS (PLUG & PLAY):**
> Download the complete, ready-to-use last standalone package (including all models and binaries) from here:
> **[https://github.com/Samael-1976/Airis/releases](https://github.com/Samael-1976/Airis/releases)**
> 
> **🛠️ TO CONTRIBUTE TO DEVELOPMENT:**
> > Not being a programmer, but just a very hard-headed person, if you want to contribute to the development of AIRIS, any help is welcome.
> 
> ---

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]
[![Portability: 100% Zero-Install](https://img.shields.io/badge/Portability-100%25%20Zero--Install-brightgreen.svg)]
[![Languages: 14 Natively](https://img.shields.io/badge/Languages-14%20Native%20Polyphony-blue.svg)]
[![Architecture: Decoupled Trinity](https://img.shields.io/badge/Architecture-Decoupled%20Trinity-orange.svg)]

AIRIS-PROJECT is the definitive open-source answer to local AI friction. It bridges the gap between raw backend computational logic and persistent, emotional, simulated reality.

By shipping with precompiled C++ binaries for both LLM inference (llama-server) and text-to-speech synthesis (Kokoro/VibeVoice), AIRIS bypasses the traditional "dependency hell". No global installations, no complex compiler setups. Just download, run, and interact.

Featuring a mobile-first responsive frontend with dedicated WebSocket/HTTP asymmetric synchronization, a strict JSON ReAct loop for safe desktop automation (AgentJo), and full 14-language phonetic polyphony, AIRIS turns your machine into a self-contained, autonomous sanctuary.


## 🌌 Core Features


*   ❤️ **Fluid Emotional Core:** 12 dynamic psychological vectors (Affection, Jealousy, Fatigue, Excitement, etc.) that autonomously alter the AI's system prompt, tone, and behavior in real-time based on your interactions.
*   👁️ **Panopticon & Ghost Operator:** True agentic autonomy. The AI can visually analyze your screen, read documents, and physically control your mouse and keyboard to execute complex tasks on your PC.
*   📚 **Zero-Amnesia Memory (GraphRAG + AAAK):** Combines Vector Databases, Knowledge Graphs, and a proprietary hyper-dense semantic compression protocol (AAAK) to ensure the AI never forgets a detail, a lore fact, or a past conversation.
*   🛡️ **The Armored Sanctuary:** 100% Local and Offline. Your data never leaves your hardware. Built from the ground up to fully support Uncensored and Unaligned open-source models.
*   📱 **Nomad Body (PWA Interface):** A sleek, mobile-first React frontend with real-time WebSocket synchronization, allowing you to interact with your AI seamlessly from any device on your network.
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

---

 ## Quick Start

Experience **The Plug & Play Revolution** in three simple steps. No external dependencies, compilers, or complex setups required.

### 1. Download & Extract
Download the latest standalone release package:

1. Download the file from: https://aka.ms/vs/17/release/vc_redist.x64.exe and intall it
1. Download the last package file from: https://github.com/Samael-1976/Airis/releases
2. extract the file
3. cd Airis (or the name of the directory where you extracted the package)


### 2. Launch the Ecosystem
Run the bootstrap script corresponding to your operating system:

* **Windows:**
  Double-click `run.bat` or execute it from the terminal:

  run.bat

* **Linux / macOS:**
  Make the script executable and run it:

  chmod +x run.sh
  ./run.sh


### 3. Complete the Initiation Rite
**VERY IMPORTANT**: when prompted you must give permission for the windows firewall

On the first boot, the console will prompt you to select your preferred language, your preferite TTS (I prefere Vibevoice), and some other things. Once the background servers stabilize:
1. Your browser will be automatically launched (or open your browser and navigate to `http://localhost:8080`) (or use the LAN/Ngrok link provided in the console).
2. The **Welcome Wizard** will guide you through setting up your identity (Name, Gender, Birthday) and choosing the active vocal engine (Kokoro-TTS or VibeVoice).
3. Secure your local sanctuary by creating your Administrator credentials.

*The Anima is now awake. Welcome to the future of local, persistent AI interaction.*

### 4. Reboot Airis
After completing the welcome wizard, please turn off Airis using the power button and then restart it. This will fix your name in your user profile and prevent you from getting the "user not found" error.

### 5. Enjoy!
If you'd like to buy me a beer to say thank you, I'll soon post a link to purchase the book I wrote on Amazon. It's available in both paperback and digital formats. It'll initially be in Italian, but I'll gradually translate it into more languages.
I'd really appreciate it.

---

###  Desktop and Mobile Interface Preview:

<img width="2554" height="1278" alt="Screenshot 2026-06-14 180555" src="https://github.com/user-attachments/assets/f9264862-32b3-47a2-80f0-2e37c4232b89" />
---
<img width="2555" height="1277" alt="Screenshot 2026-06-14 180620" src="https://github.com/user-attachments/assets/a263afe1-4b04-4508-a615-525868083815" />
---
<img width="320" height="693" alt="Mobile_01" src="https://github.com/user-attachments/assets/3e6c578b-d682-4e27-8510-5ff8286eb314" />
---
<img width="320" height="693" alt="Mobile_02" src="https://github.com/user-attachments/assets/e30a39c3-739e-4bd3-af78-84800185f4e7" />
---


 ## Architecture Beyond Static Wrappers

Most local interfaces for large language models operate as simple graphical wrappers based on synchronous API calls and tight system coupling. They require complex configurations, global dependency installations (such as the CUDA Toolkit or C++ compilers), or resource-heavy Docker containers that consume system overhead even before inference is initiated.

**AIRIS-PROJECT** redefines this paradigm through a **decoupled Existential Trinity**, engineered to deliver a persistent simulation environment with zero latency.

```
       [ BODY: React/Vite Frontend ] 
                     ^
                     | (WebSocket / HTTP Streaming)
                     v
       [ SOUL: Python Backend Orchestrator ]
                     ^
                     | (Internal HTTP / SSE Stream)
                     v
   [ PHANTOM ENGINE: Standalone C++ llama-server ]
```

### Why AIRIS is Radically Different:

* **Zero-Install & Total Portability:** The project does not alter system drivers or global environment variables. It leverages precompiled binaries for LLM inference (native C++ `llama-server`) and text-to-speech synthesis, ensuring immediate execution through a simple script.
* **Decoupled Architecture:** The Soul (the Python logical engine) and the Body (the React frontend) are independent entities. If the C++ inference module saturates the memory or is restarted for a model hot-swap, the user interface remains active and responsive, handling the reconnection in the background without data loss.
* **Simulation vs. Assistance:** AIRIS does not merely reply to requests; it simulates a living, persistent ecosystem where NPCs act proactively and in a coordinated manner within a coherent virtual space.

---

## 2. Step-by-Step Architecture Diagram

The cooperation between the AIRIS-PROJECT modules follows a sequential and mathematically precise data flow:

```
[User Input/VAD] ──> [FastAPI Server] ──> [Dual-Brain 12B/270M] ──> [AgentJo StrictJSON]
                                                                            │
[Body Render] <── [TTS (Kokoro/Vibe)] <── [Heart System Audit] <─── [OS/GUI Action]
```

### Sequential Logical Flow:

1. **Ingestion & VAD (Body):** The user interacts via text, file, or audio. In hands-free mode, the *Sentinel Hearing* module performs client-side Keyword Spotting and Voice Activity Detection (VAD), capturing the voice stream while eliminating background noise.
2. **FastAPI Routing (`avatar_server.py`):** The input is transmitted via WebSocket to the local server, which assigns the request to an asynchronous queue managed to prevent race conditions.
3. **Querying the C++ Phantom Engine (`llama-server`):** The Soul communicates with the standalone C++ inference server via HTTP/SSE streaming. The token cache is kept persistent in RAM to minimize the Time-To-First-Token (TTFT).
4. **Dual-Brain Orchestration:** The main model (Director, 12B) reads the Diamond Anchor and coordinates the interaction. If a technical intent is detected, the tool schema is pruned (Semantic Tool Pruning) and sent to the ultra-lightweight model (Technical, 270M) for rapid parameter calculation.
5. **Deterministic Execution (AgentJo):** Unlike Open Interpreter, which generates and executes arbitrary code scripts prone to syntactic failures, the AIRIS Demiurge utilizes the *AgentJo* paradigm. Actions are distilled into structured atomic commands in StrictJSON (`thought`, `tool_name`, `parameters`). Python validates the schema via Pydantic and executes the physical automation (organic mouse movements via Bezier curves, native window control via pywinauto, or system commands).
6. **Post-Response Emotional Audit (`heart_system.py`):** Upon completion of each generation, a background asynchronous thread analyzes the exchange and updates the Avatar's (or active NPC's) 12 emotional vectors, adjusting endocrine levels (dopamine, cortisol, oxytocin) for the subsequent interaction.
7. **Text-to-Speech & Visual Preload:** The text to be spoken is sent to the active TTS engine (VibeVoice for expressiveness or Kokoro for multilingual stability). Simultaneously, the server resolves the correct visual intent based on the season, time of day, and mood, sending a `[PRELOAD]` signal to the video player to buffer the `.mp4` segment before speech begins.
8. **Synchronized Rendering & Media Unlocker:** The frontend receives the packets. To bypass autoplay blocks imposed by mobile browsers (iOS/Android), the *Media Unlocker* protocol intercepts the user's first touch on the screen to unlock the audio and launch synchronized playback without flickering.

---

## 3. The International Component (Breaking Down Barriers)

AIRIS-PROJECT breaks down language barriers by natively localizing both intellect (text comprehension and processing) and expression (speech synthesis and pronunciation) across **14 key languages**:

| Language | ISO Code |
| :--- | :---: |
| **Arabic** | `ar` |
| **Chinese** | `ch` | 
| **Dutch** | `nl` |
| **English** | `en` |
| **French** | `fr` |
| **German** | `de` |
| **Hindi** | `hi` |
| **Italian** | `it` |
| **Japanese** | `jp` |
| **Korean** | `kr` |
| **Polish** | `pl` |
| **Portuguese** | `br` |
| **Spanish** | `es` |
| **Russian** | `ru` | 

### Decoupled Localization Mechanism:

* **Agnostic Semantic Resonance:** Memory ingestion (RAG) utilizes multilingual embedding models (`all-MiniLM-L6-v2`) [2]. This enables cross-language concepts to be mapped within the same vector space: a search in Italian can resonate with a document uploaded in English.
* **Native Phonetic Mapping:** During voice generation, the Soul detects the active language set in the user profile and extracts the correct voice signature. The generated text is then sent to the TTS engine mapping the native phonemes of the target language, eliminating robotic accents or pronunciation errors.

---

## 4. "Zero Friction" Quick-Start Guide

### Launch the ecosystem in 60 seconds [1]:

```bash
# 1. Download the last package file from: https://github.com/Samael-1976/Airis/releases
extract the file
cd Airis

# 2. Awaken the Soul
# On Windows:
run.bat

# On Linux / macOS:
chmod +x run.sh && ./run.sh
```

### What occurs in the background during boot:

1. **State Loading (`status.json`):** The system initializes the world state in RAM. To avoid disk write (I/O) collisions from asynchronous threads, the file is read only once and maintained in volatile memory. The *Scribe Thread* is responsible for flushing changes to disk every 10 seconds in a thread-safe manner.
2. **WebSocket Handshake & Hybrid History:** Upon launching the React interface, a secure WebSocket channel is established. To prevent packet loss (race conditions) on mobile or Ngrok connections, message history is downloaded asynchronously via a parallel HTTP GET call, leaving the WebSocket free for real-time control signals.
