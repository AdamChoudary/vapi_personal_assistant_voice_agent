import datetime as dt
from typing import Optional
from pydantic import BaseModel, Field

class CalendarEventBase(BaseModel):
    title: str = Field(..., min_length=1)
    description: Optional[str] = Field(None)
    event_from: dt.datetime = Field(...)
    event_to: dt.datetime = Field(...)

class CalendarEventCreate(CalendarEventBase):
    pass

class CalendarEventResponse(CalendarEventBase):
    id: int

    class Config:
        from_attributes = True

class CalendarEventId(BaseModel):
    id: int = Field(..., gt=0)