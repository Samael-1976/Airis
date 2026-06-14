import json

def deep_merge(d1, d2, current_path=""):
    for k, v in d2.items():
        path = f"{current_path}.{k}" if current_path else k
        
        if k in d1:
            if isinstance(d1[k], dict) and isinstance(v, dict):
                deep_merge(d1[k], v, path)
            elif isinstance(d1[k], list) and isinstance(v, list):
                d1[k].extend(v)
            # SCUDO: Se cerca di sovrascrivere un dizionario con un testo, bloccalo!
            elif isinstance(d1[k], dict) and not isinstance(v, dict):
                print(f"⚠️ PROTETTO [{path}]: Tentativo di sovrascrivere un blocco con un testo. Ignorato.")
            elif not isinstance(d1[k], dict) and isinstance(v, dict):
                d1[k] = v
            else:
                d1[k] = v
        else:
            d1[k] = v
    return d1

def merge_duplicates_hook(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            if isinstance(d[k], dict) and isinstance(v, dict):
                deep_merge(d[k], v, k)
            elif isinstance(d[k], dict) and not isinstance(v, dict):
                pass # Protegge il dizionario
            elif not isinstance(d[k], dict) and isinstance(v, dict):
                d[k] = v
            else:
                d[k] = v
        else:
            d[k] = v
    return d

def deep_sort(obj):
    if isinstance(obj, dict):
        return {k: deep_sort(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        return [deep_sort(item) for item in obj]
    else:
        return obj

print("1. Lettura e fusione sicura del file 'it.json'...")
try:
    with open('it.json', 'r', encoding='utf-8') as f:
        data = json.load(f, object_pairs_hook=merge_duplicates_hook)
    
    print("2. Riparazione strutturale (Riporto 'ui' dentro 'chat')...")
    # Se esiste un blocco "ui" alla radice, lo sposta dentro "chat"
    if "ui" in data and "chat" in data:
        if "ui" not in data["chat"]:
            data["chat"]["ui"] = {}
        deep_merge(data["chat"]["ui"], data["ui"], "chat.ui")
        del data["ui"]
        print(" -> Blocco 'ui' ripristinato con successo dentro 'chat'!")

    print("3. Ordinamento alfabetico profondo...")
    data_ordinata = deep_sort(data)

    print("4. Salvataggio in 'it_sistemato.json'...")
    with open('it_sistemato.json', 'w', encoding='utf-8') as f:
        json.dump(data_ordinata, f, indent=2, ensure_ascii=False)

    print("✅ Fatto! Il file ora è strutturalmente corretto, ordinato e senza perdite di dati.")
except Exception as e:
    print(f"❌ Errore critico: {e}")