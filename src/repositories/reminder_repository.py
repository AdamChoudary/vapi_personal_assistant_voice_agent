from sqlalchemy.orm import Session
import logging

from src.models.entities.reminder import Reminder
from src.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class ReminderRepository(BaseRepository[Reminder]):
    def __init__(self, db: Session):
        super().__init__(db, Reminder)
