from sqlalchemy.orm import Session
import logging

from src.models.entities.todo import Todo
from src.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class TodoRepository(BaseRepository[Todo]):
    def __init__(self, db: Session):
        super().__init__(db, Todo)
