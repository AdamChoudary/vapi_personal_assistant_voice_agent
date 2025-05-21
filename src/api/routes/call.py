import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from src.models.domain.call import CallRequest
from src.models.domain.response import ToolResponse
from src.models.domain.tool import ValidatedToolCall
from src.services.call_service import CallService
from src.api.dependencies import get_validated_tool_call

logger = logging.getLogger(__name__)

router = APIRouter(tags=["call"])

def get_call_service() -> CallService:
    return CallService()

@router.post('/make_call/', response_model=ToolResponse)
async def make_call(
    validated: Annotated[ValidatedToolCall[CallRequest], Depends(get_validated_tool_call('makeCall', CallRequest))],
    service: Annotated[CallService, Depends(get_call_service)]
):
    result = await service.make_call(validated.args)
    return ToolResponse.create(validated.tool_call_id, result)
