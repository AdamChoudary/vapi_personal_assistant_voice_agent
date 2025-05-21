from sqlalchemy.orm import Session
import logging

from src.models.entities.calendar_event import CalendarEvent
from src.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class CalendarEventRepository(BaseRepository[CalendarEvent]):
    def __init__(self, db: Session):
        super().__init__(db, CalendarEvent)
