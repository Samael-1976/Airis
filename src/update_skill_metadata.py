# src/update_skills_json.py
# [DEV] Il Purificatore delle Skills (v1.0)
# Riscrive massivamente tutti i file JSON in src/skills/ inserendo descrizioni ultra-sintetiche
# e assicurandosi che la struttura sia perfetta per l'LLM e per la UI.

import json
from pathlib import Path
from utils.translator import t

SCRIPT_DIR = Path(__file__).parent.resolve()
SKILLS_DIR = SCRIPT_DIR / "skills"

# Mappa delle descrizioni ultra-sintetiche e precise per l'LLM
SKILL_DESCRIPTIONS = {
    "ai_research.json": t("skills.descriptions.ai_research"),
    "asana_manager.json": t("skills.descriptions.asana_manager"),
    "discord_bot.json": t("skills.descriptions.discord_bot"),
    "document_processing.json": t("skills.descriptions.document_processing"),
    "excel_manager.json": t("skills.descriptions.excel_manager"),
    "git_workflow.json": t("skills.descriptions.git_workflow"),
    "github_manager.json": t("skills.descriptions.github_manager"),
    "gitlab_manager.json": t("skills.descriptions.gitlab_manager"),
    "gmail_manager.json": t("skills.descriptions.gmail_manager"),
    "google_calendar.json": t("skills.descriptions.google_calendar"),
    "google_contacts.json": t("skills.descriptions.google_contacts"),
    "google_drive.json": t("skills.descriptions.google_drive"),
    "google_photos.json": t("skills.descriptions.google_photos"),
    "google_sheets.json": t("skills.descriptions.google_sheets"),
    "google_tasks.json": t("skills.descriptions.google_tasks"),
    "image_generation.json": t("skills.descriptions.image_generation"),
    "iot_control.json": t("skills.descriptions.iot_control"),
    "jira_manager.json": t("skills.descriptions.jira_manager"),
    "microsoft_todo.json": t("skills.descriptions.microsoft_todo"),
    "notion_manager.json": t("skills.descriptions.notion_manager"),
    "onedrive_manager.json": t("skills.descriptions.onedrive_manager"),
    "outlook_manager.json": t("skills.descriptions.outlook_manager"),
    "reddit_manager.json": t("skills.descriptions.reddit_manager"),
    "slack_bot.json": t("skills.descriptions.slack_bot"),
    "sms_sender.json": t("skills.descriptions.sms_sender"),
    "telegram_bot.json": t("skills.descriptions.telegram_bot"),
    "trello_manager.json": t("skills.descriptions.trello_manager"),
    "twitter_manager.json": t("skills.descriptions.twitter_manager"),
    "typeform_manager.json": t("skills.descriptions.typeform_manager"),
    "video_generation.json": t("skills.descriptions.video_generation"),
    "webhook_client.json": t("skills.descriptions.webhook_client"),
    "whatsapp_sender.json": t("skills.descriptions.whatsapp_sender"),
    "wordpress_manager.json": t("skills.descriptions.wordpress_manager"),
}


def update_skills():
    if not SKILLS_DIR.exists():
        print(t("skills.folder_not_found", path=SKILLS_DIR))
        return

    print(t("skills.update_start", count=len(SKILL_DESCRIPTIONS)))

    updated_count = 0

    for filename, new_desc in SKILL_DESCRIPTIONS.items():
        file_path = SKILLS_DIR / filename

        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Assicuriamo la struttura Google Native
                if "function" not in data:
                    # Se è piatto, lo convertiamo
                    old_data = data.copy()
                    data = {"type": "function", "function": old_data}

                # 1. Aggiorna la descrizione root della funzione
                data["function"]["description"] = new_desc

                # 2. Aggiorna la descrizione profonda del parametro task_description
                if "parameters" not in data["function"]:
                    data["function"]["parameters"] = {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    }

                props = data["function"]["parameters"].get("properties", {})

                if "task_description" not in props:
                    props["task_description"] = {"type": "string"}

                # Inserisce la descrizione ultra-sintetica anche qui per la UI
                props["task_description"]["description"] = t(
                    "skills.task_desc_ui", desc=new_desc
                )

                data["function"]["parameters"]["properties"] = props

                # Assicura che task_description sia required
                reqs = data["function"]["parameters"].get("required", [])
                if "task_description" not in reqs:
                    reqs.append("task_description")
                data["function"]["parameters"]["required"] = reqs

                # Scrittura
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                print(t("skills.update_ok", filename=filename))
                updated_count += 1
            except Exception as e:
                print(t("skills.update_error", filename=filename, error=e))
        else:
            print(t("skills.update_skip", filename=filename))

    print(t("skills.update_complete", count=updated_count))


if __name__ == "__main__":
    update_skills()
