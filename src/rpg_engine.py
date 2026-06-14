# src/rpg_engine.py
# [DEV] Il Motore della Singolarità (v1.0 - RPG Core)
# Gestisce la matematica, i dadi, gli HP e la risoluzione dei conflitti.
# Corregge le allucinazioni dell'LLM al volo e sincronizza l'HUD del frontend.
# LEGGE A0099: Invarianza strutturale garantita.

import json
import random
import re
import difflib
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from utils.translator import t


class RpgEngine:
    def __init__(
        self, active_rpg_path: Path, lang: str, avatar_bridge, logger, pg_name: str,
        get_world_state_cb=None, set_world_state_cb=None
    ):
        self.rpg_path = active_rpg_path
        self.lang = lang
        self.bridge = avatar_bridge
        self.logger = logger
        self.pg_name = (
            pg_name  #[FIX AGNOSTICISMO] Il motore ora conosce il suo Creatore
        )
        self.get_world_state_cb = get_world_state_cb
        self.set_world_state_cb = set_world_state_cb

        # Risoluzione percorsi
        norm_lang = lang.lower()
        lang_path = self.rpg_path / norm_lang
        self.effective_root = lang_path if lang_path.is_dir() else self.rpg_path

        self.status_file = self.effective_root / "WORLD" / "status.json"
        self.encounters_file = self.effective_root / "WORLD" / "encounters.json"

        # Inizializza encounters.json se non esiste
        if not self.encounters_file.exists():
            self._clear_encounters()

        # Mappa delle abilità alle statistiche core (Adattabilità)
        self.skill_to_stat_map = {
            "atletica": "destrezza",
            "acrobazia": "destrezza",
            "furtività": "destrezza",
            "rapidità di mano": "destrezza",
            "arcano": "intelligenza",
            "storia": "intelligenza",
            "indagare": "intelligenza",
            "natura": "intelligenza",
            "religione": "intelligenza",
            "addestrare animali": "saggezza",
            "intuizione": "saggezza",
            "medicina": "saggezza",
            "percezione": "saggezza",
            "sopravvivenza": "saggezza",
            "inganno": "carisma",
            "intimidire": "carisma",
            "intrattenere": "carisma",
            "persuasione": "carisma",
            "forza": "forza",
            "destrezza": "destrezza",
            "costituzione": "costituzione",
            "intelligenza": "intelligenza",
            "saggezza": "saggezza",
            "carisma": "carisma",
        }

    def _auto_heal_json(self, path: Path) -> Dict:
        """
        [PROTOCOLLO FENICE] Ricostruisce un file JSON corrotto partendo da uno scheletro valido.
        """
        self.logger.warning(t("avatar_server.gdr.engine.auto_heal_start", file=path.name))
        
        # 1. Backup del file corrotto (se esiste)
        if path.exists():
            try:
                backup_path = path.with_suffix(".corrupted.bak")
                import shutil
                shutil.copy2(path, backup_path)
            except:
                pass

        # 2. Generazione Scheletro in base al tipo di file
        default_data = {}
        name_lower = path.name.lower()
        
        if name_lower == "status.json":
            default_data = {
                "localizzazione": {"luogo_fisico_attuale": t("avatar_server.gdr.engine.rpg_start_point")},
                "personaggi":[{"nome": self.pg_name, "luogo": t("avatar_server.gdr.engine.rpg_start_point"), "abbigliamento": "Standard", "stato": "Pronto"}],
                "oggetti_rilevanti":[],
                "tempo": {"nella_bolla": "Morning"},
                "metadati": {"evento_corrente": "Nessun evento attivo", "game_state": {}}
            }
        elif name_lower == "encounters.json":
            default_data = {"nemici_attivi":[], "npc_casuali": []}
        elif path.parent.name.upper() in ["PG", "PNG"]:
            default_data = {
                "dati_anagrafici": {"nome": path.stem},
                "scheda_rpg": {"dati_base": {"livello": 1}, "combattimento": {"hp_massimi": 10, "hp_attuali": 10}}
            }
            
        # 3. Scrittura su disco per riparare la corruzione
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=2, ensure_ascii=False)
            self.logger.log(t("avatar_server.gdr.engine.auto_heal_success", file=path.name), "SYSTEM")
        except Exception as e:
            self.logger.error(f"Fallimento critico Auto-Heal su {path.name}: {e}")
            
        return default_data

    def _load_json(self, path: Path) -> Dict:
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        raise ValueError("File vuoto (0 byte)")
                    return json.loads(content)
        except Exception as e:
            self.logger.error(
                t("avatar_server.gdr.engine.read_error", name=path.name, error=str(e))
            )
            # --- INNESCO PROTOCOLLO FENICE ---
            return self._auto_heal_json(path)
        return {}

    def _save_json(self, path: Path, data: Dict):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(
                t("avatar_server.gdr.engine.write_error", name=path.name, error=str(e))
            )

    def _get_status_data(self) -> Dict:
        """Recupera lo status data dalla RAM se disponibile, altrimenti dal disco."""
        if self.get_world_state_cb:
            state = self.get_world_state_cb()
            if state: return state
        return self._load_json(self.status_file)

    def _save_status_data(self, data: Dict):
        """Salva lo status data in RAM se disponibile, altrimenti su disco."""
        if self.set_world_state_cb:
            self.set_world_state_cb(data)
        else:
            self._save_json(self.status_file, data)

    def _clear_encounters(self):
        """Svuota la sandbox dei nemici volatili."""
        self._save_json(self.encounters_file, {"nemici_attivi": [], "npc_casuali": []})

    def _get_all_entities(self) -> List[Dict]:
        """Recupera tutti i personaggi (status.json) e i nemici (encounters.json)."""
        status_data = self._get_status_data()
        encounters_data = self._load_json(self.encounters_file)

        entities = list()
        # Aggiungi PG/PNG
        for char in status_data.get("personaggi", []):
            # --- [FIX AGNOSTICISMO] Risoluzione nome PG a runtime ---
            char_name = char.get("nome", "")
            if char_name == "{{nome_pg}}":
                char_name = self.pg_name
                char["nome"] = self.pg_name

            # Carica la scheda completa per avere i dati RPG
            sheet_data = self._load_character_sheet(char_name)
            if sheet_data and "scheda_rpg" in sheet_data:
                char["scheda_rpg"] = sheet_data["scheda_rpg"]

                # --- [FIX CRITICO] OVERRIDE HP DA STATUS.JSON ---
                # Previene la lettura degli HP dalla scheda base, usando quelli della sessione corrente
                if "stats" in char and "HP" in char["stats"]:
                    char["scheda_rpg"].setdefault("combattimento", {})[
                        "hp_attuali"
                    ] = char["stats"]["HP"]

                char["is_enemy"] = False
                entities.append(char)

        # --- [NUOVO v28.0] AGGIUNGI GIOCATORI OSPITI ---
        for guest in status_data.get("giocatori_ospiti",[]):
            guest["is_enemy"] = False
            entities.append(guest)

        # Aggiungi Nemici
        for enemy in encounters_data.get("nemici_attivi", []):
            #[FIX CRITICO] Ignora le entità corrotte con template {{...}} per evitare allucinazioni del DM
            if "{{" not in enemy.get("nome", ""):
                enemy["is_enemy"] = True
                entities.append(enemy)

        # Aggiungi NPC Casuali/Alleati
        for npc in encounters_data.get("npc_casuali",[]):
            if "{{" not in npc.get("nome", ""):
                npc["is_enemy"] = False
                entities.append(npc)

        return entities

    def _find_character_sheet_path(
        self, directory: Path, char_name: str
    ) -> Optional[Path]:
        """Trova il file JSON leggendo il nome interno, ignorando il nome del file."""
        if not directory.is_dir():
            return None
        target_clean = char_name.lower().strip()

        for file_path in directory.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Cerca nelle chiavi anagrafiche comuni
                internal_name = (
                    data.get("dati_anagrafici", {}).get("nome_completo", "")
                    or data.get("dati_anagrafici", {}).get("nome", "")
                    or data.get("dati_anagrafici", {}).get("name", "")
                )
                if not internal_name:
                    continue

                internal_clean = internal_name.lower().strip()
                if (
                    internal_clean == target_clean
                    or target_clean in internal_clean
                    or internal_clean in target_clean
                ):
                    return file_path
            except:
                continue

        # Fallback sul nome del file
        for f in directory.glob("*.json"):
            if f.stem.lower() == target_clean or f.stem.lower() == target_clean.replace(
                " ", "_"
            ):
                return f
        return None

    def _load_character_sheet(self, char_name: str) -> Dict:
        """Cerca e carica il file JSON del personaggio in modo intelligente."""
        for tipo in ["PG", "PNG"]:
            tipo_dir = self.effective_root / tipo
            char_file = self._find_character_sheet_path(tipo_dir, char_name)
            if char_file and char_file.exists():
                return self._load_json(char_file)
        return {}

    def _fuzzy_match_entity(
        self, target_name: str, entities: List[Dict]
    ) -> Optional[Dict]:
        """Il Motore della Singolarità: corregge i typo dell'LLM trovando l'entità più simile."""
        if not target_name or not entities:
            return None

        names = [e.get("nome", "") for e in entities]
        matches = difflib.get_close_matches(target_name, names, n=1, cutoff=0.5)

        if matches:
            matched_name = matches[0]
            for e in entities:
                if e.get("nome") == matched_name:
                    return e
        return None

    def _parse_dice_string(self, dice_str: str) -> int:
        """Converte stringhe come '1d8+3' in un risultato numerico casuale."""
        try:
            # ---[FIX ROBUSTEZZA] Gestione D maiuscola e spazi ---
            dice_str = str(dice_str).lower().replace(" ", "")

            # --- [FIX DANNI FISSI] Se l'LLM passa un numero puro (es. "5") ---
            if dice_str.isdigit():
                return int(dice_str)

            match = re.search(r"(\d+)d(\d+)(?:([+-])(\d+))?", dice_str)
            if not match:
                return 1  # Fallback

            num_dice = int(match.group(1))
            dice_faces = int(match.group(2))
            sign = match.group(3)
            modifier = int(match.group(4)) if match.group(4) else 0

            total = sum(random.randint(1, dice_faces) for _ in range(num_dice))

            if sign == "+":
                total += modifier
            elif sign == "-":
                total -= modifier

            return max(0, total)  # Il danno non può essere negativo
        except:
            return 1

    def _broadcast_ui_update(self):
        """Invia lo stato degli HP al frontend tramite WebSocket."""
        entities = self._get_all_entities()
        combat_payload = []

        for e in entities:
            rpg_data = e.get("scheda_rpg", {})
            combat_data = rpg_data.get("combattimento", {})

            hp_max = combat_data.get("hp_massimi", 0)
            if hp_max > 0:  # Mostra solo chi ha statistiche di combattimento
                combat_payload.append(
                    {
                        "id": e.get("nome"),
                        "nome": e.get("nome"),
                        "hp_attuali": combat_data.get("hp_attuali", 0),
                        "hp_massimi": hp_max,
                        "is_enemy": e.get("is_enemy", False),
                    }
                )

        # --- [FIX HUD FANTASMA] Invia SEMPRE il payload, anche se vuoto, per pulire la UI ---
        if self.bridge:
            self.bridge.send_payload(
                {"type": "rpg_update", "combat_entities": combat_payload}
            )

    def _update_entity_hp(self, entity_name: str, new_hp: int, is_enemy: bool):
        """Aggiorna gli HP nel file corretto (status.json o encounters.json)."""
        encounters = self._load_json(self.encounters_file)
        updated_in_encounters = False

        # [MIGLIORAMENTO ARCHITETTURALE] Recupero HP Massimi per impedire l'over-healing
        hp_max = 999  # Fallback
        entities = self._get_all_entities()
        target = next((e for e in entities if e.get("nome") == entity_name), None)
        if target:
            hp_max = (
                target.get("scheda_rpg", {})
                .get("combattimento", {})
                .get("hp_massimi", 999)
            )

        new_hp = min(new_hp, hp_max)  # Cap superiore

        # ---[FIX CADAVERI IMMORTALI] Rimuove l'entità se gli HP sono <= 0 ---
        if new_hp <= 0:
            original_len_nemici = len(encounters.get("nemici_attivi", []))
            encounters["nemici_attivi"] = [
                e
                for e in encounters.get("nemici_attivi", [])
                if e.get("nome") != entity_name
            ]
            if len(encounters["nemici_attivi"]) < original_len_nemici:
                updated_in_encounters = True

            if not updated_in_encounters:
                original_len_npc = len(encounters.get("npc_casuali", []))
                encounters["npc_casuali"] = [
                    e
                    for e in encounters.get("npc_casuali", [])
                    if e.get("nome") != entity_name
                ]
                if len(encounters["npc_casuali"]) < original_len_npc:
                    updated_in_encounters = True
        else:
            # 1. Cerca nei nemici
            for e in encounters.get("nemici_attivi", []):
                if e.get("nome") == entity_name:
                    e.setdefault("scheda_rpg", {}).setdefault("combattimento", {})[
                        "hp_attuali"
                    ] = new_hp
                    updated_in_encounters = True
                    break

            # 2. Cerca negli NPC casuali
            if not updated_in_encounters:
                for e in encounters.get("npc_casuali", []):
                    if e.get("nome") == entity_name:
                        e.setdefault("scheda_rpg", {}).setdefault("combattimento", {})[
                            "hp_attuali"
                        ] = new_hp
                        updated_in_encounters = True
                        break

        if updated_in_encounters:
            self._save_json(self.encounters_file, encounters)
        else:
            # ---[FIX CRITICO] SALVATAGGIO IN STATUS.JSON ---
            # NON tocchiamo MAI i file in PG/PNG per non corrompere le schede base.
            status_data = self._get_status_data()
            updated_in_status = False
            for p in status_data.get("personaggi",[]):
                # ---[FIX AGNOSTICISMO] Controllo doppio per il PG ---
                if p.get("nome") == entity_name or (
                    entity_name == self.pg_name and p.get("nome") == "{{nome_pg}}"
                ):
                    if "stats" not in p:
                        p["stats"] = {}
                    p["stats"]["HP"] = new_hp
                    updated_in_status = True
                    break

            # ---[NUOVO v28.0] AGGIORNA HP OSPITI ---
            if not updated_in_status:
                for g in status_data.get("giocatori_ospiti",[]):
                    if g.get("nome") == entity_name:
                        g.setdefault("scheda_rpg", {}).setdefault("combattimento", {})[
                            "hp_attuali"
                        ] = new_hp
                        break

            self._save_status_data(status_data)

    def process_intent(self, intent_json: Dict, actor_name: str) -> str:
        """
        Punto di ingresso principale. Riceve il JSON dall'LLM e calcola l'esito.
        Restituisce una stringa di sistema per guidare la narrazione del DM.
        """
        azione = intent_json.get("azione", "").lower()

        if azione == "attacco":
            return self._resolve_attack(intent_json, actor_name)
        elif azione == "prova_caratteristica" or azione == "prova_abilita":
            return self._resolve_skill_check(intent_json, actor_name)
        elif azione == "spawn_nemico":
            return self._spawn_entity(intent_json, is_enemy=True)
        elif azione == "spawn_npc":
            return self._spawn_entity(intent_json, is_enemy=False)
        elif azione == "clear_encounters":
            self._clear_encounters()
            self._broadcast_ui_update()
            return t("avatar_server.gdr.engine.combat_end")
        else:
            return t("avatar_server.gdr.engine.narrative_action", action=azione)

    def _calculate_loot(self, enemy_entity: Dict) -> str:
        """Calcola il bottino matematico (RNG) alla morte di un nemico."""
        is_boss = enemy_entity.get("is_boss", False)

        # Livello stimato (fallback a 1 se non presente)
        enemy_level = (
            enemy_entity.get("scheda_rpg", {}).get("dati_base", {}).get("livello", 1)
        )

        roll = random.randint(1, 100)
        loot_items = list()

        if is_boss:
            # Tabella Boss: Oro elevato + Oggetto Magico garantito
            oro = random.randint(50, 200) * enemy_level
            loot_items.append(t("avatar_server.gdr.engine.gold", count=oro))

            magic_roll = random.randint(1, 100)
            if magic_roll <= 80:
                loot_items.append(t("avatar_server.gdr.engine.magic_item_rare"))
            else:
                loot_items.append(t("avatar_server.gdr.engine.cursed_ring"))
        else:
            # Tabella Standard
            if roll <= 70:
                # Drop Comune
                rame = random.randint(10, 50) * enemy_level
                argento = random.randint(0, 5) * enemy_level
                loot_items.append(t("avatar_server.gdr.engine.copper", count=rame))
                if argento > 0:
                    loot_items.append(
                        t("avatar_server.gdr.engine.silver", count=argento)
                    )
                if random.choice([True, False]):
                    loot_items.append(t("avatar_server.gdr.engine.ration"))
            elif roll <= 95:
                # Drop Raro
                oro = random.randint(1, 10) * enemy_level
                loot_items.append(t("avatar_server.gdr.engine.gold", count=oro))
                loot_items.append(t("avatar_server.gdr.engine.standard_gear"))
            else:
                # Drop Epico (5%)
                loot_items.append(t("avatar_server.gdr.engine.magic_item_uncommon"))

        loot_str = ", ".join(loot_items)
        return t("avatar_server.gdr.engine.loot_dead", loot=loot_str)

    def _resolve_attack(self, intent: Dict, actor_name: str) -> str:
        entities = self._get_all_entities()

        # 1. Identifica Attaccante
        actor = self._fuzzy_match_entity(actor_name, entities)
        if not actor:
            return t(
                "avatar_server.gdr.engine.error_attacker_not_found", name=actor_name
            )

        # 2. Identifica Bersaglio
        target_name = intent.get("bersaglio", "")
        target = self._fuzzy_match_entity(target_name, entities)
        if not target:
            return t(
                "avatar_server.gdr.engine.error_target_not_found", name=target_name
            )

        # 3. Estrai Statistiche
        actor_rpg = actor.get("scheda_rpg", {})
        target_rpg = target.get("scheda_rpg", {})

        target_ac = target_rpg.get("combattimento", {}).get("classe_armatura", 10)
        target_hp = target_rpg.get("combattimento", {}).get("hp_attuali", 10)

        # 4. Identifica Arma e Bonus
        weapon_name = intent.get("arma", t("avatar_server.gdr.engine.unarmed"))
        weapons = actor_rpg.get("equipaggiamento", {}).get("armi", [])

        # Fuzzy match sull'arma
        weapon = None
        if weapons:
            w_names = [w.get("nome", "") for w in weapons]
            w_matches = difflib.get_close_matches(weapon_name, w_names, n=1, cutoff=0.4)
            if w_matches:
                weapon = next(
                    (w for w in weapons if w.get("nome") == w_matches[0]), None
                )

        if weapon:
            atk_bonus = weapon.get("bonus_attacco", 0)
            dmg_dice = weapon.get("danno", "1d4")
            w_name_real = weapon.get("nome")
        else:
            # Fallback disarmato basato su Forza
            str_mod = (
                actor_rpg.get("statistiche_core", {})
                .get("forza", {})
                .get("modificatore", 0)
            )
            atk_bonus = str_mod
            dmg_dice = f"1d4+{str_mod}"
            w_name_real = t("avatar_server.gdr.engine.unarmed_attack")

        # 5. Lancio del Dado (D20)
        d20 = random.randint(1, 20)
        total_atk = d20 + atk_bonus

        # 6. Risoluzione
        if d20 == 20:
            is_hit = True
            is_crit = True
            dmg = self._parse_dice_string(dmg_dice) * 2  # Danno raddoppiato
            result_text = t("avatar_server.gdr.engine.crit_success")
        elif d20 == 1:
            is_hit = False
            is_crit = False
            dmg = 0
            result_text = t("avatar_server.gdr.engine.crit_fail")
        else:
            is_hit = total_atk >= target_ac
            is_crit = False
            dmg = self._parse_dice_string(dmg_dice) if is_hit else 0
            result_text = (
                t("avatar_server.gdr.engine.hit")
                if is_hit
                else t("avatar_server.gdr.engine.miss")
            )

        # 7. Applicazione Danni
        if is_hit:
            new_hp = max(0, target_hp - dmg)
            self._update_entity_hp(
                target.get("nome"), new_hp, target.get("is_enemy", False)
            )
            self._broadcast_ui_update()

            status_target = t("avatar_server.gdr.engine.alive")
            if new_hp == 0:
                status_target = t("avatar_server.gdr.engine.dead_unconscious")

            dm_directive = t(
                "avatar_server.gdr.engine.attack_report",
                actor=actor.get("nome"),
                target=target.get("nome"),
                weapon=w_name_real,
                d20=d20,
                bonus=atk_bonus,
                total=total_atk,
                ac=target_ac,
                result=result_text,
                damage=dmg,
                hp=new_hp,
                status=status_target,
            )

            if is_crit:
                dm_directive += t("avatar_server.gdr.engine.crit_desc")
            elif new_hp == 0:
                # ---[NUOVO v28.0] LOOT SYSTEM MATEMATICO ---
                if target.get("is_enemy", False):
                    loot_str = self._calculate_loot(target)
                    dm_directive += t(
                        "avatar_server.gdr.engine.kill_desc", loot=loot_str
                    )
                else:
                    dm_directive += t("avatar_server.gdr.engine.kill_desc_no_loot")
            else:
                dm_directive += t("avatar_server.gdr.engine.hit_desc")
        else:
            dm_directive = t(
                "avatar_server.gdr.engine.miss_report",
                actor=actor.get("nome"),
                target=target.get("nome"),
                weapon=w_name_real,
                d20=d20,
                bonus=atk_bonus,
                total=total_atk,
                ac=target_ac,
                result=result_text,
            )
            if d20 == 1:
                dm_directive += t("avatar_server.gdr.engine.miss_crit_desc")
            else:
                dm_directive += t("avatar_server.gdr.engine.miss_desc")

        return dm_directive

    def _resolve_skill_check(self, intent: Dict, actor_name: str) -> str:
        entities = self._get_all_entities()
        actor = self._fuzzy_match_entity(actor_name, entities)
        if not actor:
            return t("avatar_server.gdr.engine.error_char_not_found", name=actor_name)

        skill_name = intent.get("statistica", "destrezza").lower()
        dc = intent.get("difficolta_stimata", 15)  # Default Media

        # Mappa abilità a statistica core
        core_stat = self.skill_to_stat_map.get(skill_name, "saggezza")

        actor_rpg = actor.get("scheda_rpg", {})
        stat_mod = (
            actor_rpg.get("statistiche_core", {})
            .get(core_stat, {})
            .get("modificatore", 0)
        )

        d20 = random.randint(1, 20)
        total = d20 + stat_mod

        # Gradi di Successo (La filosofia "Sì, e..." / "No, ma...")
        if d20 == 20:
            esito = t("avatar_server.gdr.engine.skill_crit_success")
            direttiva = t("avatar_server.gdr.engine.skill_crit_success_desc")
        elif d20 == 1:
            esito = t("avatar_server.gdr.engine.skill_crit_fail")
            direttiva = t("avatar_server.gdr.engine.skill_crit_fail_desc")
        elif total >= dc + 5:
            esito = t("avatar_server.gdr.engine.skill_full_success")
            direttiva = t("avatar_server.gdr.engine.skill_full_success_desc")
        elif total >= dc:
            esito = t("avatar_server.gdr.engine.skill_partial_success")
            direttiva = t("avatar_server.gdr.engine.skill_partial_success_desc")
        else:
            esito = t("avatar_server.gdr.engine.skill_fail")
            direttiva = t("avatar_server.gdr.engine.skill_fail_desc")

        return t(
            "avatar_server.gdr.engine.skill_report",
            skill=skill_name.capitalize(),
            actor=actor.get("nome"),
            d20=d20,
            mod=stat_mod,
            total=total,
            dc=dc,
            result=esito,
            desc=direttiva,
        )

    def _spawn_entity(self, intent: Dict, is_enemy: bool) -> str:
        """Genera un'entità volatile (Nemico o NPC) in encounters.json."""
        nome = intent.get("nome", t("avatar_server.gdr.engine.unknown_entity"))
        
        # --- SANITIZZATORE ENTITÀ (ANTI-TEMPLATE BLEEDING) ---
        # Impedisce lo spawn di entità con nomi corrotti come {{title}}
        if "{{" in nome or "}}" in nome:
            self.logger.warning(f"Tentativo di spawn entità corrotta bloccato: {nome}")
            nome = t("avatar_server.gdr.engine.unknown_entity")
            
        hp = intent.get("hp", 20)
        ac = intent.get("ca", 12)

        encounters = self._load_json(self.encounters_file)
        target_array = "nemici_attivi" if is_enemy else "npc_casuali"

        # Genera ID univoco per permettere entità multiple con lo stesso nome
        count = sum(
            1 for e in encounters.get(target_array,[]) if nome in e.get("nome", "")
        )
        unique_name = f"{nome} {count + 1}" if count > 0 else nome

        new_entity = {
            "id": f"ent_{random.randint(1000,9999)}",
            "nome": unique_name,
            "scheda_rpg": {
                "combattimento": {
                    "hp_massimi": hp,
                    "hp_attuali": hp,
                    "classe_armatura": ac,
                    "iniziativa": random.randint(1, 20) + 2,
                }
            },
        }

        encounters.setdefault(target_array,[]).append(new_entity)
        self._save_json(self.encounters_file, encounters)

        self._broadcast_ui_update()

        tipo_str = (
            t("avatar_server.gdr.engine.enemy")
            if is_enemy
            else t("avatar_server.gdr.engine.npc_ally")
        )
        return t(
            "avatar_server.gdr.engine.spawn_report",
            type=tipo_str,
            name=unique_name,
            hp=hp,
            ac=ac,
        )

    # --- METODI DI GESTIONE STATO COMBATTIMENTO (STATE MACHINE) ---

    def get_combat_state(self) -> Dict[str, Any]:
        """Recupera lo stato attuale del combattimento dal file status.json."""
        status_data = self._get_status_data()
        return status_data.get("metadati", {}).get("game_state", {})

    def is_enemy(self, entity_name: str) -> bool:
        """Verifica se un'entità è un nemico attivo leggendo encounters.json."""
        encounters = self._load_json(self.encounters_file)
        for e in encounters.get("nemici_attivi", []):
            if e.get("nome") == entity_name:
                return True
        return False

    def start_combat(self):
        """Inizia il combattimento: tira l'iniziativa per tutti e crea la coda dei turni."""
        self.logger.log(t("avatar_server.gdr.engine.log_init_combat"), "RPG")
        status_data = self._get_status_data()
        entities = self._get_all_entities()

        initiative_list = []
        for e in entities:
            name = e.get("nome")
            # Recupera il modificatore di iniziativa dalla scheda
            init_mod = (
                e.get("scheda_rpg", {}).get("combattimento", {}).get("iniziativa", 0)
            )
            # Tiro del D20 + Modificatore
            roll = random.randint(1, 20) + init_mod
            initiative_list.append({"nome": name, "roll": roll})

        # Ordina in modo decrescente (chi fa di più agisce prima)
        initiative_list.sort(key=lambda x: x["roll"], reverse=True)
        turn_order = [item["nome"] for item in initiative_list]

        if "metadati" not in status_data:
            status_data["metadati"] = {}
        if "game_state" not in status_data["metadati"]:
            status_data["metadati"]["game_state"] = {}

        status_data["metadati"]["game_state"].update(
            {
                "is_combat": True,
                "turn_order": turn_order,
                "active_entity": turn_order[0] if turn_order else "",
                "round": 1,
            }
        )

        self._save_status_data(status_data)
        self.logger.log(
            t("avatar_server.gdr.engine.log_turn_order", order=str(turn_order)), "RPG"
        )

    def end_combat(self):
        """Termina il combattimento e pulisce la coda dei turni."""
        self.logger.log(t("avatar_server.gdr.engine.log_combat_end"), "RPG")
        status_data = self._get_status_data()

        if "metadati" in status_data and "game_state" in status_data["metadati"]:
            status_data["metadati"]["game_state"]["is_combat"] = False
            status_data["metadati"]["game_state"]["turn_order"] = []
            status_data["metadati"]["game_state"]["active_entity"] = ""

        self._save_status_data(status_data)

    def next_turn(self):
        """Avanza la coda di iniziativa al personaggio successivo."""
        status_data = self._get_status_data()
        game_state = status_data.get("metadati", {}).get("game_state", {})

        if not game_state.get("is_combat"):
            return

        turn_order = game_state.get("turn_order", [])
        if not turn_order:
            return

        current_active = game_state.get("active_entity")
        try:
            idx = turn_order.index(current_active)
            next_idx = (idx + 1) % len(turn_order)
        except ValueError:
            next_idx = 0

        game_state["active_entity"] = turn_order[next_idx]

        # Se siamo tornati all'inizio della lista, incrementa il round
        if next_idx == 0:
            game_state["round"] = game_state.get("round", 1) + 1

        self._save_status_data(status_data)
        self.logger.log(
            t(
                "avatar_server.gdr.engine.log_next_turn",
                entity=game_state["active_entity"],
                round=game_state.get("round", 1),
            ),
            "RPG",
        )
