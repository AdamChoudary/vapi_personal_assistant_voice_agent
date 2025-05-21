from operator import eq
from typing import Any, Generic, List, Type, TypeVar
from sqlalchemy.orm import Session
from fastapi import HTTPException
import logging

from src.models.base import Base

T = TypeVar('T', bound=Base)

logger = logging.getLogger(__name__)

class BaseRepository(Generic[T]):
    def __init__(self, db: Session, model: Type[T]):
        self.db = db
        self.model = model
    
    async def get_by_id(self, entity_id: int) -> T:
        entity: Any | None = self.db.query(self.model).filter(eq(self.model.id, entity_id)).first()
        
        if not entity:
            logger.warning(f"{self.model.__name__} with id {entity_id} not found")
            raise HTTPException(status_code=404, detail=f"{self.model.__name__} not found")
            
        return entity
    
    async def get_all(self) -> List[T]:
        try:
            entities = self.db.query(self.model).all()
            return entities
        except Exception as e:
            logger.error(f"Error retrieving {self.model.__name__} entities: {str(e)}")
            raise
    
    async def save(self, entity: T) -> T:
        try:
            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)
            
            logger.info(f"Created {self.model.__name__} with id {entity.id}")
            return entity
        except Exception as e:
            logger.error(f"Error creating {self.model.__name__}: {str(e)}")
            self.db.rollback()
            raise
    
    async def delete(self, entity_id: int) -> None:
        try:
            entity = await self.get_by_id(entity_id)
            self.db.delete(entity)
            self.db.commit()
            
            logger.info(f"Deleted {self.model.__name__} with id {entity_id}")
        except Exception as e:
            logger.error(f"Error deleting {self.model.__name__}: {str(e)}")
            self.db.rollback()
            raise
