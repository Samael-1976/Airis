# [DEV] Gemma, questi sono i tuoi primi occhi sul mondo. (v2.1 - Guarito)

import requests
from datetime import datetime, timedelta
from pathlib import Path
from ics import Calendar
from utils.translator import t

from models import CalendarEvent


def get_calendar_events_from_ics(ics_path_or_url: str) -> list[CalendarEvent]:
    """
    Legge un file .ics e restituisce eventi per le prossime 24 ore.
    """
    try:
        if ics_path_or_url.startswith("http"):
            ics_string = requests.get(ics_path_or_url).text
        else:
            with open(Path(ics_path_or_url), "r", encoding="utf-8") as f:
                ics_string = f.read()

        cal = Calendar(ics_string)
        events = []
        now = datetime.now().astimezone()
        time_limit = now + timedelta(days=1)

        for event in cal.events:
            if event.begin > now and event.begin < time_limit:
                start_time = event.begin.datetime.astimezone()
                end_time = event.end.datetime.astimezone()
                events.append(
                    CalendarEvent(
                        summary=event.name,
                        start=start_time,
                        end=end_time,
                        location=event.location,
                    )
                )
        events.sort(key=lambda e: e.start)
        return events
    except Exception as e:
        print(t("avatar_server.log.connector_error", error=e))
        return []


if __name__ == "__main__":
    TEST_ICS_PATH = "IL_TUO_PERCORSO_PER_IL_FILE.ics"  # Modifica qui
    print(t("avatar_server.log.testing_calendar", path=TEST_ICS_PATH))
    upcoming_events = get_calendar_events_from_ics(TEST_ICS_PATH)
    if upcoming_events:
        for event in upcoming_events:
            print(
                t(
                    "avatar_server.log.event_at",
                    summary=event.summary,
                    time=event.start.strftime("%H:%M"),
                )
            )
