import logging
from typing import List, Dict

from fastapi import HTTPException
from src.models.entities.todo import Todo
from src.models.domain.todo import TodoCreate, TodoResponse, TodoId
from src.repositories.todo_repository import TodoRepository
from src.utils.helpers import handle_service_error

logger = logging.getLogger(__name__)

class TodoService:
    def __init__(self, repository: TodoRepository):
        self.repository = repository

    async def create_todo(self, todo_data: TodoCreate) -> TodoResponse:
        try:
            todo = Todo(
                title=todo_data.title,
                description=todo_data.description
            )

            created_todo = await self.repository.save(todo)
            return TodoResponse.model_validate(created_todo)
        except Exception as e:
            handle_service_error(e, "todo_service", "create_todo")

    async def get_todos(self) -> List[TodoResponse]:
        try:
            todos = await self.repository.get_all()
            return [TodoResponse.model_validate(todo) for todo in todos]
        except Exception as e:
            handle_service_error(e, "todo_service", "get_todos")

    async def complete_todo(self, todo_id: TodoId) -> TodoResponse:
        try:
            todo = await self.repository.get_by_id(todo_id.id)

            if not todo:
                logger.warning(f"To-do with id {todo_id} not found")
                raise HTTPException(status_code=404, detail="To-do not found")


            todo.completed = True
            updated_todo = await self.repository.save(todo)

            return TodoResponse.model_validate(updated_todo)
        except HTTPException:
            raise
        except Exception as e:
            handle_service_error(e, "todo_service", "complete_todo")

    async def delete_todo(self, todo_id: TodoId) -> Dict[str, str]:
        try:
            await self.repository.delete(todo_id.id)
            return {"status": "success", "message": f"Todo {todo_id.id} deleted successfully"}
        except Exception as e:
            handle_service_error(e, "todo_service", "delete_todo")