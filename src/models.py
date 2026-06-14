# src/models.py
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CalendarEvent:
    summary: str
    start: datetime
    end: datetime
    location: str | None = None
