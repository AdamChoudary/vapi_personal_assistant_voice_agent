import logging
from typing import Dict, List

from src.models.entities.reminder import Reminder
from src.models.domain.reminder import ReminderCreate, ReminderResponse, ReminderId
from src.repositories.reminder_repository import ReminderRepository
from src.utils.helpers import handle_service_error

logger = logging.getLogger(__name__)

class ReminderService:
    def __init__(self, repository: ReminderRepository):
        self.repository = repository

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