# src/update_tool_descriptions.py
# [DEV] Il Glossario del Demiurgo (v1.0)
# Aggiorna massivamente le descrizioni dei tool in src/tools/ con testi specifici e significativi.
# Questo aiuta il Router (Regista) a scegliere lo strumento corretto.

import json
import os
from pathlib import Path
from utils.translator import t

# Configurazione Percorsi
SCRIPT_DIR = Path(__file__).parent.resolve()
TOOLS_DIR = SCRIPT_DIR / "tools"

# Mappa delle Descrizioni Specifiche
# Key: nome del file (senza .json) -> Value: Nuova descrizione
TOOL_DESCRIPTIONS = {
    # --- VISIONE & INTERAZIONE ---
    "analizza_e_agisci": t("update_tool_descriptions.tools.analizza_e_agisci"),
    "analizza_video": t("update_tool_descriptions.tools.analizza_video"),
    "click": t("update_tool_descriptions.tools.click"),
    "click_on_grid": t("update_tool_descriptions.tools.click_on_grid"),
    "click_text": t("update_tool_descriptions.tools.click_text"),
    "confronta_immagini": t("update_tool_descriptions.tools.confronta_immagini"),
    "control_window": t("update_tool_descriptions.tools.control_window"),
    "crea_da_immagini": t("update_tool_descriptions.tools.crea_da_immagini"),
    "descrivi_immagine_con_pan_scan": t(
        "update_tool_descriptions.tools.descrivi_immagine_con_pan_scan"
    ),
    "detect_screen_change": t("update_tool_descriptions.tools.detect_screen_change"),
    "double_click": t("update_tool_descriptions.tools.double_click"),
    "draw_shape": t("update_tool_descriptions.tools.draw_shape"),
    "get_avatar_visual_description": t(
        "update_tool_descriptions.tools.get_avatar_visual_description"
    ),
    "interagisci_con_interfaccia": t(
        "update_tool_descriptions.tools.interagisci_con_interfaccia"
    ),
    "locate_and_click": t("update_tool_descriptions.tools.locate_and_click"),
    "move_mouse": t("update_tool_descriptions.tools.move_mouse"),
    "press_key": t("update_tool_descriptions.tools.press_key"),
    "read_screen_area": t("update_tool_descriptions.tools.read_screen_area"),
    "salva_analisi_visiva": t("update_tool_descriptions.tools.salva_analisi_visiva"),
    "take_screenshot": t("update_tool_descriptions.tools.take_screenshot"),
    "trigger_visual_effect": t("update_tool_descriptions.tools.trigger_visual_effect"),
    "type_text": t("update_tool_descriptions.tools.type_text"),
    # --- AUDIO & VOCE ---
    "analizza_emozione_voce": t(
        "update_tool_descriptions.tools.analizza_emozione_voce"
    ),
    "analizza_stato_vitale": t("update_tool_descriptions.tools.analizza_stato_vitale"),
    "convert_audio_to_wav": t("update_tool_descriptions.tools.convert_audio_to_wav"),
    "genera_voce": t("update_tool_descriptions.tools.genera_voce"),
    "interprete_multilingua": t(
        "update_tool_descriptions.tools.interprete_multilingua"
    ),
    "transcribe_audio": t("update_tool_descriptions.tools.transcribe_audio"),
    # --- SISTEMA & FILE ---
    "delete_file": t("update_tool_descriptions.tools.delete_file"),
    "edit_file_replace": t("update_tool_descriptions.tools.edit_file_replace"),
    "find_files": t("update_tool_descriptions.tools.find_files"),
    "get_project_structure": t("update_tool_descriptions.tools.get_project_structure"),
    "get_system_health": t("update_tool_descriptions.tools.get_system_health"),
    "leggi_contenuto_da_percorso": t(
        "update_tool_descriptions.tools.leggi_contenuto_da_percorso"
    ),
    "leggi_documento": t("update_tool_descriptions.tools.leggi_documento"),
    "list_files": t("update_tool_descriptions.tools.list_files"),
    "perform_factory_reset": t("update_tool_descriptions.tools.perform_factory_reset"),
    "read_file": t("update_tool_descriptions.tools.read_file"),
    "run_system_command": t("update_tool_descriptions.tools.run_system_command"),
    "write_file": t("update_tool_descriptions.tools.write_file"),
    # --- WEB & RICERCA ---
    "fetch_wikipedia_page": t("update_tool_descriptions.tools.fetch_wikipedia_page"),
    "search_wikipedia": t("update_tool_descriptions.tools.search_wikipedia"),
    "web_fetch": t("update_tool_descriptions.tools.web_fetch"),
    "web_search": t("update_tool_descriptions.tools.web_search"),
    # --- MEMORIA & GDR ---
    "applica_azione_di_mondo": t(
        "update_tool_descriptions.tools.applica_azione_di_mondo"
    ),
    "archive_character_file": t(
        "update_tool_descriptions.tools.archive_character_file"
    ),
    "avvia_flashback": t("update_tool_descriptions.tools.avvia_flashback"),
    "clean_world_status_transients": t(
        "update_tool_descriptions.tools.clean_world_status_transients"
    ),
    "crea_file_di_mondo": t("update_tool_descriptions.tools.crea_file_di_mondo"),
    "create_event_and_reminder": t(
        "update_tool_descriptions.tools.create_event_and_reminder"
    ),
    "create_reminder": t("update_tool_descriptions.tools.create_reminder"),
    "create_session_memory": t("update_tool_descriptions.tools.create_session_memory"),
    "export_package": t("update_tool_descriptions.tools.export_package"),
    "import_package": t("update_tool_descriptions.tools.import_package"),
    "override_heart_metric": t("update_tool_descriptions.tools.override_heart_metric"),
    "read_heart_metrics": t("update_tool_descriptions.tools.read_heart_metrics"),
    "save_character_file": t("update_tool_descriptions.tools.save_character_file"),
    "save_profile_file": t("update_tool_descriptions.tools.save_profile_file"),
    "save_to_memory": t("update_tool_descriptions.tools.save_to_memory"),
    "search_in_memory": t("update_tool_descriptions.tools.search_in_memory"),
    "simula_scenari": t("update_tool_descriptions.tools.simula_scenari"),
    "sync_pg_name_to_all_gdrs": t(
        "update_tool_descriptions.tools.sync_pg_name_to_all_gdrs"
    ),
    "toggle_character_in_world": t(
        "update_tool_descriptions.tools.toggle_character_in_world"
    ),
    "update_character_sheet": t(
        "update_tool_descriptions.tools.update_character_sheet"
    ),
    "update_status_json_partial": t(
        "update_tool_descriptions.tools.update_status_json_partial"
    ),
    "write_dream_journal": t("update_tool_descriptions.tools.write_dream_journal"),
    "write_genesis_diary_entry": t(
        "update_tool_descriptions.tools.write_genesis_diary_entry"
    ),
    # --- GENERAZIONE AI ---
    "demiurgo": t("update_tool_descriptions.tools.demiurgo"),
    "generate_dalle3": t("update_tool_descriptions.tools.generate_dalle3"),
    "generate_flux": t("update_tool_descriptions.tools.generate_flux"),
    "generate_sora2": t("update_tool_descriptions.tools.generate_sora2"),
    "generate_veo3": t("update_tool_descriptions.tools.generate_veo3"),
    "invia_immagine": t("update_tool_descriptions.tools.invia_immagine"),
    "invia_video": t("update_tool_descriptions.tools.invia_video"),
    # --- CONNETTORI ESTERNI (GOOGLE) ---
    "create_calendar_event": t("update_tool_descriptions.tools.create_calendar_event"),
    "create_task": t("update_tool_descriptions.tools.create_task"),
    "gmail_manager": t("update_tool_descriptions.tools.gmail_manager"),
    "google_calendar": t("update_tool_descriptions.tools.google_calendar"),
    "google_contacts": t("update_tool_descriptions.tools.google_contacts"),
    "google_drive": t("update_tool_descriptions.tools.google_drive"),
    "google_photos": t("update_tool_descriptions.tools.google_photos"),
    "google_sheets": t("update_tool_descriptions.tools.google_sheets"),
    "google_tasks": t("update_tool_descriptions.tools.google_tasks"),
    "list_calendar_events": t("update_tool_descriptions.tools.list_calendar_events"),
    "list_drive_files": t("update_tool_descriptions.tools.list_drive_files"),
    "list_photo_albums": t("update_tool_descriptions.tools.list_photo_albums"),
    "list_task_lists": t("update_tool_descriptions.tools.list_task_lists"),
    "list_tasks": t("update_tool_descriptions.tools.list_tasks"),
    "read_emails": t("update_tool_descriptions.tools.read_emails"),
    "read_google_sheet": t("update_tool_descriptions.tools.read_google_sheet"),
    "search_contacts": t("update_tool_descriptions.tools.search_contacts"),
    "search_photos": t("update_tool_descriptions.tools.search_photos"),
    "send_email": t("update_tool_descriptions.tools.send_email"),
    "write_google_sheet": t("update_tool_descriptions.tools.write_google_sheet"),
    # --- CONNETTORI ESTERNI (MICROSOFT) ---
    "create_todo_task": t("update_tool_descriptions.tools.create_todo_task"),
    "excel_manager": t("update_tool_descriptions.tools.excel_manager"),
    "list_onedrive_files": t("update_tool_descriptions.tools.list_onedrive_files"),
    "list_todo_lists": t("update_tool_descriptions.tools.list_todo_lists"),
    "list_todo_tasks": t("update_tool_descriptions.tools.list_todo_tasks"),
    "microsoft_todo": t("update_tool_descriptions.tools.microsoft_todo"),
    "onedrive_manager": t("update_tool_descriptions.tools.onedrive_manager"),
    "outlook_manager": t("update_tool_descriptions.tools.outlook_manager"),
    "read_excel_sheet": t("update_tool_descriptions.tools.read_excel_sheet"),
    "read_outlook_emails": t("update_tool_descriptions.tools.read_outlook_emails"),
    "send_outlook_email": t("update_tool_descriptions.tools.send_outlook_email"),
    "write_excel_sheet": t("update_tool_descriptions.tools.write_excel_sheet"),
    # --- CONNETTORI ESTERNI (SOCIAL & COMMS) ---
    "discord_bot": t("update_tool_descriptions.tools.discord_bot"),
    "get_hot_reddit_posts": t("update_tool_descriptions.tools.get_hot_reddit_posts"),
    "post_tweet": t("update_tool_descriptions.tools.post_tweet"),
    "reddit_manager": t("update_tool_descriptions.tools.reddit_manager"),
    "send_discord_message": t("update_tool_descriptions.tools.send_discord_message"),
    "send_slack_message": t("update_tool_descriptions.tools.send_slack_message"),
    "send_sms": t("update_tool_descriptions.tools.send_sms"),
    "send_telegram_message": t("update_tool_descriptions.tools.send_telegram_message"),
    "send_whatsapp_message": t("update_tool_descriptions.tools.send_whatsapp_message"),
    "slack_bot": t("update_tool_descriptions.tools.slack_bot"),
    "sms_sender": t("update_tool_descriptions.tools.sms_sender"),
    "submit_reddit_post": t("update_tool_descriptions.tools.submit_reddit_post"),
    "telegram_bot": t("update_tool_descriptions.tools.telegram_bot"),
    "twitter_manager": t("update_tool_descriptions.tools.twitter_manager"),
    "whatsapp_sender": t("update_tool_descriptions.tools.whatsapp_sender"),
    # --- CONNETTORI ESTERNI (PROJECTS & DEV) ---
    "asana_manager": t("update_tool_descriptions.tools.asana_manager"),
    "create_asana_task": t("update_tool_descriptions.tools.create_asana_task"),
    "create_github_issue": t("update_tool_descriptions.tools.create_github_issue"),
    "create_jira_issue": t("update_tool_descriptions.tools.create_jira_issue"),
    "create_notion_page": t("update_tool_descriptions.tools.create_notion_page"),
    "create_trello_card": t("update_tool_descriptions.tools.create_trello_card"),
    "git_workflow": t("update_tool_descriptions.tools.git_workflow"),
    "github_manager": t("update_tool_descriptions.tools.github_manager"),
    "gitlab_manager": t("update_tool_descriptions.tools.gitlab_manager"),
    "jira_manager": t("update_tool_descriptions.tools.jira_manager"),
    "list_asana_projects": t("update_tool_descriptions.tools.list_asana_projects"),
    "list_asana_workspaces": t("update_tool_descriptions.tools.list_asana_workspaces"),
    "list_github_repos": t("update_tool_descriptions.tools.list_github_repos"),
    "list_trello_boards": t("update_tool_descriptions.tools.list_trello_boards"),
    "notion_manager": t("update_tool_descriptions.tools.notion_manager"),
    "search_jira_issues": t("update_tool_descriptions.tools.search_jira_issues"),
    "search_notion": t("update_tool_descriptions.tools.search_notion"),
    "trello_manager": t("update_tool_descriptions.tools.trello_manager"),
    # --- CONNETTORI ESTERNI (UTILITY) ---
    "ai_research": t("update_tool_descriptions.tools.ai_research"),
    "browse_and_interact": t("update_tool_descriptions.tools.browse_and_interact"),
    "create_post": t("update_tool_descriptions.tools.create_post"),
    "document_processing": t("update_tool_descriptions.tools.document_processing"),
    "get_posts": t("update_tool_descriptions.tools.get_posts"),
    "get_responses": t("update_tool_descriptions.tools.get_responses"),
    "image_generation": t("update_tool_descriptions.tools.image_generation"),
    "iot_control": t("update_tool_descriptions.tools.iot_control"),
    "list_forms": t("update_tool_descriptions.tools.list_forms"),
    "trigger_webhook": t("update_tool_descriptions.tools.trigger_webhook"),
    "typeform_manager": t("update_tool_descriptions.tools.typeform_manager"),
    "video_generation": t("update_tool_descriptions.tools.video_generation"),
    "webhook_client": t("update_tool_descriptions.tools.webhook_client"),
    "wordpress_manager": t("update_tool_descriptions.tools.wordpress_manager"),
    # --- SKILLS (GUIDE) ---
    "read_skill": t("update_tool_descriptions.tools.read_skill"),
    "save_skill": t("update_tool_descriptions.tools.save_skill"),
    "delete_skill": t("update_tool_descriptions.tools.delete_skill"),
    "scan_skills": t("update_tool_descriptions.tools.scan_skills"),
}


def update_tools():
    if not TOOLS_DIR.exists():
        print(
            t("update_tool_descriptions.log.error_tools_not_found", path=str(TOOLS_DIR))
        )
        return

    print(t("update_tool_descriptions.log.start_update", count=len(TOOL_DESCRIPTIONS)))

    updated_count = 0
    missing_count = 0

    for tool_name, new_desc in TOOL_DESCRIPTIONS.items():
        file_path = TOOLS_DIR / f"{tool_name}.json"

        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Aggiorna la descrizione
                # Gestisce sia formato standard che formato "function" (Google)
                if "function" in data:
                    data["function"]["description"] = new_desc
                else:
                    data["description"] = new_desc

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                print(t("update_tool_descriptions.log.success_updated", name=tool_name))
                updated_count += 1
            except Exception as e:
                print(
                    t(
                        "update_tool_descriptions.log.error_failed",
                        name=tool_name,
                        error=str(e),
                    )
                )
        else:
            # print(f"  [SKIP] File non trovato: {tool_name}.json")
            missing_count += 1

    print(t("update_tool_descriptions.log.completed"))
    print(t("update_tool_descriptions.log.summary_updated", count=updated_count))
    print(t("update_tool_descriptions.log.summary_missing", count=missing_count))


if __name__ == "__main__":
    update_tools()
