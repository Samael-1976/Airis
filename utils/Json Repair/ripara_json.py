import json
from collections import OrderedDict

# --- LE CHIAVI MANCANTI ESTRATTE DAL TUO CODICE ---
MISSING_KEYS = {
    "welcome_wizard": {
        "lang_ar": "Arabo",
        "lang_br": "Portoghese (BR)",
        "lang_cn": "Cinese",
        "lang_de": "Tedesco",
        "lang_en": "Inglese",
        "lang_es": "Spagnolo",
        "lang_fr": "Francese",
        "lang_hi": "Hindi",
        "lang_it": "Italiano",
        "lang_jp": "Giapponese",
        "lang_kr": "Coreano",
        "lang_nl": "Olandese",
        "lang_pl": "Polacco",
        "lang_ru": "Russo"
    },
    "vibevoice": {
        "gender_woman": "Donna",
        "gender_man": "Uomo",
        "gender_other": "Altro",
        "alias_label": "🔗 {{name}} (Alias)",
        "err_service_not_ready": "Servizio non pronto",
        "err_input_required": "Testo di input richiesto",
        "err_input_too_long": "Il testo di input supera i 4096 caratteri",
        "err_unsupported_format_api": "Formato non supportato. Supportati: {{formats}}",
        "err_model_not_loaded": "Modello non caricato",
        "err_no_audio_generated": "Nessun output audio generato",
        "err_unsupported_format": "Formato non supportato: {{format}}",
        "err_audio_conversion": "Conversione audio fallita: {{error}}",
        "err_ffmpeg_not_found": "ffmpeg non trovato. Installare ffmpeg.",
        "startup_msg": "Avvio VibeVoice TTS Server su http://{{host}}:{{port}}",
        "endpoint_msg": "Endpoint OpenAI TTS: http://{{host}}:{{port}}/v1/audio/speech",
        "log": {
            "creating_voices_dir": "[system] Creazione cartella voci: {{dir}}",
            "loading_processor": "[startup] Caricamento processore da {{path}}",
            "loading_model": "[startup] Caricamento modello con dtype={{dtype}}, attn={{attn}}",
            "model_loading_issue": "[startup] Problema caricamento modello: {{error}}. Tento fallback sicuro...",
            "model_ready": "[startup] Modello pronto su {{device}}",
            "voices_dir_not_found": "[warning] Cartella voci non trovata: {{dir}}",
            "found_local_voices": "[startup] Trovati {{count}} file voce locali in {{dir}}",
            "failed_parse_metadata": "[error] Impossibile parsare metadati per {{id}}: {{error}}",
            "voice_not_found": "[warning] Voce '{{voice}}' non trovata, uso 'Carter'. Disponibili: {{available}}",
            "loading_voice_prompt": "[tts] Caricamento prompt voce da {{path}}",
            "generating_speech": "[tts] Generazione audio per {{chars}} caratteri con voce '{{voice}}'",
            "generated_audio": "[tts] Generati {{duration}}s di audio in {{elapsed}}s (RTF: {{rtf}}x)",
            "ffmpeg_failed": "[error] ffmpeg fallito: {{error}}",
            "model_loading_failed": "[FATAL] Caricamento modello fallito: {{error}}"
        }
    }
}

# Funzione per fondere in modo sicuro senza distruggere i tuoi dati
def safe_merge(d1, d2):
    for k, v in d2.items():
        if k in d1:
            if isinstance(d1[k], dict) and isinstance(v, dict):
                safe_merge(d1[k], v)
            elif isinstance(d1[k], list) and isinstance(v, list):
                d1[k].extend(v)
                # Rimuove duplicati nelle liste
                d1[k] = list(OrderedDict.fromkeys(d1[k]))
            else:
                # Se il valore manca, o è diverso, lo aggiorna in sicurezza
                d1[k] = v
        else:
            d1[k] = v
    return d1

# L'hook per leggere il tuo file json e mantenere tutto
def dict_hook(pairs):
    d = OrderedDict()
    for k, v in pairs:
        if k in d:
            if isinstance(d[k], dict) and isinstance(v, dict):
                safe_merge(d[k], v)
            else:
                d[k] = v
        else:
            d[k] = v
    return d

# Funzione per ordinare tutto alfabeticamente
def deep_sort(obj):
    if isinstance(obj, dict):
        return {k: deep_sort(v) for k, v in sorted(obj.items(), key=lambda item: item[0].lower())}
    elif isinstance(obj, list):
        return [deep_sort(item) for item in obj]
    else:
        return obj

print("🛠️  1. Leggo il tuo file it.json...")
try:
    with open('it.json', 'r', encoding='utf-8') as f:
        tuo_data = json.load(f, object_pairs_hook=dict_hook)

    print("💉  2. Inietto le chiavi mancanti (Welcome Wizard e VibeVoice)...")
    # Fonde le chiavi mancanti con il tuo file
    safe_merge(tuo_data, MISSING_KEYS)

    print("🔤  3. Ordino tutto alfabeticamente (dalla A alla Z, sottocartelle incluse)...")
    data_ordinata = deep_sort(tuo_data)

    print("💾  4. Salvo il file perfetto...")
    with open('it_sistemato.json', 'w', encoding='utf-8') as f:
        json.dump(data_ordinata, f, indent=2, ensure_ascii=False)

    print("✅ FINITO! Sostituisci il tuo it.json con 'it_sistemato.json'. Tutto funzionerà alla perfezione.")

except Exception as e:
    print(f"❌ ERRORE: {e}")