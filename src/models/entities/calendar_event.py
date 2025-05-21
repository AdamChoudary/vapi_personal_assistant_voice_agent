from sqlalchemy import Column, Integer, String, DateTime
from src.models.base import Base

class CalendarEvent(Base):
    __tablename__ = 'calendar_events'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    event_from = Column(DateTime)
    event_to = Column(DateTime)