# src/graph_extractor.py
# [DEV] Il Filtro della Realtà Locale (Local GraphRAG v1.0)
# Estrae solo i nodi rilevanti del mondo in base alla posizione del PG,
# abbattendo il consumo di token e prevenendo l'overflow.
# LEGGE A0099: Invarianza strutturale garantita.

import json
from typing import Dict, Any, List
from utils.translator import t


class LocalGraphExtractor:
    @staticmethod
    def get_local_hierarchy(
        world_map: Dict[str, Any], current_location: str
    ) -> List[str]:
        """
        Restituisce la location corrente, il suo 'padre' (se esiste) e tutti i 'fratelli'.
        Questo crea una 'bolla di percezione' logica attorno al PG.
        """
        if not world_map:
            return [current_location]

        parent_location = current_location

        # Cerca se la location attuale è contenuta in un'altra (ricerca del padre)
        for parent, data in world_map.items():
            if current_location in data.get("contiene", []):
                parent_location = parent
                break

        valid_locations = set([parent_location])

        # Aggiunge tutti i figli del padre (i fratelli della location attuale)
        if parent_location in world_map:
            valid_locations.update(world_map[parent_location].get("contiene", []))

        valid_locations.add(current_location)
        return list(valid_locations)

    @staticmethod
    def extract_local_reality(
        status_data: Dict[str, Any], world_map: Dict[str, Any], pg_location: str
    ) -> str:
        """
        Filtra status.json per mostrare all'LLM SOLO i personaggi e gli eventi
        che si trovano nella stessa 'bolla di percezione' del PG.
        """
        valid_locations = LocalGraphExtractor.get_local_hierarchy(
            world_map, pg_location
        )

        filtered_status = {
            "localizzazione_globale": status_data.get("localizzazione", {}),
            "tempo": status_data.get("tempo", {}),
            "condizioni_atmosferiche": status_data.get(
                "condizioni_atmosferiche", t("avatar_server.system.unknown")
            ),
            "percezione_ambientale": status_data.get("percezione_ambientale", {}),
            "metadati": status_data.get("metadati", {}),
            "personaggi_nella_tua_zona":[],
            "oggetti_rilevanti": status_data.get("oggetti_rilevanti",[]),
            "oggetti_interattivi": status_data.get("oggetti_interattivi",[]),
        }

        for char in status_data.get("personaggi", []):
            # Includiamo il personaggio se è nella bolla di percezione
            if char.get("luogo") in valid_locations:
                filtered_status["personaggi_nella_tua_zona"].append(char)

        # Restituiamo un JSON compatto (senza indentazione per risparmiare token)
        return json.dumps(filtered_status, ensure_ascii=False)

    @staticmethod
    def extract_universal_context(world_data: Dict[str, Any]) -> str:
        """
        Comprime world.json rimuovendo le mappe gerarchiche pesanti,
        mantenendo solo le leggi filosofiche e narrative del mondo.
        """
        filtered_world = {}
        for key, value in world_data.items():
            key_lower = key.lower()
            # Escludiamo i capitoli che contengono solo mappe o liste di stanze
            if (
                "mappa" not in key_lower
                and "gerarchica" not in key_lower
                and key_lower != "capitolo_v"
            ):
                filtered_world[key] = value

        # Minificazione estrema: niente indentazione, risparmia centinaia di token
        return json.dumps(filtered_world, ensure_ascii=False)
