from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T')

class ValidatedToolCall(BaseModel, Generic[T]):
    tool_call_id: str
    args: T
