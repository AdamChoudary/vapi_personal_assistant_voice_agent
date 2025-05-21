from sqlalchemy import Column, Integer, String
from src.models.base import Base

class Reminder(Base):
    __tablename__ = 'reminders'
    id = Column(Integer, primary_key=True, index=True)
    reminder_text = Column(String)
    importance = Column(String)