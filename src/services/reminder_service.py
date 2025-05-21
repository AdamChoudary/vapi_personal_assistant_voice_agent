import logging
from typing import Dict, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.models.entities.reminder import Reminder
from src.models.domain.reminder import ReminderCreate, ReminderResponse, ReminderId
from src.repositories.reminder_repository import ReminderRepository
from src.utils.helpers import handle_service_error

logger = logging.getLogger(__name__)

class ReminderService:
    def __init__(self, db: Session):
        self.repository = ReminderRepository(db)

    async def _get_reminder_by_id(self, reminder_id: int) -> Reminder:
        try:
            reminder = await self.repository.get_by_id(reminder_id)
            
            if not reminder:
                logger.warning(f"Reminder with id {reminder_id} not found")
                raise HTTPException(status_code=404, detail="Reminder not found")
                
            return reminder
        except Exception as e:
            handle_service_error(e, "reminder_service", "_get_reminder_by_id")

    async def create_reminder(self, reminder_data: ReminderCreate) -> ReminderResponse:
        try:
            reminder = Reminder(
                reminder_text=reminder_data.reminder_text,
                importance=reminder_data.importance
            )

            created_reminder = await self.repository.save(reminder)
            return ReminderResponse.model_validate(created_reminder)
        except Exception as e:
            handle_service_error(e, "reminder_service", "create_reminder")

    async def get_reminders(self) -> List[ReminderResponse]:
        try:
            reminders = await self.repository.get_all()
            return [ReminderResponse.model_validate(reminder) for reminder in reminders]
        except Exception as e:
            handle_service_error(e, "reminder_service", "get_reminders")

    async def delete_reminder(self, reminder_id: ReminderId) -> Dict[str, str]:
        try:
            await self.repository.delete(reminder_id.id)
            return {"status": "success", "message": f"Reminder {reminder_id.id} deleted successfully"}
        except Exception as e:
            handle_service_error(e, "reminder_service", "delete_reminder")