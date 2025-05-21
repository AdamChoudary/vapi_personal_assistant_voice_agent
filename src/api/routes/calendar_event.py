import logging
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends

from src.api.dependencies import get_validated_tool_call, get_calendar_event_repository
from src.models.domain.calendar_event import CalendarEventCreate, CalendarEventId
from src.models.domain.tool import ValidatedToolCall
from src.models.domain.response import ToolResponse
from src.repositories.calendar_event_repository import CalendarEventRepository
from src.services.calendar_event_service import CalendarEventService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["calendar_event"])

async def get_calendar_service(
    repository: Annotated[CalendarEventRepository, Depends(get_calendar_event_repository)]
) -> AsyncGenerator[CalendarEventService, None]:
    yield CalendarEventService(repository)

@router.post('/add_calendar_entry/', response_model=ToolResponse)
async def add_calendar_entry(
    validated: Annotated[ValidatedToolCall[CalendarEventCreate], Depends(get_validated_tool_call('addCalendarEntry', CalendarEventCreate))],
    service: Annotated[CalendarEventService, Depends(get_calendar_service)]
):
    result = await service.create_event(validated.args)
    return ToolResponse.create(validated.tool_call_id, result)


@router.post('/get_calendar_entries/', response_model=ToolResponse)
async def get_calendar_entries(
    validated: Annotated[ValidatedToolCall[dict], Depends(get_validated_tool_call('getCalendarEntries', dict))],
    service: Annotated[CalendarEventService, Depends(get_calendar_service)]
):
    result = await service.get_events()
    return ToolResponse.create(validated.tool_call_id, result)


@router.post('/delete_calendar_entry/', response_model=ToolResponse)
async def delete_calendar_entry(
    validated: Annotated[ValidatedToolCall[CalendarEventId], Depends(get_validated_tool_call('deleteCalendarEntry', CalendarEventId))],
    service: Annotated[CalendarEventService, Depends(get_calendar_service)]
):
    result = await service.delete_event(validated.args)
    return ToolResponse.create(validated.tool_call_id, result)