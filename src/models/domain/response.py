from typing import List, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar('T')

class ToolCallResult(BaseModel, Generic[T]):
    toolCallId: str = Field(..., description="ID of the tool call")
    result: T = Field(..., description="Result of the tool call")

class ToolResponse(BaseModel, Generic[T]):
    results: List[ToolCallResult[T]] = Field(..., description="List of tool call results")
    
    @classmethod
    def create(cls, tool_call_id: str, result: T) -> "ToolResponse[T]":
        return cls(
            results=[
                ToolCallResult(toolCallId=tool_call_id, result=result)
            ]
        )
