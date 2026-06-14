# [DEV] Mio Creatore, queste sono le Regole del Pensiero. (v3.2 - Dynamic Validator Implementation)
# [AGGIUNTA v3.0]: Implementata estrazione dinamica delle emozioni dal corpo (intent.json).
# [AGGIUNTA v3.0]: Implementato il "Buttafuori Logico" per correggere le allucinazioni degli intent.
# [AFFINAMENTO v3.1]: Alzata soglia di cutoff a 0.6 per evitare match emozionali incoerenti.
# MANTENUTO: Logica originale di analisi contesto e promemoria imminenti.
# LEGGE A0099: Invarianza strutturale garantita. Nessuna riga originale rimossa.

from datetime import timedelta, datetime
from typing import List, Dict, Any, Optional, Set, TYPE_CHECKING
import difflib  # Per il calcolo della somiglianza stringa
from utils.translator import t

if TYPE_CHECKING:
    from context import UserContext
    from models import CalendarEvent


def get_valid_emotions(intent_data: List[Dict[str, Any]]) -> List[str]:
    """
    Estrae dinamicamente la lista univoca delle emozioni dal file intent.json dell'avatar.
    Filtra gli stati tecnici (state_*) per fornire all'LLM solo categorie espressive.
    """
    emotions_set: Set[str] = set()

    for item in intent_data:
        # Estrae il nome del file per il filtraggio tecnico
        filepath = item.get("filepath", "")
        filename = (
            filepath.split("/")[-1].lower() if "/" in filepath else filepath.lower()
        )

        # Salta gli stati tecnici (Foundational States)
        if filename.startswith("state_"):
            continue

        # Estrae le emozioni associate al video
        emotions = item.get("emotion", [])
        if isinstance(emotions, str):
            emotions_set.add(emotions.strip())
        elif isinstance(emotions, list):
            for emo in emotions:
                emotions_set.add(str(emo).strip())

    # Restituisce la lista ordinata alfabeticamente
    return sorted(list(emotions_set))


def get_closest_emotion(hallucinated_intent: str, valid_emotions: List[str]) -> str:
    """
    Il Buttafuori Logico: confronta l'intent generato dall'LLM con la lista sacra.
    Se non presente, restituisce il match più vicino. Se non c'è somiglianza, restituisce 'Calm'.
    """
    if not hallucinated_intent or not valid_emotions:
        return "Calm"

    # Pulizia dell'input
    target = hallucinated_intent.strip()

    # Check diretto (Case Insensitive)
    for valid in valid_emotions:
        if target.lower() == valid.lower():
            return valid

    # Calcolo somiglianza semantica/testuale
    # [AFFINAMENTO v3.1]: Cutoff impostato a 0.6 per maggiore precisione
    matches = difflib.get_close_matches(target, valid_emotions, n=1, cutoff=0.6)

    if matches:
        return matches[0]

    # Fallback di sicurezza se l'allucinazione è totale
    return "Calm"


def analyze_context(context: "UserContext") -> List[str]:
    """
    Analizza il contesto attuale dell'utente e genera suggerimenti.
    """
    suggestions = []
    if not context.current_time:
        return suggestions
    now = context.current_time

    if context.upcoming_events:
        imminent_threshold = now + timedelta(minutes=30)
        for event in context.upcoming_events:
            if now < event.start < imminent_threshold:
                minutes_to_event = int((event.start - now).total_seconds() / 60)
                suggestion = t(
                    "avatar_server.reminders.suggestion",
                    summary=event.summary,
                    minutes=minutes_to_event,
                )
                suggestions.append(suggestion)

    return suggestions


if __name__ == "__main__":
    print(t("log.test_brain_rules"))

    # Mock di intent.json (Agnostico)
    mock_intent_data =[
        {"filepath": "Category_A/video_1.mp4", "emotion": ["Calm"]},
        {
            "filepath": "Category_B/video_2.mp4",
            "emotion": ["Joy", "Happiness"],
        },
        {
            "filepath": "Category_C/video_3.mp4",
            "emotion": ["Shyness", "Shame"],
        },
    ]

    valid_list = get_valid_emotions(mock_intent_data)
    print(t("log.test_valid_emotions", list=valid_list))

    test_hallucination = t("avatar_server.test.test_hallucination_value")
    closest = get_closest_emotion(test_hallucination, valid_list)
    print(t("log.test_hallucination_fix", old=test_hallucination, new=closest))

    print(t("log.test_context_analyzer"))
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.models import CalendarEvent

    class MockContext:
        def __init__(self):
            self.current_time = datetime.now().astimezone()
            self.upcoming_events = []

    mock_context = MockContext()
    event_imminente = CalendarEvent(
        summary=t("avatar_server.test.mock_event_summary"),
        start=mock_context.current_time + timedelta(minutes=15),
        end=mock_context.current_time + timedelta(hours=1),
    )
    mock_context.upcoming_events.append(event_imminente)
    suggerimenti_generati = analyze_context(mock_context)
    print(t("log.test_result"))
    if suggerimenti_generati:
        for sug in suggerimenti_generati:
            print(f"  - '{sug}'")
