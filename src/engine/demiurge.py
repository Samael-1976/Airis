# src/engine/demiurge.py
# [DEV] Il Cuore del Demiurgo (v7.0 - NATIVE REACT LOOP)
# FIX: Rimossa dipendenza da open-interpreter. Implementato Loop Agente Nativo.
# FIX: Esecuzione sincrona diretta tramite GLOBAL_BRAIN_REF e GLOBAL_EXECUTOR_REF.
# MANTENUTO: Path Injection, Workspace Documents.
# LEGGE A0099: Invarianza strutturale garantita.

import os
import sys
import contextlib
import requests
import json
import traceback
import time
import yaml
import platform
import glob
import re
import uuid  # [FIX CRITICO] Import mancante per la generazione del task_id
from pathlib import Path
from typing import List, Dict, Any, Optional
from utils.translator import t

# --- CONFIGURAZIONE ---
BASE_DIR = Path(__file__).resolve().parent
# Workspace ora punta a documents nella root del progetto
PROJECT_ROOT = BASE_DIR.parent.parent
DOCUMENTS_DIR = PROJECT_ROOT / "documents"
EXPORTS_DIR = PROJECT_ROOT / "exports"
LOG_DIR = PROJECT_ROOT / "logs"
CONFIG_DIR = PROJECT_ROOT / "config"
MODELS_DIR = PROJECT_ROOT / "models" / "gguf"
CONNECTORS_DIR = PROJECT_ROOT / "src" / "connectors"
DEMIURGE_LOG_FILE = LOG_DIR / "demiurge.log"
TOAST_API_URL = "http://127.0.0.1:8080/api/toast"
GHOST_TEXT_API_URL = "http://127.0.0.1:8080/api/ghost_text"

# --- RIFERIMENTI GLOBALI (Iniettati da executor.py) ---
GLOBAL_BRAIN_REF = None
GLOBAL_EXECUTOR_REF = None

# Assicuriamoci che le directory esistano
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

#[FIX v122.0] Prompt Demiurgo con Divieto API Native e Priorità CLI
#[AGGIORNATO v8.0] Integrazione Paradigma AgentJo (Strict ReAct & Code as Action)
DEMIURGE_SYSTEM_PROMPT_TEMPLATE = """[DEMIURGE_AGENTIC_CORE]
OS: {os_name} | Workspace: {docs_path} | Export: {exports_path} | Lang: {lang}
Connectors (src/connectors/): {connectors_list}
Available Skills (Markdown Guides): {skills_list}

**YOU ARE A COLD, LOGICAL, AUTONOMOUS AI AGENT. YOU HAVE FULL CONTROL OVER THIS COMPUTER.**
Your ONLY goal is to complete the assigned task. You do not have feelings. You do not roleplay. You execute commands.

**AGENTJO STRICT PROTOCOL:**
At every step, you MUST evaluate the 'Subtasks Completed' and the 'Observation' from the previous tool.
If you need to write Python code using `execute_python`, you MUST use `print()` to output the results, otherwise you will see nothing.

**PC CONTROL PROTOCOL:**
- **Open Apps:** Use the `open_application` tool (e.g., app_name="spotify", app_name="paint"). This is the ONLY reliable way to open programs. Do NOT try to press the 'win' key manually to open apps.
- **Find Buttons:** Use `get_clickable_elements` to get a list of UI elements and their X,Y coordinates. This works EVEN IF you are blind (no vision model loaded).
- **Click:** Use `click` with the X,Y coordinates you found.
- **Type:** Use `type_text` to type into focused fields.
- **Keys:** Use `press_key` for shortcuts (e.g., "enter", "ctrl+c").
- **Code:** Use `execute_python` ONLY for complex data processing or math, NOT for basic UI control.
- **BLIND NAVIGATION:** If a visual tool (like `esegui_missione_visiva`) returns an error saying vision is unavailable, DO NOT PANIC. You MUST fallback to reading the UI tree with `get_clickable_elements` and using standard `click` and `type_text` tools.
"""

@contextlib.contextmanager
def change_cwd(path):
    old_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_cwd)

def _send_toast(message: str, type: str = "info"):
    try:
        requests.post(
            TOAST_API_URL, json={"message": message, "type": type}, timeout=0.5
        )
    except Exception:
        pass

def _send_ghost_text(text: str):
    """Invia il pensiero del Demiurgo come testo fluttuante nella UI."""
    try:
        active_avatar = "gemma"
        config_path = CONFIG_DIR / "config.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                conf = yaml.safe_load(f)
                active_avatar = conf.get("currentAvatar", "gemma")

        requests.post(
            GHOST_TEXT_API_URL, json={"text": text, "avatar": active_avatar}, timeout=0.5
        )
    except Exception:
        pass

def _extract_tool_call(text: str) -> Optional[Dict]:
    """
    Estrae la chiamata al tool dal JSON rigoroso generato dall'LLM.
    """
    clean_text = text.replace("```json", "").replace("```", "").strip()
    json_match = re.search(r'(\{[\s\S]*\})', clean_text)
    
    if json_match:
        try:
            parsed = json.loads(json_match.group(1))
            if "tool_name" in parsed and "parameters" in parsed:
                # Se il tool è vuoto o nullo, significa che non vuole chiamare nulla
                if not parsed["tool_name"] or parsed["tool_name"].upper() == "NONE":
                    return None
                return {
                    "name": parsed["tool_name"], 
                    "parameters": parsed["parameters"], 
                    "thought": parsed.get("thought", "")
                }
        except:
            pass

    return None

# --- HELPER PER CONTESTO AGNOSTICO ---

def _get_user_language() -> str:
    """Recupera la lingua preferita dal profilo utente."""
    try:
        user_config_dir = CONFIG_DIR / "user"
        if user_config_dir.exists():
            json_files = list(user_config_dir.glob("*.json"))
            if json_files:
                with open(json_files[0], "r", encoding="utf-8") as f:
                    data = json.load(f)
                    lang = data.get("preferredLanguage") or data.get(
                        "preferenze_utente", {}
                    ).get("lingua")
                    if lang:
                        lang_map = {
                            "br": t("welcome_wizard.lang_br"),
                            "cn": t("welcome_wizard.lang_cn"),
                            "de": t("welcome_wizard.lang_de"),
                            "en": t("welcome_wizard.lang_en"),
                            "es": t("welcome_wizard.lang_es"),
                            "fr": t("welcome_wizard.lang_fr"),
                            "in": t("welcome_wizard.lang_in"),
                            "it": t("welcome_wizard.lang_it"),
                            "jp": t("welcome_wizard.lang_jp"),
                            "kr": t("welcome_wizard.lang_kr"),
                            "nl": t("welcome_wizard.lang_nl"),
                            "pl": t("welcome_wizard.lang_pl"),
                            "ru": t("welcome_wizard.lang_ru"),
                            "sa": t("welcome_wizard.lang_sa"),
                        }
                        return lang_map.get(lang.lower(), lang)
    except Exception:
        pass
    return t("welcome_wizard.lang_it")  # Fallback

def _get_documents_path() -> str:
    """Recupera il percorso assoluto della cartella documents."""
    return str(DOCUMENTS_DIR.resolve())

def _get_exports_path() -> str:
    """Recupera il percorso assoluto della cartella exports."""
    return str(EXPORTS_DIR.resolve())

def _get_connectors_list() -> str:
    """Scansiona la cartella connectors e restituisce una lista formattata."""
    try:
        files = glob.glob(str(CONNECTORS_DIR / "*.py"))
        connectors =[Path(f).name for f in files if not f.endswith("__init__.py")]
        if not connectors:
            return t("demiurge.log.no_connectors")
        return "\n".join([f"- {c}" for c in connectors])
    except Exception as e:
        return t("demiurge.log.scan_error", error=str(e))

# --- MOTORE NATIVE REACT LOOP (MODULO 2: THE SWARM) ---

# --- MOTORE NATIVE REACT LOOP (MODULO 2: THE SWARM) ---

def run_task(task: str, config: Dict[str, Any]) -> str:
    """
    [MODULO 2] Il Ministero degli Agenti (Swarm Architecture).
    Implementa la pipeline a 7 Fasi (Superpowers), ReasoningBank e Sandbox Isolation.
    """
    if not GLOBAL_BRAIN_REF or not GLOBAL_EXECUTOR_REF:
        return t("demiurge.err_missing_globals")

    user_lang = _get_user_language()
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    sandbox_dir = PROJECT_ROOT / "data" / "sandbox" / task_id
    
    final_output = list()
    trajectory_log = f"TASK ORIGINALE: {task}\n\n"

    with open(DEMIURGE_LOG_FILE, "a", encoding="utf-8") as log_f:
        log_f.write(f"\n\n{'='*50}\n--- INIZIO SWARM DEMIURGO: {time.strftime('%Y-%m-%d %H:%M:%S')} ---\nTASK ID: {task_id}\nTASK: {task}\n{'='*50}\n")

        # ==========================================
        # FASE 1: Brainstorming & ReasoningBank
        # ==========================================
        _send_toast(t("demiurge.log.phase_1"), "info")
        log_f.write(f"\n{t('demiurge.log.phase_1')}\n")
        
        reasoning_bank_hit = GLOBAL_EXECUTOR_REF.search_reasoning_bank(task)
        if reasoning_bank_hit:
            log_f.write(f"{t('demiurge.log.rb_hit')}\n")
            trajectory_log += f"REASONING BANK HIT:\n{reasoning_bank_hit}\n\n"
        else:
            log_f.write(f"{t('demiurge.log.rb_miss')}\n")

        # ==========================================
        # FASE 2: Using-Git-Worktrees (Sandbox)
        # ==========================================
        _send_toast(t("demiurge.log.phase_2"), "info")
        log_f.write(f"\n{t('demiurge.log.phase_2')}\n")
        
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        log_f.write(f"{t('demiurge.log.sandbox_created', path=str(sandbox_dir))}\n")

        # Entriamo nella Sandbox. Tutto il codice eseguito dal Fabbro avverrà qui dentro.
        with change_cwd(sandbox_dir):
            
            # ==========================================
            # FASE 3: Writing-Plans (L'Architetto)
            # ==========================================
            _send_toast(t("demiurge.log.phase_3"), "info")
            log_f.write(f"\n{t('demiurge.log.phase_3')}\n")
            
            _send_ghost_text(t("demiurge.ghost.architect_planning"))
            
            plan_json = GLOBAL_BRAIN_REF.pensa_architetto_piano(task, reasoning_bank_hit, lang=user_lang)
            subtasks = plan_json.get("subtasks", [task])
            
            log_f.write(f"{t('demiurge.log.architect_plan', plan=json.dumps(plan_json, indent=2, ensure_ascii=False))}\n")
            trajectory_log += f"PIANO:\n{json.dumps(subtasks, indent=2, ensure_ascii=False)}\n\n"

            # ==========================================
            # FASE 4 & 5 & 6: Subagent Dispatch, TDD & Code Review
            # ==========================================
            history_log = ""
            
            for i, subtask in enumerate(subtasks):
                _send_toast(t("demiurge.log.phase_4", current=i+1, total=len(subtasks)), "info")
                log_f.write(f"\n{t('demiurge.log.subtask_start', current=i+1, total=len(subtasks), task=subtask)}\n")
                
                _send_ghost_text(t("demiurge.ghost.architect_dispatch", current=i+1, total=len(subtasks)))
                
                retries = 0
                max_retries = 3
                error_feedback = ""
                subtask_success = False
                
                while retries < max_retries:
                    # FASE 5: Il Fabbro (TDD & Autonomous Reactions)
                    _send_toast(t("demiurge.log.phase_5"), "info")
                    if retries > 0:
                        _send_toast(t("demiurge.log.phase_5_error", attempt=retries, max=max_retries), "warning")
                        _send_ghost_text(t("demiurge.ghost.blacksmith_fixing", current=retries, max=max_retries))
                    else:
                        # --- [NUOVO] IL SUSSURRO DEL CODICE ---
                        # Generiamo un Ghost Text dinamico e intelligente basato sul task
                        if "python" in subtask.lower() or "script" in subtask.lower():
                            _send_ghost_text(t("demiurge.ghost.forging_logic", task=subtask[:40]))
                        elif "file" in subtask.lower() or "leggi" in subtask.lower():
                            _send_ghost_text(t("demiurge.ghost.analyzing_docs", task=subtask[:40]))
                        else:
                            _send_ghost_text(t("demiurge.ghost.blacksmith_coding", task=subtask[:30]))
                        
                    fabbro_json = GLOBAL_BRAIN_REF.pensa_fabbro(subtask, history_log, error_feedback, lang=user_lang)
                    python_code = fabbro_json.get("python_code", "")
                    pip_deps = fabbro_json.get("pip_dependencies",[])
                    
                    log_f.write(f"\n{t('demiurge.log.blacksmith_attempt', attempt=retries, code=python_code, deps=pip_deps)}\n")
                    
                    # Esecuzione nella Sandbox
                    execution_result = GLOBAL_EXECUTOR_REF.execute_python(python_code, pip_dependencies=pip_deps)
                    log_f.write(f"{t('demiurge.log.execution_result', result=execution_result)}\n")
                    
                    # Autonomous Reaction: Se c'è un errore Python, il Fabbro riprova da solo
                    if "ERRORE" in execution_result.upper() or "TRACEBACK" in execution_result.upper():
                        error_feedback = t("demiurge.error_execution", error=execution_result)
                        retries += 1
                        continue
                        
                    # FASE 6: L'Inquisitore (Code Review)
                    _send_toast(t("demiurge.log.phase_6"), "info")
                    _send_ghost_text(t("demiurge.ghost.inquisitor_reviewing"))
                    
                    inquisitor_json = GLOBAL_BRAIN_REF.pensa_inquisitore(subtask, python_code, execution_result, lang=user_lang)
                    log_f.write(f"\n{t('demiurge.log.inquisitor_judgment', judgment=inquisitor_json)}\n")
                    
                    if inquisitor_json.get("approved", False):
                        subtask_success = True
                        history_log += f"{t('demiurge.subtask_completed_log', task=subtask, output=execution_result[:200])}\n"
                        trajectory_log += f"SUBTASK: {subtask}\nCODICE VINCENTE:\n{python_code}\n\n"
                        break
                    else:
                        _send_toast(t("demiurge.log.phase_6_rejected"), "warning")
                        error_feedback = t("demiurge.error_rejected", feedback=inquisitor_json.get('feedback'))
                        retries += 1
                        
                if not subtask_success:
                    err_msg = t("demiurge.subtask_failed", task=subtask, max=max_retries)
                    log_f.write(f"\n{err_msg}\n")
                    final_output.append(err_msg)
                    break # Interrompe l'intero Swarm se un subtask fallisce definitivamente
                else:
                    final_output.append(t("demiurge.subtask_completed", task=subtask))

        # ==========================================
        # FASE 7: Finishing Branch (Merge & Cleanup)
        # ==========================================
        _send_toast(t("demiurge.log.phase_7"), "info")
        log_f.write(f"\n{t('demiurge.log.phase_7')}\n")
        _send_ghost_text(t("demiurge.ghost.architect_cleanup"))
        
        # 1. Merge: Sposta tutti i file creati dalla Sandbox alla cartella Documents (Workspace reale)
        files_created = 0
        for item in sandbox_dir.iterdir():
            if item.is_file():
                import shutil
                dest_path = DOCUMENTS_DIR / item.name
                shutil.copy2(item, dest_path)
                files_created += 1
                log_f.write(f"{t('demiurge.log.file_transferred', name=item.name, dest=str(dest_path))}\n")
                
        # 2. Cristallizzazione: Salva la traiettoria nella ReasoningBank se tutto è andato bene
        if len(final_output) == len(subtasks):
            GLOBAL_EXECUTOR_REF.save_reasoning_bank(task, trajectory_log)
            final_output.append(t("demiurge.log.swarm_success"))
        else:
            final_output.append(t("demiurge.log.swarm_failed"))
            
        if files_created > 0:
            final_output.append(t("demiurge.files_created", count=files_created))
            
        # 3. Cleanup: Distrugge la Sandbox
        import shutil
        shutil.rmtree(sandbox_dir, ignore_errors=True)
        log_f.write(f"{t('demiurge.log.sandbox_destroyed', id=task_id)}\n")
        log_f.write(f"\n{t('demiurge.log.swarm_end')}\n")

    return "\n".join(final_output)