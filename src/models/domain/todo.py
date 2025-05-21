from typing import Optional
from pydantic import BaseModel, Field

class TodoBase(BaseModel):
    title: str = Field(..., min_length=1)
    description: Optional[str] = Field(None)

class TodoCreate(TodoBase):
    pass

class TodoResponse(TodoBase):
    id: int
    completed: bool = False

    class Config:
        from_attributes = True

class TodoId(BaseModel):
    id: int = Field(..., gt=0)