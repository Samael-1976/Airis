# src/setup_skills.py
#[DEV] Il Forgiatore di Abilità (v3.0 - TOTAL CLI ENFORCEMENT)
# Genera le Skills con comandi CLI espliciti per Windows e Linux per TUTTI i connettori.
# ELIMINA l'ambiguità tra computer.* e i connettori locali.

import os
import sys
from pathlib import Path
from utils.translator import t

# Configurazione Percorsi
SCRIPT_DIR = Path(__file__).parent.resolve()
CONNECTORS_DIR = SCRIPT_DIR / "connectors"

# Assicuriamoci che la cartella esista
CONNECTORS_DIR.mkdir(parents=True, exist_ok=True)

# Definizione delle Skills (CLI FIRST APPROACH)
# NOTA: Le doppie parentesi graffe {{ }} servono per non farle interpretare ad f-string.
# --- [FIX 1B] FUGA DALLA SANDBOX ---
# Usiamo sys.executable per forzare l'uso dell'ambiente virtuale corrente (venv)
# invece del python globale di sistema, prevenendo ModuleNotFoundError.

SKILLS_DATA = {
    "skill_gmail.md": f"""---
name: gmail_manager
description: {t('skills.gmail_desc')}
triggers: {t('skills.gmail_triggers')}
---
# {t('skills.gmail_manager')} (CLI)

{t('skills.cli_warning_mail')}

### Windows / Linux / Mac
1. **{t('skills.cli_label_read')}**: `{sys.executable} src/connectors/gmail.py --action list --params "{{\\"max_results\\": 5}}"`
2. **{t('skills.cli_label_send')}**: `{sys.executable} src/connectors/gmail.py --action send --params "{{\\"to\\": \\"email@example.com\\", \\"subject\\": \\"{t('skills.cli_subject_placeholder')}\\", \\"body\\": \\"{t('skills.cli_body_placeholder')}\\"}}"`
""",
    "skill_google_calendar.md": f"""---
name: google_calendar
description: {t('skills.calendar_desc')}
triggers: {t('skills.calendar_triggers')}
---
# {t('skills.google_calendar')} (CLI)

{t('skills.cli_warning_calendar')}

### Windows / Linux / Mac
1. **{t('skills.cli_label_list_events')}**: `{sys.executable} src/connectors/google_calendar.py --action list --params "{{\\"max_results\\": 10}}"`
2. **{t('skills.cli_label_create_event')}**: `{sys.executable} src/connectors/google_calendar.py --action create --params "{{\\"summary\\": \\"{t('skills.cli_title_placeholder')}\\", \\"start_time\\": \\"2023-12-25T10:00:00\\", \\"end_time\\": \\"2023-12-25T11:00:00\\"}}"`
""",
    "skill_google_tasks.md": f"""---
name: google_tasks
description: {t('skills.tasks_desc')}
triggers: {t('skills.tasks_triggers')}
---
# {t('skills.google_tasks')} (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_lists')}**: `{sys.executable} src/connectors/google_tasks.py --action list_lists`
2. **{t('skills.cli_label_list_tasks')}**: `{sys.executable} src/connectors/google_tasks.py --action list_tasks --params "{{\\"tasklist_id\\": \\"ID_LISTA\\"}}"`
3. **{t('skills.cli_label_create_task')}**: `{sys.executable} src/connectors/google_tasks.py --action create --params "{{\\"tasklist_id\\": \\"ID_LISTA\\", \\"title\\": \\"{t('skills.cli_title_placeholder')}\\"}}"`
""",
    "skill_google_drive.md": f"""---
name: google_drive
description: {t('skills.drive_desc')}
triggers: {t('skills.drive_triggers')}
---
# Google Drive (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_list_files')}**: `{sys.executable} src/connectors/google_drive.py --action list --params "{{\\"max_results\\": 10}}"`
""",
    "skill_google_sheets.md": f"""---
name: google_sheets
description: {t('skills.sheets_desc')}
triggers: {t('skills.sheets_triggers')}
---
# Google Sheets (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_read')}**: `{sys.executable} src/connectors/google_sheets.py --action read --params "{{\\"spreadsheet_id\\": \\"ID\\", \\"range_name\\": \\"Sheet1!A1:C10\\"}}"`
2. **{t('skills.cli_label_write')}**: `{sys.executable} src/connectors/google_sheets.py --action write --params "{{\\"spreadsheet_id\\": \\"ID\\", \\"range_name\\": \\"Sheet1!A1\\", \\"values\\": [[\\"A\\",\\"B\\"],[\\"1\\",\\"2\\"]]}}"`
""",
    "skill_google_photos.md": f"""---
name: google_photos
description: {t('skills.photos_desc')}
triggers: {t('skills.photos_triggers')}
---
# {t('skills.google_photos')} (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_albums')}**: `{sys.executable} src/connectors/google_photos.py --action list_albums`
2. **{t('skills.cli_label_search')}**: `{sys.executable} src/connectors/google_photos.py --action search --params "{{\\"query\\": \\"{t('skills.cli_cats_placeholder')}\\", \\"max_results\\": 5}}"`
""",
    "skill_google_contacts.md": f"""---
name: google_contacts
description: {t('skills.contacts_desc')}
triggers: {t('skills.contacts_triggers')}
---
# Google Contacts (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_search')}**: `{sys.executable} src/connectors/google_contacts.py --action search --params "{{\\"query\\": \\"Mario\\"}}"`
""",
    "skill_outlook.md": f"""---
name: outlook_manager
description: {t('skills.outlook_desc')}
triggers: {t('skills.outlook_triggers')}
---
# {t('skills.outlook_manager')} (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_read')}**: `{sys.executable} src/connectors/microsoft_outlook.py --action list --params "{{\\"max_results\\": 5}}"`
2. **{t('skills.cli_label_send')}**: `{sys.executable} src/connectors/microsoft_outlook.py --action send --params "{{\\"to\\": \\"mail@test.com\\", \\"subject\\": \\"{t('skills.cli_subject_placeholder')}\\", \\"body\\": \\"{t('skills.cli_body_placeholder')}\\"}}"`
""",
    "skill_onedrive.md": f"""---
name: onedrive_manager
description: {t('skills.onedrive_desc')}
triggers: {t('skills.onedrive_triggers')}
---
# Microsoft OneDrive (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_list')}**: `{sys.executable} src/connectors/microsoft_onedrive.py --action list --params "{{\\"max_results\\": 10}}"`
""",
    "skill_excel.md": f"""---
name: excel_manager
description: {t('skills.excel_desc')}
triggers: {t('skills.excel_triggers')}
---
# {t('skills.excel_manager')} (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_read')}**: `{sys.executable} src/connectors/microsoft_excel.py --action read --params "{{\\"file_id\\": \\"ID\\", \\"worksheet_name\\": \\"Sheet1\\", \\"range_address\\": \\"A1:B10\\"}}"`
2. **{t('skills.cli_label_write')}**: `{sys.executable} src/connectors/microsoft_excel.py --action write --params "{{\\"file_id\\": \\"ID\\", \\"worksheet_name\\": \\"Sheet1\\", \\"range_address\\": \\"A1\\", \\"values\\": [[\\"{t('skills.cli_data_placeholder')}\\"]]}}"`
""",
    "skill_microsoft_todo.md": f"""---
name: microsoft_todo
description: {t('skills.todo_desc')}
triggers: {t('skills.todo_triggers')}
---
# {t('skills.microsoft_todo')} (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_lists')}**: `{sys.executable} src/connectors/microsoft_todo.py --action list_lists`
2. **{t('skills.cli_label_task')}**: `{sys.executable} src/connectors/microsoft_todo.py --action list_tasks --params "{{\\"tasklist_id\\": \\"ID\\"}}"`
3. **{t('skills.cli_label_new')}**: `{sys.executable} src/connectors/microsoft_todo.py --action create --params "{{\\"tasklist_id\\": \\"ID\\", \\"title\\": \\"{t('skills.cli_title_placeholder')}\\"}}"`
""",
    "skill_telegram.md": f"""---
name: telegram_bot
description: {t('skills.telegram_desc')}
triggers: {t('skills.telegram_triggers')}
---
# {t('skills.telegram_bot')} (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_send')}**: `{sys.executable} src/connectors/telegram.py --action send_message --params "{{\\"chat_id\\": \\"123456\\", \\"content\\": \\"{t('skills.cli_message_placeholder')}\\"}}"`
2. **{t('skills.cli_label_read')}**: `{sys.executable} src/connectors/telegram.py --action list_messages --params "{{\\"limit\\": 5}}"`
""",
    "skill_discord.md": f"""---
name: discord_bot
description: {t('skills.discord_desc')}
triggers: {t('skills.discord_triggers')}
---
# {t('skills.discord_bot')} (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_send')}**: `{sys.executable} src/connectors/discord.py --action send_message --params "{{\\"channel_id\\": \\"123456\\", \\"content\\": \\"{t('skills.cli_message_placeholder')}\\"}}"`
2. **{t('skills.cli_label_read')}**: `{sys.executable} src/connectors/discord.py --action list_messages --params "{{\\"channel_id\\": \\"123456\\", \\"limit\\": 10}}"`
""",
    "skill_slack.md": f"""---
name: slack_bot
description: {t('skills.slack_desc')}
triggers: {t('skills.slack_triggers')}
---
# {t('skills.slack_bot')} (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_send')}**: `{sys.executable} src/connectors/slack.py --action send_message --params "{{\\"channel_id\\": \\"C12345\\", \\"content\\": \\"{t('skills.cli_message_placeholder')}\\"}}"`
2. **{t('skills.cli_label_read')}**: `{sys.executable} src/connectors/slack.py --action list_messages --params "{{\\"channel_id\\": \\"C12345\\", \\"limit\\": 10}}"`
""",
    "skill_whatsapp.md": f"""---
name: whatsapp_sender
description: {t('skills.whatsapp_desc')}
triggers: {t('skills.whatsapp_triggers')}
---
# {t('skills.whatsapp_sender')} (Twilio CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_send')}**: `{sys.executable} src/connectors/whatsapp.py --action send_message --params "{{\\"to_number\\": \\"+39333...\\", \\"body\\": \\"{t('skills.cli_message_placeholder')}\\"}}"`
""",
    "skill_twilio_sms.md": f"""---
name: sms_sender
description: {t('skills.sms_desc')}
triggers: {t('skills.sms_triggers')}
---
# {t('skills.sms_sender')} (Twilio CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_send')}**: `{sys.executable} src/connectors/twilio.py --action send_sms --params "{{\\"to_number\\": \\"+39333...\\", \\"body\\": \\"{t('skills.cli_message_placeholder')}\\"}}"`
""",
    "skill_twitter.md": f"""---
name: twitter_manager
description: {t('skills.twitter_desc')}
triggers: {t('skills.twitter_triggers')}
---
# {t('skills.twitter_manager')} (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_post')}**: `{sys.executable} src/connectors/twitter.py --action post_tweet --params "{{\\"text\\": \\"{t('skills.cli_message_placeholder')}\\"}}"`
""",
    "skill_reddit.md": f"""---
name: reddit_manager
description: {t('skills.reddit_desc')}
triggers: {t('skills.reddit_triggers')}
---
# {t('skills.reddit_manager')} (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_read')}**: `{sys.executable} src/connectors/reddit.py --action get_hot_posts --params "{{\\"subreddit\\": \\"python\\", \\"limit\\": 5}}"`
2. **{t('skills.cli_label_post')}**: `{sys.executable} src/connectors/reddit.py --action submit_post --params "{{\\"subreddit\\": \\"test\\", \\"title\\": \\"{t('skills.cli_title_placeholder')}\\", \\"selftext\\": \\"{t('skills.cli_body_placeholder')}\\"}}"`
""",
    "skill_trello.md": f"""---
name: trello_manager
description: {t('skills.trello_desc')}
triggers: {t('skills.trello_triggers')}
---
# {t('skills.trello_manager')} (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_boards')}**: `{sys.executable} src/connectors/trello.py --action list_boards`
2. **{t('skills.cli_label_new_card')}**: `{sys.executable} src/connectors/trello.py --action create_card --params "{{\\"board_name\\": \\"{t('skills.cli_name_placeholder')}\\", \\"list_name\\": \\"{t('skills.cli_list_placeholder')}\\", \\"name\\": \\"{t('skills.cli_title_placeholder')}\\"}}"`
""",
    "skill_jira.md": f"""---
name: jira_manager
description: {t('skills.jira_desc')}
triggers: {t('skills.jira_triggers')}
---
# {t('skills.jira_manager')} (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_search')}**: `{sys.executable} src/connectors/jira.py --action search_issues --params "{{\\"jql_query\\": \\"project=TEST\\", \\"max_results\\": 5}}"`
2. **{t('skills.cli_label_create')}**: `{sys.executable} src/connectors/jira.py --action create_issue --params "{{\\"project_key\\": \\"TEST\\", \\"summary\\": \\"{t('skills.cli_title_placeholder')}\\", \\"description\\": \\"{t('skills.cli_desc_placeholder')}\\", \\"issuetype_name\\": \\"Task\\"}}"`
""",
    "skill_asana.md": f"""---
name: asana_manager
description: {t('skills.asana_desc')}
triggers: {t('skills.asana_triggers')}
---
# {t('skills.asana_manager')} (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_workspace')}**: `{sys.executable} src/connectors/asana.py --action list_workspaces`
2. **{t('skills.cli_label_projects')}**: `{sys.executable} src/connectors/asana.py --action list_projects --params "{{\\"workspace_gid\\": \\"GID\\"}}"`
3. **{t('skills.cli_label_create_task')}**: `{sys.executable} src/connectors/asana.py --action create_task --params "{{\\"workspace_gid\\": \\"GID\\", \\"project_gid\\": \\"GID\\", \\"name\\": \\"{t('skills.cli_title_placeholder')}\\"}}"`
""",
    "skill_notion.md": f"""---
name: notion_manager
description: {t('skills.notion_desc')}
triggers: {t('skills.notion_triggers')}
---
# {t('skills.notion_manager')} (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_search')}**: `{sys.executable} src/connectors/notion.py --action search_notion --params "{{\\"query\\": \\"{t('skills.cli_text_placeholder')}\\"}}"`
2. **{t('skills.cli_label_create')}**: `{sys.executable} src/connectors/notion.py --action create_notion_page --params "{{\\"parent_page_id\\": \\"ID\\", \\"title\\": \\"{t('skills.cli_title_placeholder')}\\", \\"content\\": \\"{t('skills.cli_text_placeholder')}\\"}}"`
""",
    "skill_typeform.md": f"""---
name: typeform_manager
description: {t('skills.typeform_desc')}
triggers: {t('skills.typeform_triggers')}
---
# {t('skills.typeform_manager')} (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_list')}**: `{sys.executable} src/connectors/forms.py --action list_forms`
2. **{t('skills.cli_label_responses')}**: `{sys.executable} src/connectors/forms.py --action get_responses --params "{{\\"form_id\\": \\"ID\\"}}"`
""",
    "skill_wordpress.md": f"""---
name: wordpress_manager
description: {t('skills.wordpress_desc')}
triggers: {t('skills.wordpress_triggers')}
---
# {t('skills.wordpress_manager')} (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_posts')}**: `{sys.executable} src/connectors/wordpress.py --action get_posts --params "{{\\"per_page\\": 5}}"`
2. **{t('skills.cli_label_new')}**: `{sys.executable} src/connectors/wordpress.py --action create_post --params "{{\\"title\\": \\"{t('skills.cli_title_placeholder')}\\", \\"content\\": \\"{t('skills.cli_text_placeholder')}\\", \\"status\\": \\"draft\\"}}"`
""",
    "skill_image_generation.md": f"""---
name: image_generation
description: {t('skills.image_gen_desc')}
triggers: {t('skills.image_gen_triggers')}
---
# {t('skills.image_generation')} (CLI)

### Windows / Linux / Mac
1. **Flux**: `{sys.executable} src/connectors/image_gen.py --action generate_flux --params "{{\\"prompt\\": \\"{t('skills.cli_cat_prompt_placeholder')}\\"}}"`
2. **DALL-E**: `{sys.executable} src/connectors/image_gen.py --action generate_dalle3 --params "{{\\"prompt\\": \\"{t('skills.cli_cat_prompt_placeholder')}\\"}}"`
""",
    "skill_video_generation.md": f"""---
name: video_generation
description: {t('skills.video_gen_desc')}
triggers: {t('skills.video_gen_triggers')}
---
# {t('skills.video_generation')} (CLI)

### Windows / Linux / Mac
1. **VEO3**: `{sys.executable} src/connectors/video_gen.py --action generate_veo3 --params "{{\\"prompt\\": \\"{t('skills.cli_cat_video_placeholder')}\\"}}"`
2. **Sora**: `{sys.executable} src/connectors/video_gen.py --action generate_sora2 --params "{{\\"prompt\\": \\"{t('skills.cli_cat_video_placeholder')}\\"}}"`
""",
    "skill_iot_control.md": f"""---
name: iot_control
description: {t('skills.iot_desc')}
triggers: {t('skills.iot_triggers')}
---
# {t('skills.iot_control')} (CLI)

### Windows / Linux / Mac
`{sys.executable} src/connectors/iot_hub.py --action execute --params "{{\\"device_id\\": \\"luce_sala\\", \\"action\\": \\"on\\"}}"`
""",
    "skill_ai_research.md": f"""---
name: ai_research
description: {t('skills.research_desc')}
triggers: {t('skills.research_triggers')}
---
# {t('skills.ai_research')} (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_arxiv')}**: `{sys.executable} src/connectors/ai_research.py --action search_arxiv --params "{{\\"query\\": \\"{t('skills.cli_ai_agents_placeholder')}\\", \\"max_results\\": 5}}"`
2. **{t('skills.cli_label_web')}**: `{sys.executable} src/connectors/ai_research.py --action deep_web_search --params "{{\\"query\\": \\"{t('skills.cli_ai_agents_placeholder')}\\", \\"max_results\\": 5}}"`
""",
    "skill_document_processing.md": f"""---
name: document_processing
description: {t('skills.doc_proc_desc')}
triggers: {t('skills.doc_proc_triggers')}
---
# {t('skills.document_processing')} (CLI)

### Windows / Linux / Mac
`{sys.executable} src/connectors/document_processor.py --action read_document --params "{{\\"file_path\\": \\"docs/file.pdf\\"}}"`
""",
    "skill_webhooks.md": f"""---
name: webhook_client
description: {t('skills.webhook_desc')}
triggers: {t('skills.webhook_triggers')}
---
# {t('skills.webhook_client')} (CLI)

### Windows / Linux / Mac
`{sys.executable} src/connectors/webhook.py --action trigger --params "{{\\"url\\": \\"http://...\\", \\"method\\": \\"POST\\"}}"`
""",
    "skill_github.md": f"""---
name: github_manager
description: {t('skills.github_desc')}
triggers: {t('skills.github_triggers')}
---
# {t('skills.github_manager')} (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_repo')}**: `{sys.executable} src/connectors/github.py --action list_repos`
2. **{t('skills.cli_label_issue')}**: `{sys.executable} src/connectors/github.py --action create_issue --params "{{\\"repo_full_name\\": \\"user/repo\\", \\"title\\": \\"{t('skills.cli_title_placeholder')}\\"}}"`
""",
    "skill_gitlab.md": f"""---
name: gitlab_manager
description: {t('skills.gitlab_desc')}
triggers: {t('skills.gitlab_triggers')}
---
# {t('skills.gitlab_manager')} (CLI)

### Windows / Linux / Mac
1. **{t('skills.cli_label_projects')}**: `{sys.executable} src/connectors/gitlab.py --action list_projects`
2. **{t('skills.cli_label_issue')}**: `{sys.executable} src/connectors/gitlab.py --action create_issue --params "{{\\"project_id\\": \\"123\\", \\"title\\": \\"{t('skills.cli_title_placeholder')}\\"}}"`
""",
    "git_workflow.md": f"""---
name: git_workflow
description: {t('skills.git_workflow_desc')}
triggers: {t('skills.git_workflow_triggers')}
---
# {t('skills.git_workflow')} (System CLI)

{t('skills.cli_git_warning')}

### {t('skills.cli_label_commands')}
1. **{t('skills.cli_label_status')}**: `git status`
2. **{t('skills.cli_label_add')}**: `git add .`
3. **{t('skills.cli_label_commit')}**: `git commit -m "{t('skills.cli_message_placeholder')}"`
4. **{t('skills.cli_label_push')}**: `git push`
""",
}


def install_skills():
    print(t("log.skills_gen_start", count=len(SKILLS_DATA)))
    count = 0
    for filename, content in SKILLS_DATA.items():
        file_path = CONNECTORS_DIR / filename

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content.strip())
            print(t("log.skills_gen_ok", filename=filename))
            count += 1
        except Exception as e:
            print(t("log.skills_gen_error", filename=filename, error=str(e)))

    print(t("log.skills_gen_complete", count=count, path=str(CONNECTORS_DIR)))


if __name__ == "__main__":
    install_skills()