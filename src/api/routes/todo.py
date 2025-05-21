import logging
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies import get_db, get_validated_tool_call
from src.models.domain.todo import TodoCreate, TodoId
from src.models.domain.tool import ValidatedToolCall
from src.models.domain.response import ToolResponse
from src.services.todo_service import TodoService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["todo"])

async def get_todo_service(db: Annotated[Session, Depends(get_db)]) -> AsyncGenerator[TodoService, None]:
    yield TodoService(db)

@router.post('/create_todo/', response_model=ToolResponse)
async def create_todo(
    validated: Annotated[ValidatedToolCall[TodoCreate], Depends(get_validated_tool_call('createTodo', TodoCreate))],
    service: Annotated[TodoService, Depends(get_todo_service)]
):
    result = await service.create_todo(validated.args)
    return ToolResponse.create(validated.tool_call_id, result)


@router.post('/get_todos/', response_model=ToolResponse)
async def get_todos(
    validated: Annotated[ValidatedToolCall[dict], Depends(get_validated_tool_call('getTodos', dict))],
    service: Annotated[TodoService, Depends(get_todo_service)]
):
    result = await service.get_todos()
    return ToolResponse.create(validated.tool_call_id, result)


@router.post('/complete_todo/', response_model=ToolResponse)
async def complete_todo(
    validated: Annotated[ValidatedToolCall[TodoId], Depends(get_validated_tool_call('completeTodo', TodoId))],
    service: Annotated[TodoService, Depends(get_todo_service)]
):
    result = await service.complete_todo(validated.args)
    return ToolResponse.create(validated.tool_call_id, result)


@router.post('/delete_todo/', response_model=ToolResponse)
async def delete_todo(
    validated: Annotated[ValidatedToolCall[TodoId], Depends(get_validated_tool_call('deleteTodo', TodoId))],
    service: Annotated[TodoService, Depends(get_todo_service)]
):
    result = await service.delete_todo(validated.args)
    return ToolResponse.create(validated.tool_call_id, result)