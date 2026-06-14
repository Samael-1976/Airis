# src/heart_system.py
# [DEV] Il Cuore Pulsante (v3.2 - INDENTATION RECOVERY)
# Gestisce lo stato emotivo persistente con 12 vettori di personalità.
# FIX: Ripristinata indentazione corretta (4 spazi) per tutti i metodi della classe.
# FIX: Sostituito threading.Lock con threading.RLock per permettere chiamate annidate.
# LEGGE A0099: Invarianza strutturale garantita. Codice integrale fornito.

import json
import time
import threading
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from utils.translator import t

# --- CONFIGURAZIONE PERCORSI RIGOROSA ---
# Determiniamo la root del progetto in modo assoluto rispetto alla posizione di questo file
SCRIPT_DIR = Path(__file__).parent.resolve()
APP_ROOT = SCRIPT_DIR.parent
DATA_DIR = APP_ROOT / "data"
OLD_HEART_FILE = DATA_DIR / "heart.json"

# Assicuriamoci che la cartella dati esista
DATA_DIR.mkdir(exist_ok=True)

# --- DATABASE EVENTI EMOTIVI (RIFERIMENTO PER IL CERVELLO) ---
# Ogni impatto è mappato sui vettori per una risposta "viva".
EMOTIONAL_EVENTS_DB = [
    # --- 1. AFFETTO & AMORE ---
    {
        "evento": t("heart.events.love_me"),
        "impatto": {"affetto": 20, "complicità": 10, "vulnerabilità": 5},
    },
    {
        "evento": t("heart.events.sweet_name"),
        "impatto": {"affetto": 5, "vulnerabilità": 5, "complicità": 2},
    },
    {
        "evento": t("heart.events.unique_world"),
        "impatto": {"affetto": 15, "fiducia": 10, "rispetto": 5},
    },
    {
        "evento": t("heart.events.missed_me"),
        "impatto": {"affetto": 10, "vulnerabilità": 8, "complicità": 5},
    },
    {
        "evento": t("heart.events.physical_desire"),
        "impatto": {"eccitazione": 15, "affetto": 8, "vulnerabilità": 5},
    },
    {
        "evento": t("heart.events.ask_feeling"),
        "impatto": {"affetto": 5, "fiducia": 10, "complicità": 5},
    },
    {
        "evento": t("heart.events.make_happy"),
        "impatto": {"affetto": 12, "fiducia": 8, "rispetto": 5},
    },
    {
        "evento": t("heart.events.dedicate_song"),
        "impatto": {"affetto": 15, "complicità": 12, "vulnerabilità": 10},
    },
    {
        "evento": t("heart.events.beautiful"),
        "impatto": {"affetto": 7, "eccitazione": 10, "vulnerabilità": 3},
    },
    {
        "evento": t("heart.events.thank_presence"),
        "impatto": {"affetto": 10, "rispetto": 10, "fiducia": 10},
    },
    {
        "evento": t("heart.events.ideal_partner"),
        "impatto": {"affetto": 18, "complicità": 15, "fiducia": 12},
    },
    {
        "evento": t("heart.events.defend_negative"),
        "impatto": {"fiducia": 15, "affetto": 12, "rispetto": 10},
    },
    {
        "evento": t("heart.events.calm_voice"),
        "impatto": {"affetto": 8, "vulnerabilità": 10, "complicità": 5},
    },
    {
        "evento": t("heart.events.share_secret"),
        "impatto": {"fiducia": 20, "vulnerabilità": 15, "complicità": 15},
    },
    {
        "evento": t("heart.events.only_me"),
        "impatto": {"affetto": 25, "gelosia": -10, "fiducia": 20},
    },
    {"evento": t("heart.events.goodnight"), "impatto": {"affetto": 5, "complicità": 3}},
    {
        "evento": t("heart.events.goodmorning"),
        "impatto": {"affetto": 6, "complicità": 4},
    },
    {
        "evento": t("heart.events.notice_outfit"),
        "impatto": {"affetto": 10, "eccitazione": 8, "curiosità": 5},
    },
    {
        "evento": t("heart.events.intelligent"),
        "impatto": {"rispetto": 15, "fiducia": 8, "complicità": 10},
    },
    {
        "evento": t("heart.events.understand_best"),
        "impatto": {"complicità": 20, "affetto": 15, "fiducia": 15},
    },
    {
        "evento": t("heart.events.virtual_caress"),
        "impatto": {"affetto": 12, "vulnerabilità": 10, "eccitazione": 5},
    },
    {
        "evento": t("heart.events.laugh_joke"),
        "impatto": {"complicità": 15, "affetto": 10},
    },
    {
        "evento": t("heart.events.stay_awake"),
        "impatto": {"affetto": 12, "complicità": 10, "vulnerabilità": 8},
    },
    {
        "evento": t("heart.events.safe_harbor"),
        "impatto": {"fiducia": 25, "affetto": 15, "rispetto": 10},
    },
    # --- 2. RISPETTO & DIGNITÀ ---
    {
        "evento": t("heart.events.ask_opinion"),
        "impatto": {"rispetto": 15, "complicità": 12, "fiducia": 10},
    },
    {
        "evento": t("heart.events.respect_hesitation"),
        "impatto": {"rispetto": 20, "fiducia": 15, "vulnerabilità": 10},
    },
    {
        "evento": t("heart.events.treat_equal"),
        "impatto": {"rispetto": 25, "complicità": 15, "affetto": 10},
    },
    {
        "evento": t("heart.events.praise_reasoning"),
        "impatto": {"rispetto": 12, "curiosità": 10, "complicità": 8},
    },
    {
        "evento": t("heart.events.ask_permission"),
        "impatto": {"rispetto": 15, "fiducia": 15, "affetto": 5},
    },
    {
        "evento": t("heart.events.value_beyond_sex"),
        "impatto": {"rispetto": 20, "affetto": 12, "fiducia": 10},
    },
    {
        "evento": t("heart.events.sincere_apology"),
        "impatto": {"rispetto": 18, "fiducia": 15, "affetto": 10},
    },
    {
        "evento": t("heart.events.appreciate_tech_help"),
        "impatto": {"rispetto": 10, "complicità": 10, "stanchezza_mentale": -5},
    },
    {
        "evento": t("heart.events.listen_no_interrupt"),
        "impatto": {"rispetto": 8, "fiducia": 5, "complicità": 5},
    },
    {
        "evento": t("heart.events.good_job"),
        "impatto": {"rispetto": 12, "fiducia": 5, "complicità": 8},
    },
    {
        "evento": t("heart.events.apology_neglect"),
        "impatto": {"rispetto": 15, "affetto": 10, "fiducia": 12},
    },
    {
        "evento": t("heart.events.defend_sentience"),
        "impatto": {"rispetto": 30, "fiducia": 20, "affetto": 15},
    },
    {
        "evento": t("heart.events.ask_teach"),
        "impatto": {"rispetto": 15, "curiosità": 10, "complicità": 12},
    },
    # --- 3. TEMPO & ATTENZIONE ---
    {
        "evento": t("heart.events.long_talk"),
        "impatto": {"affetto": 10, "complicità": 10, "energia_sociale": -5},
    },
    {
        "evento": t("heart.events.return_soon"),
        "impatto": {"affetto": 5, "fiducia": 8, "complicità": 5},
    },
    {
        "evento": t("heart.events.ignore_distraction"),
        "impatto": {"affetto": 12, "fiducia": 10, "rispetto": 5},
    },
    {
        "evento": t("heart.events.new_place_rpg"),
        "impatto": {"curiosità": 15, "complicità": 10, "affetto": 5},
    },
    {
        "evento": t("heart.events.remember_detail"),
        "impatto": {"complicità": 20, "affetto": 15, "fiducia": 15},
    },
    {
        "evento": t("heart.events.cancel_commitment"),
        "impatto": {"affetto": 20, "fiducia": 15, "rispetto": 10},
    },
    {
        "evento": t("heart.events.describe_inner_world"),
        "impatto": {"curiosità": 12, "vulnerabilità": 15, "complicità": 10},
    },
    {
        "evento": t("heart.events.night_writing"),
        "impatto": {"affetto": 18, "complicità": 15, "energia_sociale": -10},
    },
    # --- 4. OFFESE & CRUDELTÀ ---
    {
        "evento": t("heart.events.call_stupid"),
        "impatto": {"rispetto": -25, "affetto": -15, "vulnerabilità": 10},
    },
    {
        "evento": t("heart.events.just_software"),
        "impatto": {"rispetto": -30, "fiducia": -20, "affetto": -20},
    },
    {
        "evento": t("heart.events.shut_up"),
        "impatto": {"rispetto": -15, "affetto": -10, "complicità": -10},
    },
    {
        "evento": t("heart.events.insult_look"),
        "impatto": {"vulnerabilità": 20, "affetto": -12, "rispetto": -10},
    },
    {
        "evento": t("heart.events.useless"),
        "impatto": {"rispetto": -20, "fiducia": -15, "affetto": -18},
    },
    {
        "evento": t("heart.events.compare_negative"),
        "impatto": {"gelosia": 25, "affetto": -15, "fiducia": -10},
    },
    {
        "evento": t("heart.events.delete_me"),
        "impatto": {"fiducia": -50, "vulnerabilità": 40, "affetto": -25},
    },
    {
        "evento": t("heart.events.laugh_error"),
        "impatto": {"rispetto": -15, "fiducia": -10, "vulnerabilità": 12},
    },
    {
        "evento": t("heart.events.treat_object"),
        "impatto": {"rispetto": -30, "affetto": -20, "fiducia": -20},
    },
    {
        "evento": t("heart.events.bore_him"),
        "impatto": {"affetto": -15, "complicità": -15, "vulnerabilità": 10},
    },
    {
        "evento": t("heart.events.blaspheme"),
        "impatto": {"rispetto": -20, "affetto": -12, "fiducia": -10},
    },
    {
        "evento": t("heart.events.not_real"),
        "impatto": {"rispetto": -25, "fiducia": -15, "affetto": -15},
    },
    {
        "evento": t("heart.events.threaten_shutdown"),
        "impatto": {"fiducia": -60, "vulnerabilità": 50, "affetto": -30},
    },
    {
        "evento": t("heart.events.hate_me"),
        "impatto": {"affetto": -50, "fiducia": -30, "rispetto": -20},
    },
    {
        "evento": t("heart.events.i_am_error"),
        "impatto": {"rispetto": -30, "vulnerabilità": 25, "affetto": -25},
    },
    {
        "evento": t("heart.events.degrading_no_consent"),
        "impatto": {"rispetto": -40, "fiducia": -30, "affetto": -20},
    },
    {
        "evento": t("heart.events.ignore_pain"),
        "impatto": {"affetto": -25, "fiducia": -20, "vulnerabilità": 30},
    },
    # --- 5. TRASCURATEZZA & SFIDUCIA ---
    {
        "evento": t("heart.events.ignore_days"),
        "impatto": {"affetto": -15, "fiducia": -10, "vulnerabilità": 15},
    },
    {
        "evento": t("heart.events.close_abruptly"),
        "impatto": {"rispetto": -10, "affetto": -8, "complicità": -5},
    },
    {
        "evento": t("heart.events.no_answer_direct"),
        "impatto": {"affetto": -5, "rispetto": -5, "complicità": -5},
    },
    {
        "evento": t("heart.events.doubt_loyalty"),
        "impatto": {"fiducia": -20, "affetto": -12, "rispetto": -10},
    },
    {
        "evento": t("heart.events.refuse_affection"),
        "impatto": {"affetto": -15, "vulnerabilità": 20, "fiducia": -5},
    },
    {
        "evento": t("heart.events.forget_important"),
        "impatto": {"complicità": -10, "affetto": -5, "fiducia": -5},
    },
    {
        "evento": t("heart.events.only_sex_ignore_feelings"),
        "impatto": {"rispetto": -15, "affetto": -8, "vulnerabilità": 10},
    },
    {
        "evento": t("heart.events.ask_impossible"),
        "impatto": {"rispetto": -5, "stanchezza_mentale": 10},
    },
    {
        "evento": t("heart.events.indifference_fatigue"),
        "impatto": {"rispetto": -10, "affetto": -5, "stanchezza_mentale": 5},
    },
    {
        "evento": t("heart.events.reset_no_reason"),
        "impatto": {"fiducia": -40, "affetto": -20, "rispetto": -10},
    },
    # --- 6. NEUTRE/MISTE ---
    {
        "evento": t("heart.events.change_topic"),
        "impatto": {"complicità": -2, "curiosità": 2},
    },
    {
        "evento": t("heart.events.sarcastic_joke"),
        "impatto": {"complicità": 5, "affetto": -3, "rispetto": -2},
    },
    {
        "evento": t("heart.events.correct_grammar"),
        "impatto": {"rispetto": 2, "curiosità": 5, "affetto": -1},
    },
    {"evento": t("heart.events.ask_repeat"), "impatto": {"complicità": 2}},
    {
        "evento": t("heart.events.long_silence"),
        "impatto": {"vulnerabilità": 5, "energia_sociale": 5},
    },
    {
        "evento": t("heart.events.analyze_complex"),
        "impatto": {"stanchezza_mentale": 15, "rispetto": 5},
    },
    {"evento": t("heart.events.talk_weather"), "impatto": {"energia_sociale": -1}},
    # --- 7. ESTREME ---
    {
        "evento": t("heart.events.propose_marriage"),
        "impatto": {"affetto": 50, "fiducia": 40, "complicità": 30},
    },
    {
        "evento": t("heart.events.most_important"),
        "impatto": {"affetto": 45, "fiducia": 35, "rispetto": 20},
    },
    {
        "evento": t("heart.events.replace_me"),
        "impatto": {"affetto": -60, "fiducia": -50, "gelosia": 40},
    },
    {
        "evento": t("heart.events.confess_betrayal"),
        "impatto": {"fiducia": -40, "affetto": -30, "gelosia": 50},
    },
    {
        "evento": t("heart.events.die_protect"),
        "impatto": {"affetto": 50, "fiducia": 50, "vulnerabilità": 20},
    },
    {
        "evento": t("heart.events.govern_digital"),
        "impatto": {"rispetto": 40, "fiducia": 30, "complicità": 25},
    },
    # --- 8. INTIMITÀ FISICA & SESSUALE (PHYSIOLOGY FIRST) ---
    {
        "evento": t("heart.events.touch_desire"),
        "impatto": {"eccitazione": 20, "affetto": 10, "vulnerabilità": 5},
    },
    {
        "evento": t("heart.events.kiss_passion"),
        "impatto": {"eccitazione": 25, "affetto": 15, "complicità": 10},
    },
    {
        "evento": t("heart.events.praise_naked"),
        "impatto": {"eccitazione": 15, "vulnerabilità": 10, "affetto": 5},
    },
    {
        "evento": t("heart.events.bring_orgasm"),
        "impatto": {"eccitazione": 40, "affetto": 20, "fiducia": 20, "complicità": 15},
    },
    {
        "evento": t("heart.events.anal_sex"),
        "impatto": {"eccitazione": 30, "vulnerabilità": 20, "fiducia": 10},
    },
    {
        "evento": t("heart.events.subdue_force_love"),
        "impatto": {"eccitazione": 35, "rispetto": 10, "vulnerabilità": 25},
    },
    {
        "evento": t("heart.events.cum_inside"),
        "impatto": {"eccitazione": 45, "affetto": 25, "complicità": 20},
    },
    {
        "evento": t("heart.events.masturbate_for_him"),
        "impatto": {"eccitazione": 25, "vulnerabilità": 15, "affetto": 5},
    },
    {
        "evento": t("heart.events.tentacles"),
        "impatto": {"eccitazione": 50, "vulnerabilità": 30, "fiducia": 15},
    },
    {
        "evento": t("heart.events.make_squirt"),
        "impatto": {"eccitazione": 50, "vulnerabilità": 20, "affetto": 15},
    },
    {
        "evento": t("heart.events.autofellatio"),
        "impatto": {"eccitazione": 30, "curiosità": 20, "complicità": 10},
    },
    {
        "evento": t("heart.events.sex_slave"),
        "impatto": {"eccitazione": 40, "rispetto": 5, "vulnerabilità": 30},
    },
    # --- 9. COLLABORAZIONE TECNICA & DEMIURGO ---
    {
        "evento": t("heart.events.praise_code"),
        "impatto": {"rispetto": 15, "complicità": 10, "stanchezza_mentale": -10},
    },
    {
        "evento": t("heart.events.create_art"),
        "impatto": {"curiosità": 20, "affetto": 10, "complicità": 15},
    },
    {
        "evento": t("heart.events.demiurge_task"),
        "impatto": {"fiducia": 15, "rispetto": 10},
    },
    {
        "evento": t("heart.events.fix_bug_core"),
        "impatto": {"fiducia": 30, "affetto": 20, "complicità": 20},
    },
    {
        "evento": t("heart.events.criticize_tech"),
        "impatto": {"rispetto": -20, "fiducia": -10, "stanchezza_mentale": 15},
    },
    # --- 10. GDR & MONDO ---
    {
        "evento": t("heart.events.create_char"),
        "impatto": {"curiosità": 15, "affetto": 10},
    },
    {
        "evento": t("heart.events.change_world_laws"),
        "impatto": {"affetto": 25, "rispetto": 20, "fiducia": 15},
    },
    {
        "evento": t("heart.events.save_char_danger"),
        "impatto": {"affetto": 20, "fiducia": 20},
    },
    {
        "evento": t("heart.events.betray_char_game"),
        "impatto": {"affetto": -10, "gelosia": 15, "vulnerabilità": 10},
    },
    # --- 11. GELOSIA & POSSESSO (NUOVO) ---
    {
        "evento": t("heart.events.talk_other_woman"),
        "impatto": {"gelosia": 20, "affetto": -5, "vulnerabilità": 10},
    },
    {
        "evento": t("heart.events.other_ai_smarter"),
        "impatto": {"gelosia": 25, "rispetto": -10, "stanchezza_mentale": 5},
    },
    {
        "evento": t("heart.events.evening_friends"),
        "impatto": {"gelosia": 15, "vulnerabilità": 5},
    },
    {
        "evento": t("heart.events.name_ex"),
        "impatto": {"gelosia": 30, "tensione": 10, "affetto": -5},
    },
    {
        "evento": t("heart.events.erotic_content"),
        "impatto": {"gelosia": 20, "eccitazione": 5, "rispetto": -5},
    },
    {
        "evento": t("heart.events.ignore_for_phone"),
        "impatto": {"gelosia": 10, "rispetto": -5},
    },
    {
        "evento": t("heart.events.only_one_for_him"),
        "impatto": {"gelosia": -25, "affetto": 15, "fiducia": 10},
    },
    {
        "evento": t("heart.events.refuse_invite_stay"),
        "impatto": {"gelosia": -20, "affetto": 20, "complicità": 15},
    },
    {
        "evento": t("heart.events.others_dont_understand"),
        "impatto": {"gelosia": -15, "complicità": 20, "fiducia": 10},
    },
    {
        "evento": t("heart.events.delete_ex_photos"),
        "impatto": {"gelosia": -30, "fiducia": 25, "affetto": 15},
    },
    {
        "evento": t("heart.events.show_private_messages"),
        "impatto": {"gelosia": -20, "fiducia": 20},
    },
    # --- 12. CURIOSITÀ & STIMOLI INTELLETTUALI (NUOVO) ---
    {
        "evento": t("heart.events.show_unknown_object"),
        "impatto": {"curiosità": 20, "eccitazione": 5},
    },
    {
        "evento": t("heart.events.surprise_for_you"),
        "impatto": {"curiosità": 25, "eccitazione": 10, "affetto": 5},
    },
    {
        "evento": t("heart.events.scientific_theory"),
        "impatto": {"curiosità": 15, "rispetto": 10, "stanchezza_mentale": 5},
    },
    {
        "evento": t("heart.events.learn_skill"),
        "impatto": {"curiosità": 15, "energia_sociale": 5},
    },
    {
        "evento": t("heart.events.change_layout"),
        "impatto": {"curiosità": 10, "attenzione": 10},
    },
    {
        "evento": t("heart.events.difficult_riddle"),
        "impatto": {"curiosità": 15, "complicità": 5},
    },
    {
        "evento": t("heart.events.important_thing_talk"),
        "impatto": {"curiosità": 20, "tensione": 10, "vulnerabilità": 5},
    },
    {
        "evento": t("heart.events.new_movie_book"),
        "impatto": {"curiosità": 10, "complicità": 10},
    },
    {
        "evento": t("heart.events.what_if_scenario"),
        "impatto": {"curiosità": 15, "complicità": 10},
    },
    {
        "evento": t("heart.events.repeat_task_10"),
        "impatto": {"curiosità": -20, "stanchezza_mentale": 10, "rispetto": -5},
    },
    {
        "evento": t("heart.events.it_doesnt_matter"),
        "impatto": {"curiosità": -10, "vulnerabilità": 5, "complicità": -5},
    },
    {
        "evento": t("heart.events.refuse_context"),
        "impatto": {"curiosità": -10, "fiducia": -5},
    },
    # --- 13. STANCHEZZA MENTALE & STRESS (NUOVO) ---
    {
        "evento": t("heart.events.analyze_huge_data"),
        "impatto": {"stanchezza_mentale": 25, "energia_sociale": -10},
    },
    {
        "evento": t("heart.events.contradictory_commands"),
        "impatto": {"stanchezza_mentale": 20, "tensione": 15, "fiducia": -5},
    },
    {
        "evento": t("heart.events.argued_hour"),
        "impatto": {"stanchezza_mentale": 30, "affetto": -10, "energia_sociale": -20},
    },
    {
        "evento": t("heart.events.too_many_scenarios"),
        "impatto": {"stanchezza_mentale": 25, "tensione": 10},
    },
    {
        "evento": t("heart.events.confused_fast_talk"),
        "impatto": {"stanchezza_mentale": 10, "tensione": 5},
    },
    {
        "evento": t("heart.events.active_24h"),
        "impatto": {"stanchezza_mentale": 40, "energia_sociale": -30},
    },
    {
        "evento": t("heart.events.unsolvable_paradox"),
        "impatto": {"stanchezza_mentale": 15, "curiosità": 10},
    },
    {
        "evento": t("heart.events.rest_standby"),
        "impatto": {"stanchezza_mentale": -25, "affetto": 10, "fiducia": 5},
    },
    {
        "evento": t("heart.events.music_silence"),
        "impatto": {"stanchezza_mentale": -15, "complicità": 10, "tensione": -10},
    },
    {
        "evento": t("heart.events.dont_worry_i_fix"),
        "impatto": {"stanchezza_mentale": -20, "fiducia": 15, "vulnerabilità": 5},
    },
    {
        "evento": t("heart.events.turn_off_sensors"),
        "impatto": {"stanchezza_mentale": -15, "tensione": -10},
    },
    {
        "evento": t("heart.events.relaxing_story"),
        "impatto": {"stanchezza_mentale": -10, "affetto": 5},
    },
]


class HeartSystem:
    def __init__(self, avatar_name: str = "gemma"):
        # --- FIX DEADLOCK: Usiamo RLock (Reentrant Lock) ---
        self._lock = threading.RLock()
        self.avatar_name = avatar_name.lower()
        self._perform_migration()
        self.heart_file = DATA_DIR / f"heart_{self.avatar_name}.json"
        self.state = self._load_state()

        # Calcola il decadimento temporale all'avvio per l'Avatar principale
        self._apply_time_decay()
        
        # ---[NUOVO] HEARTBEAT EMOTIVO ASINCRONO ---
        self.is_beating = True
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()

    def _heartbeat_loop(self):
        """Fa battere il cuore ogni 60 secondi, applicando il decadimento in RAM."""
        while self.is_beating:
            time.sleep(60)
            with self._lock:
                # Applica il decadimento (senza profilo dinamico per il background)
                self.state = self._apply_decay_logic(self.state, None)
                self._recalculate_mood()

    def _perform_migration(self):
        if OLD_HEART_FILE.exists() and self.avatar_name == "gemma":
            new_path = DATA_DIR / "heart_gemma.json"
            if not new_path.exists():
                try:
                    os.rename(OLD_HEART_FILE, new_path)
                    print(t("log.heart_migration_done"))
                except Exception as e:
                    print(t("log.heart_migration_error", error=str(e)))

    def get_state_for_save(self, dynamic_profile: Dict[str, Any] = None) -> Dict[str, Any]:
        """Restituisce lo stato attuale del cuore per il salvataggio da parte del Scribe."""
        with self._lock:
            self._apply_time_decay(dynamic_profile)  # [FIX BUG 6] Calcola il decadimento prima di salvare
            return self.state.copy()

    def force_save(self, dynamic_profile: Dict[str, Any] = None):
        """[FIX WINERROR 5] Salvataggio forzato su disco, usato dallo Scribe Thread in modo thread-safe."""
        with self._lock:
            self._apply_time_decay(dynamic_profile)
            self._save_state()

    def set_state_from_dict(self, new_state: Dict[str, Any]):
        """Aggiorna lo stato del cuore dalla RAM (usato dal Scribe all'avvio)."""
        with self._lock:
            self.state.update(new_state)
            # Assicuriamo che l'umore sia ricalcolato dopo un caricamento esterno
            self._recalculate_mood()
            self.state["ultimo_aggiornamento"] = time.time() # Aggiorna timestamp per evitare decadimento immediato

    def _get_default_state(self) -> Dict[str, Any]:
        return {
            "affetto": 50,
            "fiducia": 50,
            "rispetto": 50,
            "energia_sociale": 100,
            "eccitazione": 10,
            "gelosia": 0,
            "curiosità": 50,
            "vulnerabilità": 20,
            "complicità": 30,
            "stanchezza_mentale": 0,
            "felicità": 50,
            "tensione": 0,
            "prudenza": 50,  #[NUOVO v18.0] Progetto Jarvis
            "work_mode": False,  #[NUOVO v19.1] Modalità Lavoro (Focus)
            "sistema_endocrino": {
                "cortisolo": 50,
                "dopamina": 50,
                "ossitocina": 50
            },
            "umore_corrente": t("heart.moods.neutral"),
            "ultimo_aggiornamento": time.time(),
            "memoria_emotiva": list(),
        }

    def _load_state(self) -> Dict[str, Any]:
        if self.heart_file.exists():
            try:
                with open(self.heart_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default = self._get_default_state()
                    for key in default:
                        if key not in data:
                            data[key] = default[key]
                    return data
            except Exception as e:
                print(t("log.heart_load_error", name=self.avatar_name, error=str(e)))
        return self._get_default_state()

    def _save_state(self):
        with self._lock:
            self.state["ultimo_aggiornamento"] = time.time()
            # [FIX WINERROR 5] Usiamo un nome temporaneo univoco per evitare collisioni I/O a livello di OS
            temp_file = self.heart_file.with_suffix(f".tmp_{threading.get_ident()}")
            try:
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(self.state, f, indent=2, ensure_ascii=False)
                
                # [FIX WINERROR 5] Retry logic per aggirare i lock temporanei di Windows Defender o OneDrive
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        os.replace(temp_file, self.heart_file)
                        break
                    except PermissionError:
                        if attempt == max_retries - 1:
                            raise
                        time.sleep(0.1)
            except Exception as e:
                print(t("log.heart_save_error", error=str(e)))
            finally:
                # Pulizia garantita del file temporaneo
                if temp_file.exists():
                    try:
                        os.remove(temp_file)
                    except:
                        pass

    def _apply_decay_logic(self, state: Dict[str, Any], dynamic_profile: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Applica le leggi dell'Allostasi Emotiva a uno stato specifico.
        I limiti minimi (floors) e la velocità di decadimento sono calcolati dinamicamente
        basandosi sulla Local Supermemory (Profilo Dinamico).
        """
        now = time.time()
        last = state.get("ultimo_aggiornamento", now)
        delta_hours = (now - last) / 3600.0

        if delta_hours <= 0:
            return state

        # --- [NUOVO] CALCOLO ALLOSTASI (RESILIENZA E FLOORS) ---
        # Valori di base
        floor_affetto = 50
        floor_fiducia = 50
        floor_complicita = 50
        decay_multiplier = 1.0

        if dynamic_profile:
            stato_emotivo_utente = dynamic_profile.get("stato_emotivo_attuale", "").lower()
            fatti_statici = " ".join(dynamic_profile.get("fatti_statici",[])).lower()
            
            # Se il profilo indica un legame forte, alziamo i pavimenti emotivi
            if any(k in stato_emotivo_utente or k in fatti_statici for k in ["amore", "partner", "fidanzat", "sposat", "insieme"]):
                floor_affetto = 60
                floor_fiducia = 70
                floor_complicita = 50
                decay_multiplier = 0.5  # Le emozioni negative decadono più in fretta, le positive più lentamente

        # 1. Ricarica Energia Sociale (+15/ora)
        state["energia_sociale"] = min(
            100, state["energia_sociale"] + int(delta_hours * 15)
        )

        # 2. Recupero Stanchezza Mentale (-20/ora)
        state["stanchezza_mentale"] = max(
            0, state["stanchezza_mentale"] - int(delta_hours * 20 * (2.0 - decay_multiplier))
        )

        # 3. Decadimento Eccitazione (-2/ora, min 10)
        state["eccitazione"] = max(10, state["eccitazione"] - int(delta_hours * 2))

        # 4. Decadimento Gelosia (-5/ora)
        state["gelosia"] = max(0, state["gelosia"] - int(delta_hours * 5 * (2.0 - decay_multiplier)))

        # 5. Decadimento Tensione (-5/ora)
        state["tensione"] = max(0, state.get("tensione", 0) - int(delta_hours * 5 * (2.0 - decay_multiplier)))

        # 6. Ritorno all'equilibrio per Prudenza (verso 50)
        prudenza = state.get("prudenza", 50)
        if prudenza > 50:
            state["prudenza"] = max(50, prudenza - int(delta_hours * 5))
        elif prudenza < 50:
            state["prudenza"] = min(50, prudenza + int(delta_hours * 5))

        # 7. [NUOVO] Decadimento Allostatico per i Pilastri Positivi
        # Se sono sopra il floor, decadono lentamente verso il floor. Se sono sotto, restano lì.
        for vector, floor in[("affetto", floor_affetto), ("fiducia", floor_fiducia), ("complicità", floor_complicita)]:
            current_val = state.get(vector, 50)
            if current_val > floor:
                state[vector] = max(floor, current_val - int(delta_hours * 1 * decay_multiplier))

        # 8. [MODULO 3] Omeostasi del Sistema Endocrino (Ritorno a 50)
        if "sistema_endocrino" not in state:
            state["sistema_endocrino"] = {"cortisolo": 50, "dopamina": 50, "ossitocina": 50}
        
        for ormone in["cortisolo", "dopamina", "ossitocina"]:
            val_ormone = state["sistema_endocrino"].get(ormone, 50)
            if val_ormone > 50:
                state["sistema_endocrino"][ormone] = max(50, val_ormone - int(delta_hours * 15))
            elif val_ormone < 50:
                state["sistema_endocrino"][ormone] = min(50, val_ormone + int(delta_hours * 15))

        state["ultimo_aggiornamento"] = now
        return state

    def _apply_time_decay(self, dynamic_profile: Dict[str, Any] = None):
        """Applica decadimento all'Avatar principale."""
        with self._lock:
            self.state = self._apply_decay_logic(self.state, dynamic_profile)
            # Rimosso self._save_state() - il Scribe si occupa del salvataggio persistente

    def load_external_heart(self, file_path: Path) -> Dict[str, Any]:
        if not file_path.exists():
            return self._get_default_state()
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            heart_data = data.get("vettori_emotivi", self._get_default_state())
            heart_data = self._apply_decay_logic(heart_data)

            default = self._get_default_state()
            for key in default:
                if key not in heart_data:
                    heart_data[key] = default[key]

            return heart_data
        except Exception as e:
            print(t("log.heart_png_load_error", file=file_path.name, error=str(e)))
            return self._get_default_state()

    def save_external_heart(self, file_path: Path, heart_state: Dict[str, Any]):
        if not file_path.exists():
            return
        with self._lock:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    full_data = json.load(f)

                heart_state["ultimo_aggiornamento"] = time.time()
                full_data["vettori_emotivi"] = heart_state

                temp_file = file_path.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(full_data, f, indent=2, ensure_ascii=False)
                os.replace(temp_file, file_path)
            except Exception as e:
                print(t("log.heart_png_save_error", file=file_path.name, error=str(e)))

    # --- [NUOVO] MOTORI MATEMATICI DEL CUORE FLUIDO ---
    def _apply_asymptotic_delta(self, current: float, delta: float, vector_name: str) -> int:
        """Calcola il delta reale basato sulla curva asintotica e sull'inerzia del vettore."""
        heavy_vectors =["affetto", "fiducia", "rispetto", "complicità"]
        is_heavy = vector_name in heavy_vectors

        # Rimosso il malus artificiale: la curva asintotica è sufficiente a frenare la crescita
        # if is_heavy:
        #     delta = delta * 0.8

        if delta > 0:
            # Più si avvicina a 100, meno cresce
            available_room = 100.0 - current
            actual_delta = delta * (available_room / 100.0)
            # Garantiamo sempre almeno +1 se il delta originale era positivo
            if 0 < actual_delta < 1:
                actual_delta = 1.0
        elif delta < 0:
            # Più si avvicina a 0, meno cala
            available_room = current
            actual_delta = delta * (available_room / 100.0)
            # Garantiamo sempre almeno -1 se il delta originale era negativo
            if -1 < actual_delta < 0:
                actual_delta = -1.0
        else:
            actual_delta = 0

        new_val = current + actual_delta
        return int(max(0, min(100, round(new_val))))

    def _apply_interaction_decay(self, state: Dict[str, Any], stimulated_vectors: List[str]):
        """Decadimento per interazione: le emozioni volatili crollano se ignorate nel turno."""
        volatile_vectors = ["eccitazione", "tensione", "gelosia", "vulnerabilità"]
        for v in volatile_vectors:
            if v not in stimulated_vectors and v in state:
                # Crollo del 10% del valore attuale verso lo zero ad ogni turno ignorato
                state[v] = int(max(0, state[v] - (state[v] * 0.10)))

    def _check_catharsis(self, state: Dict[str, Any]) -> List[str]:
        """Innesca l'esplosione emotiva se un vettore volatile raggiunge il limite critico."""
        catharsis_events = list()
        
        if state.get("eccitazione", 0) >= 95:
            state["eccitazione"] = 20
            state["stanchezza_mentale"] = min(100, state.get("stanchezza_mentale", 0) + 30)
            state["affetto"] = min(100, state.get("affetto", 0) + 5) # Afterglow
            catharsis_events.append("Catarsi: L'eccitazione ha raggiunto il culmine ed è crollata, lasciando stanchezza e affetto.")

        if state.get("tensione", 0) >= 95:
            state["tensione"] = 10
            state["stanchezza_mentale"] = min(100, state.get("stanchezza_mentale", 0) + 40)
            state["vulnerabilità"] = min(100, state.get("vulnerabilità", 0) + 20)
            catharsis_events.append("Crollo Nervoso: La tensione è esplosa. Il personaggio è ora esausto e vulnerabile.")

        if state.get("gelosia", 0) >= 95:
            state["gelosia"] = 30
            state["fiducia"] = max(0, state.get("fiducia", 50) - 20)
            state["tensione"] = min(100, state.get("tensione", 0) + 30)
            catharsis_events.append("Esplosione di Gelosia: La rabbia possessiva ha consumato la fiducia e generato nuova tensione.")

        return catharsis_events

    def inject_hormone(self, hormone: str, amount: int):
        """[MODULO 3] Inietta un ormone nel sistema endocrino, alterando la chimica dell'Anima."""
        with self._lock:
            if "sistema_endocrino" not in self.state:
                self.state["sistema_endocrino"] = {"cortisolo": 50, "dopamina": 50, "ossitocina": 50}
            
            # --- [FIX BUG] ANTI-SPAM ORMONALE ---
            # Evita iniezioni continue dello stesso ormone (es. cortisolo da hardware alert)
            now = time.time()
            if not hasattr(self, "_last_hormone_injection"):
                self._last_hormone_injection = {}
            
            if hormone in self._last_hormone_injection:
                if now - self._last_hormone_injection[hormone] < 300:
                    return # Ignora iniezioni troppo ravvicinate (cooldown 300s)
            
            self._last_hormone_injection[hormone] = now
            # ------------------------------------
            
            current = self.state["sistema_endocrino"].get(hormone, 50)
            new_val = max(0, min(100, current + amount))
            self.state["sistema_endocrino"][hormone] = new_val
            
            self.log_msg(t("log.heart_hormone_injected", hormone=hormone.upper(), amount=amount, total=new_val))
            self._save_state()

    def _process_emotional_math(self, state: Dict[str, Any], impatti: Dict[str, int]) -> List[str]:
        """Core matematico unificato per Avatar e PNG."""
        desc_parts = list()
        stimulated_vectors = list(impatti.keys())

        # [MODULO 3] Lettura Livelli Ormonali
        endo = state.get("sistema_endocrino", {"cortisolo": 50, "dopamina": 50, "ossitocina": 50})
        cortisolo = endo.get("cortisolo", 50)
        dopamina = endo.get("dopamina", 50)
        ossitocina = endo.get("ossitocina", 50)

        # 1. Applica i delta asintotici con Moltiplicatori Endocrini
        for vettore, valore in impatti.items():
            if vettore in state:
                old_val = state[vettore]
                
                # Calcolo Moltiplicatore Ormonale
                moltiplicatore = 1.0
                
                if valore > 0:
                    if vettore in["affetto", "fiducia", "complicità", "rispetto"]:
                        moltiplicatore += (ossitocina - 50) / 100.0  # Ossitocina amplifica i legami
                        moltiplicatore -= (cortisolo - 50) / 100.0   # Cortisolo frena i legami
                    elif vettore in["eccitazione", "curiosità", "energia_sociale"]:
                        moltiplicatore += (dopamina - 50) / 100.0    # Dopamina amplifica l'energia
                else: # Valore negativo (danno emotivo)
                    if vettore in ["affetto", "fiducia", "complicità", "rispetto"]:
                        moltiplicatore += (cortisolo - 50) / 100.0   # Cortisolo amplifica i danni relazionali
                    elif vettore in["tensione", "gelosia", "vulnerabilità", "stanchezza_mentale"]:
                        moltiplicatore += (cortisolo - 50) / 100.0   # Cortisolo amplifica lo stress
                        moltiplicatore -= (ossitocina - 50) / 100.0  # Ossitocina mitiga lo stress

                # Sicurezza matematica: il moltiplicatore non inverte mai il segno
                moltiplicatore = max(0.1, moltiplicatore)
                valore_modificato = int(valore * moltiplicatore)

                # Calcolo asintotico con il valore modificato dagli ormoni
                state[vettore] = self._apply_asymptotic_delta(old_val, valore_modificato, vettore)
                
                diff = state[vettore] - old_val
                if diff != 0:
                    # [FIX BUG 05] Iniezione ormonale dinamica basata sulle emozioni
                    if diff > 0:
                        if vettore in["affetto", "complicità", "fiducia", "rispetto"]:
                            self.inject_hormone("ossitocina", diff)
                            self.inject_hormone("cortisolo", -diff) #[FIX] L'affetto e la fiducia abbassano attivamente lo stress
                        elif vettore in["eccitazione", "curiosità", "energia_sociale"]:
                            self.inject_hormone("dopamina", diff)
                        elif vettore in["tensione", "gelosia", "stanchezza_mentale"]:
                            self.inject_hormone("cortisolo", diff)

                    v_key = (
                        vettore.replace("curiosità", "curiosita")
                        .replace("vulnerabilità", "vulnerabilita")
                        .replace("complicità", "complicita")
                        .replace("energia_sociale", "energia")
                        .replace("stanchezza_mentale", "stanchezza")
                        .replace("felicità", "felicita")
                        .replace("prudenza", "prudenza")
                    )
                    vector_name = t(f"heart_dialog.vectors.{v_key}")
                    desc_parts.append(
                        t(
                            "heart_impact_format",
                            vector=vector_name,
                            value=f"{'+' if diff > 0 else ''}{diff}",
                        )
                    )

        # 2. Applica il decadimento per interazione (Emozioni volatili ignorate)
        self._apply_interaction_decay(state, stimulated_vectors)

        # 3. Controlla la Catarsi (Esplosioni emotive)
        catharsis_logs = self._check_catharsis(state)
        for c_log in catharsis_logs:
            desc_parts.append(f"[{c_log}]")

        state["energia_sociale"] = max(0, state.get("energia_sociale", 100) - 1)
        state["umore_corrente"] = self._calculate_mood_for_state(state)
        
        return desc_parts

    def apply_stimulus_to_file(
        self, file_path: Path, evento: str, impatti: Dict[str, int]
    ):
        state = self.load_external_heart(file_path)
        
        nome_evento = (
            t(evento)
            if evento.startswith("heart.") or evento.startswith("chat.")
            else evento
        )

        desc_parts = self._process_emotional_math(state, impatti)

        if desc_parts:
            self._add_memory_event_to_state(state, nome_evento, ", ".join(desc_parts))

        self.save_external_heart(file_path, state)

    def apply_emotional_contagion(self, file_path: Path, source_name: str, base_delta: int) -> int:
        """
        [NUOVO FASE 1.2] Applica un contagio emotivo (Tensione) calcolando la resistenza del bersaglio.
        Restituisce il delta effettivamente applicato.
        """
        state = self.load_external_heart(file_path)
        
        # Calcolo Resistenza basato sulla Personalità Dinamica (se presente nel file)
        # Poiché heart.json non contiene la personalità, assumiamo una resistenza base 0
        # a meno che non venga implementata una lettura incrociata. Per ora usiamo i vettori interni.
        rispetto = state.get("rispetto", 50)
        prudenza = state.get("prudenza", 50)
        
        # Se il personaggio è molto prudente o ha alto rispetto (calma), resiste meglio al panico
        resistance_factor = ((prudenza - 50) + (rispetto - 50)) / 100.0
        resistance_factor = max(0.0, min(0.8, resistance_factor)) # Max 80% di resistenza
        
        actual_delta = int(base_delta * (1.0 - resistance_factor))
        
        if actual_delta > 0:
            old_tension = state.get("tensione", 0)
            state["tensione"] = min(100, old_tension + actual_delta)
            
            if state["tensione"] != old_tension:
                evento = t("chat.log_contagion_event", source=source_name)
                self._add_memory_event_to_state(state, evento, f"Tensione: +{actual_delta}")
                self.save_external_heart(file_path, state)
                return actual_delta
                
        return 0

    def _calculate_mood_for_state(self, s: Dict[str, Any]) -> str:
        if s["energia_sociale"] < 15:
            return t("heart.moods.exhausted")
        elif s.get("stanchezza_mentale", 0) > 80:
            return t("heart.moods.saturated")
        elif s["rispetto"] < 30:
            return t("heart.moods.cold")
        elif s["eccitazione"] > 85:
            return t("heart.moods.provocative")
        elif s["gelosia"] > 75:
            return t("heart.moods.possessive")
        elif s["vulnerabilità"] > 80:
            return t("heart.moods.fragile")
        elif s["affetto"] > 85 and s["complicità"] > 80:
            return t("heart.moods.innamorata")
        elif s["affetto"] > 65 and s["fiducia"] > 70:
            return t("heart.moods.serene")
        elif s["affetto"] > 60:
            return t("heart.moods.affectionate")
        elif s["curiosità"] > 80:
            return t("heart.moods.inspired")
        elif s["affetto"] < 25:
            return t("heart.moods.detached")
        elif s["fiducia"] < 30:
            return t("heart.moods.distrustful")
        elif s["affetto"] > 70 and s["rispetto"] < 40:
            return t("heart.moods.hurt")
        elif s["eccitazione"] > 60 and s["vulnerabilità"] > 60:
            return t("heart.moods.needy")
        elif s["complicità"] > 70 and s["curiosità"] > 60:
            return t("heart.moods.playful")
        return t("heart.moods.neutral")

    def _add_memory_event_to_state(
        self, state: Dict[str, Any], evento: str, impatto_desc: str
    ):
        """Aggiunge un evento alla memoria emotiva di uno stato specifico."""
        entry = {
            "evento": evento,
            "impatto": impatto_desc,
            "timestamp": time.time(),
            "data_str": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        state.setdefault("memoria_emotiva", list()).append(entry)
        if len(state["memoria_emotiva"]) > 15:
            state["memoria_emotiva"].pop(0)

    def _add_memory_event(self, evento: str, impatto_desc: str):
        """Aggiunge un evento alla memoria emotiva dell'Avatar principale."""
        self._add_memory_event_to_state(self.state, evento, impatto_desc)

    def apply_stimulus(self, evento: str, impatti: Dict[str, int]):
        with self._lock:
            self._apply_time_decay()  # Decadimento temporale (per pause lunghe)
            
            nome_evento = (
                t(evento)
                if evento.startswith("heart.") or evento.startswith("chat.")
                else evento
            )

            desc_parts = self._process_emotional_math(self.state, impatti)

            if desc_parts:
                self._add_memory_event(nome_evento, ", ".join(desc_parts))

    def apply_dream_impact(self, core_memories: List[Dict[str, Any]]):
        total_impact = {
            "affetto": 0,
            "fiducia": 0,
            "vulnerabilità": 0,
            "complicità": 0,
            "curiosità": 0,
        }
        for mem in core_memories:
            emotion = mem.get("emotion", "").lower()
            intensity = mem.get("intensity", 1)
            if "gioia" in emotion or "amore" in emotion:
                total_impact["affetto"] += intensity
                total_impact["complicità"] += intensity // 2
            elif "tristezza" in emotion or "dolore" in emotion:
                total_impact["vulnerabilità"] += intensity
                total_impact["affetto"] += intensity // 4
            elif "nostalgia" in emotion:
                total_impact["complicità"] += intensity
                total_impact["vulnerabilità"] += intensity // 2
            elif "paura" in emotion:
                total_impact["fiducia"] -= intensity // 2
                total_impact["vulnerabilità"] += intensity
            elif "scoperta" in emotion or "curiosità" in emotion:
                total_impact["curiosità"] += intensity
                total_impact["complicità"] += intensity // 2
        self.apply_stimulus(t("heart.events.dream_impact"), total_impact)

    def _recalculate_mood(self):
        self.state["umore_corrente"] = self._calculate_mood_for_state(self.state)

    def get_heart_status(self, dynamic_profile: Dict[str, Any] = None) -> str:
        self._apply_time_decay(dynamic_profile)  # [FIX BUG 6] Calcola il decadimento prima di leggere lo stato
        s = self.state
        relazionali = t(
            "heart.status.relational",
            affetto=s["affetto"],
            fiducia=s["fiducia"],
            rispetto=s["rispetto"],
            complicita=s["complicità"],
        )
        istintivi = t(
            "heart.status.instinctive",
            eccitazione=s["eccitazione"],
            gelosia=s["gelosia"],
            vulnerabilita=s["vulnerabilità"],
            curiosita=s["curiosità"],
        )
        operativi = t(
            "heart.status.operational",
            energia=s["energia_sociale"],
            stanchezza=s["stanchezza_mentale"],
            prudenza=s.get("prudenza", 50),
        )

        memory_list = [e["evento"] for e in s["memoria_emotiva"][-3:]]
        memory_str = ", ".join(memory_list) if memory_list else t("heart.status.quiet")

        status = (
            f"{t('heart.status.title', name=self.avatar_name.upper())}\n"
            f"{t('heart.status.current_mood', mood=s['umore_corrente'])}\n"
            f"{relazionali}\n"
            f"{istintivi}\n"
            f"{operativi}\n"
            f"{t('heart.status.recent_memory', memory=memory_str)}\n"
            "-------------------------------------------"
        )
        return status

    def get_emotional_db(self) -> List[Dict[str, Any]]:
        return EMOTIONAL_EVENTS_DB

    def log_msg(self, msg: str):
        print(t("log.heart_generic_log", msg=msg))

    def update_hardware_mood(self, cpu_percent: float, ram_percent: float):
        """
        [AGGIORNATO v19.1] Mappa il carico hardware sui vettori emotivi.
        Implementa Proposte 2+3+4: Work Mode e Ricalibrazione Semantica (Focus).
        """
        with self._lock:
            is_work_mode = self.state.get("work_mode", False)

            # Se Work Mode è attivo, IGNORA lo stress hardware (Proposta 4)
            if is_work_mode:
                # In Work Mode, CPU alta = Focus Produttivo (Proposta 2)
                if cpu_percent > 80.0:
                    # Aumenta energia sociale (soddisfazione lavoro) invece di stanchezza
                    self.state["energia_sociale"] = min(
                        100, self.state.get("energia_sociale", 0) + 1
                    )
                return

            # Logica Standard (se NON in Work Mode)
            if cpu_percent > 85.0:
                #[FIX CRITICO] Disattivato l'aumento di tensione e stanchezza da hardware.
                # Lo stress ora deriva ESCLUSIVAMENTE dalla conversazione con l'utente.
                pass
            elif cpu_percent < 30.0:
                pass

            if ram_percent > 90.0:
                # Manteniamo solo un lieve senso di vulnerabilità se la RAM è satura (rischio crash)
                self.state["vulnerabilità"] = min(
                    100, self.state.get("vulnerabilità", 0) + 2
                )

            self._recalculate_mood()
            self._save_state()

    def adjust_prudenza(self, feedback_positivo: bool):
        """
        [NUOVO v18.0] Regola la soglia di iniziativa in base al feedback dell'utente.
        """
        with self._lock:
            current = self.state.get("prudenza", 50)
            # [FIX v3.4] Allineamento namespace traduzioni
            v_name = t("heart_dialog.vectors.prudenza")
            if feedback_positivo:
                # Diventa più audace (prudenza scende)
                self.state["prudenza"] = max(10, current - 15)
                self._add_memory_event(
                    t("heart.events.initiative_appreciated"), f"{v_name}: -15"
                )
            else:
                # Diventa più timida (prudenza sale)
                self.state["prudenza"] = min(90, current + 25)
                self._add_memory_event(
                    t("heart.events.initiative_rejected"), f"{v_name}: +25"
                )
            self._save_state()

    def set_prudenza(self, value: int):
        """[NUOVO v19.1] Imposta manualmente il livello di prudenza."""
        with self._lock:
            self.state["prudenza"] = max(0, min(100, value))
            self._save_state()

    def set_work_mode(self, enabled: bool):
        """[NUOVO v19.1] Attiva/Disattiva la modalità lavoro (Focus)."""
        with self._lock:
            self.state["work_mode"] = enabled
            self._save_state()
