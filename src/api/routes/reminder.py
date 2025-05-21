import logging
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends

from src.api.dependencies import get_validated_tool_call, get_reminder_repository
from src.models.domain.reminder import ReminderCreate, ReminderId
from src.models.domain.tool import ValidatedToolCall
from src.models.domain.response import ToolResponse
from src.repositories.reminder_repository import ReminderRepository
from src.services.reminder_service import ReminderService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["reminder"])

async def get_reminder_service(
    repository: Annotated[ReminderRepository, Depends(get_reminder_repository)]
) -> AsyncGenerator[ReminderService, None]:
    yield ReminderService(repository)

@router.post('/add_reminder/', response_model=ToolResponse)
async def add_reminder(
    validated: Annotated[ValidatedToolCall[ReminderCreate], Depends(get_validated_tool_call('addReminder', ReminderCreate))],
    service: Annotated[ReminderService, Depends(get_reminder_service)]
):
    result = await service.create_reminder(validated.args)
    return ToolResponse.create(validated.tool_call_id, result)


@router.post('/get_reminders/', response_model=ToolResponse)
async def get_reminders(
    validated: Annotated[ValidatedToolCall[dict], Depends(get_validated_tool_call('getReminders', dict))],
    service: Annotated[ReminderService, Depends(get_reminder_service)]
):
    result = await service.get_reminders()
    return ToolResponse.create(validated.tool_call_id, result)


@router.post('/delete_reminder/', response_model=ToolResponse)
async def delete_reminder(
    validated: Annotated[ValidatedToolCall[ReminderId], Depends(get_validated_tool_call('deleteReminder', ReminderId))],
    service: Annotated[ReminderService, Depends(get_reminder_service)]
):
    result = await service.delete_reminder(validated.args)
    return ToolResponse.create(validated.tool_call_id, result)