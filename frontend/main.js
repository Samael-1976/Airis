// Cuore del Corpo Digitale di Gemma v9.1 - La Sincronia Perfetta

const videoElement = document.getElementById('avatar-video');
const audioElement = document.getElementById('avatar-audio-player');
const startOverlay = document.getElementById('start-overlay');
const startButton = document.getElementById('start-button');

const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;

let intentMap = {};
let idleStates = [];
let currentIntent = null;
let isPlayingAction = false; // Flag per tracciare se stiamo eseguendo un'azione
let idleTimeout = null;
let translations = {}; // [NUOVO] Cache traduzioni

// [NUOVO] Funzione helper per traduzioni semplici
function t(key, params = {}) {
    const keys = key.split('.');
    let value = translations;
    for (const k of keys) {
        if (value && typeof value === 'object' && k in value) value = value[k];
        else return `[${key}]`;
    }
    if (typeof value !== 'string') return `[${key}]`;
    for (const [k, v] of Object.entries(params)) {
        value = value.replace(new RegExp(`\\{\\{\\s*${k}\\s*\\}\\}`, 'g'), v);
    }
    return value;
}

async function fetchTranslations() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/translations/frontend?lang=it`);
        translations = await response.json();
        startButton.innerText = t("index.start_button");
        document.title = t("index.title");
    } catch (e) { console.error("Corpo: Errore caricamento traduzioni", e); }
}

async function fetchIntentMap() {
    try {
        console.log(t("main_js.requesting_map"));
        const response = await fetch(`${API_BASE_URL}/get_intent_map`);
        if (!response.ok) throw new Error(`Errore dal server: ${response.statusText}`);
        const data = await response.json();
        intentMap = data.intent_map;
        idleStates = data.idle_states;
        console.log(t("main_js.map_received", { count: Object.keys(intentMap).length }));
        playInitialGreeting();
    } catch (error) {
        console.error("Corpo: ERRORE CRITICO - Impossibile recuperare la mappa.", error);
        setTimeout(fetchIntentMap, 5000);
    }
}

function playVideo(intent, shouldLoop = false) {
    if (!intent || !intentMap[intent]) {
        console.warn(t("main_js.intent_not_found", { intent: intent }));
        return;
    }
    
    console.log(t("main_js.executing_intent", { intent: intent, loop: shouldLoop ? t("main_js.loop") : "" }));
    currentIntent = intent;

    const videoUrl = `${API_BASE_URL}/${intentMap[intent]}`;
    
    const onVideoReady = () => {
        videoElement.play().catch(e => {
            if (e.name !== 'AbortError') {
                console.error(t("main_js.error_video", { intent: intent }), e);
            }
        });
        videoElement.removeEventListener('canplay', onVideoReady);
    };

    videoElement.addEventListener('canplay', onVideoReady);
    videoElement.loop = shouldLoop;
    videoElement.muted = true;
    videoElement.src = videoUrl;
    videoElement.load();
}

function playRandomIdle() {
    if (isPlayingAction) {
        console.log(t("main_js.action_in_progress"));
        return;
    }
    
    if (idleStates.length === 0) {
        playVideo('state_idle', true);
        return;
    }
    const nextIdle = idleStates[Math.floor(Math.random() * idleStates.length)];
    playVideo(nextIdle, true);
}

function scheduleNextIdle() {
    if (idleTimeout) {
        clearTimeout(idleTimeout);
        idleTimeout = null;
    }
    
    const delay = 5000 + Math.random() * 3000;
    idleTimeout = setTimeout(() => {
        if (!isPlayingAction) {
            playRandomIdle();
        }
    }, delay);
}

function playInitialGreeting() {
    isPlayingAction = true;
    playVideo('state_hello', false);
    
    videoElement.addEventListener('ended', function onGreetingEnd() {
        videoElement.removeEventListener('ended', onGreetingEnd);
        isPlayingAction = false;
        playRandomIdle();
        scheduleNextIdle();
    }, { once: true });
}

function connectWebSocket() {
    const wsUrl = `ws://${window.location.hostname}:${window.location.port}/ws`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => console.log(t("main_js.ws_connected"));
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type !== 'action' || !data.intent) return;

            const { intent, audio_url } = data;
            
            if (idleTimeout) {
                clearTimeout(idleTimeout);
                idleTimeout = null;
            }
            
            if (intent === 'state_speaking2' && audio_url) {
                isPlayingAction = true;
                playVideo(intent, true);
                
                audioElement.onended = () => {
                    console.log(t("main_js.audio_finished"));
                    isPlayingAction = false;
                };
                
                audioElement.src = `${API_BASE_URL}${audio_url}`;
                audioElement.play().catch(e => { 
                    console.error(t("main_js.audio_error"), e);
                    isPlayingAction = false;
                    playRandomIdle();
                    scheduleNextIdle();
                });
            } 
            else {
                if (!audioElement.paused) audioElement.pause();
                isPlayingAction = true;
                
                const loop_prefixes = [
                    'state_idle', 'state_blinking', 'state_looking_down',
                    'state_speaking', 'state_generating_thinking', 'state_listening_intently'
                ];
                
                const shouldLoop = loop_prefixes.some(prefix => intent.startsWith(prefix));
                
                playVideo(intent, shouldLoop);
                
                if (!shouldLoop) {
                    videoElement.addEventListener('ended', function onActionEnd() {
                        videoElement.removeEventListener('ended', onActionEnd);
                        console.log(t("main_js.action_completed", { intent: intent }));
                        isPlayingAction = false;
                        playRandomIdle();
                        scheduleNextIdle();
                    }, { once: true });
                } else {
                    console.log(t("main_js.intent_looping", { intent: intent }));
                }
            }
        } catch (error) {
            console.error("Corpo: Errore processamento messaggio WebSocket.", error);
        }
    };

    ws.onclose = () => { 
        console.warn(t("main_js.ws_disconnected")); 
        setTimeout(connectWebSocket, 3000); 
    };
    
    ws.onerror = (error) => { 
        console.error(t("main_js.ws_error"), error); 
        ws.close(); 
    };
}

videoElement.addEventListener('ended', () => {
    if (!isPlayingAction) {
        console.log(t("main_js.idle_finished"));
        playRandomIdle();
        scheduleNextIdle();
    }
});

document.addEventListener('DOMContentLoaded', async () => {
    await fetchTranslations(); // [NUOVO] Carica traduzioni prima di tutto
    startButton.addEventListener('click', () => {
        console.log(t("main_js.user_interaction"));
        videoElement.muted = true;
        startOverlay.style.opacity = '0';
        setTimeout(() => startOverlay.style.display = 'none', 500);
        fetchIntentMap();
        connectWebSocket();
    }, { once: true });
});