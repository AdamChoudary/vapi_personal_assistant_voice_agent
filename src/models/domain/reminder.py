from pydantic import BaseModel, Field

class ReminderBase(BaseModel):
    reminder_text: str = Field(..., min_length=1)
    importance: str = Field(..., min_length=1)

class ReminderCreate(ReminderBase):
    pass

class ReminderResponse(ReminderBase):
    id: int

    class Config:
        from_attributes = True

class ReminderId(BaseModel):
    id: int = Field(..., gt=0)