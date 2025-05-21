import logging
from typing import List, Dict

from src.models.entities.calendar_event import CalendarEvent
from src.models.domain.calendar_event import CalendarEventCreate, CalendarEventResponse, CalendarEventId
from src.repositories.calendar_event_repository import CalendarEventRepository
from src.utils.helpers import handle_service_error

logger = logging.getLogger(__name__)

class CalendarEventService:
    def __init__(self, repository: CalendarEventRepository):
        self.repository = repository

    async def create_event(self, event_data: CalendarEventCreate) -> CalendarEventResponse:
        try:
            calendar_event = CalendarEvent(
                title=event_data.title,
                description=event_data.description,
                event_from=event_data.event_from,
                event_to=event_data.event_to
            )

            created_event = await self.repository.save(calendar_event)
            return CalendarEventResponse.model_validate(created_event)
        except Exception as e:
            handle_service_error(e, "calendar_event_service", "create_event")

    async def get_events(self) -> List[CalendarEventResponse]:
        try:
            events = await self.repository.get_all()
            return [CalendarEventResponse.model_validate(event) for event in events]
        except Exception as e:
            handle_service_error(e, "calendar_event_service", "get_events")

    async def delete_event(self, event_id: CalendarEventId) -> Dict[str, str]:
        try:
            await self.repository.delete(event_id.id)
            return {"status": "success", "message": f"Calendar event {event_id.id} deleted successfully"}
        except Exception as e:
            handle_service_error(e, "calendar_event_service", "delete_event")
