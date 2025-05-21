import logging

from sqlalchemy import inspect
from src.models.base import Base, engine

logger = logging.getLogger(__name__)

def create_tables():
    Base.metadata.create_all(bind=engine)
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    logger.info(f"Tables in database: {tables}")