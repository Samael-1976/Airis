### Architecture Beyond Static Wrappers

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
| :--- | :---: | :---: | :---: | :--- |
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
1. Download the file from: 
2. extract the file
3. cd Airis

# 2. Awaken the Soul
# On Windows:
run.bat

# On Linux / macOS:
chmod +x run.sh && ./run.sh
```

### What occurs in the background during boot:

1. **State Loading (`status.json`):** The system initializes the world state in RAM. To avoid disk write (I/O) collisions from asynchronous threads, the file is read only once and maintained in volatile memory. The *Scribe Thread* is responsible for flushing changes to disk every 10 seconds in a thread-safe manner.
2. **WebSocket Handshake & Hybrid History:** Upon launching the React interface, a secure WebSocket channel is established. To prevent packet loss (race conditions) on mobile or Ngrok connections, message history is downloaded asynchronously via a parallel HTTP GET call, leaving the WebSocket free for real-time control signals.